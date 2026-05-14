"""In-process job store with async pub/sub for progress streaming.

For a single-instance deployment this is sufficient. Swap in Redis +
streams if the API needs to scale horizontally.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from ..models.schemas import (
    IngestSource,
    Job,
    JobProgress,
    JobResult,
    JobStage,
)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._subs: dict[str, list[asyncio.Queue[Job]]] = {}
        self._lock = asyncio.Lock()

    async def create(self, source: IngestSource, source_ref: str) -> Job:
        async with self._lock:
            now = datetime.now(timezone.utc)
            job = Job(
                job_id=uuid.uuid4().hex,
                source=source,
                source_ref=source_ref,
                created_at=now,
                updated_at=now,
                progress=JobProgress(stage=JobStage.pending, percent=0),
            )
            self._jobs[job.job_id] = job
            self._subs[job.job_id] = []
            return job

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def list(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    async def update_progress(
        self, job_id: str, stage: JobStage, percent: int, message: str = ""
    ) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.progress = JobProgress(stage=stage, percent=percent, message=message)
        job.updated_at = datetime.now(timezone.utc)
        await self._broadcast(job)

    async def complete(self, job_id: str, result: JobResult) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.result = result
        job.progress = JobProgress(stage=JobStage.completed, percent=100, message="done")
        job.updated_at = datetime.now(timezone.utc)
        await self._broadcast(job)

    async def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.error = error
        job.progress = JobProgress(stage=JobStage.failed, percent=100, message=error)
        job.updated_at = datetime.now(timezone.utc)
        await self._broadcast(job)

    def subscribe(self, job_id: str) -> asyncio.Queue[Job]:
        q: asyncio.Queue[Job] = asyncio.Queue()
        self._subs.setdefault(job_id, []).append(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue[Job]) -> None:
        if job_id in self._subs and q in self._subs[job_id]:
            self._subs[job_id].remove(q)

    async def _broadcast(self, job: Job) -> None:
        for q in self._subs.get(job.job_id, []):
            await q.put(job)


_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store
