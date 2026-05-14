"""ffprobe helper for video duration.

Keyframe extraction was removed along with the VLM stage; the pipeline only
needs the source video's duration for the result payload.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path


async def probe_duration(video: Path) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(video),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    try:
        return float(json.loads(stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return 0.0
