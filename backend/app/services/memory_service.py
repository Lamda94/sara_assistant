import uuid
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    SearchRequest,
)
from app.config import settings
from app.services.embedding_service import get_embedding

VECTOR_SIZE = 768

client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def init_collection():
    """Crea la colección en Qdrant si no existe."""
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


async def store_memory(
    content: str,
    session_id: str,
    device: str = "cli",
    role: str = "user",
    memory_type: str = "message",
):
    """Guarda un mensaje como recuerdo en Qdrant."""
    vector = await get_embedding(content)
    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "content": content,
                    "session_id": session_id,
                    "device": device,
                    "role": role,
                    "type": memory_type,
                },
            )
        ],
    )


async def retrieve_memories(query: str, top_k: int = None) -> list[dict]:
    """Recupera los recuerdos más relevantes para una consulta."""
    if top_k is None:
        top_k = settings.memory_top_k

    vector = await get_embedding(query)
    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "content": r.payload["content"],
            "device": r.payload.get("device", "unknown"),
            "role": r.payload.get("role", "user"),
            "score": round(r.score, 3),
        }
        for r in results
        if r.score > 0.4
    ]


async def list_all_memories() -> list[dict]:
    """Lista todos los recuerdos almacenados."""
    results, _ = await client.scroll(
        collection_name=settings.qdrant_collection,
        limit=200,
        with_payload=True,
    )
    return [
        {
            "id": str(r.id),
            "content": r.payload["content"],
            "device": r.payload.get("device", "unknown"),
            "role": r.payload.get("role", "user"),
            "type": r.payload.get("type", "message"),
        }
        for r in results
    ]


async def consolidate_memories() -> dict:
    """
    Fusiona memorias similares en una sola más rica.
    Retorna estadísticas de la consolidación.
    """
    from groq import AsyncGroq
    from app.config import settings as s

    groq = AsyncGroq(api_key=s.groq_api_key)

    # Obtener todos los puntos con vectores
    all_points, _ = await client.scroll(
        collection_name=settings.qdrant_collection,
        limit=200,
        with_payload=True,
        with_vectors=True,
    )

    if len(all_points) < 2:
        return {"merged": 0, "total_before": len(all_points)}

    # Buscar pares con similitud > 0.88 (muy similares)
    merged_ids = set()
    merged_count = 0

    for i, point in enumerate(all_points):
        if str(point.id) in merged_ids:
            continue

        # Buscar vecinos muy cercanos
        similar = await client.search(
            collection_name=settings.qdrant_collection,
            query_vector=point.vector,
            limit=5,
            with_payload=True,
            score_threshold=0.88,
        )

        # Filtrar el mismo punto y ya fusionados
        candidates = [
            r for r in similar
            if str(r.id) != str(point.id) and str(r.id) not in merged_ids
        ]

        if not candidates:
            continue

        # Fusionar con LLM
        contents = [point.payload["content"]] + [c.payload["content"] for c in candidates]
        combined = "\n".join(f"- {c}" for c in contents)

        try:
            resp = await groq.chat.completions.create(
                model=s.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente que fusiona recuerdos similares en uno solo más completo y conciso. Responde solo con el recuerdo fusionado, sin explicaciones.",
                    },
                    {
                        "role": "user",
                        "content": f"Fusiona estos recuerdos similares en uno más rico y completo:\n{combined}",
                    },
                ],
                max_tokens=256,
                temperature=0.3,
            )
            fused_content = resp.choices[0].message.content.strip()

            # Eliminar los originales
            ids_to_delete = [str(point.id)] + [str(c.id) for c in candidates]
            for mid in ids_to_delete:
                merged_ids.add(mid)

            await client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=ids_to_delete,
            )

            # Guardar la memoria fusionada
            device = point.payload.get("device", "system")
            session_id = point.payload.get("session_id", "system")
            await store_memory(
                fused_content,
                session_id=session_id,
                device=device,
                role=point.payload.get("role", "user"),
                memory_type="consolidated",
            )
            merged_count += 1

        except Exception:
            continue

    return {
        "merged": merged_count,
        "removed": len(merged_ids),
        "total_before": len(all_points),
    }


async def extract_user_profile(session_id: str) -> str:
    """
    Analiza las memorias del usuario y extrae un perfil de preferencias y patrones.
    Guarda el perfil como memoria especial.
    """
    from groq import AsyncGroq
    from app.config import settings as s

    groq = AsyncGroq(api_key=s.groq_api_key)

    all_points, _ = await client.scroll(
        collection_name=settings.qdrant_collection,
        limit=100,
        with_payload=True,
    )

    user_messages = [
        p.payload["content"]
        for p in all_points
        if p.payload.get("role") == "user" and p.payload.get("session_id") == session_id
    ]

    if len(user_messages) < 5:
        return "No hay suficientes conversaciones para generar un perfil."

    sample = "\n".join(f"- {m}" for m in user_messages[-30:])

    resp = await groq.chat.completions.create(
        model=s.groq_model,
        messages=[
            {
                "role": "system",
                "content": "Analiza los mensajes del usuario y extrae un perfil conciso: temas de interés, estilo de comunicación, proyectos activos, preferencias. Sé específico y útil.",
            },
            {
                "role": "user",
                "content": f"Mensajes del usuario:\n{sample}\n\nGenera un perfil del usuario en 3-5 puntos clave.",
            },
        ],
        max_tokens=300,
        temperature=0.4,
    )

    profile = resp.choices[0].message.content.strip()

    # Guardar el perfil como memoria especial
    await store_memory(
        f"[PERFIL DE USUARIO] {profile}",
        session_id=session_id,
        device="system",
        role="system",
        memory_type="profile",
    )

    return profile
