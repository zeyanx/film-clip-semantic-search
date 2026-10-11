from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


class MediaToolError(RuntimeError):
    pass


def validate_video_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise MediaToolError(f"video file does not exist: {candidate}")
    if candidate.suffix.casefold() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise MediaToolError(
            f"unsupported video extension {candidate.suffix!r}; supported: "
            + ", ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
        )
    return candidate.resolve()


def find_media_tool(name: str, env_name: str) -> str | None:
    configured = os.environ.get(env_name, "").strip()
    if configured:
        path = Path(configured).expanduser()
        return str(path.resolve()) if path.is_file() else None
    return shutil.which(name)


def probe_duration(path: str | Path, ffprobe_path: str | None = None) -> float:
    video = validate_video_path(path)
    ffprobe = ffprobe_path or find_media_tool("ffprobe", "FILM_SEARCH_FFPROBE")
    if not ffprobe:
        raise MediaToolError(
            "FFprobe is unavailable; configure FILM_SEARCH_FFPROBE or import subtitles/JSONL instead"
        )
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(video),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise MediaToolError(completed.stderr.strip() or "FFprobe could not read the video")
    try:
        duration = float(json.loads(completed.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MediaToolError("FFprobe returned an invalid duration") from exc
    if duration <= 0:
        raise MediaToolError("video duration must be positive")
    return duration


def build_time_windows(
    duration: float, *, window_seconds: float = 12.0, stride_seconds: float = 8.0
) -> list[tuple[float, float]]:
    if duration <= 0 or window_seconds <= 0 or stride_seconds <= 0:
        raise ValueError("duration, window_seconds, and stride_seconds must be positive")
    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < duration:
        end = min(duration, start + window_seconds)
        windows.append((round(start, 3), round(end, 3)))
        if end >= duration:
            break
        start += stride_seconds
    return windows


def extract_keyframe(
    video_path: str | Path,
    timestamp_seconds: float,
    output_path: str | Path,
    ffmpeg_path: str | None = None,
) -> Path:
    if timestamp_seconds < 0:
        raise ValueError("timestamp_seconds must be non-negative")
    video = validate_video_path(video_path)
    ffmpeg = ffmpeg_path or find_media_tool("ffmpeg", "FILM_SEARCH_FFMPEG")
    if not ffmpeg:
        raise MediaToolError(
            "FFmpeg is unavailable; configure FILM_SEARCH_FFMPEG or provide existing keyframes"
        )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{timestamp_seconds:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file():
        raise MediaToolError(completed.stderr.strip() or "FFmpeg did not create a keyframe")
    return output.resolve()
