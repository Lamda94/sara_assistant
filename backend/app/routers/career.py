"""CareerRouter — Endpoints REST para las vistas de CareerOps."""
from fastapi import APIRouter, Request
from sqlalchemy import select, func as sqlfunc
from app.db.postgres import SessionLocal
from app.models.career import CareerApplication, CareerProfile, CareerActivityLog
from app.limiter import limiter

router = APIRouter(prefix="/career", tags=["career"])


@router.get("/status")
@limiter.limit("30/minute")
async def get_status(request: Request, session_id: str = ""):
    """Estado general de CareerOps."""
    async with SessionLocal() as s:
        profile = None
        if session_id:
            profile = (await s.execute(
                select(CareerProfile).where(CareerProfile.session_id == session_id)
            )).scalar_one_or_none()

        total = (await s.execute(select(sqlfunc.count(CareerApplication.id)))).scalar() or 0

        by_status = {}
        for status in ["evaluated", "cv_generated", "applied", "interview", "offer", "rejected"]:
            count = (await s.execute(
                select(sqlfunc.count(CareerApplication.id))
                .where(CareerApplication.status == status)
            )).scalar() or 0
            by_status[status] = count

        last_log = (await s.execute(
            select(CareerActivityLog).order_by(CareerActivityLog.created_at.desc()).limit(1)
        )).scalar_one_or_none()

    return {
        "career_mode": profile.career_mode if profile else False,
        "total_applications": total,
        "by_status": by_status,
        "last_scan": {
            "date": last_log.cycle_date.isoformat() if last_log and last_log.cycle_date else None,
            "found": last_log.vacancies_found if last_log else 0,
            "evaluated": last_log.vacancies_evaluated if last_log else 0,
            "cv_generated": last_log.vacancies_cv_generated if last_log else 0,
        } if last_log else None,
    }


@router.get("/applications")
@limiter.limit("30/minute")
async def get_applications(request: Request, limit: int = 20):
    """Lista de aplicaciones/evaluaciones."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(CareerApplication).order_by(CareerApplication.created_at.desc()).limit(limit)
        )
        apps = r.scalars().all()

    return [
        {
            "id": a.id,
            "company": a.company,
            "role": a.role,
            "url": a.url,
            "portal_source": a.portal_source,
            "score": a.score,
            "compatibility_pct": a.compatibility_pct,
            "archetype": a.archetype,
            "evaluation_summary": a.evaluation_summary,
            "evaluation_blocks": a.evaluation_blocks,
            "cv_path": a.cv_path,
            "legitimacy": a.legitimacy,
            "status": a.status,
            "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in apps
    ]


@router.get("/activity")
@limiter.limit("30/minute")
async def get_activity(request: Request, limit: int = 10):
    """Historial de ciclos de escaneo."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(CareerActivityLog).order_by(CareerActivityLog.created_at.desc()).limit(limit)
        )
        logs = r.scalars().all()

    return [
        {
            "id": l.id,
            "cycle_date": l.cycle_date.isoformat() if l.cycle_date else None,
            "portals_scanned": l.portals_scanned,
            "vacancies_found": l.vacancies_found,
            "vacancies_evaluated": l.vacancies_evaluated,
            "vacancies_cv_generated": l.vacancies_cv_generated,
            "top_score": l.top_score,
            "top_company": l.top_company,
            "top_role": l.top_role,
            "duration_seconds": l.duration_seconds,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
