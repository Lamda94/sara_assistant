from fastapi import APIRouter
from app.services.knowledge_service import kg_get_full

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/{session_id}")
async def get_graph(session_id: str):
    """Devuelve el grafo completo de conocimiento de un usuario."""
    return await kg_get_full(session_id)
