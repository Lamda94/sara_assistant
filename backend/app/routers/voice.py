"""
VoiceRouter — STT y TTS para SARA.

POST /voice/stt  → audio (multipart) → {"text": "..."}
POST /voice/tts  → {"text": "...", "voice": "..."} → audio/mpeg stream
"""
import io
import os
import tempfile
import logging
from functools import lru_cache

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


@lru_cache(maxsize=1)
def _get_whisper():
    """Carga el modelo Whisper una sola vez (tiny, CPU, int8)."""
    from faster_whisper import WhisperModel
    logger.info("Cargando modelo Whisper tiny …")
    return WhisperModel("tiny", device="cpu", compute_type="int8")


class TTSRequest(BaseModel):
    text: str
    voice: str = "es-CO-SalomeNeural"


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio a texto (faster-whisper, idioma español)."""
    import asyncio

    content = await audio.read()
    ext = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        model = _get_whisper()

        def _run():
            segs, _ = model.transcribe(tmp_path, language="es", beam_size=1)
            return " ".join(s.text for s in segs).strip()

        text = await asyncio.to_thread(_run)
        return {"text": text}
    except Exception as e:
        logger.error(f"STT error: {e}")
        return {"text": "", "error": str(e)}
    finally:
        os.unlink(tmp_path)


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Convierte texto a audio MP3 via edge-tts."""
    try:
        import edge_tts

        communicate = edge_tts.Communicate(req.text, voice=req.voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
