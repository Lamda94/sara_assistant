from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.postgres import init_db
import app.models.reminder       # noqa: F401
import app.models.device_token   # noqa: F401
import app.models.user_profile   # noqa: F401
import app.models.knowledge      # noqa: F401
import app.models.monitoring     # noqa: F401
import app.models.approved_user  # noqa: F401
import app.models.consolidation_log    # noqa: F401
import app.models.conversation         # noqa: F401
import app.models.proactive_insight    # noqa: F401
from app.services.memory_service import init_collection
from app.services.knowledge_service import init_kg_collection
from app.services.notification_service import start_scheduler
from app.routers import chat, memory, agents, knowledge
from app.routers import notifications, voice, monitoring, auth_web
from app.config import settings

_scheduler = None


def _preload_whisper():
    try:
        from app.routers.voice import _get_whisper
        _get_whisper()
        print("✓ Whisper precargado.")
    except Exception as e:
        print(f"Whisper preload skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    global _scheduler
    await init_db()
    await init_collection()
    await init_kg_collection()
    _scheduler = start_scheduler()
    # Precargar Whisper en background para que el primer STT sea rápido
    asyncio.create_task(asyncio.to_thread(_preload_whisper))
    print(f"✓ {settings.app_name} lista. Memoria vectorial y scheduler iniciados.")
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)
    print(f"✓ {settings.app_name} detenida.")


app = FastAPI(
    title=f"{settings.app_name} API",
    description="Asistente virtual con conciencia única y memoria compartida",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(notifications.router)
app.include_router(voice.router)
app.include_router(monitoring.router)
app.include_router(auth_web.router)


@app.get("/health")
async def health():
    return {"status": "ok", "assistant": settings.app_name}
