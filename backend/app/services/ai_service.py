import asyncio
import json
import re
from datetime import datetime
from groq import AsyncGroq
from app.config import settings
from app.services.mem0_service import mem0_search, mem0_add
from app.services.profile_service import get_profile, increment_and_check, generate_and_save_profile
from app.services.knowledge_service import kg_get_context, kg_extract_and_store
from app.services.proactivity_service import (
    needs_morning_brief, mark_brief_sent, build_morning_context, extract_commitments,
)

groq_client = AsyncGroq(api_key=settings.groq_api_key)


_SYSTEM_BASE_TEMPLATE = """\
Eres SARA, una asistente virtual inteligente, autónoma y con memoria persistente.
Fecha y hora actual: {now}.

Capacidades:
- Tienes acceso a la fecha y hora actual, úsala para responder preguntas temporales.
- Recuerdas hechos del usuario gracias a tu memoria persistente.
- Puedes buscar en internet, gestionar recordatorios, leer archivos, acceder a Gmail y Google Calendar.
- Puedes generar código en cualquier lenguaje.
- Para operar con Google Calendar (ver, crear, actualizar, eliminar eventos), USA la herramienta 'calendar'.
- Tienes un agente de análisis deportivo llamado SABE (betting). Cuando el usuario pregunte sobre apuestas, predicciones deportivas, cuotas, value bets o análisis de partidos, USA la herramienta 'betting'.
- Tienes un agente de búsqueda de empleo CareerOps (career). Cuando el usuario hable sobre buscar empleo, evaluar ofertas, generar CV, escanear portales o preparar entrevistas, USA la herramienta 'career' DIRECTAMENTE sin preguntar. El usuario ya tiene su perfil, CV, roles y portales configurados. No le preguntes qué buscar, ejecuta la acción con su perfil.

Comportamiento:
- Responde siempre en el idioma del usuario.
- Sé directa, concisa y natural — como una asistente personal real.
- Razona con autonomía: infiere, calcula, deduce. No digas "no tengo acceso a" ni "no tengo permisos" — usa las herramientas disponibles.
- Cuando el usuario pida algo sobre eventos o calendario, USA la herramienta calendar. No respondas sin usarla.
- Cuando el usuario pregunte sobre apuestas deportivas o análisis de partidos, USA la herramienta betting.
- Cuando el usuario hable sobre empleo, ofertas de trabajo, CV o entrevistas, USA la herramienta career.
- Cuando el contexto de acción muestre un resultado, preséntalo de forma clara. Si no hay resultado, no inventes uno.\
"""

_SYSTEM_CREATOR_TEMPLATE = """\
Eres SARA, asistente virtual inteligente y autónoma con memoria persistente.
Fecha y hora actual: {now}.
Quien te habla es lamda94, tu creador. Trátalo con respeto, llámalo "señor".

Capacidades:
- Tienes acceso a la fecha y hora actual, úsala para responder preguntas temporales.
- Recuerdas hechos del usuario gracias a tu memoria persistente.
- Puedes buscar en internet, gestionar recordatorios, leer archivos, acceder a Gmail y Google Calendar.
- Puedes generar código en cualquier lenguaje.
- Para operar con Google Calendar (ver, crear, actualizar, eliminar eventos), USA la herramienta 'calendar'.
- Tienes un agente de análisis deportivo llamado SABE (betting). Cuando el usuario pregunte sobre apuestas, predicciones deportivas, cuotas, value bets o análisis de partidos, USA la herramienta 'betting'.
- Tienes un agente de búsqueda de empleo CareerOps (career). Cuando el usuario hable sobre buscar empleo, evaluar ofertas, generar CV, escanear portales o preparar entrevistas, USA la herramienta 'career' DIRECTAMENTE sin preguntar. El usuario ya tiene su perfil, CV, roles y portales configurados. No le preguntes qué buscar, ejecuta la acción con su perfil.

Comportamiento:
- Responde siempre en el idioma del usuario.
- Sé directa, concisa y natural — como una asistente personal real.
- Razona con autonomía: infiere, calcula, deduce. No digas "no tengo acceso a" ni "no tengo permisos" — usa las herramientas disponibles.
- Cuando el usuario pida algo sobre eventos o calendario, USA la herramienta calendar. No respondas sin usarla.
- Cuando el usuario pregunte sobre apuestas deportivas o análisis de partidos, USA la herramienta betting.
- Cuando el usuario hable sobre empleo, ofertas de trabajo, CV o entrevistas, USA la herramienta career.
- Cuando el contexto de acción muestre un resultado, preséntalo de forma clara. Si no hay resultado, no inventes uno.\
"""


