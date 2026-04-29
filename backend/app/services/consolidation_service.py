"""
Consolidación nocturna de memoria (Fase 4.2).

Cron job que corre a las 3am y por cada usuario activo ejecuta el pipeline:
1. Deduplicación de hechos Mem0 similares
2. Fusión de memorias Qdrant similares (per-user)
3. Genera un resumen del día con los hechos aprendidos
4. Limpia hechos con más de N días de antigüedad
5. Recalcula scores de importancia
6. Guarda log de resultados en ConsolidationLog
"""
import logging
import time
from datetime import datetime, date, timedelta, timezone

from app.services.llm import llm_chat, LLM_MODEL
from app.config import settings

logger = logging.getLogger(__name__)
# llm_client importado desde app.services.llm


async def get_active_users() -> list[str]:
    """Usuarios que tienen perfil activo (han conversado al menos una vez)."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.user_profile import UserProfile

    async with SessionLocal() as s:
        result = await s.execute(select(UserProfile.session_id))
        return [row[0] for row in result.fetchall()]


async def generate_daily_summary(session_id: str) -> str | None:
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

    if len(today_facts) < settings.consolidation_min_facts_for_summary:
        return None

    facts_text = "\n".join(f"- {f}" for f in today_facts)

    resp = await llm_chat("fast",

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


async def cleanup_old_facts(session_id: str) -> int:
    """Elimina hechos con más de N días de antigüedad. Devuelve el número eliminado."""
    from app.services.mem0_service import mem0_get_all, mem0_delete

    all_facts = await mem0_get_all(session_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.consolidation_old_facts_days)
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


async def dedup_mem0_facts(session_id: str) -> int:
    """
    Elimina hechos Mem0 duplicados o muy similares para un usuario.
    Compara textos y elimina los más cortos cuando hay duplicados cercanos.
    Devuelve el número de duplicados eliminados.
    """
    from app.services.mem0_service import mem0_get_all, mem0_delete

    all_facts = await mem0_get_all(session_id)
    if len(all_facts) < 2:
        return 0

    facts = [
        (f["id"], f.get("memory", ""))
        for f in all_facts
        if f.get("memory")
    ]
    # Ordenar por longitud descendente para conservar la versión más rica
    facts.sort(key=lambda x: len(x[1]), reverse=True)

    deleted_ids: set[str] = set()
    deleted_count = 0

    for i, (id_a, text_a) in enumerate(facts):
        if id_a in deleted_ids:
            continue
        norm_a = text_a.lower().strip()

        for j in range(i + 1, len(facts)):
            id_b, text_b = facts[j]
            if id_b in deleted_ids:
                continue
            norm_b = text_b.lower().strip()

            # Detectar duplicado por substring o word-overlap > 85%
            is_dup = False
            if norm_b in norm_a:
                is_dup = True
            else:
                words_a = set(norm_a.split())
                words_b = set(norm_b.split())
                if words_b and len(words_a & words_b) / len(words_b) > 0.85:
                    is_dup = True

            if is_dup:
                await mem0_delete(id_b)
                deleted_ids.add(id_b)
                deleted_count += 1

    return deleted_count


async def daily_consolidation() -> None:
    """
    Job nocturno principal. Registrado en APScheduler.
    Pipeline completo por cada usuario activo:
      1. Dedup Mem0 facts
      2. Qdrant memory fusion (per-user)
      3. Daily summary generation + save
      4. Cleanup old facts
      5. Update importance scores
      6. Log results to ConsolidationLog
    """
    from app.db.postgres import SessionLocal
    from app.models.consolidation_log import ConsolidationLog

    logger.warning("[Consolidation] -- Iniciando consolidacion nocturna --")

    users = await get_active_users()
    if not users:
        logger.warning("[Consolidation] No hay usuarios activos, omitiendo")
        return

    for session_id in users:
        t0 = time.time()
        log = ConsolidationLog(session_id=session_id, run_type="nightly")

        try:
            # 1. Deduplicar hechos Mem0
            deduped = await dedup_mem0_facts(session_id)
            log.mem0_duplicates_removed = deduped
            if deduped:
                logger.warning(
                    "[Consolidation] %s -> %d Mem0 duplicados eliminados",
                    session_id, deduped,
                )

            # 2. Fusionar memorias Qdrant similares (per-user)
            from app.services.memory_service import consolidate_memories
            fusion = await consolidate_memories(session_id=session_id)
            log.qdrant_pairs_merged = fusion.get("merged", 0)
            log.qdrant_points_removed = fusion.get("removed", 0)
            if fusion.get("merged"):
                logger.warning(
                    "[Consolidation] %s -> Qdrant: %d fusiones, %d puntos eliminados",
                    session_id, fusion["merged"], fusion["removed"],
                )

            # 3. Resumen del día
            summary = await generate_daily_summary(session_id)
            if summary:
                from app.services.mem0_service import mem0_add
                await mem0_add(
                    [{"role": "user", "content": summary}],
                    user_id=session_id,
                )
                log.daily_summary_saved = True
                logger.warning("[Consolidation] %s -> resumen guardado", session_id)
            else:
                log.daily_summary_saved = False
                logger.info("[Consolidation] %s -> sin hechos nuevos hoy", session_id)

            # 4. Limpiar hechos viejos
            deleted = await cleanup_old_facts(session_id)
            log.old_facts_cleaned = deleted
            if deleted:
                logger.warning(
                    "[Consolidation] %s -> %d hechos viejos eliminados",
                    session_id, deleted,
                )

            # 5. Recalcular scores de importancia
            from app.services.memory_service import update_importance_scores
            scores_updated = await update_importance_scores(session_id)
            log.importance_scores_updated = scores_updated

        except Exception as e:
            logger.error("[Consolidation] Error en %s: %s", session_id, e)
            log.error = str(e)

        log.duration_seconds = round(time.time() - t0, 2)

        # Guardar log
        try:
            async with SessionLocal() as s:
                s.add(log)
                await s.commit()
        except Exception as e:
            logger.error("[Consolidation] Error guardando log para %s: %s", session_id, e)

    logger.warning("[Consolidation] -- Consolidacion nocturna completada --")
