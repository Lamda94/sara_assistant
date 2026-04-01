"""
VoiceRouter — STT y TTS para SARA.

POST /voice/stt  → audio (multipart) → {"text": "..."}
POST /voice/tts  → {"text": "...", "voice": "...", "rate": "...", "pitch": "...", "volume": "..."} → audio/mpeg stream
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
    """Carga el modelo Whisper una sola vez (base, CPU, int8)."""
    from faster_whisper import WhisperModel
    logger.info("Cargando modelo Whisper base …")
    return WhisperModel("base", device="cpu", compute_type="int8")


class TTSRequest(BaseModel):
    text: str
    voice: str = "es-ES-ElviraNeural"
    rate: str = "+0%"     # velocidad: -50% (lenta) a +100% (rápida). 0% = flujo natural
    pitch: str = "-5Hz"   # tono: -50Hz (grave) a +50Hz (agudo). -5Hz da más calidez
    volume: str = "+0%"   # volumen: -50% a +50%


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio a texto (faster-whisper, idioma español)."""
    import asyncio
    import subprocess

    content = await audio.read()
    ext = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    wav_path = tmp_path + ".wav"
    try:
        # Usar ffmpeg de imageio-ffmpeg (no requiere instalación del sistema)
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

        # Convertir a WAV 16kHz mono (formato óptimo para Whisper)
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
            segs, _ = model.transcribe(wav_path, language="es", beam_size=1)
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
async def text_to_speech(req: TTSRequest):
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
async def text_to_speech_get(
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
