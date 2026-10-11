from __future__ import annotations


def format_timecode(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    total_milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    return f"{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def format_range(start_seconds: float, end_seconds: float) -> str:
    return f"{format_timecode(start_seconds)} – {format_timecode(end_seconds)}"

