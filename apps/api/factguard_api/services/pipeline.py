"""End-to-end fact-check pipeline.

Flow:
  ingest → transcript → LLM picks checkworthy points and flags which need a
                        fresh web search → for flagged points, Tavily +
                        WebBaseLoader + rerank → LLM writes a cited answer.
                        Unflagged points are answered from the picker's own
                        preliminary answer with no Tavily round-trip.
"""
from __future__ import annotations

from pathlib import Path

from ..core.logging import get_logger
from ..core.progress import ProgressReporter
from ..core.qdrant import cleanup_job as cleanup_qdrant_job
from ..models.schemas import IngestSource, JobResult, JobStage
from ..store.jobs import JobStore, get_job_store
from .agent import answer_all
from .claims import extract_claims
from .eval import run_ragas
from .frames import probe_duration
from .score import compute_overall_score
from .transcript import to_text, transcript_from_file, transcript_from_youtube
from .youtube import download_video, fetch_video_metadata

log = get_logger(__name__)


# Stage percent bands — only four real stages now that the agent absorbs
# search + retrieval + verification.
BAND = {
    JobStage.ingesting: (5, 25),
    JobStage.transcribing: (25, 50),
    JobStage.extracting_claims: (50, 60),
    JobStage.verifying: (60, 98),
    JobStage.evaluating: (98, 100),
}


def _reporter(store: JobStore, job_id: str, stage: JobStage) -> ProgressReporter:
    base, end = BAND[stage]
    return ProgressReporter(store, job_id, stage, base, end)


async def run_pipeline(
    job_id: str,
    source: IngestSource,
    source_ref: str,
    *,
    local_video: Path | None = None,
) -> None:
    store = get_job_store()
    try:
        # --- ingest -----------------------------------------------------------
        ingest = _reporter(store, job_id, JobStage.ingesting)
        await ingest.start("Fetching video")
        title: str | None = None
        if source is IngestSource.youtube:
            meta = await fetch_video_metadata(source_ref)
            title = meta.get("title")
            await ingest.tick(1, 2, f"Downloading: {title or source_ref}")
            video_path = await download_video(source_ref, job_id)
            await ingest.tick(2, 2, "Downloaded")
        else:
            assert local_video is not None
            video_path = local_video
            title = video_path.stem
            await ingest.tick(2, 2, f"Using upload: {video_path.name}")

        duration = await probe_duration(video_path)

        # --- transcript -------------------------------------------------------
        trx = _reporter(store, job_id, JobStage.transcribing)
        if source is IngestSource.youtube:
            await trx.start("Fetching YouTube captions")
            segments = await transcript_from_youtube(source_ref)
            if not segments:
                await trx.tick(1, 2, "Captions unavailable — transcribing with whisper")
                segments = await transcript_from_file(video_path)
        else:
            await trx.start("Transcribing audio with whisper")
            segments = await transcript_from_file(video_path)
        transcript = to_text(segments)
        await trx.tick(2, 2, f"Transcript: {len(transcript)} chars across {len(segments)} segments")

        # --- points -----------------------------------------------------------
        cl = _reporter(store, job_id, JobStage.extracting_claims)
        await cl.start("LLM picking checkworthy points from transcript")
        points = await extract_claims(transcript)
        needs = sum(1 for p in points if p.needs_search)
        await cl.tick(
            1, 1,
            f"Selected {len(points)} point{'s' if len(points) != 1 else ''} "
            f"— {needs} need web search",
        )

        # --- answering --------------------------------------------------------
        ans = _reporter(store, job_id, JobStage.verifying)
        await ans.start(
            f"Answering {len(points)} point{'s' if len(points) != 1 else ''} "
            f"({needs} via Tavily + WebBaseLoader, "
            f"{len(points) - needs} from parametric memory)"
        )

        async def ans_progress(done: int, total: int, msg: str) -> None:
            await ans.tick(done, total, msg)

        verifications = await answer_all(points, on_progress=ans_progress, job_id=job_id)

        # --- eval / score -----------------------------------------------------
        ev2 = _reporter(store, job_id, JobStage.evaluating)
        await ev2.start("Finalizing")
        ragas = await run_ragas(verifications)
        overall = compute_overall_score(verifications, ragas)
        summary = _build_summary(verifications)

        result = JobResult(
            job_id=job_id,
            source=source,
            source_ref=source_ref,
            title=title,
            duration_seconds=duration or None,
            transcript=transcript,
            claims=points,
            verifications=verifications,
            ragas=ragas,
            overall_score=overall,
            summary=summary,
        )
        await store.complete(job_id, result)
        log.info("Job %s complete — %d points answered", job_id, len(verifications))
    except Exception as exc:
        log.exception("Pipeline failed for job %s", job_id)
        await store.fail(job_id, str(exc))
    finally:
        await cleanup_qdrant_job(job_id)


def _build_summary(verifications: list) -> str:
    total = len(verifications)
    if total == 0:
        return (
            "No points were extracted. The transcript was empty or no "
            "checkworthy sentences were found."
        )
    grounded = sum(1 for v in verifications if v.citations)
    total_sources = sum(len(v.citations) for v in verifications)
    parametric = total - grounded
    return (
        f"Answered {total} point{'s' if total != 1 else ''} from the transcript. "
        f"Web search was used for {grounded} of them, citing "
        f"{total_sources} source{'s' if total_sources != 1 else ''}; "
        f"the remaining {parametric} were answered from the model's own knowledge."
    )
