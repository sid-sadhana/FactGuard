"""LLM-driven checkworthy-point selection.

The LLM reads the whole transcript and decides:
  * which sentences are checkworthy factual points (skipping filler,
    opinions, hypotheticals, meta-statements);
  * for each point, whether it needs a fresh web search, or whether the
    model can answer it confidently from parametric knowledge — and in
    the latter case, what that answer is.

Downstream, the agent uses `needs_search` to skip the search call when
the LLM already knows the answer (saving a Tavily round-trip) and only
runs Tavily + WebBaseLoader for the points it flagged.

If the LLM call fails or returns malformed JSON the function returns an
empty list — the pipeline degrades gracefully (no claims, no verdicts).
"""
from __future__ import annotations

import json

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.ollama import get_ollama
from ..models.schemas import Claim
from ..prompts.templates import POINT_SELECTION_SYSTEM, POINT_SELECTION_USER

log = get_logger(__name__)


def _coerce_bool(v, default: bool = True) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "yes", "1"}
    return default


def _coerce_prelim(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


async def extract_claims(transcript: str) -> list[Claim]:
    """Ask the LLM to pick checkworthy points from the transcript."""
    settings = get_settings()
    transcript = (transcript or "").strip()
    if not transcript:
        log.info("Transcript empty — no points to extract")
        return []

    user_prompt = POINT_SELECTION_USER.format(transcript=transcript)
    data = await get_ollama().generate_json(
        model=settings.ollama_llm_model,
        prompt=user_prompt,
        system=POINT_SELECTION_SYSTEM,
        options={"temperature": 0.1, "num_predict": -1},
    )

    raw_points = data.get("points") if isinstance(data, dict) else None
    if not isinstance(raw_points, list):
        raise RuntimeError(
            f"Point selection LLM returned no 'points' list (got {type(data).__name__})."
            " Check the model output."
        )

    seen: set[str] = set()
    claims: list[Claim] = []
    for p in raw_points:
        if not isinstance(p, dict):
            continue
        text = str(p.get("text", "")).strip().rstrip(".")
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        needs_search = _coerce_bool(p.get("needs_search"), default=True)
        prelim = _coerce_prelim(p.get("prelim_answer"))
        if not needs_search and not prelim:
            # Model said "I know this" but gave no answer — treat as needing search.
            needs_search = True
        claims.append(Claim(
            id=len(claims),
            text=text,
            source="transcript",
            needs_search=needs_search,
            prelim_answer=prelim if not needs_search else None,
        ))

    log.info(
        "LLM selected %d point(s) — %d need search, %d answered parametrically",
        len(claims),
        sum(1 for c in claims if c.needs_search),
        sum(1 for c in claims if not c.needs_search),
    )
    return claims
