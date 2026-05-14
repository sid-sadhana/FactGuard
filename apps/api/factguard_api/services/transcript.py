"""Transcript extraction.

Two paths:
  * YouTube: try the captions API first (free, fast), fall back to whisper on the local file.
  * Upload: faster-whisper on the audio track extracted by ffmpeg.

faster-whisper is imported lazily so the API can boot without it installed.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.schemas import TranscriptSegment
from ..services.youtube import extract_video_id

log = get_logger(__name__)


def _segments_to_text(segments: list[TranscriptSegment]) -> str:
    return " ".join(s.text.strip() for s in segments if s.text.strip())


async def transcript_from_youtube(url: str) -> list[TranscriptSegment]:
    video_id = extract_video_id(url)
    if not video_id:
        return []

    def _fetch() -> list[TranscriptSegment]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            log.warning("youtube-transcript-api not installed")
            return []

        # v1.x (instance-based, .fetch()) vs <1.0 (classmethod .get_transcript()).
        try:
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                raw = YouTubeTranscriptApi.get_transcript(video_id)  # type: ignore[attr-defined]
                items = [
                    (float(it.get("start", 0.0)), float(it.get("duration", 0.0)), str(it.get("text", "")))
                    for it in raw
                ]
            else:
                api = YouTubeTranscriptApi()
                fetched = api.fetch(video_id)
                rows = getattr(fetched, "snippets", None) or list(fetched)
                items = [
                    (float(getattr(r, "start", 0.0)),
                     float(getattr(r, "duration", 0.0)),
                     str(getattr(r, "text", "")))
                    for r in rows
                ]
        except Exception as exc:
            log.info("Captions unavailable for %s: %s", video_id, exc)
            return []

        return [TranscriptSegment(start=s, duration=d, text=t) for s, d, t in items]

    return await asyncio.to_thread(_fetch)


async def transcript_from_file(video: Path) -> list[TranscriptSegment]:
    """Run faster-whisper on the audio track.

    The model is loaded once per process and kept in module state.
    """
    audio = video.with_suffix(".wav")
    if not audio.exists():
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-ac", "1", "-ar", "16000",
            str(audio),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0 or not audio.exists():
            log.warning("ffmpeg audio extraction failed: %s", stderr.decode(errors="ignore")[:200])
            return []

    def _transcribe() -> list[TranscriptSegment]:
        try:
            model = _get_whisper()
        except Exception as exc:
            log.warning("Whisper unavailable: %s", exc)
            return []
        segments_iter, _info = model.transcribe(str(audio), vad_filter=True)
        out: list[TranscriptSegment] = []
        for seg in segments_iter:
            out.append(
                TranscriptSegment(
                    start=float(seg.start),
                    duration=float(seg.end - seg.start),
                    text=seg.text,
                )
            )
        return out

    return await asyncio.to_thread(_transcribe)


_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    from faster_whisper import WhisperModel
    _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def to_text(segments: list[TranscriptSegment]) -> str:
    return _segments_to_text(segments)
