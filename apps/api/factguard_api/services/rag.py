"""Per-claim context-engineered retrieval.

For one claim we already have a small set of web pages (from DDG).
This module turns those pages into a compact, ranked evidence pack that
fits the LLM's context budget. Steps:

  1. Chunk each page (character-aware, with overlap).
  2. Push chunks into a per-job Qdrant collection. Embeddings are computed
     server-side by Qdrant Cloud Inference (`qmodels.Document(...)`), so
     there is no local embed call.
  3. Query top-k against the claim, also via Cloud Inference.
  4. Greedily pack top chunks until we hit the per-claim character budget,
     deduplicating by URL so we don't burn the budget on one source.

The collection is dropped at the end of the pipeline run by
`pipeline.run_pipeline`.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass

from qdrant_client.http import models as qmodels

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.qdrant import collection_name, ensure_collection, get_qdrant
from ..models.schemas import Evidence


async def _with_retry(coro_factory, *, attempts: int = 2, backoff: float = 1.5, label: str = "qdrant"):
    """Call an async factory; retry once on transient errors (timeouts, 5xx).

    Cloud Inference upserts and queries occasionally time out under
    parallel load even with a generous client timeout — a single retry
    after a brief backoff almost always succeeds.
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            transient = (
                "timeout" in str(exc).lower()
                or "responsehandling" in type(exc).__name__.lower()
                or "503" in str(exc)
                or "502" in str(exc)
            )
            if not transient or i == attempts - 1:
                raise
            log.info("%s transient error (%s) — retrying in %.1fs", label, type(exc).__name__, backoff)
            await asyncio.sleep(backoff)
    raise last_exc  # unreachable

log = get_logger(__name__)


@dataclass
class Chunk:
    text: str
    url: str
    title: str
    base_score: float
    rank_score: float = 0.0


def _chunk(text: str, size: int, overlap: int) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out: list[str] = []
    start = 0
    step = max(1, size - overlap)
    while start < len(text):
        out.append(text[start:start + size])
        start += step
    return out


async def _rank_qdrant(claim: str, chunks: list[Chunk], job_id: str) -> list[Chunk]:
    """Upsert + query a per-job Qdrant collection. Embeddings are server-side."""
    client = get_qdrant()
    if client is None:
        log.warning("Qdrant unavailable — returning chunks ranked by base score only")
        for c in chunks:
            c.rank_score = c.base_score
        chunks.sort(key=lambda c: c.rank_score, reverse=True)
        return chunks

    settings = get_settings()
    name = collection_name(job_id)

    try:
        points = [
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=qmodels.Document(text=c.text[:1500], model=settings.embed_model),
                payload={
                    "text": c.text,
                    "url": c.url,
                    "title": c.title,
                    "base_score": c.base_score,
                },
            )
            for c in chunks
        ]
        if not points:
            return []

        await ensure_collection(client, name, vector_size=settings.embed_dim)
        await _with_retry(
            lambda: client.upsert(collection_name=name, points=points, wait=True),
            label=f"qdrant upsert ({len(points)} pts)",
        )

        res = await _with_retry(
            lambda: client.query_points(
                collection_name=name,
                query=qmodels.Document(text=claim, model=settings.embed_model),
                limit=max(settings.rag_top_k * 4, 12),
                with_payload=True,
            ),
            label="qdrant query",
        )
        ranked: list[Chunk] = []
        for p in res.points:
            payload = p.payload or {}
            cos = float(p.score or 0.0)
            base = float(payload.get("base_score", 0.0))
            ranked.append(Chunk(
                text=payload.get("text", ""),
                url=payload.get("url", ""),
                title=payload.get("title", ""),
                base_score=base,
                rank_score=0.7 * cos + 0.3 * base,
            ))
        ranked.sort(key=lambda c: c.rank_score, reverse=True)
        return ranked
    except Exception as exc:
        log.warning(
            "Qdrant rerank failed (%s: %s) — falling back to base-score order",
            type(exc).__name__, exc or "<no message>", exc_info=True,
        )
        for c in chunks:
            c.rank_score = c.base_score
        chunks.sort(key=lambda c: c.rank_score, reverse=True)
        return chunks


async def build_evidence(
    claim: str,
    results: list[dict],
    *,
    per_claim_char_budget: int = 2400,
    job_id: str | None = None,
) -> list[Evidence]:
    """Rank-and-pack web results into a compact evidence list for one claim."""
    settings = get_settings()
    if not results:
        return []

    chunks: list[Chunk] = []
    for r in results:
        for piece in _chunk(r.get("content", ""), settings.rag_chunk_size, settings.rag_chunk_overlap):
            chunks.append(Chunk(
                text=piece,
                url=r.get("url", ""),
                title=r.get("title", ""),
                base_score=r.get("score", 0.0),
            ))

    if not chunks:
        return []

    if job_id:
        chunks = await _rank_qdrant(claim, chunks, job_id)
    else:
        for c in chunks:
            c.rank_score = c.base_score
        chunks.sort(key=lambda c: c.rank_score, reverse=True)

    packed: list[Evidence] = []
    used_urls: set[str] = set()
    spent = 0
    for c in chunks:
        if len(packed) >= settings.rag_top_k:
            break
        if c.url in used_urls:
            continue
        snippet = c.text[:900]
        if spent + len(snippet) > per_claim_char_budget:
            continue
        packed.append(Evidence(
            url=c.url,
            title=c.title or c.url,
            snippet=snippet,
            score=round(c.rank_score, 4),
        ))
        used_urls.add(c.url)
        spent += len(snippet)
    return packed