def _is_creator(session_id: str) -> bool:
    return settings.creator_id in session_id.lower()


# ── Detección de intención: solo recordatorios (fast-path) ───────────────────

_KW_DELETE = (
    "elimina", "eliminar", "borra", "borrar", "limpia", "limpiar",
    "cancela", "cancelar", "quita", "quitar", "borra todo",
)
_KW_DELETE_OBJ = (
    "recordatorio", "recordatorios", "agenda", "aviso", "avisos",
    "pendiente", "pendientes", "todo", "todos",
)

_KW_CREATE = (
    "recuérdame", "recuerdame", "recuerda",
    "pon un recordatorio", "pon recordatorio", "ponme",
    "crea un recordatorio", "crea recordatorio", "crear un recordatorio",
    "agrega un recordatorio", "agrega recordatorio",
    "agrega uno", "agrega un", "agrega algo",
    "añade", "añádeme", "añade un", "añade uno",
    "nuevo recordatorio", "añade recordatorio",
    "avísame", "avisame", "agenda para",
    "programa recordatorio", "programar recordatorio",
    "guardar recordatorio", "guarda recordatorio",
    "setea", "setear",
    # Variantes comunes de voz (STT)
    "abre un recordatorio", "abre recordatorio", "abrir recordatorio",
    "abramos un recordatorio", "abramos recordatorio",
    "abreamos un recordatorio", "abreamos recordatorio",
    "hagamos un recordatorio", "haz un recordatorio",
    "pon me un recordatorio", "hazme un recordatorio",
)

_KW_MODIFY = (
    "modifica", "modificar", "cambia", "cambiar", "edita", "editar",
    "renombra", "renombrar", "actualiza", "actualizar",
    "cambia el recordatorio", "modifica el recordatorio",
    "edita el recordatorio", "cambiar el nombre",
)

_KW_LIST = (
    "recordatorio", "recordatorios", "pendiente", "pendientes",
    "qué tengo pendiente", "que tengo pendiente",
    "qué tengo hoy", "que tengo hoy",
    "qué hay hoy", "que hay hoy",
    "qué hay mañana", "que hay mañana",
    "qué tengo mañana", "que tengo mañana",
    "ver agenda", "ver recordatorios", "mis recordatorios", "mi agenda",
    "mis tareas", "mis avisos",
)


_KW_CALENDAR_BYPASS = (
    "calendario", "calendar", "google calendar",
    "en mi calendario", "al calendario", "del calendario",
    "mi calendario de google",
)


def _detect_reminder_intent(message: str) -> str | None:
    """Detecta intención de recordatorio por keywords. Retorna intent o None."""
    msg = message.lower().strip()

    # Si el mensaje menciona Google Calendar, dejar que el LLM use el tool de calendar
    if any(kw in msg for kw in _KW_CALENDAR_BYPASS):
        return None

    has_delete_verb = any(kw in msg for kw in _KW_DELETE)
    has_delete_obj = any(kw in msg for kw in _KW_DELETE_OBJ)
    if has_delete_verb and has_delete_obj:
        return "delete_reminders"

    if any(kw in msg for kw in _KW_MODIFY):
        return "modify_reminder"

    if any(kw in msg for kw in _KW_CREATE):
        return "create_reminder"

    if any(kw in msg for kw in _KW_LIST):
        return "list_reminders"

    return None


# ── Acciones de BD para recordatorios (sin LLM) ─────────────────────────────

