"""
Knowledge Graph — grafo de conocimiento del usuario.

Cada conversación alimenta automáticamente un grafo de nodos (entidades)
y aristas (relaciones) que conectan el conocimiento de SARA.

Arquitectura:
- PostgreSQL: estructura del grafo (nodos y aristas)
- Qdrant (sara_knowledge): embeddings de nodos para búsqueda semántica
- Groq: extracción de entidades y relaciones desde el texto
"""
import json
import logging
import re
import uuid

from groq import AsyncGroq
from app.config import settings
from app.services.embedding_service import get_embedding

logger = logging.getLogger(__name__)
groq_client = AsyncGroq(api_key=settings.groq_api_key)

_KG_COLLECTION = "sara_knowledge"


# ── Inicialización ─────────────────────────────────────────────────────────────

async def init_kg_collection() -> None:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import VectorParams, Distance

    client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if _KG_COLLECTION not in names:
        await client.create_collection(
            collection_name=_KG_COLLECTION,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        logger.warning("[KG] Colección '%s' creada en Qdrant", _KG_COLLECTION)


# ── Escritura ──────────────────────────────────────────────────────────────────

async def _upsert_node(label: str, node_type: str, session_id: str) -> str:
    """
    Inserta o actualiza un nodo. Devuelve su id canónico.
    Embebe el label en Qdrant para búsqueda semántica.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.db.postgres import SessionLocal
    from app.models.knowledge import KgNode

    node_id = str(uuid.uuid4())

    async with SessionLocal() as s:
        stmt = (
            pg_insert(KgNode)
            .values(id=node_id, label=label, type=node_type, session_id=session_id)
            .on_conflict_do_update(
                index_elements=["label", "session_id"],
                set_={"type": node_type},
            )
            .returning(KgNode.id)
        )
        result = await s.execute(stmt)
        canonical_id = result.scalar_one()
        await s.commit()

    # Embed en Qdrant (usa el id canónico como punto)
    try:
        vector = await get_embedding(label)
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import PointStruct

        qdrant = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        await qdrant.upsert(
            collection_name=_KG_COLLECTION,
            points=[
                PointStruct(
                    id=canonical_id,
                    vector=vector,
                    payload={"label": label, "type": node_type, "session_id": session_id},
                )
            ],
        )
    except Exception as e:
        logger.error("[KG] Error embebiendo nodo '%s': %s", label, e)

    return canonical_id


async def _upsert_edge(source_id: str, target_id: str, relation: str, session_id: str) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.db.postgres import SessionLocal
    from app.models.knowledge import KgEdge

    async with SessionLocal() as s:
        stmt = (
            pg_insert(KgEdge)
            .values(
                id=str(uuid.uuid4()),
                source_id=source_id,
                target_id=target_id,
                relation=relation,
                session_id=session_id,
            )
            .on_conflict_do_nothing(index_elements=["source_id", "target_id", "relation"])
        )
        await s.execute(stmt)
        await s.commit()


async def kg_extract_and_store(messages: list[dict], session_id: str) -> None:
    """
    Extrae entidades y relaciones de un turno de conversación y las guarda.
    Diseñado para ejecutarse en background (asyncio.create_task).
    """
    try:
        conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)

        resp = await groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un extractor de conocimiento. Analiza la conversación y extrae "
                        "entidades concretas (tecnologías, proyectos, personas, conceptos, lugares) "
                        "y las relaciones entre ellas.\n\n"
                        "REGLAS:\n"
                        "- Solo nombres propios o términos técnicos concretos (FastAPI, Python, SARA, etc.)\n"
                        "- Tipos válidos: tecnologia, proyecto, persona, concepto, lugar\n"
                        "- Máximo 6 entidades y 6 relaciones\n"
                        "- Si no hay entidades claras, devuelve listas vacías\n\n"
                        "EJEMPLO de salida para 'estoy construyendo SARA con Python':\n"
                        '{"entities": [{"label": "SARA", "type": "proyecto"}, {"label": "Python", "type": "tecnologia"}], '
                        '"relations": [{"from": "SARA", "relation": "construido_con", "to": "Python"}]}\n\n'
                        "Responde SOLO con el JSON, sin explicaciones."
                    ),
                },
                {"role": "user", "content": conversation},
            ],
            temperature=0,
            max_tokens=350,
        )

        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return

        data = json.loads(match.group())
        entities  = data.get("entities", [])
        relations = data.get("relations", [])

        if not entities:
            return

        # Upsert nodos
        label_to_id: dict[str, str] = {}
        for ent in entities:
            label = ent.get("label", "").strip()
            etype = ent.get("type", "concept")
            if label:
                nid = await _upsert_node(label, etype, session_id)
                label_to_id[label.lower()] = nid

        # Upsert aristas
        saved_edges = 0
        for rel in relations:
            src_label = rel.get("from", "").strip().lower()
            tgt_label = rel.get("to", "").strip().lower()
            relation  = rel.get("relation", "relacionado_con")
            src_id = label_to_id.get(src_label)
            tgt_id = label_to_id.get(tgt_label)
            if src_id and tgt_id and src_id != tgt_id:
                await _upsert_edge(src_id, tgt_id, relation, session_id)
                saved_edges += 1

        logger.warning(
            "[KG] %s → %d nodos, %d relaciones",
            session_id, len(label_to_id), saved_edges,
        )

    except Exception as e:
        logger.error("[KG] Extract error: %s", e)


# ── Lectura ────────────────────────────────────────────────────────────────────

async def kg_get_context(query: str, session_id: str, limit: int = 3) -> str:
    """
    Busca nodos semánticamente relacionados con la query y devuelve tripletas
    formateadas para inyectar en el system prompt de SARA.
    """
    try:
        vector = await get_embedding(query)

        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        results = await qdrant.search(
            collection_name=_KG_COLLECTION,
            query_vector=vector,
            limit=limit,
            with_payload=True,
            score_threshold=0.5,
            query_filter=Filter(
                must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
            ),
        )

        if not results:
            return ""

        node_ids = [r.id for r in results]

        from sqlalchemy import select, or_
        from app.db.postgres import SessionLocal
        from app.models.knowledge import KgNode, KgEdge

        triples: list[str] = []

        async with SessionLocal() as s:
            edges_result = await s.execute(
                select(KgEdge)
                .where(
                    KgEdge.session_id == session_id,
                    or_(KgEdge.source_id.in_(node_ids), KgEdge.target_id.in_(node_ids)),
                )
                .limit(10)
            )
            edges = edges_result.scalars().all()

            if not edges:
                triples = [r.payload.get("label", "") for r in results]
            else:
                all_ids = {e.source_id for e in edges} | {e.target_id for e in edges}
                nodes_result = await s.execute(
                    select(KgNode).where(KgNode.id.in_(all_ids))
                )
                id_to_label = {n.id: n.label for n in nodes_result.scalars().all()}

                for e in edges:
                    src = id_to_label.get(e.source_id, "?")
                    tgt = id_to_label.get(e.target_id, "?")
                    triples.append(f"{src} {e.relation} {tgt}")

        if not triples:
            return ""

        return "\n".join(f"- {t}" for t in triples[:8])

    except Exception as e:
        logger.error("[KG] Context error: %s", e)
        return ""


async def kg_get_full(session_id: str) -> dict:
    """Devuelve el grafo completo para visualización."""
    from sqlalchemy import select
    from app.db.postgres import SessionLocal
    from app.models.knowledge import KgNode, KgEdge

    async with SessionLocal() as s:
        nodes = (await s.execute(
            select(KgNode).where(KgNode.session_id == session_id)
        )).scalars().all()

        edges = (await s.execute(
            select(KgEdge).where(KgEdge.session_id == session_id)
        )).scalars().all()

    return {
        "nodes": [{"id": n.id, "label": n.label, "type": n.type} for n in nodes],
        "edges": [
            {"source": e.source_id, "target": e.target_id, "relation": e.relation}
            for e in edges
        ],
    }
