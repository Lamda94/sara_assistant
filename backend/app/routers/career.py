"""CareerRouter — Endpoints REST para las vistas de CareerOps."""
from typing import Optional
from fastapi import APIRouter, Request, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sqlfunc
from app.db.postgres import SessionLocal
from app.models.career import CareerApplication, CareerProfile, CareerActivityLog, CareerPortal
from app.limiter import limiter
from app.config import settings

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


# ── Profile ──────────────────────────────────────────────────────────


class ProfileBody(BaseModel):
    full_name: str = Field(..., max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=200)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    cv_markdown: Optional[str] = Field(None, max_length=50000)
    target_roles: Optional[list[str]] = None
    compensation: Optional[dict] = None
    title_positive: Optional[list[str]] = None
    title_negative: Optional[list[str]] = None
    scan_interval_hours: int = Field(6, ge=1, le=48)
    min_score_cv: float = Field(4.0, ge=1.0, le=5.0)


@router.get("/profile")
@limiter.limit("30/minute")
async def get_profile(request: Request, session_id: str = ""):
    """Obtener perfil profesional."""
    if not session_id:
        return {"profile": None}
    async with SessionLocal() as s:
        profile = (await s.execute(
            select(CareerProfile).where(CareerProfile.session_id == session_id)
        )).scalar_one_or_none()

    if not profile:
        return {"profile": None}

    return {
        "profile": {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "linkedin_url": profile.linkedin_url,
            "portfolio_url": profile.portfolio_url,
            "github_url": profile.github_url,
            "cv_markdown": profile.cv_markdown,
            "target_roles": profile.target_roles,
            "compensation": profile.compensation,
            "title_positive": profile.title_positive,
            "title_negative": profile.title_negative,
            "career_mode": profile.career_mode,
            "scan_interval_hours": profile.scan_interval_hours,
            "min_score_cv": profile.min_score_cv,
        }
    }


@router.post("/profile")
@limiter.limit("10/minute")
async def save_profile(request: Request, body: ProfileBody, session_id: str = ""):
    """Crear o actualizar perfil profesional."""
    if not session_id:
        return {"error": "session_id requerido"}

    async with SessionLocal() as s:
        profile = (await s.execute(
            select(CareerProfile).where(CareerProfile.session_id == session_id)
        )).scalar_one_or_none()

        if not profile:
            profile = CareerProfile(session_id=session_id)
            s.add(profile)

        profile.full_name = body.full_name
        profile.email = body.email
        profile.phone = body.phone
        profile.location = body.location
        profile.linkedin_url = body.linkedin_url
        profile.portfolio_url = body.portfolio_url
        profile.github_url = body.github_url
        profile.cv_markdown = body.cv_markdown
        profile.target_roles = body.target_roles
        profile.compensation = body.compensation
        profile.title_positive = body.title_positive
        profile.title_negative = body.title_negative
        profile.scan_interval_hours = body.scan_interval_hours
        profile.min_score_cv = body.min_score_cv

        await s.commit()

    return {"ok": True}


@router.post("/toggle")
@limiter.limit("10/minute")
async def toggle_career_mode(request: Request, session_id: str = ""):
    """Activar/desactivar modo búsqueda."""
    if not session_id:
        return {"error": "session_id requerido"}

    async with SessionLocal() as s:
        profile = (await s.execute(
            select(CareerProfile).where(CareerProfile.session_id == session_id)
        )).scalar_one_or_none()

        if not profile:
            return {"error": "Perfil no configurado"}

        if not profile.cv_markdown:
            return {"error": "CV requerido para activar"}

        profile.career_mode = not profile.career_mode
        await s.commit()
        new_mode = profile.career_mode

    return {"ok": True, "career_mode": new_mode}


# ── Portals ──────────────────────────────────────────────────────────


class PortalBody(BaseModel):
    company_name: str = Field(..., max_length=200)
    careers_url: str = Field(..., max_length=500)
    ats_provider: Optional[str] = Field(None, max_length=50)


@router.get("/portals")
@limiter.limit("30/minute")
async def get_portals(request: Request, session_id: str = ""):
    """Listar portales configurados."""
    async with SessionLocal() as s:
        query = select(CareerPortal).order_by(CareerPortal.company_name)
        if session_id:
            query = query.where(CareerPortal.session_id == session_id)
        r = await s.execute(query)
        portals = r.scalars().all()

    return [
        {
            "id": p.id,
            "company_name": p.company_name,
            "careers_url": p.careers_url,
            "ats_provider": p.ats_provider,
            "enabled": p.enabled,
            "last_scanned_at": p.last_scanned_at.isoformat() if p.last_scanned_at else None,
        }
        for p in portals
    ]


