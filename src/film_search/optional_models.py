from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

from .models import Segment


class OptionalModelError(RuntimeError):
    pass


class SimilarityProvider(Protocol):
    name: str

    def score(self, query: str, segment: Segment) -> float | None: ...


def cosine(left: list[float] | tuple[float, ...], right: list[float] | tuple[float, ...]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("vectors must be non-empty and have equal dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    raw = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return max(-1.0, min(1.0, raw))


class LocalSentenceTransformerProvider:
    name = "local_sentence_transformer"

    def __init__(self, model_dir: str | Path):
        model_path = Path(model_dir).expanduser()
        if not model_path.is_dir():
            raise OptionalModelError(f"sentence model directory does not exist: {model_path}")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise OptionalModelError(
                "sentence-transformers is not installed; TF-IDF remains available"
            ) from exc
        self.model = SentenceTransformer(str(model_path), local_files_only=True)
        self._segment_cache: dict[str, list[float]] = {}

    def _encode(self, text: str) -> list[float]:
        vector = self.model.encode([text], normalize_embeddings=True)[0]
        return [float(item) for item in vector]

    def score(self, query: str, segment: Segment) -> float:
        query_vector = self._encode(query)
        segment_vector = self._segment_cache.setdefault(
            segment.segment_id, self._encode(segment.searchable_text)
        )
        return max(0.0, cosine(query_vector, segment_vector))


class LocalClipProvider:
    name = "local_clip"

    def __init__(self, model_dir: str | Path, project_root: str | Path):
        model_path = Path(model_dir).expanduser()
        if not model_path.is_dir():
            raise OptionalModelError(f"CLIP model directory does not exist: {model_path}")
        try:
            from PIL import Image
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise OptionalModelError(
                "Pillow/transformers/torch are not installed; visual search is unavailable"
            ) from exc
        self.Image = Image
        self.processor = CLIPProcessor.from_pretrained(str(model_path), local_files_only=True)
        self.model = CLIPModel.from_pretrained(str(model_path), local_files_only=True)
        self.project_root = Path(project_root)
        self._image_cache: dict[str, list[float]] = {}

    def _text_vector(self, text: str) -> list[float]:
        values = self.processor(text=[text], return_tensors="pt", padding=True)
        vector = self.model.get_text_features(**values)[0].detach().cpu().tolist()
        return [float(item) for item in vector]

    def _image_vector(self, segment: Segment) -> list[float] | None:
        raw = segment.keyframe_path
        if not raw:
            return None
        path = Path(raw)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.is_file():
            return None
        if segment.segment_id not in self._image_cache:
            image = self.Image.open(path).convert("RGB")
            values = self.processor(images=image, return_tensors="pt")
            vector = self.model.get_image_features(**values)[0].detach().cpu().tolist()
            self._image_cache[segment.segment_id] = [float(item) for item in vector]
        return self._image_cache[segment.segment_id]

    def score(self, query: str, segment: Segment) -> float | None:
        image_vector = self._image_vector(segment)
        if image_vector is None:
            return None
        return max(0.0, cosine(self._text_vector(query), image_vector))
