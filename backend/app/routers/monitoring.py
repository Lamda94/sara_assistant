"""
MonitoringRouter — Control parental para SARA.

POST /monitoring/register-child       → registra dispositivo hijo
POST /monitoring/batch                → recibe eventos cada 15 min
POST /monitoring/suspicious           → alerta inmediata (contenido sospechoso)
GET  /monitoring/summary/{parent_id}  → resumen de actividad (usado por SARA chat)
GET  /monitoring/children/{parent_id} → lista dispositivos hijo registrados
"""
import logging
from datetime import datetime, date
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, func as sqlfunc

from app.db.postgres import SessionLocal as AsyncSessionLocal
from app.models.monitoring import (
    ChildDevice, AppUsageEvent, NotificationEvent, BrowserEvent, PackageEvent
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# ──────────────────────────────────────────────
# Schemas de entrada
# ──────────────────────────────────────────────

class RegisterChildRequest(BaseModel):
    child_session_id: str
    parent_session_id: str
    device_label: str = "Dispositivo hijo"
    device_identifier: Optional[str] = None


class UpdateDeviceRequest(BaseModel):
    device_label: Optional[str] = None
    monitoring_enabled: Optional[bool] = None


class AppUsageItem(BaseModel):
    package_name: str
    app_label: str
    foreground_ms: int
    launches: int
    event_date: str  # "YYYY-MM-DD"


class NotificationItem(BaseModel):
    package_name: str
    title: Optional[str] = None
    body: Optional[str] = None
    is_suspicious: bool = False
    posted_at: int  # epoch ms


class BrowserItem(BaseModel):
    browser_package: str
    url: str
    visited_at: int  # epoch ms


class PackageItem(BaseModel):
    package_name: str
    app_label: Optional[str] = None
    event_type: str  # "install" | "uninstall"
    occurred_at: int  # epoch ms


class BatchRequest(BaseModel):
    child_session_id: str
    app_usage: list[AppUsageItem] = []
    notifications: list[NotificationItem] = []
    browser: list[BrowserItem] = []
    packages: list[PackageItem] = []


class SuspiciousRequest(BaseModel):
    child_session_id: str
    package_name: str
    title: Optional[str] = None
    body: Optional[str] = None
    posted_at: int  # epoch ms


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/register-child")
async def register_child(req: RegisterChildRequest):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChildDevice).where(ChildDevice.child_session_id == req.child_session_id)
        )
        device = result.scalar_one_or_none()
        if device:
            device.parent_session_id = req.parent_session_id
            device.last_seen = datetime.utcnow()
            if req.device_identifier:
                device.device_identifier = req.device_identifier
        else:
            device = ChildDevice(
                child_session_id=req.child_session_id,
                parent_session_id=req.parent_session_id,
                device_label=req.device_label,
                device_identifier=req.device_identifier,
                monitoring_enabled=False,
            )
            db.add(device)
        await db.commit()
    return {"status": "ok"}


@router.get("/status/{child_session_id}")
async def get_device_status(child_session_id: str):
    """El dispositivo hijo consulta si debe monitorear."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChildDevice).where(ChildDevice.child_session_id == child_session_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            return {"monitoring_enabled": False, "registered": False}
        device.last_seen = datetime.utcnow()
        await db.commit()
    return {"monitoring_enabled": device.monitoring_enabled, "registered": True}


@router.patch("/device/{child_session_id}")
async def update_device(child_session_id: str, req: UpdateDeviceRequest):
    """El padre actualiza nombre y estado de monitoreo de un dispositivo."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChildDevice).where(ChildDevice.child_session_id == child_session_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        if req.device_label is not None:
            device.device_label = req.device_label
        if req.monitoring_enabled is not None:
            device.monitoring_enabled = req.monitoring_enabled
        await db.commit()
    return {"status": "ok", "monitoring_enabled": device.monitoring_enabled}


@router.post("/batch")
async def receive_batch(req: BatchRequest):
    counts = {"app_usage": 0, "notifications": 0, "browser": 0, "packages": 0}
    async with AsyncSessionLocal() as db:
        for item in req.app_usage:
            db.add(AppUsageEvent(
                child_session_id=req.child_session_id,
                package_name=item.package_name,
                app_label=item.app_label,
                foreground_ms=item.foreground_ms,
                launches=item.launches,
                event_date=date.fromisoformat(item.event_date),
            ))
            counts["app_usage"] += 1

        for item in req.notifications:
            db.add(NotificationEvent(
                child_session_id=req.child_session_id,
                package_name=item.package_name,
                title=item.title,
                body=item.body,
                is_suspicious=item.is_suspicious,
                posted_at=datetime.utcfromtimestamp(item.posted_at / 1000),
            ))
            counts["notifications"] += 1

        for item in req.browser:
            domain = _extract_domain(item.url)
            db.add(BrowserEvent(
                child_session_id=req.child_session_id,
                browser_package=item.browser_package,
                url=item.url,
                domain=domain,
                visited_at=datetime.utcfromtimestamp(item.visited_at / 1000),
            ))
            counts["browser"] += 1

        for item in req.packages:
            db.add(PackageEvent(
                child_session_id=req.child_session_id,
                package_name=item.package_name,
                app_label=item.app_label,
                event_type=item.event_type,
                occurred_at=datetime.utcfromtimestamp(item.occurred_at / 1000),
            ))
            counts["packages"] += 1

        await db.commit()
    return {"accepted": counts}


