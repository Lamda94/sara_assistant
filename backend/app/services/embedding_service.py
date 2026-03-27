import httpx
from app.config import settings


async def get_embedding(text: str) -> list[float]:
    """Genera un embedding usando Ollama (nomic-embed-text)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.ollama_host}/api/embeddings",
            json={"model": settings.embed_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]
