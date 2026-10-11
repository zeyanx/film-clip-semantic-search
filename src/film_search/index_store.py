from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Iterable

from .loader import parse_segment
from .models import Segment


INDEX_SCHEMA_VERSION = 1


class PersistentIndex:
    def __init__(self, segments: Iterable[Segment]):
        self._segments = {segment.segment_id: segment for segment in segments}
        if not self._segments:
            raise ValueError("index requires at least one segment")

    @property
    def segments(self) -> tuple[Segment, ...]:
        return tuple(self._segments[key] for key in sorted(self._segments))

    def upsert(self, segments: Iterable[Segment]) -> tuple[int, int]:
        inserted = 0
        updated = 0
        for segment in segments:
            if segment.segment_id in self._segments:
                updated += 1
            else:
                inserted += 1
            self._segments[segment.segment_id] = segment
        return inserted, updated

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "segments": [asdict(segment) for segment in self.segments],
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(destination)
        return destination.resolve()

    @classmethod
    def load(cls, path: str | Path) -> "PersistentIndex":
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot load index {source}: {exc}") from exc
        if payload.get("schema_version") != INDEX_SCHEMA_VERSION:
            raise ValueError("unsupported index schema version")
        records = payload.get("segments")
        if not isinstance(records, list):
            raise ValueError("index segments must be a list")
        return cls(parse_segment(record, line_number=index) for index, record in enumerate(records, 1))
