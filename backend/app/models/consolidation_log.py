from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class ConsolidationLog(Base):
    __tablename__ = "consolidation_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, index=True)
    run_type: Mapped[str] = mapped_column(String, default="nightly")
    mem0_duplicates_removed: Mapped[int] = mapped_column(Integer, default=0)
    qdrant_pairs_merged: Mapped[int] = mapped_column(Integer, default=0)
    qdrant_points_removed: Mapped[int] = mapped_column(Integer, default=0)
    old_facts_cleaned: Mapped[int] = mapped_column(Integer, default=0)
    daily_summary_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    importance_scores_updated: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
