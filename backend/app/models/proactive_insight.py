from typing import Optional
from sqlalchemy import String, Text, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class ProactiveInsight(Base):
    __tablename__ = "proactive_insights"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String, index=True)
    insight_type: Mapped[str] = mapped_column(String)  # commitment | follow_up | pattern_alert | inactivity
    content: Mapped[str] = mapped_column(Text)
    source_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    due_date: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True, default=None)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
