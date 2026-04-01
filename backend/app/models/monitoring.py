from sqlalchemy import String, Text, BigInteger, Integer, Boolean, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import uuid


class ChildDevice(Base):
    __tablename__ = "child_devices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_session_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    parent_session_id: Mapped[str] = mapped_column(String, index=True)
    device_label: Mapped[str] = mapped_column(String, default="Dispositivo hijo")
    registered_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AppUsageEvent(Base):
    __tablename__ = "app_usage_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_session_id: Mapped[str] = mapped_column(String, index=True)
    package_name: Mapped[str] = mapped_column(String)
    app_label: Mapped[str] = mapped_column(String)
    foreground_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    launches: Mapped[int] = mapped_column(Integer, default=0)
    event_date: Mapped[Date] = mapped_column(Date, index=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_session_id: Mapped[str] = mapped_column(String, index=True)
    package_name: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class BrowserEvent(Base):
    __tablename__ = "browser_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_session_id: Mapped[str] = mapped_column(String, index=True)
    browser_package: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String)
    visited_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class PackageEvent(Base):
    __tablename__ = "package_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_session_id: Mapped[str] = mapped_column(String, index=True)
    package_name: Mapped[str] = mapped_column(String)
    app_label: Mapped[str] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)  # "install" | "uninstall"
    occurred_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
