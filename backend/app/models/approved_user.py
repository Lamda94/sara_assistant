from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class ApprovedUser(Base):
    __tablename__ = "approved_users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    approved_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
