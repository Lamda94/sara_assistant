"""
SecOps Agent -- Fase 1 (solo lectura).

Consulta telemetria de seguridad de la VPS a traves del daemon sara-secops
(host, fuera de Docker, sin LLM). Este agente NUNCA ejecuta acciones -- solo
lee datos ya normalizados a JSON tipado y los resume para el creador. Las
acciones (bloquear IPs, etc.) llegan en Fase 3 con aprobacion humana.

Exclusivo del creador (lamda94); cualquier otra sesion recibe acceso denegado.
"""
import logging

from app.config import settings
from app.services import secops_service
from .base import BaseAgent

logger = logging.getLogger(__name__)


class SecOpsAgent(BaseAgent):
    name = "secops"
    description = (
        "Consulta el estado de seguridad de la VPS de SARA: intentos de "
        "intrusión SSH, IPs bloqueadas por fail2ban, estado del firewall, "
        "puertos abiertos y uso de disco. Solo lectura — no ejecuta ninguna "
        "acción. Úsalo cuando el usuario pregunte por la seguridad, "
        "intrusiones o el estado del servidor. Exclusivo del creador."
    )
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["report"],
                "description": "report: genera un resumen completo de seguridad de la VPS.",
            },
        },
        "required": ["operation"],
    }

    async def run(self, operation: str = "report", session_id: str = "", **_) -> str:
        if settings.creator_id not in (session_id or "").lower():
            return "Acceso denegado: la función de seguridad de la VPS es exclusiva del creador."

        if operation != "report":
            return f"Operación desconocida: {operation}"

        try:
            data = await secops_service.get_report()
        except Exception as e:
            logger.error(f"SecOps error: {e}")
            return f"Error consultando el daemon de seguridad: {e}"

        if "error" in data:
            return f"⚠️ {data['error']}"

        return self._format_report(data)

    def _format_report(self, data: dict) -> str:
        ssh = data.get("ssh_bruteforce", {})
        f2b = data.get("fail2ban", {})
        fw = data.get("firewall", {})
        ports = data.get("open_ports", {})
        disk = data.get("disk", {})

        lines = ["🛡️ **Estado de seguridad de la VPS**\n"]

        lines.append(
            f"**SSH (últimas {ssh.get('window', '24h')}):**\n"
            f"  {ssh.get('failed_password_total', 0)} intentos de password fallidos\n"
            f"  {ssh.get('invalid_user_attempts', 0)} intentos con usuario inválido"
        )
        top_ips = ssh.get("top_ips", [])
        if top_ips:
            ip_lines = "\n".join(f"    - {i['ip']}: {i['count']} intentos" for i in top_ips[:5])
            lines.append(f"  Top IPs atacantes:\n{ip_lines}")

        lines.append(
            f"\n**fail2ban ({f2b.get('jail', 'sshd')}):**\n"
            f"  {f2b.get('currently_banned', 0)} IPs baneadas ahora "
            f"({f2b.get('total_banned_ever', 0)} baneos históricos)"
        )

        fw_status = "✅ activo" if fw.get("active") else "❌ INACTIVO"
        lines.append(f"\n**Firewall (ufw):** {fw_status}")
        rules = fw.get("rules", [])
        if rules:
            unique_ports = sorted({r["to"] for r in rules if "(v6)" not in r["to"]})
            lines.append(f"  Puertos permitidos: {', '.join(unique_ports)}")

        listening = ports.get("listening", [])
        if listening:
            procs = sorted({f"{p['process']}:{p['port']}" for p in listening})
            lines.append(f"\n**Puertos en escucha:** {', '.join(procs)}")

        used_pct = disk.get("used_pct")
        if used_pct is not None:
            icon = "⚠️" if used_pct >= 85 else "✅"
            free_gb = (disk.get("free_bytes") or 0) / (1024 ** 3)
            lines.append(f"\n**Disco:** {icon} {used_pct}% usado ({free_gb:.1f} GB libres)")

        return "\n".join(lines)
