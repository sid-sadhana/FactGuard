"""Per-point grounded answerer.

For each point extracted from the transcript, the LLM writes a short
Perplexity-style answer grounded in the retrieved web evidence. The output
is plain prose with inline `[N]` citation markers — no verdict, no
confidence number.

The shape of the return value (`ClaimVerification`) is unchanged for
compatibility with the existing job schema and frontend types; we keep
`verdict` as a flat "supported" sentinel and `confidence` constant so old
clients don't break. The meaningful field is `reasoning`, which holds the
cited answer text.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.ollama import get_ollama
from ..models.schemas import Claim, ClaimVerification, Evidence
from ..prompts.templates import ANSWER_SYSTEM, ANSWER_USER

log = get_logger(__name__)

ProgressCB = Callable[[int, int, str], Awaitable[None]]


def _format_evidence(evidence: list[Evidence]) -> str:
    if not evidence:
        return "(no evidence retrieved)"
    return "\n\n".join(
        f"[{i}] {e.title}\nURL: {e.url}\n{e.snippet}"
        for i, e in enumerate(evidence)
    )


async def answer_point(point: Claim, evidence: list[Evidence]) -> ClaimVerification:
    settings = get_settings()
    ollama = get_ollama()

    if not evidence:
        return ClaimVerification(
            claim=point,
            verdict="unverifiable",
            confidence=0.0,
            reasoning="No reliable source addresses this point.",
            citations=[],
        )

    user = ANSWER_USER.format(
        claim=point.text,
        evidence_block=_format_evidence(evidence),
    )
    data = await ollama.generate_json(
        model=settings.ollama_llm_model,
        prompt=user,
        system=ANSWER_SYSTEM,
        options={"temperature": 0.1, "num_predict": 420},
    )

    answer = ""
    if isinstance(data, dict):
        answer = str(data.get("answer", "")).strip()
    if not answer:
        answer = "No reliable source addresses this point."

    cited: list[Evidence] = []
    if isinstance(data, dict):
        for idx in data.get("supporting_indices", []) or []:
            try:
                i = int(idx)
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(evidence) and evidence[i] not in cited:
                cited.append(evidence[i])
    if not cited:
        cited = evidence[: min(3, len(evidence))]

    return ClaimVerification(
        claim=point,
        verdict="supported" if cited else "unverifiable",
        confidence=1.0 if cited else 0.0,
        reasoning=answer,
        citations=cited,
    )


async def verify_all(
    claims: list[Claim],
    evidence_by_claim: dict[int, list[Evidence]],
    *,
    on_progress: ProgressCB | None = None,
) -> list[ClaimVerification]:
    """Answer every point in parallel (concurrency 3) with progress reporting."""
    sem = asyncio.Semaphore(3)
    total = len(claims) or 1
    done = 0
    lock = asyncio.Lock()

    async def run(c: Claim) -> ClaimVerification:
        nonlocal done
        async with sem:
            result = await answer_point(c, evidence_by_claim.get(c.id, []))
        async with lock:
            done += 1
            n = done
        if on_progress:
            preview = c.text[:64] + ("…" if len(c.text) > 64 else "")
            await on_progress(n, total, f"Answered point {n}/{total} · {preview}")
        return result

    return await asyncio.gather(*(run(c) for c in claims))
