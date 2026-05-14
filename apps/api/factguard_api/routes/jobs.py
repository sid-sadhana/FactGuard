from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models.schemas import Job
from ..store.jobs import get_job_store

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[Job])
async def list_jobs() -> list[Job]:
    return await get_job_store().list()


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str) -> Job:
    job = await get_job_store().get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/events")
async def stream_events(job_id: str):
    store = get_job_store()
    job = await store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue = store.subscribe(job_id)

    async def event_source():
        try:
            yield _sse(job)
            while True:
                try:
                    updated = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _sse(updated)
                    if updated.progress.stage.value in {"completed", "failed"}:
                        break
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            store.unsubscribe(job_id, queue)

    return StreamingResponse(event_source(), media_type="text/event-stream")


def _sse(job: Job) -> str:
    payload = json.dumps(job.model_dump(mode="json"))
    return f"event: job\ndata: {payload}\n\n"
