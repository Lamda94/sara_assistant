import logging
from datetime import datetime

from app.services.llm import llm_chat, LLM_MODEL
from app.config import settings

logger = logging.getLogger(__name__)
# llm_client importado desde app.services.llm

# Cada cuántas conversaciones se regenera el perfil
_UPDATE_EVERY = 10


async def get_profile(session_id: str) -> str:
    """Devuelve el perfil actual del usuario, o '' si aún no existe."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.user_profile import UserProfile

    async with SessionLocal() as s:
        r = await s.execute(select(UserProfile).where(UserProfile.session_id == session_id))
        row = r.scalar_one_or_none()
        return row.profile_text if row and row.profile_text else ""


async def increment_and_check(session_id: str) -> bool:
    """
    Incrementa el contador de conversaciones.
    Devuelve True si se alcanzó el umbral de actualización.
    """
    from sqlalchemy.dialects.postgresql import insert
    from app.db.postgres import SessionLocal
    from app.models.user_profile import UserProfile

    async with SessionLocal() as s:
        stmt = insert(UserProfile).values(
            session_id=session_id,
            conversation_count=1,
            profile_text="",
        ).on_conflict_do_update(
            index_elements=["session_id"],
            set_={"conversation_count": UserProfile.conversation_count + 1},
        ).returning(UserProfile.conversation_count)

        result = await s.execute(stmt)
        count = result.scalar_one()
        await s.commit()

    return (count % _UPDATE_EVERY) == 0


async def generate_and_save_profile(session_id: str) -> None:
    """
    Analiza las memorias del usuario y genera un perfil evolutivo.
    Se llama en background — nunca propaga excepciones.
    """
    try:
        from app.services.mem0_service import mem0_get_all

        all_facts = await mem0_get_all(session_id)
        memories = [f["memory"] for f in all_facts if f.get("memory")]

        if len(memories) < 5:
            logger.info(f"[Profile] Pocas memorias para {session_id}, omitiendo")
            return

        sample = "\n".join(f"- {m[:200]}" for m in memories[-60:])

        resp = await llm_chat("fast",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un sistema de análisis de patrones de usuario. "
                        "Basándote en las conversaciones, genera un perfil conciso "
                        "en forma de instrucciones directas para SARA (el asistente). "
                        "Escribe en español, máximo 180 palabras, sin saludos ni explicaciones. "
                        "Sé específico sobre patrones reales observados, no genérico."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Conversaciones del usuario:\n{sample}\n\n"
                        "Genera el perfil con estos apartados (omite los que no apliquen):\n"
                        "- Estilo de comunicación (cómo escribe, nivel de formalidad)\n"
                        "- Intereses y proyectos recurrentes\n"
                        "- Patrones de comportamiento o hábitos observados\n"
                        "- Cómo debe responderle SARA específicamente\n"
                        "- Qué temas o términos son importantes para él"
                    ),
                },
            ],
            temperature=0.4,
            max_tokens=250,
        )

        profile_text = resp.choices[0].message.content.strip()

        # Guardar en PostgreSQL (upsert — crea o actualiza)
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.db.postgres import SessionLocal
        from app.models.user_profile import UserProfile

        async with SessionLocal() as db:
            stmt = pg_insert(UserProfile).values(
                session_id=session_id,
                profile_text=profile_text,
                conversation_count=0,
            ).on_conflict_do_update(
                index_elements=["session_id"],
                set_={"profile_text": profile_text, "last_updated": datetime.now()},
            )
            await db.execute(stmt)
            await db.commit()

        logger.warning(f"[Profile] Perfil actualizado para {session_id}: {len(profile_text)} chars")

    except Exception as e:
        logger.error(f"[Profile] Error generando perfil para {session_id}: {e}")
