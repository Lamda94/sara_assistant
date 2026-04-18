"""Modelos para Career-Ops — Sistema de búsqueda y gestión de carrera profesional."""
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class CareerProfile(Base):
    """Perfil profesional del usuario para búsqueda activa."""
    __tablename__ = "career_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(254), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str] = mapped_column(String(500), nullable=True)
    cv_markdown: Mapped[str] = mapped_column(Text)
    target_roles: Mapped[dict] = mapped_column(JSON, nullable=True)
    archetypes: Mapped[dict] = mapped_column(JSON, nullable=True)
    narrative: Mapped[dict] = mapped_column(JSON, nullable=True)
    compensation: Mapped[dict] = mapped_column(JSON, nullable=True)
    title_positive: Mapped[dict] = mapped_column(JSON, nullable=True)
    title_negative: Mapped[dict] = mapped_column(JSON, nullable=True)
    career_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    scan_interval_hours: Mapped[int] = mapped_column(Integer, default=6)
    min_score_cv: Mapped[float] = mapped_column(Float, default=4.0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class CareerPortal(Base):
    """Portal de empleo configurado para escaneo automático."""
    __tablename__ = "career_portals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    careers_url: Mapped[str] = mapped_column(String(500))
    api_url: Mapped[str] = mapped_column(String(500), nullable=True)
    ats_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scanned_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class CareerApplication(Base):
    """Vacante evaluada y/o aplicada."""
    __tablename__ = "career_applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    company: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500), nullable=True)
    portal_source: Mapped[str] = mapped_column(String(100), nullable=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    compatibility_pct: Mapped[int] = mapped_column(Integer, nullable=True)
    archetype: Mapped[str] = mapped_column(String(100), nullable=True)
    evaluation_blocks: Mapped[dict] = mapped_column(JSON, nullable=True)
    evaluation_summary: Mapped[str] = mapped_column(Text, nullable=True)
    cv_path: Mapped[str] = mapped_column(String(500), nullable=True)
    cv_changes: Mapped[dict] = mapped_column(JSON, nullable=True)
    interview_stories: Mapped[dict] = mapped_column(JSON, nullable=True)
    legitimacy: Mapped[str] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="evaluated")
    applied_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    applied_method: Mapped[str] = mapped_column(String(20), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class CareerActivityLog(Base):
    """Log de cada ciclo de escaneo automático."""
    __tablename__ = "career_activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100))
    cycle_date: Mapped[DateTime] = mapped_column(DateTime)
    portals_scanned: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_found: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_cv_generated: Mapped[int] = mapped_column(Integer, default=0)
    top_score: Mapped[float] = mapped_column(Float, nullable=True)
    top_company: Mapped[str] = mapped_column(String(200), nullable=True)
    top_role: Mapped[str] = mapped_column(String(300), nullable=True)
    errors: Mapped[str] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class CareerScanHistory(Base):
    """Historial de URLs ya escaneadas para deduplicación."""
    __tablename__ = "career_scan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500), index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=True)
    portal_source: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    first_seen_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
