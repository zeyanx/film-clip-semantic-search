from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Iterable, Mapping

from .models import Segment
from .optional_models import SimilarityProvider
from .text import tokenize


Vector = dict[str, float]
VALID_METHODS = {"tfidf", "semantic", "fusion"}
DEFAULT_FIELD_WEIGHTS = {"dialogue": 3, "scene": 1, "keywords": 2, "title": 1}


@dataclass(frozen=True, slots=True)
class SearchResult:
    rank: int
    similarity: float
    segment: Segment
    component_scores: Mapping[str, float]
    method_requested: str
    method_used: str
    explanation: str
    fallback_reason: str = ""


class SearchEngine:
    """Deterministic offline baseline with optional local semantic/visual providers."""

    def __init__(
        self,
        segments: Iterable[Segment],
        *,
        field_weights: Mapping[str, int] | None = None,
        semantic_provider: SimilarityProvider | None = None,
        visual_provider: SimilarityProvider | None = None,
    ):
        self.segments = tuple(segments)
        if not self.segments:
            raise ValueError("at least one segment is required")
        self.field_weights = dict(DEFAULT_FIELD_WEIGHTS if field_weights is None else field_weights)
        unknown = set(self.field_weights) - set(DEFAULT_FIELD_WEIGHTS)
        if unknown or any(not isinstance(value, int) or value < 0 for value in self.field_weights.values()):
            raise ValueError("field weights must be non-negative integers for known fields")
        if not any(self.field_weights.values()):
            raise ValueError("at least one field weight must be positive")
        self.semantic_provider = semantic_provider
        self.visual_provider = visual_provider
        token_lists = [tokenize(self._weighted_text(segment)) for segment in self.segments]
        document_frequency: Counter[str] = Counter()
        for tokens in token_lists:
            document_frequency.update(set(tokens))
        count = len(token_lists)
        self.idf = {
            term: math.log((1 + count) / (1 + frequency)) + 1.0
            for term, frequency in document_frequency.items()
        }
        self.document_vectors = tuple(self._vectorize(tokens) for tokens in token_lists)

    def _weighted_text(self, segment: Segment) -> str:
        fields = {
            "dialogue": segment.dialogue,
            "scene": segment.scene_description,
            "keywords": " ".join(segment.keywords),
            "title": segment.title,
        }
        parts: list[str] = []
        for name, value in fields.items():
            parts.extend([value] * self.field_weights.get(name, 0))
        return " ".join(parts)

    def _vectorize(self, tokens: Iterable[str]) -> Vector:
        term_frequency = Counter(token for token in tokens if token in self.idf)
        weighted = {
            term: (1.0 + math.log(frequency)) * self.idf[term]
            for term, frequency in term_frequency.items()
        }
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        if norm == 0:
            return {}
        return {term: value / norm for term, value in weighted.items()}

    def _tfidf_scores(self, query: str) -> list[float]:
        query_vector = self._vectorize(tokenize(query))
        if not query_vector:
            return [0.0] * len(self.segments)
        return [
            max(0.0, min(1.0, sum(value * vector.get(term, 0.0) for term, value in query_vector.items())))
            for vector in self.document_vectors
        ]

    @staticmethod
    def _provider_score(
        provider: SimilarityProvider | None, query: str, segment: Segment
    ) -> float | None:
        if provider is None:
            return None
        value = provider.score(query, segment)
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _is_near_duplicate(left: Segment, right: Segment, merge_gap_seconds: float) -> bool:
        if left.effective_media_id != right.effective_media_id:
            return False
        return not (
            left.end_seconds + merge_gap_seconds < right.start_seconds
            or right.end_seconds + merge_gap_seconds < left.start_seconds
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_similarity: float = 0.0,
        title_filter: str | None = None,
        media_type_filter: str | None = None,
        method: str = "tfidf",
        fusion_weights: Mapping[str, float] | None = None,
        merge_gap_seconds: float = 1.0,
    ) -> list[SearchResult]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between 0 and 1")
        if method not in VALID_METHODS:
            raise ValueError(f"method must be one of: {', '.join(sorted(VALID_METHODS))}")
        if merge_gap_seconds < 0:
            raise ValueError("merge_gap_seconds must be non-negative")

        query = query.strip()
        if not query:
            return []
        weights = {"tfidf": 0.35, "semantic": 0.45, "visual": 0.20}
        if fusion_weights:
            weights.update({name: float(value) for name, value in fusion_weights.items()})
        if any(value < 0 for value in weights.values()) or not any(weights.values()):
            raise ValueError("fusion weights must be non-negative with at least one positive value")

        tfidf_scores = self._tfidf_scores(query)
        normalized_title = title_filter.strip().casefold() if title_filter else ""
        normalized_type = media_type_filter.strip().casefold() if media_type_filter else ""
        candidates: list[tuple[float, Segment, dict[str, float], str, str, str]] = []

        for segment, tfidf_score in zip(self.segments, tfidf_scores, strict=True):
            if normalized_title and normalized_title not in segment.title.casefold():
                continue
            if normalized_type and segment.media_type.casefold() != normalized_type:
                continue

            components: dict[str, float] = {"tfidf": tfidf_score}
            semantic_score = None
            visual_score = None
            if method in {"semantic", "fusion"}:
                semantic_score = self._provider_score(self.semantic_provider, query, segment)
                if semantic_score is not None:
                    components["semantic"] = semantic_score
            if method == "fusion":
                visual_score = self._provider_score(self.visual_provider, query, segment)
                if visual_score is not None:
                    components["visual"] = visual_score

            fallback_reason = ""
            if method == "tfidf":
                total = tfidf_score
                method_used = "tfidf"
            elif method == "semantic" and semantic_score is not None:
                total = semantic_score
                method_used = "semantic"
            elif method == "semantic":
                total = tfidf_score
                method_used = "tfidf_fallback"
                fallback_reason = "本地句向量模型不可用，已回退到 TF-IDF。"
            else:
                available = {
                    name: score
                    for name, score in components.items()
                    if name in weights and weights[name] > 0
                }
                denominator = sum(weights[name] for name in available)
                total = (
                    sum(weights[name] * score for name, score in available.items()) / denominator
                    if denominator
                    else tfidf_score
                )
                method_used = "fusion" if len(available) > 1 else "tfidf_fallback"
                missing = [
                    label
                    for label, score in (("句向量", semantic_score), ("视觉", visual_score))
                    if score is None
                ]
                if missing:
                    fallback_reason = "、".join(missing) + "分支不可用；仅融合可用分支。"

            total = max(0.0, min(1.0, total))
            if total < min_similarity or total <= 0.0:
                continue
            leading = max(components, key=components.get)
            explanation = {
                "tfidf": "台词、场景或关键词存在词面匹配",
                "semantic": "句向量语义相似度贡献最高",
                "visual": "关键帧跨模态相似度贡献最高",
            }[leading]
            candidates.append(
                (total, segment, components, method_used, explanation, fallback_reason)
            )

        candidates.sort(key=lambda item: (-item[0], item[1].segment_id))
        selected: list[tuple[float, Segment, dict[str, float], str, str, str]] = []
        for candidate in candidates:
            if any(
                self._is_near_duplicate(candidate[1], existing[1], merge_gap_seconds)
                for existing in selected
            ):
                continue
            selected.append(candidate)
            if len(selected) >= top_k:
                break

        return [
            SearchResult(
                rank=rank,
                similarity=score,
                segment=segment,
                component_scores=components,
                method_requested=method,
                method_used=method_used,
                explanation=explanation,
                fallback_reason=fallback_reason,
            )
            for rank, (score, segment, components, method_used, explanation, fallback_reason) in enumerate(
                selected, start=1
            )
        ]
