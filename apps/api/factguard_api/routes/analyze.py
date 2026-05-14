from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..models.schemas import CreateYouTubeJob, IngestSource, Job
from ..services.pipeline import run_pipeline
from ..services.upload import save_upload
from ..services.youtube import extract_video_id
from ..store.jobs import get_job_store

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/youtube", response_model=Job)
async def analyze_youtube(payload: CreateYouTubeJob, background: BackgroundTasks) -> Job:
    url = str(payload.url)
    if not extract_video_id(url):
        raise HTTPException(status_code=400, detail="Not a recognizable YouTube URL")

    store = get_job_store()
    job = await store.create(IngestSource.youtube, url)
    background.add_task(run_pipeline, job.job_id, IngestSource.youtube, url, local_video=None)
    return job


@router.post("/upload", response_model=Job)
async def analyze_upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    filename: str | None = Form(default=None),
) -> Job:
    store = get_job_store()
    job = await store.create(IngestSource.upload, filename or file.filename or "uploaded-video")
    try:
        path = await save_upload(file, job.job_id)
    except ValueError as exc:
        await store.fail(job.job_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background.add_task(
        run_pipeline,
        job.job_id,
        IngestSource.upload,
        str(path),
        local_video=Path(path),
    )
    return job
