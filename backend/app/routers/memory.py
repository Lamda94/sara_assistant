from fastapi import APIRouter
from app.services.mem0_service import mem0_get_all, mem0_search, mem0_delete_all
from app.dependencies import validate_session_id

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{user_id}")
async def get_all_memories(user_id: str):
    """Devuelve todos los hechos atómicos almacenados para un usuario."""
    validate_session_id(user_id)
    facts = await mem0_get_all(user_id)
    return {"user_id": user_id, "total": len(facts), "facts": facts}


@router.get("/{user_id}/search")
async def search_memories(user_id: str, q: str, limit: int = 5):
    """Busca hechos relevantes para una query."""
    validate_session_id(user_id)
    facts = await mem0_search(q, user_id=user_id, limit=limit)
    return {"user_id": user_id, "query": q, "results": facts}


@router.delete("/{user_id}")
async def delete_all_memories(user_id: str):
    """Elimina todos los hechos de un usuario."""
    validate_session_id(user_id)
    n = await mem0_delete_all(user_id)
    return {"user_id": user_id, "deleted": n}
