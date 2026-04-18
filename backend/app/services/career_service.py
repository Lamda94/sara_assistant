"""
CareerOps — Job programado de escaneo automático.

Corre cada 6h (configurable). Solo ejecuta si career_mode=True.
Escanea portales → evalúa ofertas → genera CVs si score >= min_score_cv.
"""
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy import select

from app.config import settings
from app.db.postgres import SessionLocal
from app.models.career import (
    CareerProfile, CareerApplication, CareerActivityLog, CareerScanHistory,
)

logger = logging.getLogger(__name__)

_CAREER_URL = "http://sara_career:4000"


async def career_auto_scan():
    """Job principal — escanea y evalúa si el modo está activo."""
    logger.info("[CareerOps] Verificando modo de búsqueda...")

    # Buscar perfiles con career_mode activo
    async with SessionLocal() as s:
        r = await s.execute(
            select(CareerProfile).where(CareerProfile.career_mode == True)
        )
        active_profiles = r.scalars().all()

    if not active_profiles:
        logger.info("[CareerOps] No hay perfiles con búsqueda activa.")
        return

    for profile in active_profiles:
        try:
            await _run_cycle(profile)
        except Exception as e:
            logger.error("[CareerOps] Error en ciclo para %s: %s", profile.session_id, e)


async def _run_cycle(profile: CareerProfile):
    """Ejecuta un ciclo completo de escaneo + evaluación para un perfil."""
    session_id = profile.session_id
    t0 = time.time()
    log = CareerActivityLog(session_id=session_id, cycle_date=datetime.utcnow())

    logger.warning("[CareerOps] Iniciando ciclo para %s...", session_id)

    # 1. Escanear portales
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{_CAREER_URL}/scan")
            r.raise_for_status()
            scan_data = r.json()
    except Exception as e:
        logger.error("[CareerOps] Error escaneando: %s", e)
        log.errors = str(e)
        log.duration_seconds = round(time.time() - t0, 2)
        await _save_log(log)
        return

    offers = scan_data.get("offers", [])
    log.vacancies_found = len(offers)
    log.portals_scanned = scan_data.get("portals_scanned", 0)

    if not offers:
        logger.info("[CareerOps] No hay ofertas nuevas.")
        log.duration_seconds = round(time.time() - t0, 2)
        await _save_log(log)
        return

    # 2. Guardar en scan history
    async with SessionLocal() as s:
        for offer in offers:
            s.add(CareerScanHistory(
                session_id=session_id,
                url=offer.get("url", ""),
                company=offer.get("company", ""),
                title=offer.get("title", ""),
                portal_source=offer.get("source", ""),
                status="added",
            ))
        await s.commit()

    # 3. Evaluar cada oferta
    evaluated = 0
    cv_generated = 0
    top_score = 0
    top_company = ""
    top_role = ""

    # Filtrar solo ofertas de engineering/desarrollo y limitar a 10 por ciclo
    eng_keywords = {"engineer", "developer", "desarrollador", "architect", "lead", "software", "backend", "frontend", "full stack", "devops", "sre", "platform"}
    eval_candidates = []
    for o in offers:
        if not o.get("url"):
            continue
        title_lower = (o.get("title") or "").lower()
        if any(kw in title_lower for kw in eng_keywords):
            eval_candidates.append(o)
        if len(eval_candidates) >= 10:
            break

    for offer in eval_candidates:
        try:
            # Evaluar
            async with httpx.AsyncClient(timeout=180) as client:
                r = await client.post(f"{_CAREER_URL}/evaluate", json={
                    "url": offer.get("url", ""),
                    "company": offer.get("company", ""),
                    "title": offer.get("title", ""),
                })
                if r.status_code != 200:
                    logger.warning("[CareerOps] Evaluate retornó %d para %s", r.status_code, offer.get("title"))
                    continue
                eval_data = r.json()

            score = eval_data.get("score") or 0
            if isinstance(score, str):
                try:
                    score = float(score)
                except ValueError:
                    score = 0
            evaluated += 1

            # Guardar aplicación
            async with SessionLocal() as s:
                app = CareerApplication(
                    session_id=session_id,
                    company=offer.get("company", eval_data.get("company", "?")),
                    role=offer.get("title", eval_data.get("role", "?")),
                    url=offer.get("url"),
                    portal_source=offer.get("source"),
                    score=score,
                    compatibility_pct=eval_data.get("compatibility_pct"),
                    archetype=eval_data.get("archetype"),
                    evaluation_blocks=eval_data.get("blocks"),
                    evaluation_summary=eval_data.get("summary"),
                    legitimacy=eval_data.get("legitimacy"),
                )

                # Si score >= min_score_cv, generar CV
                if score >= (profile.min_score_cv or 4.0):
                    try:
                        async with httpx.AsyncClient(timeout=120) as cv_client:
                            cv_r = await cv_client.post(f"{_CAREER_URL}/generate-cv", json={
                                "company": app.company,
                                "role": app.role,
                                "cv_changes": eval_data.get("cv_changes"),
                            })
                            if cv_r.status_code == 200:
                                cv_data = cv_r.json()
                                app.cv_path = cv_data.get("path")
                                app.status = "cv_generated"
                                cv_generated += 1
                    except Exception:
                        pass

                s.add(app)
                await s.commit()

            if score > top_score:
                top_score = score
                top_company = app.company
                top_role = app.role

        except Exception as e:
            logger.error("[CareerOps] Error evaluando %s: %s", offer.get("url", "?"), e)

    # 4. Actualizar log
    log.vacancies_evaluated = evaluated
    log.vacancies_cv_generated = cv_generated
    log.top_score = top_score if top_score > 0 else None
    log.top_company = top_company or None
    log.top_role = top_role or None
    log.duration_seconds = round(time.time() - t0, 2)

    await _save_log(log)

    # 5. Notificar si hay ofertas buenas
    if top_score >= 4.0:
        await _notify_good_match(session_id, top_company, top_role, top_score, evaluated, cv_generated)

    logger.warning(
        "[CareerOps] Ciclo completado: %d encontradas, %d evaluadas, %d CVs, top: %.1f (%s)",
        len(offers), evaluated, cv_generated, top_score, top_company,
    )


async def _save_log(log: CareerActivityLog):
    """Guarda el log del ciclo."""
    async with SessionLocal() as s:
        s.add(log)
        await s.commit()


async def _notify_good_match(session_id: str, company: str, role: str, score: float,
                              evaluated: int, cv_generated: int):
    """Envía push notification cuando hay una oferta con buen score."""
    try:
        from app.services.notification_service import _send_push, _init_firebase
        from app.models.device_token import DeviceToken

        _init_firebase()

        async with SessionLocal() as s:
            r = await s.execute(
                select(DeviceToken).where(DeviceToken.session_id.contains(settings.creator_id))
            )
            token = r.scalar_one_or_none()
            if token:
                await _send_push(
                    token.token,
                    "🎯 CareerOps — Match encontrado",
                    f"{company} — {role}: {score}/5 ({evaluated} evaluadas, {cv_generated} CVs)",
                )
    except Exception as e:
        logger.error("[CareerOps] Error enviando push: %s", e)
