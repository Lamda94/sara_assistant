from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import Optional
from app.services.ai_service import chat
from app.dependencies import validate_session_id
from app.limiter import limiter

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field("default", max_length=100)
    device: str = Field("web", max_length=20)
    google_access_token: Optional[str] = Field(None, max_length=2048)


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_used: Optional[str] = None


@router.post("", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(request: Request, req: ChatRequest):
    validate_session_id(req.session_id)
    result = await chat(
        req.message,
        session_id=req.session_id,
        device=req.device,
        google_access_token=req.google_access_token,
    )
    return ChatResponse(
        response=result["response"],
        session_id=req.session_id,
        agent_used=result.get("agent_used"),
    )