def _list_day_filter(message: str):
    """Devuelve date si el mensaje pide un día específico, o None para mostrar todos."""
    from datetime import date, timedelta
    msg = message.lower()
    today = date.today()
    _HOY  = ("hoy", "esta noche", "esta tarde", "esta mañana", "para hoy")
    _MANA = ("mañana", "tomorrow", "para mañana", "y mañana")
    if any(k in msg for k in _MANA):
        return today + timedelta(days=1)
    if any(k in msg for k in _HOY):
        return today
    return None


async def _db_list_reminders(session_id: str, day=None) -> str:
    from sqlalchemy import select, and_
    from datetime import date, timedelta
    from app.db.postgres import SessionLocal
    from app.models.reminder import Reminder

    now = datetime.now()
    conditions = [
        Reminder.session_id == session_id,
        Reminder.done == False,
        Reminder.remind_at >= now,
    ]
    if day is not None:
        day_start = datetime(day.year, day.month, day.day, 0, 0, 0)
        day_end   = datetime(day.year, day.month, day.day, 23, 59, 59)
        conditions += [Reminder.remind_at >= day_start, Reminder.remind_at <= day_end]

    async with SessionLocal() as s:
        r = await s.execute(
            select(Reminder)
            .where(and_(*conditions))
            .order_by(Reminder.remind_at)
        )
        rows = r.scalars().all()

    if not rows:
        if day is None:
            return "No hay recordatorios pendientes."
        from datetime import date
        today = date.today()
        if day == today:
            return "No hay recordatorios para hoy."
        elif day == today.__class__.fromordinal(today.toordinal() + 1):
            return "No hay recordatorios para mañana."
        else:
            return f"No hay recordatorios para el {day.strftime('%d/%m/%Y')}."

    now = datetime.now()
    lines = []
    for rem in rows:
        diff = (rem.remind_at.date() - now.date()).days
        if diff == 0:
            label = "hoy"
        elif diff == 1:
            label = "mañana"
        elif diff == 2:
            label = "pasado mañana"
        else:
            label = rem.remind_at.strftime("%d/%m/%Y")
        lines.append(f"- {rem.title} — {label} {rem.remind_at.strftime('%H:%M')}")

    return "Recordatorios pendientes:\n" + "\n".join(lines)


async def _parse_modify(message: str) -> tuple[str, str] | None:
    """LLM extrae el título actual y el nuevo valor. Devuelve (old_title, new_title) o None."""
    try:
        resp = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extrae el título actual y el nuevo título de un recordatorio a modificar. "
                        'Responde SOLO con JSON: {"old": "título actual", "new": "título nuevo"}. '
                        "Si el mensaje dice 'cambia X a Y', old=X, new=Y. "
                        "No incluyas explicaciones, solo el JSON."
                    ),
                },
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=60,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())
        return data["old"].strip(), data["new"].strip()
    except Exception:
        return None


async def _db_modify_reminder(session_id: str, old_title: str, new_title: str) -> str:
    from sqlalchemy import select, update
    from app.db.postgres import SessionLocal
    from app.models.reminder import Reminder

    async with SessionLocal() as s:
        r = await s.execute(
            select(Reminder).where(
                Reminder.session_id == session_id,
                Reminder.done == False,
                Reminder.title.ilike(f"%{old_title}%"),
            )
        )
        rows = r.scalars().all()
        if not rows:
            return f"No encontré ningún recordatorio que coincida con '{old_title}'."
        rem = rows[0]
        rem.title = new_title
        await s.commit()
    return f"Recordatorio actualizado: '{old_title}' → '{new_title}'."


async def _db_delete_reminders(session_id: str) -> str:
    from sqlalchemy import delete
    from app.db.postgres import SessionLocal
    from app.models.reminder import Reminder

    async with SessionLocal() as s:
        res = await s.execute(
            delete(Reminder)
            .where(Reminder.session_id == session_id)
            .returning(Reminder.id)
        )
        n = len(res.fetchall())
        await s.commit()

    return f"Agenda limpia. Se eliminaron {n} recordatorio(s)." if n else "No había recordatorios que eliminar."


