"""
ProactivityService — Fase 5.2

Al primer mensaje del día por sesión:
- Genera un resumen matutino con recordatorios pendientes y puntos de contexto
- Detecta patrones inactivos (temas que no se han tocado en días)

El contexto generado se inyecta en ai_service.chat() como sección adicional
del system prompt, de modo que SARA lo integra de forma natural.
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Optional

from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)
groq_client = AsyncGroq(api_key=settings.groq_api_key)

# Registro en memoria de la última vez que se generó el brief por sesión
# {session_id: date}  — se reinicia al reiniciar el servidor (comportamiento correcto)
_last_brief: dict[str, date] = {}


def needs_morning_brief(session_id: str) -> bool:
    """True si es la primera interacción del día para esta sesión."""
    today = date.today()
    return _last_brief.get(session_id) != today


def mark_brief_sent(session_id: str) -> None:
    _last_brief[session_id] = date.today()


async def get_pending_reminders(session_id: str) -> list[str]:
    """Devuelve recordatorios pendientes para hoy y mañana."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.reminder import Reminder

    now = datetime.now()
    tomorrow_end = datetime(now.year, now.month, now.day, 23, 59, 59) + timedelta(days=1)

    async with SessionLocal() as s:
        r = await s.execute(
            select(Reminder)
            .where(
                Reminder.session_id == session_id,
                Reminder.done == False,
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

        # Pedir al LLM que identifique temas del pasado que no aparecen en lo reciente
        recent_text = "\n".join(f"- {f}" for f in recent_facts[:20]) or "(ninguno reciente)"
        older_text  = "\n".join(f"- {f}" for f in older_facts[:20])

        resp = await groq_client.chat.completions.create(
            model=settings.groq_model,
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
        return [line.lstrip("- •").strip() for line in raw.splitlines() if line.strip()]
    except Exception as e:
        logger.warning(f"detect_inactive_topics error: {e}")
        return []


async def build_morning_context(session_id: str) -> Optional[str]:
    """
    Genera el bloque de contexto matutino para inyectar en el system prompt.
    Devuelve None si no hay nada relevante que añadir.
    """
    reminders, topics = await _gather(session_id)

    parts: list[str] = []

    if reminders:
        parts.append("Recordatorios próximos:\n" + "\n".join(f"- {r}" for r in reminders))

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


async def _gather(session_id: str):
    import asyncio
    return await asyncio.gather(
        get_pending_reminders(session_id),
        detect_inactive_topics(session_id),
    )
