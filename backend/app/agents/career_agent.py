"""
CareerOps Agent — Búsqueda de empleo autónoma.

Bridge entre SARA y el contenedor career-ops (sara_career:4000).
Actions: activate, deactivate, scan, evaluate, cv, status, prep, profile, portals
"""
import logging
from datetime import datetime

import httpx
from app.config import settings
from .base import BaseAgent

logger = logging.getLogger(__name__)

_CAREER_URL = "http://sara_career:4000"


class CareerAgent(BaseAgent):
    name = "career"
    description = (
        "Agente de búsqueda de empleo CareerOps. "
        "Activa/desactiva modo búsqueda, escanea portales de empleo, "
        "evalúa ofertas con scoring A-F, genera CVs personalizados, "
        "prepara entrevistas y trackea aplicaciones."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "activate", "deactivate", "scan", "evaluate",
                    "cv", "status", "prep", "profile", "portals",
                ],
                "description": (
                    "activate: activa modo búsqueda. "
                    "deactivate: desactiva modo búsqueda. "
                    "scan: escanear portales ahora. "
                    "evaluate: evaluar una oferta (URL o texto). "
                    "cv: generar CV personalizado. "
                    "status: ver estado y aplicaciones. "
                    "prep: preparación de entrevista. "
                    "profile: ver/editar perfil profesional. "
                    "portals: gestionar portales."
                ),
            },
            "url": {
                "type": "string",
                "description": "URL de la oferta de empleo (para evaluate)",
            },
            "jd_text": {
                "type": "string",
                "description": "Texto del job description (para evaluate, alternativa a url)",
            },
            "company": {
                "type": "string",
                "description": "Nombre de empresa (para prep, scan, portals)",
            },
            "role": {
                "type": "string",
                "description": "Nombre del rol (para prep)",
            },
            "evaluation_id": {
                "type": "string",
                "description": "ID de evaluación (para cv)",
            },
        },
        "required": ["action"],
    }

    async def run(self, action: str, session_id: str = "", url: str = "",
                  jd_text: str = "", company: str = "", role: str = "",
                  evaluation_id: str = "", **_) -> str:
        try:
            if action == "activate":
                return await self._activate(session_id)
            elif action == "deactivate":
                return await self._deactivate(session_id)
            elif action == "scan":
                return await self._scan(session_id, company)
            elif action == "evaluate":
                return await self._evaluate(session_id, url, jd_text)
            elif action == "cv":
                return await self._generate_cv(session_id, evaluation_id)
            elif action == "status":
                return await self._status(session_id)
            elif action == "prep":
                return await self._prep(session_id, company, role)
            elif action == "profile":
                return await self._profile(session_id)
            elif action == "portals":
                return await self._portals(session_id, company)
            else:
                return f"Acción desconocida: {action}"
        except Exception as e:
            logger.error(f"CareerOps error ({action}): {e}")
            return f"Error en CareerOps: {str(e)}"

    # ─── ACTIVATE ────────────────────────────────────────────

    async def _activate(self, session_id: str) -> str:
        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.career import CareerProfile

        async with SessionLocal() as s:
            profile = (await s.execute(
                select(CareerProfile).where(CareerProfile.session_id == session_id)
            )).scalar_one_or_none()

            if not profile:
                return (
                    "No tienes un perfil profesional configurado. "
                    "Primero necesito tu CV y datos básicos. "
                    "Dime tu nombre, roles objetivo y experiencia, o pega tu CV."
                )

            if not profile.cv_markdown:
                return "Tu perfil existe pero no tiene CV. Pega tu CV para activar la búsqueda."

            profile.career_mode = True
            await s.commit()

        return (
            "✅ **Modo búsqueda activado.** SARA escaneará portales cada "
            f"{profile.scan_interval_hours}h buscando ofertas que encajen con tu perfil. "
            "Te notificaré cuando encuentre algo interesante."
        )

    # ─── DEACTIVATE ──────────────────────────────────────────

    async def _deactivate(self, session_id: str) -> str:
        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.career import CareerProfile

        async with SessionLocal() as s:
            profile = (await s.execute(
                select(CareerProfile).where(CareerProfile.session_id == session_id)
            )).scalar_one_or_none()
            if profile:
                profile.career_mode = False
                await s.commit()

        return "⏸️ **Modo búsqueda desactivado.** Tu historial se mantiene."

    # ─── SCAN ────────────────────────────────────────────────

    async def _scan(self, session_id: str, company: str = "") -> str:
        # Call career container
        try:
            body = {}
            if company:
                body["company"] = company
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(f"{_CAREER_URL}/scan", json=body)
                r.raise_for_status()
                data = r.json()
        except httpx.ConnectError:
            return "El contenedor career-ops no está disponible. Verifica que esté corriendo."
        except Exception as e:
            return f"Error al escanear: {e}"

        offers = data.get("offers", [])
        found = data.get("found", 0)

        if not offers:
            return "No se encontraron ofertas nuevas en los portales configurados."

        # Save to scan history
        from app.db.postgres import SessionLocal
        from app.models.career import CareerScanHistory

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

        lines = [f"📡 **Escaneo completado** — {found} ofertas nuevas encontradas\n"]
        for i, o in enumerate(offers[:10], 1):
            lines.append(f"{i}. **{o.get('company', '?')}** — {o.get('title', '?')}\n   {o.get('url', '')}")

        if found > 10:
            lines.append(f"\n... y {found - 10} más.")

        return "\n\n".join(lines)

    # ─── EVALUATE ────────────────────────────────────────────

    async def _evaluate(self, session_id: str, url: str = "", jd_text: str = "") -> str:
        if not url and not jd_text:
            return "Necesito la URL de la oferta o el texto del job description."

        try:
            body = {}
            if url:
                body["url"] = url
            if jd_text:
                body["jd_text"] = jd_text

            async with httpx.AsyncClient(timeout=180) as client:
                r = await client.post(f"{_CAREER_URL}/evaluate", json=body)
                r.raise_for_status()
                data = r.json()
        except httpx.ConnectError:
            return "El contenedor career-ops no está disponible."
        except Exception as e:
            return f"Error al evaluar: {e}"

        # Save evaluation
        from app.db.postgres import SessionLocal
        from app.models.career import CareerApplication

        score = data.get("score", 0)
        compat = data.get("compatibility_pct", 0)

        async with SessionLocal() as s:
            app = CareerApplication(
                session_id=session_id,
                company=data.get("company", "Desconocida"),
                role=data.get("role", "Desconocido"),
                url=url or None,
                jd_text=jd_text or data.get("jd_text"),
                score=score,
                compatibility_pct=compat,
                archetype=data.get("archetype"),
                evaluation_blocks=data.get("blocks"),
                evaluation_summary=data.get("summary"),
                legitimacy=data.get("legitimacy", "unknown"),
            )
            s.add(app)
            await s.commit()
            app_id = app.id

        # Format response
        score_emoji = "🟢" if score >= 4.5 else "🟡" if score >= 4.0 else "🟠" if score >= 3.5 else "🔴"
        return (
            f"📋 **Evaluación completada** (ID: {app_id[:8]})\n\n"
            f"{score_emoji} **Score: {score}/5.0** | Compatibilidad: {compat}%\n"
            f"Arquetipo: {data.get('archetype', 'N/A')}\n"
            f"Legitimidad: {data.get('legitimacy', 'N/A')}\n\n"
            f"**Resumen:**\n{data.get('summary', 'Sin resumen')}\n\n"
            f"{'⚡ Score alto — recomiendo aplicar.' if score >= 4.0 else '⚠️ Score bajo — evalúa si vale la pena.'}"
        )

    # ─── GENERATE CV ─────────────────────────────────────────

    async def _generate_cv(self, session_id: str, evaluation_id: str = "") -> str:
        if not evaluation_id:
            return "Necesito el ID de la evaluación para personalizar el CV. Usa 'status' para ver tus evaluaciones."

        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.career import CareerApplication

        async with SessionLocal() as s:
            app = (await s.execute(
                select(CareerApplication).where(
                    CareerApplication.id.startswith(evaluation_id),
                    CareerApplication.session_id == session_id,
                )
            )).scalar_one_or_none()

        if not app:
            return f"No encontré evaluación con ID {evaluation_id}."

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(f"{_CAREER_URL}/generate-cv", json={
                    "evaluation_id": evaluation_id,
                    "company": app.company,
                    "role": app.role,
                    "cv_changes": app.cv_changes,
                })
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            return f"Error generando CV: {e}"

        # Update application
        async with SessionLocal() as s:
            app_db = (await s.execute(
                select(CareerApplication).where(CareerApplication.id == app.id)
            )).scalar_one_or_none()
            if app_db:
                app_db.cv_path = data.get("path")
                app_db.status = "cv_generated"
                await s.commit()

        return (
            f"📄 **CV generado** para {app.company} — {app.role}\n"
            f"Archivo: {data.get('path', 'N/A')}\n"
            f"Optimizado para ATS."
        )

    # ─── STATUS ──────────────────────────────────────────────

    async def _status(self, session_id: str) -> str:
        from sqlalchemy import select, func as sqlfunc
        from app.db.postgres import SessionLocal
        from app.models.career import CareerApplication, CareerProfile, CareerActivityLog

        async with SessionLocal() as s:
            profile = (await s.execute(
                select(CareerProfile).where(CareerProfile.session_id == session_id)
            )).scalar_one_or_none()

            total = (await s.execute(
                select(sqlfunc.count(CareerApplication.id))
                .where(CareerApplication.session_id == session_id)
            )).scalar() or 0

            by_status = {}
            for status in ["evaluated", "cv_generated", "applied", "interview", "offer", "rejected", "discarded"]:
                count = (await s.execute(
                    select(sqlfunc.count(CareerApplication.id))
                    .where(CareerApplication.session_id == session_id)
                    .where(CareerApplication.status == status)
                )).scalar() or 0
                if count > 0:
                    by_status[status] = count

            # Last 5 applications
            r = await s.execute(
                select(CareerApplication)
                .where(CareerApplication.session_id == session_id)
                .order_by(CareerApplication.created_at.desc())
                .limit(5)
            )
            recent = r.scalars().all()

            # Last scan
            last_log = (await s.execute(
                select(CareerActivityLog)
                .where(CareerActivityLog.session_id == session_id)
                .order_by(CareerActivityLog.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()

        mode = "🟢 ACTIVO" if profile and profile.career_mode else "⏸️ INACTIVO"
        status_line = " | ".join(f"{s}: {c}" for s, c in by_status.items())

        lines = [
            f"📊 **CareerOps — Estado**\n",
            f"Modo: {mode}",
            f"Total aplicaciones: {total}",
        ]

        if status_line:
            lines.append(f"Desglose: {status_line}")

        if last_log:
            lines.append(
                f"Último escaneo: {last_log.cycle_date.strftime('%d/%m %H:%M') if last_log.cycle_date else 'N/A'} "
                f"({last_log.vacancies_found} encontradas)"
            )

        if recent:
            lines.append("\n**Últimas evaluaciones:**")
            for i, app in enumerate(recent, 1):
                score_emoji = "🟢" if (app.score or 0) >= 4.0 else "🟡" if (app.score or 0) >= 3.5 else "🔴"
                lines.append(
                    f"{i}. {score_emoji} **{app.company}** — {app.role}\n"
                    f"   Score: {app.score or '?'}/5 | {app.status} | {app.id[:8]}"
                )

        return "\n".join(lines)

    # ─── INTERVIEW PREP ─────────────────────────────────────

    async def _prep(self, session_id: str, company: str, role: str = "") -> str:
        if not company:
            return "Necesito el nombre de la empresa para preparar la entrevista."

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(f"{_CAREER_URL}/interview-prep", json={
                    "company": company, "role": role,
                })
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            return f"Error preparando entrevista: {e}"

        return data.get("prep_text", "No se pudo generar la preparación.")

    # ─── PROFILE ─────────────────────────────────────────────

    async def _profile(self, session_id: str) -> str:
        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.career import CareerProfile

        async with SessionLocal() as s:
            profile = (await s.execute(
                select(CareerProfile).where(CareerProfile.session_id == session_id)
            )).scalar_one_or_none()

        if not profile:
            return (
                "No tienes perfil configurado. Dime:\n"
                "- Tu nombre completo\n"
                "- Roles que buscas (ej: 'Senior Backend Engineer')\n"
                "- Tu experiencia resumida o pega tu CV\n"
                "- Rango salarial objetivo"
            )

        roles = ", ".join(profile.target_roles) if profile.target_roles else "No configurados"
        return (
            f"👤 **Perfil CareerOps**\n\n"
            f"Nombre: {profile.full_name}\n"
            f"Roles objetivo: {roles}\n"
            f"Ubicación: {profile.location or 'N/A'}\n"
            f"LinkedIn: {profile.linkedin_url or 'N/A'}\n"
            f"CV: {'✅ Cargado' if profile.cv_markdown else '❌ No cargado'}\n"
            f"Modo búsqueda: {'🟢 Activo' if profile.career_mode else '⏸️ Inactivo'}\n"
            f"Escaneo cada: {profile.scan_interval_hours}h\n"
            f"Score mínimo para CV: {profile.min_score_cv}/5"
        )

    # ─── PORTALS ─────────────────────────────────────────────

    async def _portals(self, session_id: str, company: str = "") -> str:
        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.career import CareerPortal

        async with SessionLocal() as s:
            r = await s.execute(
                select(CareerPortal)
                .where(CareerPortal.session_id == session_id)
                .order_by(CareerPortal.company_name)
            )
            portals = r.scalars().all()

        if not portals:
            return (
                "No tienes portales configurados. Dime qué empresas te interesan "
                "y configuraré sus portales de empleo automáticamente."
            )

        lines = ["📡 **Portales configurados**\n"]
        for p in portals:
            status = "🟢" if p.enabled else "⏸️"
            scanned = p.last_scanned_at.strftime("%d/%m %H:%M") if p.last_scanned_at else "nunca"
            lines.append(
                f"{status} **{p.company_name}** ({p.ats_provider or 'custom'})\n"
                f"   Último escaneo: {scanned}"
            )

        return "\n".join(lines)
