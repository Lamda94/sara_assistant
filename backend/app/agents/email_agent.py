"""
EmailAgent — integración con Gmail.

Configuración necesaria en .env:
  GOOGLE_CREDENTIALS_PATH=/ruta/a/credentials.json

Usa las mismas credenciales OAuth que CalendarAgent (Google API).
El scope adicional gmail.readonly/modify se añade automáticamente.
"""
from .base import BaseAgent
from app.config import settings


class EmailAgent(BaseAgent):
    name = "email_assistant"
    description = (
        "Lee y redacta correos de Gmail. "
        "Úsalo cuando el usuario pida ver sus correos recientes, leer un email específico "
        "o redactar y enviar un mensaje."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "read", "send"],
                "description": "list=ver correos recientes, read=leer uno, send=enviar",
            },
            "max_results": {
                "type": "integer",
                "description": "Número de correos a listar (default 5)",
            },
            "message_id": {
                "type": "string",
                "description": "ID del mensaje a leer (para action=read)",
            },
            "to": {
                "type": "string",
                "description": "Destinatario (para action=send)",
            },
            "subject": {
                "type": "string",
                "description": "Asunto del correo (para action=send)",
            },
            "body": {
                "type": "string",
                "description": "Cuerpo del correo (para action=send)",
            },
        },
        "required": ["action"],
    }

    def _get_service(self):
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import os, pickle

        SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]
        token_path = settings.google_credentials_path.replace("credentials.json", "gmail_token.pickle")

        creds = None
        if os.path.exists(token_path):
            with open(token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.google_credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as f:
                pickle.dump(creds, f)

        return build("gmail", "v1", credentials=creds)

    def _decode_body(self, msg: dict) -> str:
        """Extrae el texto plano del cuerpo de un mensaje Gmail."""
        import base64

        payload = msg.get("payload", {})
        parts = payload.get("parts", [])

        if not parts:
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            return ""

        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return ""

    async def run(self, action: str, max_results: int = 5,
                  message_id: str = "", to: str = "",
                  subject: str = "", body: str = "", **_) -> str:
        if not settings.google_credentials_path:
            return (
                "EmailAgent no está configurado. "
                "Define GOOGLE_CREDENTIALS_PATH en el .env con la ruta a tu credentials.json de Google."
            )

        try:
            import asyncio
            service = await asyncio.to_thread(self._get_service)
        except Exception as e:
            return f"Error conectando con Gmail: {e}"

        if action == "list":
            try:
                import asyncio
                result = await asyncio.to_thread(
                    lambda: service.users().messages().list(
                        userId="me", maxResults=max_results, labelIds=["INBOX"]
                    ).execute()
                )
                messages = result.get("messages", [])
                if not messages:
                    return "No hay correos en la bandeja de entrada."

                lines = []
                for m in messages:
                    msg = await asyncio.to_thread(
                        lambda mid=m["id"]: service.users().messages().get(
                            userId="me", id=mid, format="metadata",
                            metadataHeaders=["Subject", "From", "Date"],
                        ).execute()
                    )
                    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                    subj   = headers.get("Subject", "(sin asunto)")[:60]
                    sender = headers.get("From", "?")[:40]
                    lines.append(f"[{m['id'][:8]}] {sender} — {subj}")

                return f"Últimos {len(lines)} correos:\n" + "\n".join(lines)

            except Exception as e:
                return f"Error listando correos: {e}"

        elif action == "read":
            if not message_id:
                return "Especifica el ID del mensaje a leer."
            try:
                import asyncio
                msg = await asyncio.to_thread(
                    lambda: service.users().messages().get(
                        userId="me", id=message_id, format="full"
                    ).execute()
                )
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subj   = headers.get("Subject", "(sin asunto)")
                sender = headers.get("From", "?")
                date_h = headers.get("Date", "")
                body_text = self._decode_body(msg)[:2000]

                return (
                    f"**De:** {sender}\n"
                    f"**Asunto:** {subj}\n"
                    f"**Fecha:** {date_h}\n\n"
                    f"{body_text}"
                )
            except Exception as e:
                return f"Error leyendo correo: {e}"

        elif action == "send":
            if not to or not subject or not body:
                return "Para enviar un correo necesito: destinatario, asunto y cuerpo."
            try:
                import asyncio, base64
                from email.mime.text import MIMEText

                mime = MIMEText(body)
                mime["to"]      = to
                mime["subject"] = subject
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

                await asyncio.to_thread(
                    lambda: service.users().messages().send(
                        userId="me", body={"raw": raw}
                    ).execute()
                )
                return f"Correo enviado a {to} con asunto '{subject}'."
            except Exception as e:
                return f"Error enviando correo: {e}"

        return f"Acción '{action}' no reconocida. Usa: list, read, send."
