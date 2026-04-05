"""Modelos para el agente SABE — Sistema de Análisis de Betting Estratégico."""
from sqlalchemy import String, Text, Float, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class SimBet(Base):
    """Apuesta simulada (paper betting)."""
    __tablename__ = "sim_bets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, index=True)
    sport: Mapped[str] = mapped_column(String(50))
    event_name: Mapped[str] = mapped_column(String(300))
    event_date: Mapped[DateTime] = mapped_column(DateTime)
    event_api_id: Mapped[str] = mapped_column(String(100), nullable=True)
    league: Mapped[str] = mapped_column(String(100), nullable=True)
    market: Mapped[str] = mapped_column(String(50))
    selection: Mapped[str] = mapped_column(String(200))
    odds: Mapped[float] = mapped_column(Float)
    stake_pct: Mapped[float] = mapped_column(Float)
    stake_units: Mapped[float] = mapped_column(Float)
    predicted_prob: Mapped[float] = mapped_column(Float)
    implied_prob: Mapped[float] = mapped_column(Float)
    edge: Mapped[float] = mapped_column(Float)
    confidence: Mapped[int] = mapped_column(Integer)
    analysis_summary: Mapped[str] = mapped_column(Text)
    factors_used: Mapped[dict] = mapped_column(JSON, nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="pending")  # pending, win, loss, push, void
    profit_loss: Mapped[float] = mapped_column(Float, default=0.0)
    post_mortem: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)


class SabeModelMetrics(Base):
    """Métricas diarias de evolución del modelo."""
    __tablename__ = "sabe_model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True)
    total_bets: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate_last_5: Mapped[float] = mapped_column(Float, default=0.0)
    roi: Mapped[float] = mapped_column(Float, default=0.0)
    avg_edge: Mapped[float] = mapped_column(Float, default=0.0)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    adjustments_made: Mapped[dict] = mapped_column(JSON, nullable=True)
    model_status: Mapped[str] = mapped_column(String(20), default="learning")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class SabeBankroll(Base):
    """Estado del bankroll simulado."""
    __tablename__ = "sabe_bankroll"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True)
    initial_balance: Mapped[float] = mapped_column(Float, default=1000.0)
    current_balance: Mapped[float] = mapped_column(Float, default=1000.0)
    daily_stop_loss: Mapped[float] = mapped_column(Float, default=0.10)
    weekly_stop_loss: Mapped[float] = mapped_column(Float, default=0.20)
    max_stake_pct: Mapped[float] = mapped_column(Float, default=0.05)
    min_edge: Mapped[float] = mapped_column(Float, default=0.05)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
