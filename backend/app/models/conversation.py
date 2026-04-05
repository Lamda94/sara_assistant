from typing import Optional
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, index=True)
    device: Mapped[str] = mapped_column(String, default="cli")
    role: Mapped[str] = mapped_column(String)          # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    agent_used: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
