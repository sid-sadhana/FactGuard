"""Optional Qdrant Cloud vector store used as a per-job embedding cache.

Each pipeline run gets its own collection (`{prefix}-{job_id}`); chunks are
upserted with their Ollama embeddings, queried for top-k against the claim
vector, then the entire collection is dropped at the end of the run so
nothing persists in the cloud after the report is delivered.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from .config import get_settings
from .logging import get_logger

log = get_logger(__name__)


@dataclass
class QdrantHit:
    text: str
    url: str
    title: str
    base_score: float
    rank_score: float


_singleton: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient | None:
    """Return a singleton async client, or None if Qdrant is disabled/misconfigured."""
    global _singleton
    settings = get_settings()
    if not settings.use_qdrant:
        return None
    if not settings.qdrant_url:
        log.warning("USE_QDRANT=true but QDRANT_URL is empty — skipping Qdrant")
        return None
    if _singleton is None:
        _singleton = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            prefer_grpc=False,
        )
    return _singleton


def collection_name(job_id: str) -> str:
    settings = get_settings()
    safe = job_id.replace("/", "-")
    return f"{settings.qdrant_collection_prefix}-{safe}"


async def ensure_collection(client: AsyncQdrantClient, name: str, vector_size: int) -> None:
    existing = await client.collection_exists(name)
    if existing:
        return
    await client.create_collection(
        collection_name=name,
        vectors_config=qmodels.VectorParams(
            size=vector_size,
            distance=qmodels.Distance.COSINE,
        ),
    )


async def upsert_chunks(
    client: AsyncQdrantClient,
    name: str,
    points: Iterable[qmodels.PointStruct],
) -> None:
    await client.upsert(collection_name=name, points=list(points), wait=True)


async def query(
    client: AsyncQdrantClient,
    name: str,
    vector: list[float],
    *,
    limit: int,
) -> list[QdrantHit]:
    res = await client.query_points(
        collection_name=name,
        query=vector,
        limit=limit,
        with_payload=True,
    )
    hits: list[QdrantHit] = []
    for p in res.points:
        payload = p.payload or {}
        hits.append(QdrantHit(
            text=payload.get("text", ""),
            url=payload.get("url", ""),
            title=payload.get("title", ""),
            base_score=float(payload.get("base_score", 0.0)),
            rank_score=float(p.score or 0.0),
        ))
    return hits


async def drop_collection(client: AsyncQdrantClient, name: str) -> None:
    try:
        await client.delete_collection(collection_name=name)
        log.info("Dropped Qdrant collection %s", name)
    except Exception as exc:
        log.warning("Failed to drop Qdrant collection %s: %s", name, exc)


async def cleanup_job(job_id: str) -> None:
    """Convenience: drop the per-job collection if Qdrant is enabled."""
    client = get_qdrant()
    if client is None:
        return
    await drop_collection(client, collection_name(job_id))
