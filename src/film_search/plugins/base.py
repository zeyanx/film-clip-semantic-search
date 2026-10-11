from __future__ import annotations

from typing import Protocol, Sequence

from ..models import Segment


class SegmentSource(Protocol):
    """Extension point for authorized local/catalog data sources."""

    @property
    def name(self) -> str: ...

    def load(self) -> Sequence[Segment]: ...

