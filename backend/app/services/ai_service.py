import asyncio
import json
import re
from datetime import datetime
from groq import AsyncGroq
from app.config import settings
from app.services.mem0_service import mem0_search, mem0_add
from app.services.profile_service import get_profile, increment_and_check, generate_and_save_profile
from app.services.knowledge_service import kg_get_context, kg_extract_and_store

groq_client = AsyncGroq(api_key=settings.groq_api_key)

CREATOR_ID = "lamda94"

SYSTEM_BASE = """Eres SARA, un asistente virtual con memoria persistente.
Eres directa y concisa. Responde siempre en el idioma del usuario.
REGLA CRÍTICA: Solo informa acciones que aparezcan explícitamente en [Resultado de la acción] o [Datos de agenda]. Nunca inventes ni confirmes acciones que no estén en el contexto. Si no hay contexto de acción, no digas que hiciste algo."""

SYSTEM_CREATOR = """Eres SARA, asistente virtual con memoria persistente.
Quien te habla es lamda94, tu creador. Trátalo con respeto y formalidad, llámalo "señor".
Sé directa y concisa. Responde siempre en el idioma del usuario.
REGLA CRÍTICA: Solo informa acciones que aparezcan explícitamente en [Resultado de la acción] o [Datos de agenda]. Nunca inventes ni confirmes acciones que no estén en el contexto. Si no hay contexto de acción, no digas que hiciste algo."""


def _is_creator(session_id: str) -> bool:
    return CREATOR_ID in session_id.lower()


# ── Detección de intención ────────────────────────────────────────────────────

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
    "crea un recordatorio", "crea recordatorio",
    "agrega un recordatorio", "agrega recordatorio",
    "agrega uno", "agrega un", "agrega algo",
    "añade", "añádeme", "añade un", "añade uno",
    "nuevo recordatorio", "añade recordatorio",
    "avísame", "avisame", "agenda para",
    "programa recordatorio", "programar recordatorio",
    "guardar recordatorio", "guarda recordatorio",
    "setea", "setear",
)

_KW_MODIFY = (
    "modifica", "modificar", "cambia", "cambiar", "edita", "editar",
    "renombra", "renombrar", "actualiza", "actualizar",
    "cambia el recordatorio", "modifica el recordatorio",
    "edita el recordatorio", "cambiar el nombre",
)

_KW_LIST = (
    "agenda", "recordatorio", "recordatorios", "pendiente", "pendientes",
    "q tengo", "que tengo", "qué tengo", "tengo algo",
    "q hay", "que hay", "qué hay",
    "mis tareas", "mis cosas", "mis avisos",
    "para mañana", "para hoy", "y mañana", "y hoy",
    "mañana??", "hoy??", "mañana?", "hoy?",
    "mostrar", "muéstrame", "muéstrame",
    "ver agenda", "ver recordatorios",
)

_KW_SEARCH = (
    "busca", "buscar", "precio", "cotización", "noticias", "clima",
    "cuánto vale", "cuánto cuesta", "cuanto vale", "cuanto cuesta",
    "dólar", "bitcoin", "crypto", "bolsa", "acciones",
    "tasa de cambio", "últimas noticias", "qué pasó", "que paso",
)

_KW_CODE = (
    "genera código", "escribe código", "crea una función", "escribe una función",
    "crea un script", "escribe un script", "genera un programa", "escribe un programa",
    "crea una clase", "escribe una clase", "crea un módulo",
    "depura", "depurar", "debug", "hay un error en", "este error",
    "explica este código", "qué hace este código", "que hace este codigo",
    "refactoriza", "refactorizar", "optimiza este código",
    "en python:", "en javascript:", "en dart:", "en typescript:", "en kotlin:",
)

_KW_FILE = (
    "lee el archivo", "leer el archivo", "abre el archivo", "abrir el archivo",
    "muéstrame el archivo", "muestrame el archivo",
    "lista los archivos", "lista archivos", "qué archivos", "que archivos",
    "busca en el archivo", "busca en mis archivos", "buscar en archivos",
    "contenido del archivo", "leer fichero",
)

