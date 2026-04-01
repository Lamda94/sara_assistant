"""
AuthRouter — Control de acceso a la web app.

GET  /auth/check?email=...   → {"approved": true/false}
POST /auth/request           → registra solicitud de acceso
GET  /auth/pending           → lista solicitudes pendientes (solo creador)
POST /auth/approve           → aprueba un usuario
DELETE /auth/revoke          → revoca acceso
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from app.db.postgres import SessionLocal as AsyncSessionLocal
from app.models.approved_user import ApprovedUser

router = APIRouter(prefix="/auth", tags=["auth"])

CREATOR_EMAIL = "lamda94@gmail.com"


def normalize_email(email: str) -> str:
    email = email.lower().strip()
    local, _, domain = email.partition("@")
    if domain == "gmail.com":
        local = local.replace(".", "")
    return f"{local}@{domain}"


def is_creator(email: str) -> bool:
    return normalize_email(email) == normalize_email(CREATOR_EMAIL)


class RequestAccessBody(BaseModel):
    email: str
    name: Optional[str] = None


class ApproveBody(BaseModel):
    email: str


@router.get("/check")
async def check_approval(email: str = Query(...)):
    if is_creator(email):
        return {"approved": True, "is_creator": True}
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ApprovedUser).where(ApprovedUser.email == email))
        user = result.scalar_one_or_none()
    if not user:
        return {"approved": False, "is_creator": False}
    return {"approved": user.approved, "is_creator": False}


@router.post("/request")
async def request_access(body: RequestAccessBody):
    if is_creator(body.email):
        return {"status": "creator"}
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ApprovedUser).where(ApprovedUser.email == body.email))
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(ApprovedUser(email=body.email, name=body.name, approved=False))
            await db.commit()
            return {"status": "requested"}
        return {"status": "already_requested", "approved": existing.approved}


@router.get("/pending")
async def list_pending():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ApprovedUser).where(ApprovedUser.approved == False).order_by(ApprovedUser.requested_at.desc())
        )
        users = result.scalars().all()
    return [{"email": u.email, "name": u.name, "requested_at": u.requested_at} for u in users]


@router.get("/approved")
async def list_approved():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ApprovedUser).where(ApprovedUser.approved == True).order_by(ApprovedUser.approved_at.desc())
        )
        users = result.scalars().all()
    return [{"email": u.email, "name": u.name, "approved_at": u.approved_at} for u in users]


@router.post("/approve")
async def approve_user(body: ApproveBody):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ApprovedUser).where(ApprovedUser.email == body.email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.approved = True
        user.approved_at = datetime.utcnow()
        await db.commit()
    return {"status": "approved", "email": body.email}


@router.delete("/revoke")
async def revoke_user(email: str = Query(...)):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ApprovedUser).where(ApprovedUser.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.approved = False
        await db.commit()
    return {"status": "revoked", "email": email}
