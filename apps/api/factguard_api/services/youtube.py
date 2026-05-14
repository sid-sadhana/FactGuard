from __future__ import annotations

import asyncio
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str | None:
    """Return the 11-char YouTube video id, or None if the URL is unrecognized."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
        return candidate if _VIDEO_ID_RE.match(candidate) else None
    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            v = parse_qs(parsed.query).get("v", [None])[0]
            return v if v and _VIDEO_ID_RE.match(v) else None
        for prefix in ("/embed/", "/shorts/", "/v/"):
            if parsed.path.startswith(prefix):
                v = parsed.path[len(prefix):].split("/")[0]
                return v if _VIDEO_ID_RE.match(v) else None
    return None


async def download_video(url: str, job_id: str) -> Path:
    """Download to <storage>/<job_id>/source.mp4 via yt-dlp.

    We intentionally cap height to 720p — frames go to a VLM, more pixels
    don't help and cost bandwidth + disk.
    """
    settings = get_settings()
    out_dir = settings.storage_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "source.mp4"

    cmd = [
        "yt-dlp",
        "-f", "best[height<=720][ext=mp4]/best[height<=720]/best",
        "--no-playlist",
        "--quiet",
        "-o", str(target),
        url,
    ]
    log.info("yt-dlp downloading %s -> %s", url, target)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {stderr.decode(errors='ignore')[:500]}")
    if not target.exists():
        raise RuntimeError("yt-dlp finished but no output file was produced")
    return target


async def fetch_video_metadata(url: str) -> dict:
    """Lightweight metadata fetch (title, duration) without downloading."""
    cmd = ["yt-dlp", "--dump-single-json", "--skip-download", "--quiet", url]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return {}
    import json
    try:
        data = json.loads(stdout)
        return {"title": data.get("title"), "duration": data.get("duration")}
    except json.JSONDecodeError:
        return {}
