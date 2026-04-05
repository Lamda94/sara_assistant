from fastapi import APIRouter
from app.services.knowledge_service import kg_get_full
from app.dependencies import validate_session_id

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/{session_id}")
async def get_graph(session_id: str):
    """Devuelve el grafo completo de conocimiento de un usuario."""
    validate_session_id(session_id)
    return await kg_get_full(session_id)
