"""
Consolidación nocturna de memoria (Fase 4.2).

Cron job que corre a las 3am y por cada usuario activo:
1. Genera un resumen del día con los hechos aprendidos
2. Lo guarda en Mem0 como memoria especial
3. Limpia hechos con más de 60 días de antigüedad
"""
import logging
from datetime import datetime, date, timedelta, timezone

from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)
groq_client = AsyncGroq(api_key=settings.groq_api_key)


async def _get_active_users() -> list[str]:
    """Usuarios que tienen perfil activo (han conversado al menos una vez)."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.user_profile import UserProfile

    async with SessionLocal() as s:
        result = await s.execute(select(UserProfile.session_id))
        return [row[0] for row in result.fetchall()]


async def _generate_daily_summary(session_id: str) -> str | None:
    """
    Genera un resumen de los hechos aprendidos hoy sobre el usuario.
    Devuelve None si no hay suficientes hechos nuevos.
    """
    from app.services.mem0_service import mem0_get_all

    all_facts = await mem0_get_all(session_id)
    today_str = str(date.today())

    today_facts = [
        f.get("memory", "")
        for f in all_facts
        if f.get("created_at", "")[:10] == today_str and f.get("memory")
    ]

    if len(today_facts) < 2:
        return None

    facts_text = "\n".join(f"- {f}" for f in today_facts)

    resp = await groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Genera un resumen conciso de lo aprendido hoy sobre el usuario. "
                    "Máximo 2 oraciones, en tercera persona. Sin encabezados ni viñetas, "
                    "solo el texto del resumen."
                ),
            },
            {
                "role": "user",
                "content": f"Hechos de hoy sobre el usuario:\n{facts_text}",
            },
        ],
        temperature=0.3,
        max_tokens=120,
    )

    summary = resp.choices[0].message.content.strip()
    return f"[Resumen {date.today().strftime('%d/%m/%Y')}] {summary}"


async def _cleanup_old_facts(session_id: str) -> int:
    """Elimina hechos con más de 60 días de antigüedad. Devuelve el número eliminado."""
    from app.services.mem0_service import mem0_get_all, mem0_delete

    all_facts = await mem0_get_all(session_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    deleted = 0

    for f in all_facts:
        created_str = f.get("created_at", "")
        if not created_str:
            continue
        try:
            created_at = datetime.fromisoformat(created_str)
            if created_at < cutoff:
                await mem0_delete(f["id"])
                deleted += 1
        except Exception:
            continue

    return deleted


async def daily_consolidation() -> None:
    """
    Job nocturno principal. Registrado en APScheduler (3am).
    Procesa todos los usuarios activos secuencialmente.
    """
    logger.warning("[Consolidation] ── Iniciando consolidación nocturna ──")

    users = await _get_active_users()
    if not users:
        logger.warning("[Consolidation] No hay usuarios activos, omitiendo")
        return

    for session_id in users:
        try:
            # 1. Resumen del día
            summary = await _generate_daily_summary(session_id)
            if summary:
                from app.services.mem0_service import mem0_add
                await mem0_add(
                    [{"role": "user", "content": summary}],
                    user_id=session_id,
                )
                logger.warning("[Consolidation] %s → resumen guardado", session_id)
            else:
                logger.info("[Consolidation] %s → sin hechos nuevos hoy", session_id)

            # 2. Limpiar hechos viejos
            deleted = await _cleanup_old_facts(session_id)
            if deleted:
                logger.warning(
                    "[Consolidation] %s → %d hechos viejos eliminados", session_id, deleted
                )

        except Exception as e:
            logger.error("[Consolidation] Error en %s: %s", session_id, e)

    logger.warning("[Consolidation] ── Consolidación nocturna completada ──")
