"""
Capa de memoria inteligente basada en Mem0.

Modos de operación (controlado por MEM0_API_KEY en .env):
  - Local (por defecto): Qdrant + Ollama + Groq. Sin coste, datos en tu servidor.
  - Cloud (MEM0_API_KEY definida): mem0.ai managed service. Para migrar, solo añade
    MEM0_API_KEY=tu_key al .env y reinicia — sin cambiar nada más.

Ventajas sobre memoria vectorial manual:
- Almacena hechos atómicos, no texto completo
- Deduplicación automática
- Resolución de contradicciones
- El LLM decide qué vale la pena recordar
"""
import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

_MEM0_COLLECTION = "sara_mem0"


@lru_cache(maxsize=1)
def _get_mem0():
    """
    Inicializa el cliente Mem0 una sola vez (singleton).
    Si MEM0_API_KEY está definida → usa Mem0 cloud (MemoryClient).
    Si no → usa infraestructura local (Memory.from_config).
    """
    from app.config import settings

    if settings.mem0_api_key:
        from mem0 import MemoryClient
        client = MemoryClient(api_key=settings.mem0_api_key)
        logger.warning("[Mem0] Modo CLOUD activado")
        return client

    from mem0 import Memory
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": _MEM0_COLLECTION,
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
                "embedding_model_dims": 768,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": settings.embed_model,
                "ollama_base_url": settings.ollama_host,
                "embedding_dims": 768,
            },
        },
        "llm": {
            "provider": "groq",
            "config": {
                "model": settings.groq_model,
                "api_key": settings.groq_api_key,
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        },
        "version": "v1.1",
    }
    client = Memory.from_config(config)
    logger.warning("[Mem0] Modo LOCAL activado (colección '%s')", _MEM0_COLLECTION)
    return client


async def mem0_search(query: str, user_id: str, limit: int = 5) -> list[str]:
    """
    Busca memorias relevantes para la query.
    Devuelve lista de hechos atómicos como strings.
    """
    try:
        results = await asyncio.to_thread(
            _get_mem0().search, query, user_id=user_id, limit=limit
        )
        facts = [r["memory"] for r in results.get("results", []) if r.get("score", 0) > 0.35]
        return facts
    except Exception as e:
        logger.error("[Mem0] Search error: %s", e)
        return []


async def mem0_add(messages: list[dict], user_id: str) -> None:
    """
    Procesa un turno de conversación y extrae hechos para recordar.
    Diseñado para ejecutarse en background (asyncio.create_task).
    """
    try:
        result = await asyncio.to_thread(
            _get_mem0().add, messages, user_id=user_id
        )
        events = result.get("results", [])
        adds    = sum(1 for e in events if e.get("event") == "ADD")
        updates = sum(1 for e in events if e.get("event") == "UPDATE")
        deletes = sum(1 for e in events if e.get("event") == "DELETE")
        if events:
            logger.warning(
                "[Mem0] %s → +%d hechos, ~%d actualizados, -%d eliminados",
                user_id, adds, updates, deletes,
            )
    except Exception as e:
        logger.error("[Mem0] Add error: %s", e)


async def mem0_get_all(user_id: str) -> list[dict]:
    """Devuelve todos los hechos almacenados para un usuario."""
    try:
        results = await asyncio.to_thread(
            _get_mem0().get_all, user_id=user_id
        )
        return results.get("results", [])
    except Exception as e:
        logger.error("[Mem0] Get all error: %s", e)
        return []


async def mem0_delete(memory_id: str) -> None:
    """Elimina un hecho específico por ID."""
    try:
        await asyncio.to_thread(_get_mem0().delete, memory_id)
    except Exception as e:
        logger.error("[Mem0] Delete error: %s", e)


async def mem0_delete_all(user_id: str) -> int:
    """Elimina todos los hechos de un usuario. Devuelve el número eliminado."""
    try:
        all_mem = await mem0_get_all(user_id)
        for m in all_mem:
            await mem0_delete(m["id"])
        return len(all_mem)
    except Exception as e:
        logger.error("[Mem0] Delete all error: %s", e)
        return 0