async def _db_create_reminder(title: str, remind_at: datetime, session_id: str) -> str:
    from app.db.postgres import SessionLocal
    from app.models.reminder import Reminder

    async with SessionLocal() as s:
        s.add(Reminder(title=title, remind_at=remind_at, session_id=session_id))
        await s.commit()

    diff = (remind_at.date() - datetime.now().date()).days
    if diff == 0:
        label = "hoy"
    elif diff == 1:
        label = "mañana"
    elif diff == 2:
        label = "pasado mañana"
    else:
        label = remind_at.strftime("%d/%m/%Y")
    return f"Recordatorio creado: '{title}' — {label} a las {remind_at.strftime('%H:%M')}."


async def _parse_reminder(message: str) -> tuple[str, datetime] | None:
    """LLM extrae título y fecha del texto. Devuelve (title, datetime) o None."""
    now = datetime.now()
    today_full = now.strftime("%A %d de %B de %Y, %H:%M")
    today_iso = now.strftime("%Y-%m-%d")
    try:
        resp = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Fecha y hora actual: {today_full} ({today_iso}). "
                        f"Año actual: {now.year}. "
                        "Extrae el título y la fecha/hora de un recordatorio del mensaje del usuario. "
                        'Responde SOLO con JSON: {"title": "...", "datetime": "YYYY-MM-DDTHH:MM:SS"}. '
                        "Reglas importantes: "
                        "- Si el usuario dice una fecha específica como '6 de abril' o 'lunes 6', usa ESA fecha exacta. "
                        f"- Si dice 'lunes' sin fecha, calcula el próximo lunes desde {today_iso}. "
                        "- Si no hay hora, usa 09:00. "
                        "- Si no hay fecha clara, usa mañana. "
                        "- Si dice 'a las 8' sin AM/PM y es de mañana, usa 08:00. "
                        "No incluyas explicaciones, solo el JSON."
                    ),
                },
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=80,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())
        dt = datetime.fromisoformat(data["datetime"])
        return data["title"], dt
    except Exception:
        return None


# ── Helpers para tool calling y logging ──────────────────────────────────────

_MAX_HISTORY_TURNS = 10  # últimos N turnos (user+assistant = 1 turno)