@router.post("/portals")
@limiter.limit("10/minute")
async def add_portal(request: Request, body: PortalBody, session_id: str = ""):
    """Agregar un portal."""
    if not session_id:
        return {"error": "session_id requerido"}

    # Detectar ATS provider
    ats = body.ats_provider
    if not ats:
        url = body.careers_url.lower()
        if "greenhouse" in url:
            ats = "greenhouse"
        elif "ashbyhq" in url:
            ats = "ashby"
        elif "lever.co" in url:
            ats = "lever"
        elif "workday" in url:
            ats = "workday"

    async with SessionLocal() as s:
        portal = CareerPortal(
            session_id=session_id,
            company_name=body.company_name,
            careers_url=body.careers_url,
            ats_provider=ats,
        )
        s.add(portal)
        await s.commit()
        pid = portal.id

    return {"ok": True, "id": pid}


@router.delete("/portals/{portal_id}")
@limiter.limit("10/minute")
async def delete_portal(request: Request, portal_id: int):
    """Eliminar un portal."""
    async with SessionLocal() as s:
        portal = (await s.execute(
            select(CareerPortal).where(CareerPortal.id == portal_id)
        )).scalar_one_or_none()
        if portal:
            await s.delete(portal)
            await s.commit()
    return {"ok": True}


# ── CV Parser ────────────────────────────────────────────────────────

_MAX_CV_BYTES = 5 * 1024 * 1024  # 5MB

@router.post("/parse-cv")
@limiter.limit("5/minute")
async def parse_cv(request: Request, file: UploadFile = File(...)):
    """
    Recibe un CV (PDF o texto) y usa el LLM para extraer perfil profesional.
    Retorna todos los campos del perfil autocompletados.
    """
    content = await file.read()
    if len(content) > _MAX_CV_BYTES:
        return {"error": "Archivo muy grande (máximo 5MB)"}

    filename = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        cv_text = _extract_pdf_text(content)
    else:
        cv_text = content.decode("utf-8", errors="replace")

    if not cv_text or len(cv_text.strip()) < 50:
        return {"error": "No se pudo extraer texto del archivo"}

    from groq import AsyncGroq
    groq = AsyncGroq(api_key=settings.groq_api_key)

    resp = await groq.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un parser de CVs profesional. Extrae la información del CV y responde "
                    "SOLO en JSON con esta estructura exacta:\n"
                    "{\n"
                    '  "full_name": "nombre completo",\n'
                    '  "email": "email o null",\n'
                    '  "phone": "teléfono o null",\n'
                    '  "location": "ciudad, país o null",\n'
                    '  "linkedin_url": "url linkedin o null",\n'
                    '  "portfolio_url": "url portfolio o null",\n'
                    '  "github_url": "url github o null",\n'
                    '  "target_roles": ["rol1", "rol2"] basado en experiencia reciente,\n'
                    '  "title_positive": ["keyword1", "keyword2"] tecnologías y skills principales,\n'
                    '  "title_negative": ["keyword1"] tecnologías que NO maneja,\n'
                    '  "cv_markdown": "el CV completo convertido a formato Markdown limpio"\n'
                    "}\n"
                    "Para cv_markdown: convierte todo el contenido a Markdown bien estructurado con "
                    "# para nombre, ## para secciones (Experiencia, Educación, Skills, etc.), "
                    "### para cada puesto, y - para items. Mantén toda la información original."
                ),
            },
            {
                "role": "user",
                "content": f"CV:\n\n{cv_text[:15000]}",
            },
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    import json
    try:
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
    except Exception:
        return {"error": "No se pudo parsear el CV", "raw": resp.choices[0].message.content}

    return {"ok": True, "profile": parsed}


def _extract_pdf_text(content: bytes) -> str:
    """Extrae texto de un PDF."""
    import io
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages[:20]]
            return "\n\n".join(pages)
    except ImportError:
        pass
    try:
        import re
        text = content.decode("latin-1", errors="replace")
        parts = re.findall(r'\(([^)]+)\)', text)
        return " ".join(parts)[:15000]
    except Exception:
        return ""
