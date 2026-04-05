"""
VoiceRouter — STT y TTS para SARA.

POST /voice/stt  → audio (multipart) → {"text": "..."}
POST /voice/tts  → {"text": "...", "voice": "...", "rate": "...", "pitch": "...", "volume": "..."} → audio/mpeg stream
"""
import os
import tempfile
import logging
from functools import lru_cache

from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from app.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB


@lru_cache(maxsize=1)
def _get_whisper():
    """Carga el modelo Whisper una sola vez."""
    from faster_whisper import WhisperModel
    model_name = os.environ.get("WHISPER_MODEL", "small")
    logger.info(f"Cargando modelo Whisper {model_name} …")
    return WhisperModel(model_name, device="cpu", compute_type="int8")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field("es-ES-ElviraNeural", max_length=50)
    rate: str = Field("+0%", max_length=10)
    pitch: str = Field("-5Hz", max_length=10)
    volume: str = Field("+0%", max_length=10)


@router.post("/stt")
@limiter.limit("15/minute")
async def speech_to_text(request: Request, audio: UploadFile = File(...)):
    """Transcribe audio a texto (faster-whisper, idioma español)."""
    import asyncio
    import subprocess

    content = await audio.read()

    if len(content) > _MAX_AUDIO_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Audio demasiado grande (máx 10MB)"})

    ext = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    wav_path = tmp_path + ".wav"
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

        result = subprocess.run(
            [ffmpeg_bin, "-y", "-i", tmp_path,
             "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr.decode()}")
            return {"text": "", "error": "ffmpeg conversion failed"}

        model = _get_whisper()

        def _run():
            segs, _ = model.transcribe(
                wav_path,
                language="es",
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                initial_prompt="Conversación en español colombiano con un asistente virtual.",
            )
            return " ".join(s.text for s in segs).strip()

        text = await asyncio.to_thread(_run)
        return {"text": text}
    except Exception as e:
        logger.error(f"STT error: {e}")
        return {"text": "", "error": str(e)}
    finally:
        os.unlink(tmp_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)


@router.post("/tts")
@limiter.limit("30/minute")
async def text_to_speech(request: Request, req: TTSRequest):
    """Convierte texto a audio MP3 via edge-tts (streaming directo)."""
    import edge_tts

    communicate = edge_tts.Communicate(
        req.text,
        voice=req.voice,
        rate=req.rate,
        pitch=req.pitch,
        volume=req.volume,
    )

    async def audio_stream():
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"TTS stream error: {e}")

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/tts")
@limiter.limit("30/minute")
async def text_to_speech_get(
    request: Request,
    text: str,
    voice: str = "es-ES-ElviraNeural",
    rate: str = "+0%",
    pitch: str = "-5Hz",
    volume: str = "+0%",
):
    """TTS via GET para streaming directo desde clientes móviles."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch, volume=volume)

    async def audio_stream():
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"TTS stream error: {e}")

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )
