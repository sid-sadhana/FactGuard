from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class JobStage(str, Enum):
    pending = "pending"
    ingesting = "ingesting"
    transcribing = "transcribing"
    extracting_claims = "extracting_claims"
    retrieving_evidence = "retrieving_evidence"
    verifying = "verifying"
    evaluating = "evaluating"
    completed = "completed"
    failed = "failed"


class IngestSource(str, Enum):
    youtube = "youtube"
    upload = "upload"


class CreateYouTubeJob(BaseModel):
    url: HttpUrl


class JobProgress(BaseModel):
    stage: JobStage
    message: str = ""
    percent: int = 0


class TranscriptSegment(BaseModel):
    start: float
    duration: float
    text: str


class Claim(BaseModel):
    id: int
    text: str
    source: Literal["transcript"] = "transcript"
    needs_search: bool = True
    prelim_answer: str | None = None


class Evidence(BaseModel):
    url: str
    title: str
    snippet: str
    score: float = 0.0


Verdict = Literal["supported", "refuted", "unverifiable"]


class ClaimVerification(BaseModel):
    claim: Claim
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    citations: list[Evidence] = Field(default_factory=list)


class RagasScores(BaseModel):
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None


class JobResult(BaseModel):
    job_id: str
    source: IngestSource
    source_ref: str
    title: str | None = None
    duration_seconds: float | None = None
    transcript: str = ""
    claims: list[Claim] = Field(default_factory=list)
    verifications: list[ClaimVerification] = Field(default_factory=list)
    ragas: RagasScores | None = None
    overall_score: int = 0
    summary: str = ""


class Job(BaseModel):
    job_id: str
    source: IngestSource
    source_ref: str
    created_at: datetime
    updated_at: datetime
    progress: JobProgress
    result: JobResult | None = None
    error: str | None = None
