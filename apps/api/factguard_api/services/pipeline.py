"""End-to-end fact-check pipeline.

Flow:
  ingest → transcript → sentence-split → LLM extracts every checkworthy
  point as a self-contained sentence → each point goes through DDG +
  WebBaseLoader + Qdrant Cloud Inference rerank → gemma4:e4b writes a
  cited answer → all citations are pooled into a global evidence list
  and the LLM writes one overall cited synthesis with inline [N] markers
  referencing that global list.
"""
from __future__ import annotations

import asyncio
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
from .synthesize import synthesize_summary
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


async def _creep_progress(
    store: JobStore,
    job_id: str,
    *,
    interval: float = 0.7,
) -> None:
    """Fake loader: inch the bar toward (band_end - 1) between real ticks.

    Reads the current stage's percent and nudges it up by ~5% of the gap to
    its ceiling each tick. Real ticks always override; the creep only fills
    silent stretches so the UI never looks stuck. Cancelled in pipeline's
    finally block.
    """
    try:
        while True:
            await asyncio.sleep(interval)
            job = await store.get(job_id)
            if not job:
                continue
            stage = job.progress.stage
            band = BAND.get(stage)
            if band is None:
                continue
            _, end = band
            ceiling = end - 1
            current = job.progress.percent
            if current >= ceiling:
                continue
            gap = ceiling - current
            step = max(1, int(gap * 0.05))
            await store.update_progress(
                job_id, stage, current + step, job.progress.message,
            )
    except asyncio.CancelledError:
        return


async def run_pipeline(
    job_id: str,
    source: IngestSource,
    source_ref: str,
    *,
    local_video: Path | None = None,
) -> None:
    store = get_job_store()
    creep_task = asyncio.create_task(_creep_progress(store, job_id))
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
        await cl.tick(
            1, 1,
            f"Selected {len(points)} point{'s' if len(points) != 1 else ''} "
            f"— all routed through web search",
        )

        # --- answering --------------------------------------------------------
        ans = _reporter(store, job_id, JobStage.verifying)
        await ans.start(
            f"Fact-checking {len(points)} point{'s' if len(points) != 1 else ''} "
            f"via DDG + WebBaseLoader + Qdrant rerank"
        )

        async def ans_progress(done: int, total: int, msg: str) -> None:
            await ans.tick(done, total, msg)

        verifications = await answer_all(points, on_progress=ans_progress, job_id=job_id)

        # --- eval / score / synthesis ----------------------------------------
        ev2 = _reporter(store, job_id, JobStage.evaluating)
        await ev2.start("Synthesizing overall answer")
        ragas = await run_ragas(verifications)
        overall = compute_overall_score(verifications, ragas)
        summary_text, summary_citations = await synthesize_summary(transcript, verifications)

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
            summary=summary_text,
            summary_citations=summary_citations,
        )
        await store.complete(job_id, result)
        log.info("Job %s complete — %d points answered", job_id, len(verifications))
    except Exception as exc:
        log.exception("Pipeline failed for job %s", job_id)
        await store.fail(job_id, str(exc))
    finally:
        creep_task.cancel()
        try:
            await creep_task
        except asyncio.CancelledError:
            pass
        await cleanup_qdrant_job(job_id)


