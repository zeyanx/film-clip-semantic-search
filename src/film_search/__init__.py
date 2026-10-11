"""Offline film-clip semantic search baseline."""

from .engine import SearchEngine, SearchResult
from .index_store import PersistentIndex
from .loader import DatasetError, load_jsonl, load_jsonl_text
from .media import MediaToolError
from .models import Segment

__all__ = [
    "DatasetError",
    "MediaToolError",
    "PersistentIndex",
    "SearchEngine",
    "SearchResult",
    "Segment",
    "load_jsonl",
    "load_jsonl_text",
]

