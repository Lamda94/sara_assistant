from sqlalchemy import String, Text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_text: Mapped[str] = mapped_column(Text, default="")
    conversation_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
