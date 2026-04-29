"""
Cliente LLM centralizado — OpenRouter (OpenAI-compatible).
Todos los servicios y agentes importan `llm_client` desde aquí.
"""
from openai import AsyncOpenAI
from app.config import settings

llm_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key or settings.groq_api_key,
    default_headers={
        "HTTP-Referer": settings.public_url,
        "X-Title": "SARA Assistant",
    },
)

# Alias corto para el nombre del modelo activo
LLM_MODEL = settings.openrouter_model
