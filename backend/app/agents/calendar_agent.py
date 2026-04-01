"""
CalendarAgent — integración con Google Calendar via OAuth del usuario.
El access_token se recibe del frontend (web/móvil) — no se almacena en servidor.
"""
from .base import BaseAgent


class CalendarAgent(BaseAgent):
    name = "calendar"
    description = (
        "Lee y crea eventos en Google Calendar. "
        "Úsalo cuando el usuario pregunte por sus eventos del calendario, "
        "quiera añadir una cita o consultar su agenda de Google."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create"],
                "description": "list=ver eventos, create=crear evento",
            },
            "days_ahead": {
                "type": "integer",
                "description": "Número de días hacia adelante a consultar (default 7)",
            },
            "title": {
                "type": "string",
                "description": "Título del evento (solo para create)",
            },
            "start_datetime": {
                "type": "string",
                "description": "Fecha y hora de inicio ISO 8601 (solo para create)",
            },
            "end_datetime": {
                "type": "string",
                "description": "Fecha y hora de fin ISO 8601 (solo para create)",
            },
        },
        "required": ["action"],
    }

    def _get_service(self, access_token: str):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(token=access_token)
        return build("calendar", "v3", credentials=creds)

    async def run(self, action: str, google_access_token: str | None = None,
                  days_ahead: int = 7, title: str = "",
                  start_datetime: str = "", end_datetime: str = "", **_) -> str:

        if not google_access_token:
            return (
                "Para acceder a Google Calendar necesito que inicies sesión con tu cuenta de Google "
                "y autorices el acceso al calendario. Por favor cierra sesión y vuelve a entrar — "
                "en el login se te pedirá permiso para el calendario."
            )

        try:
            import asyncio
            service = await asyncio.to_thread(self._get_service, google_access_token)
        except Exception as e:
            return f"Error conectando con Google Calendar: {e}"

        if action == "list":
            try:
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)
                end = now + timedelta(days=days_ahead)

                result = await asyncio.to_thread(
                    lambda: service.events().list(
                        calendarId="primary",
                        timeMin=now.isoformat(),
                        timeMax=end.isoformat(),
                        maxResults=15,
                        singleEvents=True,
                        orderBy="startTime",
                    ).execute()
                )

                events = result.get("items", [])
                if not events:
                    return f"No hay eventos en los próximos {days_ahead} días."

                lines = []
                for ev in events:
                    start = ev["start"].get("dateTime", ev["start"].get("date", ""))
                    summary = ev.get("summary", "Sin título")
                    if "T" in start:
                        dt = datetime.fromisoformat(start)
                        label = dt.strftime("%d/%m %H:%M")
                    else:
                        label = start
                    lines.append(f"- {label}: {summary}")

                return f"Eventos próximos ({days_ahead} días):\n" + "\n".join(lines)

            except Exception as e:
                return f"Error obteniendo eventos: {e}"

        elif action == "create":
            if not title or not start_datetime:
                return "Para crear un evento necesito el título y la fecha de inicio."
            try:
                from datetime import datetime, timedelta
                start = datetime.fromisoformat(start_datetime)
                end_dt = datetime.fromisoformat(end_datetime) if end_datetime else start + timedelta(hours=1)

                event = {
                    "summary": title,
                    "start": {"dateTime": start.isoformat(), "timeZone": "America/Bogota"},
                    "end":   {"dateTime": end_dt.isoformat(), "timeZone": "America/Bogota"},
                }

                await asyncio.to_thread(
                    lambda: service.events().insert(calendarId="primary", body=event).execute()
                )
                return f"Evento creado: '{title}' el {start.strftime('%d/%m/%Y a las %H:%M')}."

            except Exception as e:
                return f"Error creando evento: {e}"

        return f"Acción '{action}' no reconocida."
