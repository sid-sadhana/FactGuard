"""Sub-stage progress reporting.

A pipeline stage owns a percent *range* (e.g. verifying = 60..98) and emits
ticks inside it: "Answered 1/5", "Answered 2/5"... so the UI sees both a
moving bar and a moving message, instead of a long flat plateau.

Usage:

    reporter = ProgressReporter(store, job_id, JobStage.verifying, 60, 98)
    await reporter.tick(0, total=5, message="Starting")
    for i, point in enumerate(points):
        ...
        await reporter.tick(i + 1, total=5, message=f"Answered {i + 1}/5")
"""
from __future__ import annotations

from ..models.schemas import JobStage
from ..store.jobs import JobStore


class ProgressReporter:
    def __init__(
        self,
        store: JobStore,
        job_id: str,
        stage: JobStage,
        base_pct: int,
        end_pct: int,
    ) -> None:
        self.store = store
        self.job_id = job_id
        self.stage = stage
        self.base = base_pct
        self.span = max(0, end_pct - base_pct)

    def percent_for(self, done: int, total: int) -> int:
        if total <= 0:
            return self.base + self.span
        ratio = min(1.0, max(0.0, done / total))
        return self.base + int(self.span * ratio)

    async def tick(self, done: int, total: int, message: str) -> None:
        pct = self.percent_for(done, total)
        await self.store.update_progress(self.job_id, self.stage, pct, message)

    async def start(self, message: str) -> None:
        await self.store.update_progress(self.job_id, self.stage, self.base, message)
