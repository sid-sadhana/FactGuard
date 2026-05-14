"""LLM-driven checkworthy-point selection.

The transcript is pre-split into sentences; the LLM then evaluates each
sentence and decides:
  * whether it is a checkworthy factual point (skipping filler, opinions,
    hypotheticals, meta-statements);
  * if so, whether it needs a fresh web search or can be answered
    confidently from parametric memory — and in the latter case, what
    that answer is.

Pre-splitting forces high recall: small models tend to summarize a whole
transcript into a handful of mega-points; feeding them a numbered sentence
list makes them consider each one.

If the LLM call fails or returns malformed JSON the function returns an
empty list — the pipeline degrades gracefully (no claims, no verdicts).
"""
from __future__ import annotations

import json
import re

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.ollama import get_ollama
from ..models.schemas import Claim
from ..prompts.templates import POINT_SELECTION_SYSTEM, POINT_SELECTION_USER

log = get_logger(__name__)


_ABBREVIATIONS = (
    "mr", "mrs", "ms", "dr", "prof", "jr", "sr", "st", "vs", "etc",
    "e.g", "i.e", "u.s", "u.k", "approx", "inc", "ltd", "co", "fig",
    "vol", "no", "p", "pp",
)
_ABBREV_RE = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in _ABBREVIATIONS) + r")\.",
    flags=re.IGNORECASE,
)

_UTTERANCE_MAX_WORDS = 25


def _split_sentences(text: str) -> list[str]:
    """Split transcript into ≤25-word utterances.

    YouTube auto-captions arrive as one giant unpunctuated blob, so a
    pure punctuation splitter yields one mega-sentence. Instead we walk
    word-by-word and cut on either:
      * a sentence-ending punctuation token (after abbreviation masking), or
      * a 25-word hard cap.

    Abbreviation dots are masked first so "Dr. Smith" stays together.
    """
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    masked = _ABBREV_RE.sub(lambda m: m.group(1) + "<DOT>", text)
    words = masked.split(" ")
    out: list[str] = []
    buf: list[str] = []
    for w in words:
        buf.append(w)
        ends_sentence = w.endswith((".", "!", "?")) and not w.endswith("<DOT>")
        if ends_sentence or len(buf) >= _UTTERANCE_MAX_WORDS:
            out.append(" ".join(buf).replace("<DOT>", ".").strip())
            buf = []
    if buf:
        out.append(" ".join(buf).replace("<DOT>", ".").strip())
    return [s for s in out if s]


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
    """Ask the LLM to pick checkworthy points, one decision per sentence."""
    settings = get_settings()
    transcript = (transcript or "").strip()
    if not transcript:
        log.info("Transcript empty — no points to extract")
        return []

    sentences = _split_sentences(transcript)
    if not sentences:
        log.info("Transcript produced zero sentences — no points to extract")
        return []
    log.info("Transcript split into %d sentences", len(sentences))

    numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))
    user_prompt = POINT_SELECTION_USER.format(
        transcript=transcript,
        sentence_count=len(sentences),
        numbered_sentences=numbered,
    )
    data = await get_ollama().generate_json(
        model=settings.ollama_llm_model,
        prompt=user_prompt,
        system=POINT_SELECTION_SYSTEM,
        options={
            "temperature": 0.1,
            "num_ctx": 16384,    # fit long transcript + numbered list + output
            "num_predict": 8192, # let the model emit dozens of points
        },
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
        # Force every point through web search — parametric memory is
        # disabled at the pipeline level. The model's needs_search hint
        # is ignored, but we still drop the prelim_answer to keep the
        # downstream answerer clean.
        claims.append(Claim(
            id=len(claims),
            text=text,
            source="transcript",
            needs_search=True,
            prelim_answer=None,
        ))

    log.info("LLM selected %d point(s) — all routed through web search", len(claims))
    return claims
