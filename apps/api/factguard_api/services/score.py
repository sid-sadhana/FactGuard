from __future__ import annotations

from ..models.schemas import ClaimVerification, RagasScores


def compute_overall_score(
    verifications: list[ClaimVerification],
    ragas: RagasScores | None,
) -> int:
    """Blend claim-level verdicts with Ragas signals into a 0-100 score.

    Two halves:
      * claim_score: confidence-weighted, with refuted claims subtracting.
      * rag_score:   average of available Ragas metrics (0..1).

    When Ragas is unavailable we fall back to the claim score alone.
    """
    if not verifications:
        return 0

    weight_sum = 0.0
    score_sum = 0.0
    for v in verifications:
        w = max(v.confidence, 0.25)
        if v.verdict == "supported":
            score_sum += 1.0 * w
        elif v.verdict == "refuted":
            score_sum += -1.0 * w
        else:
            score_sum += 0.5 * w
        weight_sum += w

    normalized = (score_sum / weight_sum + 1) / 2  # map [-1,1] -> [0,1]
    claim_score = max(0.0, min(1.0, normalized))

    if ragas is None:
        return round(claim_score * 100)

    rag_components = [
        v for v in (
            ragas.faithfulness,
            ragas.answer_relevancy,
            ragas.context_precision,
            ragas.context_recall,
        ) if v is not None
    ]
    if not rag_components:
        return round(claim_score * 100)

    rag_score = sum(rag_components) / len(rag_components)
    blended = 0.65 * claim_score + 0.35 * rag_score
    return round(max(0.0, min(1.0, blended)) * 100)
