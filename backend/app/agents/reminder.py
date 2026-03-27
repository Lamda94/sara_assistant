from datetime import datetime
from .base import BaseAgent
from app.db.postgres import SessionLocal
from app.models.reminder import Reminder


class ReminderAgent(BaseAgent):
    name = "set_reminder"
    description = (
        "Crea un recordatorio para el usuario. "
        "Úsalo cuando el usuario pida que le recuerdes algo en una fecha u hora específica. "
        "Convierte expresiones como 'mañana a las 9' a formato ISO 8601."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Descripción del recordatorio",
            },
            "remind_at": {
                "type": "string",
                "description": "Fecha y hora en formato ISO 8601, e.g. 2026-03-28T09:00:00",
            },
        },
        "required": ["title", "remind_at"],
    }

    async def run(self, title: str, remind_at: str, session_id: str = "unknown", **_) -> str:
        try:
            dt = datetime.fromisoformat(remind_at)
            async with SessionLocal() as session:
                reminder = Reminder(
                    title=title,
                    remind_at=dt,
                    session_id=session_id,
                )
                session.add(reminder)
                await session.commit()
            formatted = dt.strftime("%d/%m/%Y a las %H:%M")
            return f"Recordatorio guardado: '{title}' para el {formatted}."
        except ValueError:
            return "No pude interpretar la fecha. Por favor especifica el formato YYYY-MM-DDTHH:MM:SS."
        except Exception as e:
            return f"Error al guardar el recordatorio: {str(e)}"