_KW_CALENDAR = (
    "calendario", "google calendar", "mis eventos", "eventos de hoy",
    "eventos de mañana", "qué tengo en el calendario", "que tengo en el calendario",
    "añadir al calendario", "agregar al calendario", "crear evento",
    "cita en el calendario",
)

_KW_EMAIL = (
    "correos", "emails", "bandeja de entrada", "inbox", "mis correos",
    "correo nuevo", "correos sin leer", "redacta un correo", "redactar correo",
    "envía un correo", "enviar correo", "envía un email", "enviar email",
    "lee mi correo", "leer correo", "ver correos", "gmail",
)


def _intent(message: str) -> str:
    msg = message.lower().strip()

    # Eliminar: primero porque puede coincidir con palabras de lista
    has_delete_verb = any(kw in msg for kw in _KW_DELETE)
    has_delete_obj  = any(kw in msg for kw in _KW_DELETE_OBJ)
    if has_delete_verb and has_delete_obj:
        return "delete_reminders"

    # Modificar: antes de crear/listar (también menciona "recordatorio")
    if any(kw in msg for kw in _KW_MODIFY):
        return "modify_reminder"

    # Crear: verbos específicos de creación
    if any(kw in msg for kw in _KW_CREATE):
        return "create_reminder"

    # Código
    if any(kw in msg for kw in _KW_CODE):
        return "code"

    # Archivos
    if any(kw in msg for kw in _KW_FILE):
        return "file"

    # Calendario
    if any(kw in msg for kw in _KW_CALENDAR):
        return "calendar"

    # Email
    if any(kw in msg for kw in _KW_EMAIL):
        return "email"

    # Búsqueda web (antes de lista, para que "precio mañana" no sea list)
    if any(kw in msg for kw in _KW_SEARCH):
        return "web_search"

    # Listar: cualquier mención de agenda/recordatorio/pendiente
    if any(kw in msg for kw in _KW_LIST):
        return "list_reminders"

    return "chat"


# ── Acciones de BD (sin LLM) ─────────────────────────────────────────────────

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
        # Busca por coincidencia parcial case-insensitive
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
        # Actualiza el primero que coincida
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
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        resp = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Ahora mismo es {today}. "
                        "Extrae el título y la fecha/hora de un recordatorio del mensaje. "
                        'Responde SOLO con JSON: {"title": "...", "datetime": "YYYY-MM-DDTHH:MM:SS"}. '
                        "Si no hay fecha clara, usa mañana a las 09:00. "
                        "Si dice 'a las 8' sin AM/PM y es de mañana, usa 08:00. "
                        "No incluyas explicaciones, solo el JSON."
                    ),
                },
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=80,
        )
        raw = resp.choices[0].message.content.strip()
        # Extraer JSON aunque tenga texto alrededor
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())
        dt = datetime.fromisoformat(data["datetime"])
        return data["title"], dt
    except Exception:
        return None


# ── Agentes externos ──────────────────────────────────────────────────────────

async def _web_search(query: str) -> str:
    from app.agents.web_search import WebSearchAgent
    try:
        result = await WebSearchAgent().run(query=query, max_results=4)
        return result if result and "No se encontraron" not in result else ""
    except Exception:
        return ""


async def _run_code_agent(message: str) -> str:
    from app.agents.code_agent import CodeAgent
    # Detectar lenguaje mencionado en el mensaje
    lang = "python"
    for l in ("javascript", "typescript", "dart", "kotlin", "go", "rust", "java", "bash"):
        if l in message.lower():
            lang = l
            break
    try:
        return await CodeAgent().run(task=message, language=lang)
    except Exception as e:
        return f"Error en CodeAgent: {e}"


async def _run_file_agent(message: str) -> str:
    from app.agents.file_agent import FileAgent
    msg = message.lower()
    if any(k in msg for k in ("lista", "qué archivos", "que archivos", "listar")):
        action = "list"
    elif any(k in msg for k in ("busca en", "buscar en", "busca el texto")):
        action = "search"
    else:
        action = "read"

    # Intento extraer ruta del mensaje (entre comillas o después de "archivo")
    import re
    path_match = re.search(r'["\']([^"\']+)["\']', message)
    path = path_match.group(1) if path_match else ""

    try:
        return await FileAgent().run(action=action, path=path, query=message)
    except Exception as e:
        return f"Error en FileAgent: {e}"


