"""
Dependencias de seguridad reutilizables para FastAPI.
"""
import re
from fastapi import HTTPException
from app.config import settings

_SESSION_RE = re.compile(r"^[a-zA-Z0-9@._-]{1,100}$")


def validate_session_id(session_id: str) -> str:
    """Valida formato y longitud de session_id."""
    if not session_id or session_id == "default":
        raise HTTPException(status_code=400, detail="session_id requerido")
    if not _SESSION_RE.match(session_id):
        raise HTTPException(status_code=400, detail="session_id inválido")
    return session_id


def require_creator(session_id: str) -> str:
    """Valida que el session_id pertenece al creador."""
    session_id = validate_session_id(session_id)
    if settings.creator_id not in session_id.lower():
        raise HTTPException(status_code=403, detail="Acceso restringido")
    return session_id
