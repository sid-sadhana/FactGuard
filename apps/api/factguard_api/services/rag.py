"""Context-engineered retrieval for claim verification.

For each claim we already have a small set of web pages (from Tavily).
This module turns those pages into a compact, ranked evidence pack that
fits the LLM's context budget. Three steps:

  1. Chunk each page (character-aware, with overlap).
  2. Rank chunks by embedding cosine similarity to the claim — either
     in-memory (default) or via a per-job Qdrant collection (when
     USE_QDRANT=true). The collection is dropped at the end of the
     pipeline run by `pipeline.run_pipeline`.
  3. Greedily pack top chunks until we hit the per-claim character budget,
     deduplicating by URL so we don't burn the budget on one source.
"""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass

from qdrant_client.http import models as qmodels

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.ollama import get_ollama
from ..core.qdrant import (
    QdrantHit,
    collection_name,
    ensure_collection,
    get_qdrant,
    query as qdrant_query,
    upsert_chunks,
)
from ..models.schemas import Evidence

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


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)


async def _rank_inline(claim: str, chunks: list[Chunk]) -> list[Chunk]:
    settings = get_settings()
    ollama = get_ollama()
    try:
        claim_vec = await ollama.embed(settings.ollama_embed_model, claim)
        for c in chunks:
            cvec = await ollama.embed(settings.ollama_embed_model, c.text[:1500])
            c.rank_score = 0.7 * _cosine(claim_vec, cvec) + 0.3 * c.base_score
    except Exception as exc:
        log.warning("Embedding rerank failed (%s) — falling back to Tavily score", exc)
        for c in chunks:
            c.rank_score = c.base_score
    chunks.sort(key=lambda c: c.rank_score, reverse=True)
    return chunks


async def _rank_qdrant(claim: str, chunks: list[Chunk], job_id: str) -> list[Chunk]:
    """Push chunks into a per-job Qdrant collection, query top-k, return ordered."""
    client = get_qdrant()
    if client is None:
        return await _rank_inline(claim, chunks)

    settings = get_settings()
    ollama = get_ollama()
    name = collection_name(job_id)

    try:
        claim_vec = await ollama.embed(settings.ollama_embed_model, claim)
        if not claim_vec:
            raise RuntimeError("empty claim embedding")

        points: list[qmodels.PointStruct] = []
        for c in chunks:
            cvec = await ollama.embed(settings.ollama_embed_model, c.text[:1500])
            if not cvec:
                continue
            points.append(qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=cvec,
                payload={
                    "text": c.text,
                    "url": c.url,
                    "title": c.title,
                    "base_score": c.base_score,
                },
            ))

        if not points:
            return await _rank_inline(claim, chunks)

        await ensure_collection(client, name, vector_size=len(claim_vec))
        await upsert_chunks(client, name, points)

        hits: list[QdrantHit] = await qdrant_query(
            client, name, claim_vec, limit=max(settings.rag_top_k * 4, 12),
        )
        ranked = [
            Chunk(
                text=h.text,
                url=h.url,
                title=h.title,
                base_score=h.base_score,
                rank_score=0.7 * h.rank_score + 0.3 * h.base_score,
            )
            for h in hits
        ]
        ranked.sort(key=lambda c: c.rank_score, reverse=True)
        return ranked
    except Exception as exc:
        log.warning("Qdrant rerank failed (%s) — falling back to inline", exc)
        return await _rank_inline(claim, chunks)


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

    if settings.use_qdrant and job_id:
        chunks = await _rank_qdrant(claim, chunks, job_id)
    else:
        chunks = await _rank_inline(claim, chunks)

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