async def _run_calendar_agent(message: str) -> str:
    from app.agents.calendar_agent import CalendarAgent
    msg = message.lower()
    action = "create" if any(k in msg for k in ("añadir", "agregar", "crear evento", "nueva cita")) else "list"
    try:
        return await CalendarAgent().run(action=action)
    except Exception as e:
        return f"Error en CalendarAgent: {e}"


async def _run_email_agent(message: str) -> str:
    from app.agents.email_agent import EmailAgent
    msg = message.lower()
    if any(k in msg for k in ("envía", "enviar", "redacta", "mandar")):
        action = "send"
    elif any(k in msg for k in ("lee", "leer", "abre", "abrir", "muéstrame")):
        action = "read"
    else:
        action = "list"
    try:
        return await EmailAgent().run(action=action)
    except Exception as e:
        return f"Error en EmailAgent: {e}"


# ── Función principal ─────────────────────────────────────────────────────────

async def chat(message: str, session_id: str, device: str = "cli") -> str:
    is_creator = _is_creator(session_id)
    base_system = SYSTEM_CREATOR if is_creator else SYSTEM_BASE

    # Perfil evolutivo del usuario (siempre inyectado si existe)
    profile_text = await get_profile(session_id)
    profile_context = f"\n\n[Perfil del usuario]\n{profile_text}" if profile_text else ""

    # Memoria Mem0 (hechos atómicos) + Knowledge Graph (relaciones entre conceptos)
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

    # Detectar intención y ejecutar acción directamente
    intent = _intent(message)
    action_context = ""
    direct_answer = None   # si se asigna, se devuelve sin pasar por LLM

    if intent == "modify_reminder":
        parsed = await _parse_modify(message)
        if parsed:
            old_title, new_title = parsed
            direct_answer = await _db_modify_reminder(session_id, old_title, new_title)
        else:
            direct_answer = "No pude entender qué recordatorio modificar. Indícame: 'cambia X a Y'."

    elif intent == "delete_reminders":
        direct_answer = await _db_delete_reminders(session_id)

    elif intent == "create_reminder":
        parsed = await _parse_reminder(message)
        if parsed:
            title, dt = parsed
            direct_answer = await _db_create_reminder(title, dt, session_id)
        else:
            direct_answer = "No pude determinar la fecha del recordatorio. Indícame cuándo quieres el recordatorio."

    elif intent == "list_reminders":
        day = _list_day_filter(message)
        direct_answer = await _db_list_reminders(session_id, day=day)

    elif intent == "code":
        direct_answer = await _run_code_agent(message)

    elif intent == "file":
        direct_answer = await _run_file_agent(message)

    elif intent == "calendar":
        result = await _run_calendar_agent(message)
        action_context = f"\n\n[Calendario]\n{result}"

    elif intent == "email":
        result = await _run_email_agent(message)
        action_context = f"\n\n[Email]\n{result}"

    elif intent == "web_search":
        result = await _web_search(message)
        if result:
            action_context = f"\n\n[Resultados de búsqueda]\n{result}"

    # Para crear/eliminar: respuesta directa, sin LLM (evita alucinaciones)
    if direct_answer is not None:
        return direct_answer

    # Para listar/buscar/chat: LLM redacta la respuesta
    system = base_system + profile_context + memory_context + action_context
    temp = 0.3 if action_context else 0.7
    response = await groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        temperature=temp,
        max_tokens=400,
    )
    answer = response.choices[0].message.content or ""

    # Guardar en Mem0 + Knowledge Graph en background
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

    # Incrementar contador y regenerar perfil en background cada 10 conversaciones
    should_update = await increment_and_check(session_id)
    if should_update:
        asyncio.create_task(generate_and_save_profile(session_id))

    return answer
