"""Ragas-based evaluation of the retrieval pipeline.

Ragas is heavy and optional; we import it lazily. If it (or its required
LLM backend) is unavailable, we return None and the score function falls
back to claim-level signals alone.
"""
from __future__ import annotations

import asyncio
import os

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.schemas import ClaimVerification, Evidence, RagasScores

log = get_logger(__name__)


def _verdict_text(v: ClaimVerification) -> str:
    """Treat each verification as a Q/A pair: claim -> reasoning."""
    return v.reasoning


def _contexts(citations: list[Evidence]) -> list[str]:
    return [f"{e.title}\n{e.snippet}" for e in citations][:4]


async def run_ragas(verifications: list[ClaimVerification]) -> RagasScores | None:
    settings = get_settings()
    if not settings.enable_ragas or not verifications:
        return None

    def _evaluate() -> RagasScores | None:
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import (
                answer_relevancy,
                context_precision,
                context_recall,
                faithfulness,
            )
            from langchain_community.chat_models import ChatOllama
            from langchain_community.embeddings import OllamaEmbeddings
        except ImportError as exc:
            log.info("Ragas dependencies unavailable: %s", exc)
            return None

        rows = {
            "question": [v.claim.text for v in verifications],
            "answer": [_verdict_text(v) for v in verifications],
            "contexts": [_contexts(v.citations) for v in verifications],
            "ground_truth": [v.claim.text for v in verifications],
        }
        ds = Dataset.from_dict(rows)

        llm = ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=0.0,
        )
        embeddings = OllamaEmbeddings(
            model=settings.ollama_embed_model,
            base_url=settings.ollama_base_url,
        )

        # Ragas writes telemetry by default; silence it.
        os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

        try:
            result = evaluate(
                ds,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=llm,
                embeddings=embeddings,
                raise_exceptions=False,
            )
        except Exception as exc:
            log.warning("Ragas evaluate() failed: %s", exc)
            return None

        def pick(name: str) -> float | None:
            val = result.get(name) if hasattr(result, "get") else None
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        return RagasScores(
            faithfulness=pick("faithfulness"),
            answer_relevancy=pick("answer_relevancy"),
            context_precision=pick("context_precision"),
            context_recall=pick("context_recall"),
        )

    return await asyncio.to_thread(_evaluate)