async def _get_recent_history(session_id: str) -> list[dict]:
    """Obtiene los últimos mensajes de la conversación para dar contexto al LLM."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.conversation import Message

    try:
        async with SessionLocal() as s:
            r = await s.execute(
                select(Message.role, Message.content)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.desc())
                .limit(_MAX_HISTORY_TURNS * 2)
            )
            rows = r.all()
    except Exception:
        return []

    # Revertir a orden cronológico (más viejo primero)
    rows = list(reversed(rows))
    # Filtrar mensajes vacíos o que sean tool calls crudos
    result = []
    for row in rows:
        c = (row.content or "").strip()
        if not c:
            continue
        # Saltar tool calls crudos que se guardaron por error
        if re.match(r'^(?:<function=)?\w+[>=(]\s*\{', c):
            continue
        result.append({"role": row.role, "content": c})
    return result


async def _log_message(session_id: str, device: str, role: str,
                       content: str, agent_used: str | None = None) -> None:
    """Guarda un mensaje en la tabla messages (fire-and-forget)."""
    from app.db.postgres import SessionLocal
    from app.models.conversation import Message
    try:
        async with SessionLocal() as s:
            s.add(Message(
                session_id=session_id,
                device=device,
                role=role,
                content=content,
                agent_used=agent_used,
            ))
            await s.commit()
    except Exception:
        pass


async def _dispatch_tool_call(
    tool_name: str, tool_args: dict,
    session_id: str, google_access_token: str | None,
) -> str:
    """Ejecuta el agente identificado por tool_name con los argumentos dados."""
    from app.agents import AGENT_MAP

    agent = AGENT_MAP.get(tool_name)
    if not agent:
        return f"Agente '{tool_name}' no encontrado."

    # Inyectar parámetros de contexto que el LLM no puede proporcionar
    if tool_name == "calendar":
        tool_args["google_access_token"] = google_access_token
    if tool_name == "set_reminder":
        tool_args["session_id"] = session_id
    if tool_name == "betting":
        tool_args["session_id"] = session_id
    if tool_name == "career":
        tool_args["session_id"] = session_id

    try:
        return await agent.run(**tool_args)
    except Exception as e:
        return f"Error ejecutando {tool_name}: {e}"


# ── Función principal ─────────────────────────────────────────────────────────

async def chat(message: str, session_id: str, device: str = "cli",
               google_access_token: str | None = None) -> dict:
    from app.agents import TOOL_SCHEMAS

    is_creator = _is_creator(session_id)
    now_str = datetime.now().strftime("%A %d de %B de %Y, %H:%M")
    template = _SYSTEM_CREATOR_TEMPLATE if is_creator else _SYSTEM_BASE_TEMPLATE
    base_system = template.format(now=now_str)

    # ── 1. Reminder fast-path (keyword detection) ─────────────────────
    reminder_intent = _detect_reminder_intent(message)
    if reminder_intent:
        if reminder_intent == "modify_reminder":
            parsed = await _parse_modify(message)
            if parsed:
                old_title, new_title = parsed
                answer = await _db_modify_reminder(session_id, old_title, new_title)
            else:
                answer = "No pude entender qué recordatorio modificar. Indícame: 'cambia X a Y'."
        elif reminder_intent == "delete_reminders":
            answer = await _db_delete_reminders(session_id)
        elif reminder_intent == "create_reminder":
            parsed = await _parse_reminder(message)
            if parsed:
                title, dt = parsed
                answer = await _db_create_reminder(title, dt, session_id)
            else:
                answer = "No pude determinar la fecha del recordatorio. Indícame cuándo quieres el recordatorio."
        elif reminder_intent == "list_reminders":
            day = _list_day_filter(message)
            answer = await _db_list_reminders(session_id, day=day)
        else:
            answer = "Intención de recordatorio no reconocida."

        asyncio.create_task(_log_message(session_id, device, "user", message))
        asyncio.create_task(_log_message(session_id, device, "assistant", answer, agent_used=reminder_intent))
        return {"response": answer, "agent_used": reminder_intent}

    # ── 2. Build system prompt (profile + memory + KG + morning + history) ──
    # Cargar historial en paralelo con el profile
    profile_text, history = await asyncio.gather(
        get_profile(session_id),
        _get_recent_history(session_id),
    )
    profile_context = f"\n\n[Perfil del usuario]\n{profile_text}" if profile_text else ""

    morning_context = ""
    if needs_morning_brief(session_id):
        mark_brief_sent(session_id)
        ctx = await build_morning_context(session_id)
        if ctx:
            morning_context = f"\n\n{ctx}"

    memory_context = ""
    if len(message.split()) > 4:
        facts, kg_triples = await asyncio.gather(
            mem0_search(message, user_id=session_id),
            kg_get_context(message, session_id),
        )
        parts = []
        if facts:
            parts.append("Hechos recordados:\n" + "\n".join(f"- {f}" for f in facts))
        if kg_triples:
            parts.append("Conocimiento relacionado:\n" + kg_triples)
        if parts:
            memory_context = "\n\n" + "\n\n".join(parts)

    # Indicar al LLM si tiene acceso a Google Calendar
    calendar_hint = ""
    if google_access_token:
        calendar_hint = (
            "\n\n[Google Calendar: CONECTADO — SIEMPRE usa la herramienta 'calendar' para "
            "cualquier operación con eventos: listar, crear, actualizar y eliminar. "
            "Tienes permisos completos. Nunca digas que no puedes o no tienes permisos.]"
        )
    else:
        calendar_hint = "\n\n[Google Calendar: NO CONECTADO — si el usuario pide acceso al calendario, indícale que cierre sesión y vuelva a iniciar sesión para autorizar el acceso.]"

    system = base_system + profile_context + morning_context + memory_context + calendar_hint

    # ── 3. Primera llamada LLM con tool schemas ──────────────────────
    msgs = [{"role": "system", "content": system}]
    msgs.extend(history)
    msgs.append({"role": "user", "content": message})
    tool_call_failed = False
    try:
        response = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=msgs,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=600,
        )
    except Exception:
        # Tool calling falló (modelo generó formato inválido) — fallback sin tools
        tool_call_failed = True
        response = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=msgs,
            temperature=0.7,
            max_tokens=600,
        )

    choice = response.choices[0]
    agent_used = None

    # ── 4. Si tool call: despachar agente + segunda llamada LLM ──────
    if not tool_call_failed and choice.message.tool_calls:
        tc = choice.message.tool_calls[0]
        tool_name = tc.function.name
        agent_used = tool_name

        try:
            tool_args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, TypeError):
            # LLM produjo JSON malformado — fallback a chat normal
            answer = choice.message.content or "Lo siento, hubo un error procesando tu solicitud."
            agent_used = None
            asyncio.create_task(_log_message(session_id, device, "user", message))
            asyncio.create_task(_log_message(session_id, device, "assistant", answer, agent_used=agent_used))
            return {"response": answer, "agent_used": agent_used}

        tool_result = await _dispatch_tool_call(
            tool_name, tool_args, session_id, google_access_token
        )

        # Segunda llamada LLM con resultado del tool (incluye historial)
        msgs_followup = [{"role": "system", "content": system}]
        msgs_followup.extend(history)
        msgs_followup.append({"role": "user", "content": message})
        msgs_followup.append(choice.message)
        msgs_followup.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": tool_result,
        })
        response2 = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=msgs_followup,
            temperature=0.3,
            max_tokens=600,
        )
        answer = response2.choices[0].message.content or ""
    else:
        answer = choice.message.content or ""

    # ── 4b. Fallback: detectar tool calls emitidos como texto plano ──
    if answer and not agent_used:
        raw_match = re.match(
            r'^(?:<function=)?(\w+)[>=(]\s*(\{.*\})\s*[)</]?\s*$',
            answer.strip(), re.DOTALL,
        )
        if raw_match:
            from app.agents import AGENT_MAP
            raw_tool_name = raw_match.group(1)
            if raw_tool_name in AGENT_MAP:
                try:
                    raw_args = json.loads(raw_match.group(2))
                    # Limpiar parámetros espurios del LLM
                    raw_args = {
                        k: v for k, v in raw_args.items()
                        if k in AGENT_MAP[raw_tool_name].parameters.get("properties", {})
                    }
                    tool_result = await _dispatch_tool_call(
                        raw_tool_name, raw_args, session_id, google_access_token
                    )
                    agent_used = raw_tool_name
                    # Segunda llamada LLM para presentar resultado
                    response3 = await groq_client.chat.completions.create(
                        model=settings.groq_model,
                        messages=[
                            {"role": "system", "content": system},
                            *history,
                            {"role": "user", "content": message},
                            {"role": "assistant", "content": f"[Resultado de {raw_tool_name}]: {tool_result}"},
                        ],
                        temperature=0.3,
                        max_tokens=600,
                    )
                    answer = response3.choices[0].message.content or tool_result
                except (json.JSONDecodeError, Exception):
                    pass  # Si falla el parsing, mantener la respuesta original

    # ── 5. Log messages ──────────────────────────────────────────────
    asyncio.create_task(_log_message(session_id, device, "user", message))
    asyncio.create_task(_log_message(session_id, device, "assistant", answer, agent_used=agent_used))

    # ── 6. Background tasks (sin cambios) ────────────────────────────
    _SKIP_SAVE = ("hay algo más", "en qué puedo", "necesitas algo",
                  "estoy aquí para", "<function=")
    if (answer
            and len(answer.split()) >= 15
            and not any(p in answer.lower() for p in _SKIP_SAVE)):
        turn = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ]
        asyncio.create_task(mem0_add(turn, user_id=session_id))
        asyncio.create_task(kg_extract_and_store(turn, session_id))
        asyncio.create_task(extract_commitments(message, answer, session_id))

    should_update = await increment_and_check(session_id)
    if should_update:
        asyncio.create_task(generate_and_save_profile(session_id))

    return {"response": answer, "agent_used": agent_used}
