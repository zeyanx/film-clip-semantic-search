from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..loader import load_jsonl
from ..models import Segment


@dataclass(frozen=True, slots=True)
class LocalJsonlSource:
    path: Path

    @property
    def name(self) -> str:
        return f"local-jsonl:{self.path.name}"

    def load(self) -> list[Segment]:
        return load_jsonl(self.path)

