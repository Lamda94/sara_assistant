from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.ai_service import chat

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    device: str = "web"
    google_access_token: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_used: Optional[str] = None


@router.post("", response_model=ChatResponse)
async def send_message(req: ChatRequest):
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
