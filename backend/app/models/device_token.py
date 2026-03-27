from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    token: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
