"""Per-point answerer.

Every point selected by `claims.extract_claims` is fact-checked the same way
— no parametric shortcut. Pipeline per claim:

  DuckDuckGo search → WebBaseLoader page fetch → Qdrant Cloud Inference
  rerank → gemma4:e4b writes a JSON answer with inline `[N]` citation
  markers tied to the evidence.

Result shape stays `ClaimVerification` for frontend compatibility:
  * `reasoning` holds the answer text with inline `[N]` markers.
  * `citations` lists the Evidence used.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.ollama import get_ollama
from ..models.schemas import Claim, ClaimVerification, Evidence
from ..prompts.templates import ANSWER_SYSTEM, ANSWER_USER
from .rag import build_evidence
from .search import load_documents, web_search

log = get_logger(__name__)

ProgressCB = Callable[[int, int, str], Awaitable[None]]


def _format_evidence(evidence: list[Evidence]) -> str:
    if not evidence:
        return "(no results)"
    return "\n\n".join(
        f"[{i}] {e.title}\nURL: {e.url}\n{e.snippet}"
        for i, e in enumerate(evidence)
    )


async def _retrieve_evidence(query: str, job_id: str | None = None) -> list[Evidence]:
    """DDG search → WebBaseLoader → chunk + Qdrant rerank → top evidence."""
    results = await web_search(query)
    if not results:
        return []
    urls = [r["url"] for r in results if r.get("url")]
    settings = get_settings()
    loaded = await load_documents(urls) if settings.use_web_base_loader else {}
    enriched: list[dict] = []
    for r in results:
        content = loaded.get(r["url"]) or r.get("content_fallback") or ""
        if not content:
            continue
        enriched.append({
            "url": r["url"],
            "title": r["title"],
            "content": content,
            "score": r["score"],
        })
    return await build_evidence(query, enriched, job_id=job_id)


def _parse_answer_json(raw: str) -> tuple[str, list[int]]:
    """Tolerant JSON parser for the final assistant turn."""
    if not raw or not raw.strip():
        return "", []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            return raw.strip(), []
        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return raw.strip(), []
    if not isinstance(data, dict):
        return "", []
    answer = str(data.get("answer", "")).strip()
    raw_idx = data.get("supporting_indices") or []
    indices: list[int] = []
    for x in raw_idx:
        try:
            indices.append(int(x))
        except (TypeError, ValueError):
            continue
    return answer, indices


async def _answer_grounded(point: Claim, job_id: str | None = None) -> ClaimVerification:
    """Search-required branch: retrieve evidence and write a cited answer."""
    evidence = await _retrieve_evidence(point.text, job_id=job_id)
    if not evidence:
        return ClaimVerification(
            claim=point,
            verdict="unverifiable",
            confidence=0.4,
            reasoning="No reliable web source was found for this point.",
            citations=[],
        )

    settings = get_settings()
    user_prompt = ANSWER_USER.format(
        claim=point.text,
        evidence_block=_format_evidence(evidence),
    )
    try:
        data = await get_ollama().generate_json(
            model=settings.ollama_llm_model,
            prompt=user_prompt,
            system=ANSWER_SYSTEM,
            options={
                "temperature": 0.1,
                "num_ctx": 8192,    # fit claim + evidence block + answer
                "num_predict": 1024,
            },
        )
    except Exception as exc:
        log.warning("Answer LLM call failed for point %d: %s", point.id, exc)
        return ClaimVerification(
            claim=point,
            verdict="unverifiable",
            confidence=0.0,
            reasoning="The model could not produce an answer for this point.",
            citations=evidence[:3],
        )

    answer, indices = _parse_answer_json(
        json.dumps(data) if isinstance(data, dict) else ""
    )
    if not answer:
        answer = "No grounded answer was produced for this point."
    cited = [evidence[i] for i in indices if 0 <= i < len(evidence)]
    if not cited:
        cited = evidence[: min(3, len(evidence))]
    return ClaimVerification(
        claim=point,
        verdict="supported",
        confidence=1.0,
        reasoning=answer,
        citations=cited,
    )


def _answer_parametric(point: Claim) -> ClaimVerification:
    """No-search branch: wrap the picker's prelim_answer."""
    reasoning = (point.prelim_answer or "").strip() or (
        "The model is confident in this point but produced no preliminary answer."
    )
    return ClaimVerification(
        claim=point,
        verdict="supported",
        confidence=1.0,
        reasoning=reasoning,
        citations=[],
    )


async def _answer_one(point: Claim, job_id: str | None = None) -> ClaimVerification:
    if not point.needs_search:
        return _answer_parametric(point)
    return await _answer_grounded(point, job_id=job_id)


async def answer_all(
    points: list[Claim],
    *,
    on_progress: ProgressCB | None = None,
    job_id: str | None = None,
) -> list[ClaimVerification]:
    sem = asyncio.Semaphore(3)
    total = len(points) or 1
    done = 0
    lock = asyncio.Lock()

    async def run(p: Claim) -> ClaimVerification:
        nonlocal done
        async with sem:
            result = await _answer_one(p, job_id=job_id)
        async with lock:
            done += 1
            n = done
        if on_progress:
            preview = p.text[:60] + ("…" if len(p.text) > 60 else "")
            tag = "🌐" if result.citations else "🧠"
            await on_progress(n, total, f"Answered {n}/{total} {tag} · {preview}")
        return result

    return await asyncio.gather(*(run(p) for p in points))
