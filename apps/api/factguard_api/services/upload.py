from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)

ALLOWED_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


async def save_upload(file: UploadFile, job_id: str) -> Path:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"Unsupported video format: {suffix or 'unknown'}")

    out_dir = settings.storage_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"source{suffix}"

    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    with target.open("wb") as fh:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                target.unlink(missing_ok=True)
                raise ValueError(f"Upload exceeds {settings.max_upload_mb} MB limit")
            fh.write(chunk)

    log.info("Saved upload %s (%d bytes) -> %s", file.filename, written, target)
    return target
