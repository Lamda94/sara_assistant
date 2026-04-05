from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.db.postgres import SessionLocal
from app.models.device_token import DeviceToken
from app.models.proactive_insight import ProactiveInsight

router = APIRouter(prefix="/notifications", tags=["notifications"])


class TokenRequest(BaseModel):
    session_id: str
    token: str


@router.post("/register-token")
async def register_token(req: TokenRequest):
    """Registra o actualiza el FCM token de un dispositivo."""
    async with SessionLocal() as s:
        stmt = insert(DeviceToken).values(
            session_id=req.session_id,
            token=req.token,
        ).on_conflict_do_update(
            index_elements=["session_id"],
            set_={"token": req.token},
        )
        await s.execute(stmt)
        await s.commit()
    return {"status": "ok"}


@router.get("/insights/all")
async def get_all_insights():
    """Lista TODOS los insights no descartados de todos los usuarios (para creador)."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(ProactiveInsight)
            .where(ProactiveInsight.dismissed == False)     # noqa: E712
            .order_by(ProactiveInsight.created_at.desc())
            .limit(100)
        )
        rows = r.scalars().all()

    return [
        {
            "id": ins.id,
            "session_id": ins.session_id,
            "type": ins.insight_type,
            "content": ins.content,
            "due_date": ins.due_date.isoformat() if ins.due_date else None,
            "notified": ins.notified,
            "created_at": ins.created_at.isoformat() if ins.created_at else None,
        }
        for ins in rows
    ]


@router.get("/insights/{session_id}")
async def get_insights(session_id: str):
    """Lista insights proactivos pendientes (no descartados) para una sesión."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(ProactiveInsight)
            .where(
                ProactiveInsight.session_id == session_id,
                ProactiveInsight.dismissed == False,        # noqa: E712
            )
            .order_by(ProactiveInsight.created_at.desc())
            .limit(20)
        )
        rows = r.scalars().all()

    return [
        {
            "id": ins.id,
            "session_id": ins.session_id,
            "type": ins.insight_type,
            "content": ins.content,
            "due_date": ins.due_date.isoformat() if ins.due_date else None,
            "notified": ins.notified,
            "created_at": ins.created_at.isoformat() if ins.created_at else None,
        }
        for ins in rows
    ]


@router.post("/dismiss/{insight_id}")
async def dismiss_insight(insight_id: str):
    """Marca un insight proactivo como descartado."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(ProactiveInsight).where(ProactiveInsight.id == insight_id)
        )
        ins = r.scalar_one_or_none()
        if not ins:
            return {"status": "not_found"}
        ins.dismissed = True
        await s.commit()
    return {"status": "ok"}
