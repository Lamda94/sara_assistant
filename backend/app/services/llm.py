"""
Cliente LLM centralizado con routing por tarea y fallback automático.

Pools gratuitos por tipo de tarea:
  chat      → conversación general con SARA
  reasoning → análisis complejo, apuestas, carrera
  code      → generación y revisión de código
  fast      → tareas de fondo (memoria, consolidación, perfil)
"""
import logging
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Timeout por intento (segundos): si un modelo no responde a tiempo, se pasa al
# siguiente del pool. Mantiene la latencia total acotada muy por debajo del
# timeout del cliente móvil (30s).
_ATTEMPT_TIMEOUT = 12.0

# Cliente OpenRouter (modelos gratuitos, usados como respaldo).
llm_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key or settings.groq_api_key,
    default_headers={
        "HTTP-Referer": settings.public_url,
        "X-Title": "SARA Assistant",
    },
)

# Cliente Groq (rápido y estable ~1-3s), primario para chat/fast/reasoning.
groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key,
)

# Prefijo que marca un modelo servido por Groq. El resto van por OpenRouter.
_GROQ_PREFIX = "groq:"


def _resolve(model: str):
    """Devuelve (cliente, nombre_real) según el prefijo del modelo."""
    if model.startswith(_GROQ_PREFIX):
        return groq_client, model[len(_GROQ_PREFIX):]
    return llm_client, model


# ── Pools por tarea (orden = prioridad) ───────────────────────────────────────
# Groq primero (rápido) → modelos gratuitos de OpenRouter como fallback.

_POOLS: dict[str, list[str]] = {
    "chat": [
        "groq:llama-3.3-70b-versatile",                  # Groq, ~2s, primario
        "groq:llama-3.1-8b-instant",                     # Groq, aún más rápido
        "nousresearch/hermes-3-llama-3.1-405b:free",     # OpenRouter fallback
        "openai/gpt-oss-120b:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-31b-it:free",
    ],
    "reasoning": [
        "groq:llama-3.3-70b-versatile",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "openai/gpt-oss-120b:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-31b-it:free",
    ],
    "code": [
        "qwen/qwen3-coder:free",                         # 480B MoE, mejor en código
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "openai/gpt-oss-120b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "groq:llama-3.3-70b-versatile",
    ],
    "fast": [
        "groq:llama-3.1-8b-instant",                     # Groq, tareas de fondo
        "groq:llama-3.3-70b-versatile",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "google/gemma-4-31b-it:free",
    ],
}

# Alias para compatibilidad con código antiguo (nombre real, sin prefijo interno)
LLM_MODEL = _resolve(_POOLS["chat"][0])[1]


async def llm_chat(task: str = "chat", **kwargs):
    """
    Llama al LLM con selección automática de modelo y fallback por rate limit.

    Uso:
        resp = await llm_chat("chat", messages=[...], temperature=0.7)
        resp = await llm_chat("code", messages=[...], max_tokens=1000)

    El parámetro `model` es ignorado — el pool lo gestiona internamente.
    """
    kwargs.pop("model", None)
    kwargs.setdefault("timeout", _ATTEMPT_TIMEOUT)
    models = _POOLS.get(task, _POOLS["chat"])
    last_error = None

    for model in models:
        client, real_model = _resolve(model)
        try:
            resp = await client.chat.completions.create(model=real_model, **kwargs)
            if model != models[0]:
                logger.info("[LLM] Fallback activo: usando %s", model)
            return resp
        except Exception as e:
            msg = str(e).lower()
            transient = any(k in msg for k in (
                "rate limit", "429", "quota", "limit exceeded", "tokens",
                "timeout", "timed out", "connection", "temporarily",
                "503", "502", "500", "overloaded",
            ))
            if transient:
                logger.warning("[LLM] %s en %s → probando siguiente", type(e).__name__, model)
                last_error = e
                continue
            raise

    logger.error("[LLM] Todos los modelos del pool '%s' agotados", task)
    raise last_error or RuntimeError(f"Todos los modelos del pool '{task}' fallaron")
