import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_firebase_ok = False


def _init_firebase():
    global _firebase_ok
    if _firebase_ok:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials
        from app.config import settings

        if not settings.firebase_credentials_path:
            logger.warning("FIREBASE_CREDENTIALS_PATH no configurado — push desactivado")
            return False

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)

        _firebase_ok = True
        logger.info("Firebase inicializado correctamente")
        return True
    except Exception as e:
        logger.error(f"Firebase init error: {e}")
        return False


async def _send_push(token: str, title: str, body: str) -> bool:
    try:
        from firebase_admin import messaging

        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="sara_reminders",
                ),
            ),
            token=token,
        )
        messaging.send(msg)
        return True
    except Exception as e:
        logger.error(f"Push error: {e}")
        return False


async def check_and_fire_reminders():
    """Revisa recordatorios vencidos y envía notificaciones push."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.reminder import Reminder
    from app.models.device_token import DeviceToken

    now = datetime.now()
    window_start = now - timedelta(minutes=1)

    try:
        async with SessionLocal() as s:
            r = await s.execute(
                select(Reminder).where(
                    Reminder.done == False,           # noqa: E712
                    Reminder.remind_at >= window_start,
                    Reminder.remind_at <= now,
                )
            )
            reminders = r.scalars().all()

            if not reminders:
                return

            for rem in reminders:
                t = await s.execute(
                    select(DeviceToken).where(DeviceToken.session_id == rem.session_id)
                )
                token_row = t.scalar_one_or_none()

                if token_row and _firebase_ok:
                    sent = await _send_push(
                        token_row.token,
                        "⏰ Recordatorio",
                        rem.title,
                    )
                    if sent:
                        logger.info(f"Push enviado: {rem.title} → {rem.session_id}")

                rem.done = True

            await s.commit()
            logger.info(f"Procesados {len(reminders)} recordatorio(s)")

    except Exception as e:
        logger.error(f"check_and_fire_reminders error: {e}")


def start_scheduler():
    """Inicia el scheduler de recordatorios."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    _init_firebase()

    scheduler = AsyncIOScheduler(timezone="America/Bogota")
    scheduler.add_job(
        check_and_fire_reminders,
        trigger="interval",
        seconds=30,
        id="reminder_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler de recordatorios iniciado (cada 30s)")
    return scheduler
