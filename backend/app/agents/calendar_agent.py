"""
CalendarAgent — integración con Google Calendar via OAuth del usuario.
El access_token se recibe del frontend (web/móvil) — no se almacena en servidor.
"""
from .base import BaseAgent


class CalendarAgent(BaseAgent):
    name = "calendar"
    description = (
        "Lee, crea, actualiza y elimina eventos en Google Calendar. "
        "Úsalo cuando el usuario pregunte por sus eventos del calendario, "
        "quiera añadir, modificar, eliminar una cita o consultar su agenda de Google. "
        "Los eventos se listan enumerados (1, 2, 3…). Para update/delete el usuario "
        "puede referirse al número del evento en la lista."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create", "update", "delete"],
                "description": "list=ver eventos, create=crear evento, update=modificar evento, delete=eliminar evento",
            },
            "days_ahead": {
                "type": "integer",
                "description": "Número de días hacia adelante a consultar (default 7)",
            },
            "title": {
                "type": "string",
                "description": "Título del evento (para create, delete o update)",
            },
            "start_datetime": {
                "type": "string",
                "description": "Fecha y hora de inicio ISO 8601 (para create o update)",
            },
            "end_datetime": {
                "type": "string",
                "description": "Fecha y hora de fin ISO 8601 (para create o update)",
            },
            "event_query": {
                "type": "string",
                "description": "Texto para buscar el evento a modificar o eliminar",
            },
            "event_number": {
                "type": "integer",
                "description": "Número del evento en la lista (1, 2, 3…) para update o delete",
            },
            "new_title": {
                "type": "string",
                "description": "Nuevo título del evento (solo para update)",
            },
        },
        "required": ["action"],
    }

    def _get_service(self, access_token: str):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(token=access_token)
        return build("calendar", "v3", credentials=creds)

    async def _fetch_events(self, service, days_ahead: int = 7,
                            query: str = "", max_results: int = 15) -> list:
        """Obtiene eventos del calendario. Reutilizado por list, update y delete."""
        import asyncio
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days_ahead)

        kwargs = {
            "calendarId": "primary",
            "timeMin": now.isoformat(),
            "timeMax": end.isoformat(),
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if query:
            kwargs["q"] = query

        result = await asyncio.to_thread(
            lambda: service.events().list(**kwargs).execute()
        )
        return result.get("items", [])

    @staticmethod
    def _format_event_date(ev: dict) -> str:
        from datetime import datetime
        start = ev["start"].get("dateTime", ev["start"].get("date", ""))
        if "T" in start:
            dt = datetime.fromisoformat(start)
            return dt.strftime("%d/%m %H:%M")
        return start

    async def run(self, action: str, google_access_token: str | None = None,
                  days_ahead: int = 7, title: str = "",
                  start_datetime: str = "", end_datetime: str = "",
                  event_query: str = "", event_number: int = 0,
                  new_title: str = "", **_) -> str:

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
            return await self._list_events(service, days_ahead)
        elif action == "create":
            return await self._create_event(service, title, start_datetime, end_datetime)
        elif action == "update":
            return await self._update_event(service, event_query or title,
                                            event_number, new_title,
                                            start_datetime, end_datetime, days_ahead)
        elif action == "delete":
            return await self._delete_event(service, event_query or title,
                                            event_number, days_ahead)

        return f"Acción '{action}' no reconocida."

    async def _list_events(self, service, days_ahead: int) -> str:
        try:
            events = await self._fetch_events(service, days_ahead)
            if not events:
                return f"No hay eventos en los próximos {days_ahead} días."

            lines = []
            for i, ev in enumerate(events, 1):
                summary = ev.get("summary", "Sin título")
                label = self._format_event_date(ev)
                lines.append(f"{i}. {label} — {summary}")

            return f"Eventos próximos ({days_ahead} días):\n" + "\n".join(lines)

        except Exception as e:
            return f"Error obteniendo eventos: {e}"

    async def _create_event(self, service, title: str,
                            start_datetime: str, end_datetime: str) -> str:
        if not title or not start_datetime:
            return "Para crear un evento necesito el título y la fecha de inicio."
        try:
            import asyncio
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

    async def _resolve_event(self, service, query: str, event_number: int,
                             days_ahead: int) -> dict | str:
        """Encuentra un evento por número de lista o por búsqueda de texto."""
        try:
            if event_number > 0:
                # Re-listar eventos y tomar el índice
                events = await self._fetch_events(service, days_ahead)
                if not events:
                    return "No hay eventos en el calendario."
                if event_number > len(events):
                    return f"Solo hay {len(events)} evento(s). Elige un número del 1 al {len(events)}."
                return events[event_number - 1]
            elif query:
                events = await self._fetch_events(service, days_ahead=30, query=query)
                if not events:
                    return f"No encontré eventos que coincidan con '{query}'."
                return events[0]
            else:
                return "Necesito el número del evento o su nombre."
        except Exception as e:
            return f"Error buscando evento: {e}"

    async def _update_event(self, service, query: str, event_number: int,
                            new_title: str, new_start: str, new_end: str,
                            days_ahead: int) -> str:
        if not new_title and not new_start:
            return "Necesito saber qué cambiar: nuevo título, nueva fecha o ambos."

        result = await self._resolve_event(service, query, event_number, days_ahead)
        if isinstance(result, str):
            return result

        ev = result
        try:
            import asyncio
            from datetime import datetime, timedelta

            ev_id = ev["id"]
            old_summary = ev.get("summary", "Sin título")
            changes = []

            if new_title:
                ev["summary"] = new_title
                changes.append(f"título → '{new_title}'")

            if new_start:
                start_dt = datetime.fromisoformat(new_start)
                ev["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "America/Bogota"}
                end_dt = datetime.fromisoformat(new_end) if new_end else start_dt + timedelta(hours=1)
                ev["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "America/Bogota"}
                changes.append(f"fecha → {start_dt.strftime('%d/%m/%Y a las %H:%M')}")

            await asyncio.to_thread(
                lambda: service.events().update(
                    calendarId="primary", eventId=ev_id, body=ev
                ).execute()
            )

            return f"Evento '{old_summary}' actualizado: {', '.join(changes)}."

        except Exception as e:
            return f"Error actualizando evento: {e}"

    async def _delete_event(self, service, query: str, event_number: int,
                            days_ahead: int) -> str:
        result = await self._resolve_event(service, query, event_number, days_ahead)
        if isinstance(result, str):
            return result

        ev = result
        try:
            import asyncio

            ev_id = ev["id"]
            summary = ev.get("summary", "Sin título")
            label = self._format_event_date(ev)

            await asyncio.to_thread(
                lambda: service.events().delete(calendarId="primary", eventId=ev_id).execute()
            )

            return f"Evento eliminado: '{summary}' del {label}."

        except Exception as e:
            return f"Error eliminando evento: {e}"
