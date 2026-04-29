"""
ProactivityService — Fase 5.2

Motor de proactividad completo:
- Morning brief enriquecido (recordatorios + compromisos + resumen de ayer + temas inactivos)
- Extracción automática de compromisos de cada conversación
- Triggers proactivos: compromisos vencidos, inactividad del usuario
- Generación de mensajes push naturales
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional

from app.services.llm import llm_client, LLM_MODEL
from sqlalchemy import select, func as sa_func, and_

from app.config import settings
from app.db.postgres import SessionLocal
from app.models.proactive_insight import ProactiveInsight

logger = logging.getLogger(__name__)
# llm_client importado desde app.services.llm

# Registro en memoria de la última vez que se generó el brief por sesión
_last_brief: dict[str, date] = {}


# ── Morning brief (existente, mejorado) ─────────────────────────────────────

def needs_morning_brief(session_id: str) -> bool:
    """True si es la primera interacción del día para esta sesión."""
    today = date.today()
    return _last_brief.get(session_id) != today


def mark_brief_sent(session_id: str) -> None:
    _last_brief[session_id] = date.today()


async def get_pending_reminders(session_id: str) -> list[str]:
    """Devuelve recordatorios pendientes para hoy y mañana."""
    from app.models.reminder import Reminder

    now = datetime.now()
    tomorrow_end = datetime(now.year, now.month, now.day, 23, 59, 59) + timedelta(days=1)

    async with SessionLocal() as s:
        r = await s.execute(
            select(Reminder)
            .where(
                Reminder.session_id == session_id,
                Reminder.done == False,                  # noqa: E712
                Reminder.remind_at >= now,
                Reminder.remind_at <= tomorrow_end,
            )
            .order_by(Reminder.remind_at)
        )
        rows = r.scalars().all()

    result = []
    for rem in rows:
        diff = (rem.remind_at.date() - now.date()).days
        label = "hoy" if diff == 0 else "mañana"
        result.append(f"{rem.title} ({label} {rem.remind_at.strftime('%H:%M')})")
    return result


async def get_pending_commitments(session_id: str) -> list[str]:
    """Devuelve compromisos pendientes para los próximos 3 días."""
    now = datetime.now()
    limit = now + timedelta(days=3)

    async with SessionLocal() as s:
        r = await s.execute(
            select(ProactiveInsight)
            .where(
                ProactiveInsight.session_id == session_id,
                ProactiveInsight.insight_type == "commitment",
                ProactiveInsight.dismissed == False,       # noqa: E712
                ProactiveInsight.due_date != None,         # noqa: E711
                ProactiveInsight.due_date <= limit,
            )
            .order_by(ProactiveInsight.due_date)
        )
        rows = r.scalars().all()

    result = []
    for ins in rows:
        diff = (ins.due_date.date() - now.date()).days
        if diff < 0:
            label = "vencido"
        elif diff == 0:
            label = "hoy"
        elif diff == 1:
            label = "mañana"
        else:
            label = ins.due_date.strftime("%d/%m")
        result.append(f"{ins.content} ({label})")
    return result


async def get_yesterday_summary(session_id: str) -> Optional[str]:
    """Busca el resumen diario de ayer generado por consolidación en Mem0."""
    try:
        from app.services.mem0_service import mem0_get_all
        all_facts = await mem0_get_all(user_id=session_id)

        yesterday = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        tag = f"[Resumen {yesterday}]"

        for f in all_facts:
            memory = f.get("memory", "")
            if tag in memory:
                return memory.replace(tag, "").strip()
        return None
    except Exception as e:
        logger.warning(f"get_yesterday_summary error: {e}")
        return None


async def detect_inactive_topics(session_id: str) -> list[str]:
    """
    Busca en Mem0 temas/proyectos mencionados en los últimos 30 días
    que no aparecen en los últimos 5 días — posibles puntos de seguimiento.
    """
    try:
        from app.services.mem0_service import mem0_get_all
        all_facts = await mem0_get_all(user_id=session_id)

        today = date.today()
        recent_cutoff = today - timedelta(days=5)
        old_cutoff = today - timedelta(days=30)

        recent_facts: list[str] = []
        older_facts: list[str] = []

        for f in all_facts:
            created_raw = f.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_raw[:10]).date()
            except Exception:
                continue
            content = f.get("memory", "")
            if not content:
                continue
            if created >= recent_cutoff:
                recent_facts.append(content)
            elif created >= old_cutoff:
                older_facts.append(content)

        if not older_facts:
            return []

        recent_text = "\n".join(f"- {f}" for f in recent_facts[:20]) or "(ninguno reciente)"
        older_text = "\n".join(f"- {f}" for f in older_facts[:20])

        resp = await llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analiza dos listas de hechos de memoria de un usuario. "
                        "Identifica hasta 3 temas, proyectos o pendientes que aparecen en "
                        "la lista ANTIGUA pero NO en la lista RECIENTE — son candidatos para seguimiento. "
                        "Responde SOLO con una lista de frases cortas (máx. 10 palabras cada una), "
                        "una por línea. Si no hay candidatos claros, responde 'ninguno'."
                    ),
                },
                {
                    "role": "user",
                    "content": f"RECIENTE (últimos 5 días):\n{recent_text}\n\nANTIGUO (últimos 30 días):\n{older_text}",
                },
            ],
            temperature=0,
            max_tokens=120,
        )
        raw = resp.choices[0].message.content.strip()
        if "ninguno" in raw.lower():
            return []
        return [line.lstrip("- ").strip() for line in raw.splitlines() if line.strip()]
    except Exception as e:
        logger.warning(f"detect_inactive_topics error: {e}")
        return []


async def build_morning_context(session_id: str) -> Optional[str]:
    """
    Genera el bloque de contexto matutino para inyectar en el system prompt.
    Incluye: recordatorios, compromisos pendientes, resumen de ayer, temas inactivos.
    Devuelve None si no hay nada relevante que añadir.
    """
    import asyncio
    reminders, commitments, yesterday, topics = await asyncio.gather(
        get_pending_reminders(session_id),
        get_pending_commitments(session_id),
        get_yesterday_summary(session_id),
        detect_inactive_topics(session_id),
    )

    parts: list[str] = []

    if reminders:
        parts.append("Recordatorios próximos:\n" + "\n".join(f"- {r}" for r in reminders))

    if commitments:
        parts.append("Compromisos pendientes:\n" + "\n".join(f"- {c}" for c in commitments))

    if yesterday:
        parts.append(f"Resumen de ayer:\n- {yesterday}")

    if topics:
        parts.append(
            "Temas sin actividad reciente (posible seguimiento):\n"
            + "\n".join(f"- {t}" for t in topics)
        )

    if not parts:
        return None

    block = "\n\n".join(parts)
    return (
        "[Contexto matutino — primer uso del día]\n"
        + block
        + "\n\nSi es natural dentro de la respuesta, menciona brevemente alguno de estos puntos."
    )


# ── Extracción de compromisos ────────────────────────────────────────────────

async def extract_commitments(
    user_msg: str, assistant_msg: str, session_id: str
) -> None:
    """
    Analiza un turno de conversación y extrae compromisos del usuario.
    Se ejecuta como background task tras cada chat.
    """
    if len(user_msg.split()) < 5:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        resp = await llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Hoy es {today}. "
                        "Analiza esta conversación y extrae compromisos o promesas del USUARIO "
                        "(cosas que dijo que haría, plazos que mencionó, tareas que se propuso). "
                        "NO incluyas cosas que el asistente ofreció hacer. "
                        "Responde SOLO con un JSON array: "
                        '[{"content": "descripción breve", "due_date": "YYYY-MM-DD"}]. '
                        "Si no hay fecha clara, usa null en due_date. "
                        "Si no hay compromisos, responde exactamente: []"
                    ),
                },
                {
                    "role": "user",
                    "content": f"USUARIO: {user_msg}\nASISTENTE: {assistant_msg}",
                },
            ],
            temperature=0,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()

        # Extraer JSON del response
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        if not items:
            return

        async with SessionLocal() as s:
            for item in items:
                content = item.get("content", "").strip()
                if not content:
                    continue
                due_raw = item.get("due_date")
                due_date = None
                if due_raw:
                    try:
                        due_date = datetime.fromisoformat(due_raw)
                    except (ValueError, TypeError):
                        pass

                s.add(ProactiveInsight(
                    session_id=session_id,
                    insight_type="commitment",
                    content=content,
                    source_message=user_msg[:500],
                    due_date=due_date,
                ))
            await s.commit()
            logger.info(f"Extraídos {len(items)} compromiso(s) para {session_id}")

    except Exception as e:
        logger.warning(f"extract_commitments error: {e}")


# ── Motor de triggers proactivos ────────────────────────────────────��────────

async def check_proactive_triggers(session_id: str) -> list[dict]:
    """
    Revisa triggers proactivos para un usuario.
    Retorna lista de dicts con insights a notificar.
    """
    from app.models.conversation import Message

    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    insights: list[dict] = []

    async with SessionLocal() as s:
        # Rate limit: contar pushes enviados hoy
        count_r = await s.execute(
            select(sa_func.count(ProactiveInsight.id)).where(
                ProactiveInsight.session_id == session_id,
                ProactiveInsight.notified == True,          # noqa: E712
                ProactiveInsight.created_at >= today_start,
            )
        )
        pushes_today = count_r.scalar() or 0
        if pushes_today >= settings.proactive_max_daily_pushes:
            return []

        # 1. Compromisos vencidos o del día
        r = await s.execute(
            select(ProactiveInsight).where(
                ProactiveInsight.session_id == session_id,
                ProactiveInsight.insight_type == "commitment",
                ProactiveInsight.dismissed == False,         # noqa: E712
                ProactiveInsight.notified == False,          # noqa: E712
                ProactiveInsight.due_date != None,           # noqa: E711
                ProactiveInsight.due_date <= now,
            )
        )
        due_commitments = r.scalars().all()
        for c in due_commitments:
            insights.append({
                "id": c.id,
                "type": "commitment",
                "content": c.content,
            })

        # 2. Inactividad del usuario
        last_msg_r = await s.execute(
            select(Message.created_at)
            .where(
                Message.session_id == session_id,
                Message.role == "user",
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg_row = last_msg_r.scalar_one_or_none()
        if last_msg_row:
            hours_since = (now - last_msg_row).total_seconds() / 3600
            if hours_since >= settings.proactive_inactivity_hours:
                # Verificar que no hemos enviado inactividad recientemente
                inact_r = await s.execute(
                    select(ProactiveInsight).where(
                        ProactiveInsight.session_id == session_id,
                        ProactiveInsight.insight_type == "inactivity",
                        ProactiveInsight.created_at >= now - timedelta(days=2),
                    )
                )
                if not inact_r.scalars().first():
                    # Crear insight de inactividad
                    inact = ProactiveInsight(
                        session_id=session_id,
                        insight_type="inactivity",
                        content=f"Sin interacción en {int(hours_since)} horas",
                    )
                    s.add(inact)
                    await s.flush()
                    insights.append({
                        "id": inact.id,
                        "type": "inactivity",
                        "content": inact.content,
                    })
                    await s.commit()

    return insights


async def generate_proactive_message(session_id: str, insights: list[dict]) -> str:
    """Genera un mensaje push natural y breve a partir de los insights."""
    items = "\n".join(f"- [{i['type']}] {i['content']}" for i in insights)
    try:
        resp = await llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres SARA, una asistente virtual amigable. "
                        "Genera un mensaje push corto (máximo 2 frases) y natural "
                        "basado en los siguientes puntos de seguimiento del usuario. "
                        "Sé breve, cálida y no intrusiva. No uses emojis excesivos. "
                        "Responde SOLO con el texto del mensaje."
                    ),
                },
                {"role": "user", "content": f"Puntos de seguimiento:\n{items}"},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"generate_proactive_message error: {e}")
        # Fallback: mensaje simple basado en el primer insight
        first = insights[0]
        if first["type"] == "commitment":
            return f"Recuerda: {first['content']}"
        return "Hace un tiempo que no hablamos. Estoy aquí si necesitas algo."


async def mark_insights_notified(insight_ids: list[str]) -> None:
    """Marca una lista de insights como notificados."""
    if not insight_ids:
        return
    async with SessionLocal() as s:
        for iid in insight_ids:
            r = await s.execute(
                select(ProactiveInsight).where(ProactiveInsight.id == iid)
            )
            ins = r.scalar_one_or_none()
            if ins:
                ins.notified = True
        await s.commit()
