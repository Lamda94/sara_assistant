import time

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.services.memory_service import consolidate_memories, update_importance_scores
from app.services.profile_service import get_profile, generate_and_save_profile
from app.dependencies import validate_session_id

router = APIRouter(prefix="/agents", tags=["agents"])


class ProfileRequest(BaseModel):
    session_id: str = Field(..., max_length=100)


class ConsolidateRequest(BaseModel):
    session_id: str = Field(..., max_length=100)


@router.post("/consolidate")
async def consolidate(req: ConsolidateRequest):
    """
    Ejecuta el pipeline completo de consolidación para un usuario.
    Incluye: Mem0 dedup -> Qdrant fusion -> daily summary -> cleanup -> importance scores.
    """
    from app.db.postgres import SessionLocal
    from app.models.consolidation_log import ConsolidationLog
    from app.services.consolidation_service import (
        dedup_mem0_facts,
        generate_daily_summary,
        cleanup_old_facts,
    )
    from app.services.mem0_service import mem0_add

    validate_session_id(req.session_id)
    session_id = req.session_id
    t0 = time.time()
    log = ConsolidationLog(session_id=session_id, run_type="manual")

    try:
        # 1. Mem0 dedup
        log.mem0_duplicates_removed = await dedup_mem0_facts(session_id)

        # 2. Qdrant fusion
        fusion = await consolidate_memories(session_id=session_id)
        log.qdrant_pairs_merged = fusion.get("merged", 0)
        log.qdrant_points_removed = fusion.get("removed", 0)

        # 3. Daily summary
        summary = await generate_daily_summary(session_id)
        if summary:
            await mem0_add(
                [{"role": "user", "content": summary}],
                user_id=session_id,
            )
            log.daily_summary_saved = True

        # 4. Cleanup old facts
        log.old_facts_cleaned = await cleanup_old_facts(session_id)

        # 5. Importance scores
        log.importance_scores_updated = await update_importance_scores(session_id)

    except Exception as e:
        log.error = str(e)

    log.duration_seconds = round(time.time() - t0, 2)

    async with SessionLocal() as s:
        s.add(log)
        await s.commit()

    return {
        "ok": True,
        "session_id": session_id,
        "mem0_duplicates_removed": log.mem0_duplicates_removed,
        "qdrant_pairs_merged": log.qdrant_pairs_merged,
        "qdrant_points_removed": log.qdrant_points_removed,
        "old_facts_cleaned": log.old_facts_cleaned,
        "daily_summary_saved": log.daily_summary_saved,
        "importance_scores_updated": log.importance_scores_updated,
        "duration_seconds": log.duration_seconds,
        "error": log.error,
    }


@router.get("/consolidation/history")
async def consolidation_history(
    session_id: Optional[str] = Query(None, description="Filtrar por usuario"),
    limit: int = Query(20, ge=1, le=100),
):
    """Devuelve el historial de consolidaciones ejecutadas."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.consolidation_log import ConsolidationLog

    async with SessionLocal() as s:
        query = select(ConsolidationLog).order_by(
            ConsolidationLog.created_at.desc()
        ).limit(limit)

        if session_id:
            query = query.where(ConsolidationLog.session_id == session_id)

        result = await s.execute(query)
        logs = result.scalars().all()

    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "session_id": log.session_id,
                "run_type": log.run_type,
                "mem0_duplicates_removed": log.mem0_duplicates_removed,
                "qdrant_pairs_merged": log.qdrant_pairs_merged,
                "qdrant_points_removed": log.qdrant_points_removed,
                "old_facts_cleaned": log.old_facts_cleaned,
                "daily_summary_saved": log.daily_summary_saved,
                "importance_scores_updated": log.importance_scores_updated,
                "duration_seconds": log.duration_seconds,
                "error": log.error,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/profile/{session_id}")
async def view_profile(session_id: str):
    """Muestra el perfil evolutivo actual de un usuario."""
    validate_session_id(session_id)
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.user_profile import UserProfile

    async with SessionLocal() as s:
        r = await s.execute(select(UserProfile).where(UserProfile.session_id == session_id))
        row = r.scalar_one_or_none()

    if not row:
        return {"session_id": session_id, "profile": None, "conversation_count": 0}

    return {
        "session_id": session_id,
        "profile": row.profile_text,
        "conversation_count": row.conversation_count,
        "last_updated": row.last_updated,
    }


@router.post("/profile/refresh")
async def refresh_profile(req: ProfileRequest):
    """Fuerza la regeneración inmediata del perfil del usuario."""
    validate_session_id(req.session_id)
    await generate_and_save_profile(req.session_id)
    profile = await get_profile(req.session_id)
    return {"ok": True, "profile": profile}
