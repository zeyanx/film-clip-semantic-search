from __future__ import annotations

from dataclasses import dataclass
import re


TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    start_seconds: float
    end_seconds: float
    text: str


def parse_timestamp(value: str) -> float:
    hours, minutes, remainder = value.replace(",", ".").split(":")
    seconds = int(hours) * 3600 + int(minutes) * 60 + float(remainder)
    if seconds < 0:
        raise ValueError("timestamp must be non-negative")
    return seconds


def _clean_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_srt(text: str) -> list[SubtitleCue]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cues: list[SubtitleCue] = []
    for block in re.split(r"\n\s*\n", normalized):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timestamp_index = next(
            (index for index, line in enumerate(lines) if TIMESTAMP_RE.search(line)), None
        )
        if timestamp_index is None:
            continue
        match = TIMESTAMP_RE.search(lines[timestamp_index])
        assert match is not None
        cue_text = _clean_text(lines[timestamp_index + 1 :])
        if not cue_text:
            continue
        start = parse_timestamp(match.group("start"))
        end = parse_timestamp(match.group("end"))
        if end <= start:
            raise ValueError(f"subtitle end must be after start: {match.group(0)}")
        cues.append(SubtitleCue(start, end, cue_text))
    return cues


def parse_vtt(text: str) -> list[SubtitleCue]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"^\ufeff?WEBVTT[^\n]*\n", "", normalized, count=1)
    return parse_srt(normalized)
