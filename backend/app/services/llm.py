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

llm_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key or settings.groq_api_key,
    default_headers={
        "HTTP-Referer": settings.public_url,
        "X-Title": "SARA Assistant",
    },
)

# ── Pools gratuitos por tarea (orden = prioridad) ─────────────────────────────

_POOLS: dict[str, list[str]] = {
    "chat": [
        "nousresearch/hermes-3-llama-3.1-405b:free",   # 405B, mejor razonamiento
        "nvidia/nemotron-3-super-120b-a12b:free",        # 120B, 262K ctx
        "openai/gpt-oss-120b:free",                      # 120B, sólido
        "qwen/qwen3-next-80b-a3b-instruct:free",         # 80B MoE, rápido
        "meta-llama/llama-3.3-70b-instruct:free",        # fallback probado
        "google/gemma-4-31b-it:free",                    # último recurso
    ],
    "reasoning": [
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
        "meta-llama/llama-3.3-70b-instruct:free",
    ],
    "fast": [
        "meta-llama/llama-3.3-70b-instruct:free",        # más estable para bg tasks
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "google/gemma-4-31b-it:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
}

# Alias para compatibilidad con código antiguo
LLM_MODEL = _POOLS["chat"][0]


async def llm_chat(task: str = "chat", **kwargs):
    """
    Llama al LLM con selección automática de modelo y fallback por rate limit.

    Uso:
        resp = await llm_chat("chat", messages=[...], temperature=0.7)
        resp = await llm_chat("code", messages=[...], max_tokens=1000)

    El parámetro `model` es ignorado — el pool lo gestiona internamente.
    """
    kwargs.pop("model", None)
    models = _POOLS.get(task, _POOLS["chat"])
    last_error = None

    for model in models:
        try:
            resp = await llm_client.chat.completions.create(model=model, **kwargs)
            if model != models[0]:
                logger.info("[LLM] Fallback activo: usando %s", model)
            return resp
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("rate limit", "429", "quota", "limit exceeded", "tokens")):
                logger.warning("[LLM] Rate limit en %s → probando siguiente", model)
                last_error = e
                continue
            raise

    logger.error("[LLM] Todos los modelos del pool '%s' agotados", task)
    raise last_error or RuntimeError(f"Todos los modelos del pool '{task}' fallaron")