@router.post("/suspicious")
async def report_suspicious(req: SuspiciousRequest):
    async with AsyncSessionLocal() as db:
        db.add(NotificationEvent(
            child_session_id=req.child_session_id,
            package_name=req.package_name,
            title=req.title,
            body=req.body,
            is_suspicious=True,
            posted_at=datetime.utcfromtimestamp(req.posted_at / 1000),
        ))
        await db.commit()
    logger.warning(f"ALERTA PARENTAL [{req.child_session_id}] {req.package_name}: {req.title} — {req.body}")
    return {"status": "alerted"}


@router.get("/children/{parent_session_id}")
async def list_children(parent_session_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChildDevice).where(ChildDevice.parent_session_id == parent_session_id)
        )
        devices = result.scalars().all()
    return [{
        "child_session_id": d.child_session_id,
        "label": d.device_label,
        "monitoring_enabled": d.monitoring_enabled,
        "last_seen": d.last_seen,
    } for d in devices]


@router.get("/summary/{parent_session_id}")
async def get_summary(parent_session_id: str, target_date: Optional[str] = None):
    """Devuelve resumen de actividad para que SARA lo narre al padre."""
    day = date.fromisoformat(target_date) if target_date else date.today()

    async with AsyncSessionLocal() as db:
        # Buscar todos los hijos de este padre
        children_result = await db.execute(
            select(ChildDevice).where(ChildDevice.parent_session_id == parent_session_id)
        )
        children = children_result.scalars().all()
        if not children:
            return {"date": str(day), "children": []}

        summaries = []
        for child in children:
            cid = child.child_session_id

            # App usage del día
            usage_result = await db.execute(
                select(AppUsageEvent)
                .where(AppUsageEvent.child_session_id == cid, AppUsageEvent.event_date == day)
                .order_by(AppUsageEvent.foreground_ms.desc())
            )
            usage = usage_result.scalars().all()

            # Notificaciones del día
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            notif_result = await db.execute(
                select(NotificationEvent)
                .where(
                    NotificationEvent.child_session_id == cid,
                    NotificationEvent.posted_at >= day_start,
                    NotificationEvent.posted_at <= day_end,
                )
            )
            notifs = notif_result.scalars().all()

            # Navegación del día
            browser_result = await db.execute(
                select(BrowserEvent)
                .where(
                    BrowserEvent.child_session_id == cid,
                    BrowserEvent.visited_at >= day_start,
                    BrowserEvent.visited_at <= day_end,
                )
                .order_by(BrowserEvent.visited_at.desc())
            )
            browser = browser_result.scalars().all()

            # Instalaciones del día
            pkg_result = await db.execute(
                select(PackageEvent)
                .where(
                    PackageEvent.child_session_id == cid,
                    PackageEvent.occurred_at >= day_start,
                    PackageEvent.occurred_at <= day_end,
                )
            )
            pkgs = pkg_result.scalars().all()

            suspicious = [n for n in notifs if n.is_suspicious]

            summaries.append({
                "child_session_id": cid,
                "device_label": child.device_label,
                "date": str(day),
                "screen_time_total_min": sum(u.foreground_ms for u in usage) // 60000,
                "top_apps": [
                    {"app": u.app_label, "minutes": u.foreground_ms // 60000, "launches": u.launches}
                    for u in usage[:8]
                ],
                "notifications_total": len(notifs),
                "notifications_by_app": _group_notifs(notifs),
                "suspicious_alerts": [
                    {"app": n.package_name, "title": n.title, "body": n.body, "at": str(n.posted_at)}
                    for n in suspicious
                ],
                "websites_visited": list({b.domain for b in browser}),
                "installs": [p.app_label or p.package_name for p in pkgs if p.event_type == "install"],
                "uninstalls": [p.app_label or p.package_name for p in pkgs if p.event_type == "uninstall"],
            })

    return {"date": str(day), "children": summaries}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url[:50]


def _group_notifs(notifs) -> list:
    counts: dict[str, int] = {}
    for n in notifs:
        counts[n.package_name] = counts.get(n.package_name, 0) + 1
    return [{"package": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])[:6]]
