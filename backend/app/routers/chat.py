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


@router.post("", response_model=ChatResponse)
async def send_message(req: ChatRequest):
    response = await chat(
        req.message,
        session_id=req.session_id,
        device=req.device,
        google_access_token=req.google_access_token,
    )
    return ChatResponse(response=response, session_id=req.session_id)
