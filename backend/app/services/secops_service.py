"""
Cliente HTTP hacia el daemon sara-secops (host de la VPS, fuera de Docker).

Fase 1 — solo lectura. El daemon nunca ejecuta acciones en esta fase; este
servicio solo consulta telemetría de seguridad ya normalizada a JSON tipado.
Si SECOPS_TOKEN está vacío, el agente se considera deshabilitado.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(settings.secops_token)


async def get_report() -> dict:
    """Snapshot completo de telemetría de seguridad (todos los collectors)."""
    if not is_enabled():
        return {"error": "SecOps deshabilitado (SECOPS_TOKEN no configurado)."}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.secops_daemon_url}/report",
                headers={"X-SecOps-Token": settings.secops_token},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"[SecOps] Error consultando /report: {e}")
        return {"error": f"No se pudo consultar el daemon de seguridad: {e}"}


async def get_collector(name: str) -> dict:
    """Un collector puntual (ssh_bruteforce, fail2ban, firewall, open_ports, disk)."""
    if not is_enabled():
        return {"error": "SecOps deshabilitado (SECOPS_TOKEN no configurado)."}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.secops_daemon_url}/report/{name}",
                headers={"X-SecOps-Token": settings.secops_token},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"[SecOps] Error consultando /report/{name}: {e}")
        return {"error": f"No se pudo consultar el collector '{name}': {e}"}
