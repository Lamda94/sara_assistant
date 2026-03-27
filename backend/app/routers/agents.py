from fastapi import APIRouter
from pydantic import BaseModel
from app.services.memory_service import consolidate_memories
from app.services.profile_service import get_profile, generate_and_save_profile

router = APIRouter(prefix="/agents", tags=["agents"])


class ProfileRequest(BaseModel):
    session_id: str


@router.post("/consolidate")
async def consolidate():
    """Fusiona memorias similares para reducir redundancia."""
    result = await consolidate_memories()
    return {"ok": True, **result}


@router.get("/profile/{session_id}")
async def view_profile(session_id: str):
    """Muestra el perfil evolutivo actual de un usuario."""
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
    await generate_and_save_profile(req.session_id)
    profile = await get_profile(req.session_id)
    return {"ok": True, "profile": profile}
