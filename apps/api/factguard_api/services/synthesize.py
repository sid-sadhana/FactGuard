"""Overall cited summary synthesis.

After per-point answers are written, this module pulls every citation
across every point into a single de-duplicated global evidence list,
remaps each point's local [i] markers to the new global indices, then
asks the LLM to write one coherent multi-sentence answer that grounds
the whole video's factual content against the global evidence.

Returned in `JobResult.summary` (text with inline [N] markers) and
`JobResult.summary_citations` (the global evidence list in [N] order).
"""
from __future__ import annotations

import json
import re

from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.ollama import get_ollama
from ..models.schemas import ClaimVerification, Evidence
from ..prompts.templates import SUMMARY_SYSTEM, SUMMARY_USER

log = get_logger(__name__)

_MARKER_RE = re.compile(r"\[(\d+)\]")


def _build_global_evidence(verifications: list[ClaimVerification]) -> tuple[list[Evidence], dict[int, dict[int, int]]]:
    """Dedupe every cited Evidence across all points by URL.

    Returns:
      * global_list: [Evidence, ...] in deterministic order (first-seen).
      * remap: {claim_id: {local_index: global_index}}

    Earlier evidence in the per-point lists wins when duplicates collide,
    so the global ordering tracks the order facts were introduced in the
    video.
    """
    global_list: list[Evidence] = []
    url_to_global: dict[str, int] = {}
    remap: dict[int, dict[int, int]] = {}

    for v in verifications:
        local_to_global: dict[int, int] = {}
        for local_i, ev in enumerate(v.citations):
            key = ev.url or f"__noref__{local_i}_{v.claim.id}"
            gi = url_to_global.get(key)
            if gi is None:
                gi = len(global_list)
                global_list.append(ev)
                url_to_global[key] = gi
            local_to_global[local_i] = gi
        remap[v.claim.id] = local_to_global
    return global_list, remap


def _remap_markers(text: str, local_to_global: dict[int, int]) -> str:
    """Rewrite every [i] in text using the local→global lookup."""
    if not local_to_global:
        return text

    def sub(m: re.Match[str]) -> str:
        local = int(m.group(1))
        gi = local_to_global.get(local)
        return f"[{gi}]" if gi is not None else m.group(0)

    return _MARKER_RE.sub(sub, text)


def _format_point_answers(
    verifications: list[ClaimVerification],
    remap: dict[int, dict[int, int]],
) -> str:
    """One line per point: claim → answer with remapped citation markers."""
    lines: list[str] = []
    for v in verifications:
        local_to_global = remap.get(v.claim.id, {})
        answer = _remap_markers(v.reasoning or "", local_to_global)
        if not answer.strip():
            continue
        lines.append(f"- Claim: {v.claim.text}\n  Answer: {answer}")
    return "\n\n".join(lines)


def _format_evidence_block(global_evidence: list[Evidence]) -> str:
    if not global_evidence:
        return "(no web sources)"
    return "\n\n".join(
        f"[{i}] {e.title}\n    URL: {e.url}\n    {e.snippet}"
        for i, e in enumerate(global_evidence)
    )


def _parse_summary_json(raw: str | dict) -> tuple[str, list[int]]:
    """Tolerant parser — same shape as agent._parse_answer_json."""
    if not raw:
        return "", []
    data = raw if isinstance(raw, dict) else None
    if data is None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            text = str(raw)
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end <= start:
                return text.strip(), []
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return text.strip(), []
    if not isinstance(data, dict):
        return "", []
    summary = str(data.get("summary", "")).strip()
    raw_idx = data.get("supporting_indices") or []
    indices: list[int] = []
    for x in raw_idx:
        try:
            indices.append(int(x))
        except (TypeError, ValueError):
            continue
    return summary, indices


async def synthesize_summary(
    transcript: str,
    verifications: list[ClaimVerification],
) -> tuple[str, list[Evidence]]:
    """LLM-driven overall cited synthesis with a globally-numbered evidence list."""
    if not verifications:
        return "", []

    global_evidence, remap = _build_global_evidence(verifications)
    if not global_evidence:
        # Fall back to a flat stat string if nothing was cited at all.
        return _stat_fallback(verifications), []

    settings = get_settings()
    user_prompt = SUMMARY_USER.format(
        transcript=transcript[:8000],  # keep some headroom in the ctx window
        point_answers=_format_point_answers(verifications, remap),
        evidence_block=_format_evidence_block(global_evidence),
        last_index=len(global_evidence) - 1,
    )
    try:
        data = await get_ollama().generate_json(
            model=settings.ollama_llm_model,
            prompt=user_prompt,
            system=SUMMARY_SYSTEM,
            options={
                "temperature": 0.2,
                "num_ctx": 16384,
                "num_predict": 1200,
            },
        )
    except Exception as exc:
        log.warning("Summary synthesis LLM failed: %s", exc)
        return _stat_fallback(verifications), global_evidence

    summary, _indices = _parse_summary_json(data)
    if not summary:
        log.warning("Summary synthesis returned empty text — falling back")
        return _stat_fallback(verifications), global_evidence
    return summary, global_evidence


def _stat_fallback(verifications: list[ClaimVerification]) -> str:
    total = len(verifications)
    if total == 0:
        return "No checkworthy points were extracted from the transcript."
    grounded = sum(1 for v in verifications if v.citations)
    total_sources = sum(len(v.citations) for v in verifications)
    return (
        f"Fact-checked {total} point{'s' if total != 1 else ''} from the transcript. "
        f"Web evidence backed {grounded} of them, citing "
        f"{total_sources} source{'s' if total_sources != 1 else ''}."
    )
