from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from app.db.postgres import SessionLocal
from app.models.device_token import DeviceToken

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
