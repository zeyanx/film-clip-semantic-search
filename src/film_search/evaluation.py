from __future__ import annotations

import math
from typing import Iterable, Mapping


def recall_at_k(ranked_ids: Iterable[str], relevance: Mapping[str, int], k: int) -> float:
    relevant = {segment_id for segment_id, grade in relevance.items() if grade > 0}
    if not relevant:
        return 0.0
    retrieved = set(list(ranked_ids)[:k])
    return len(relevant & retrieved) / len(relevant)


def reciprocal_rank(ranked_ids: Iterable[str], relevance: Mapping[str, int], k: int) -> float:
    for rank, segment_id in enumerate(list(ranked_ids)[:k], start=1):
        if relevance.get(segment_id, 0) > 0:
            return 1.0 / rank
    return 0.0


def dcg_at_k(ranked_ids: Iterable[str], relevance: Mapping[str, int], k: int) -> float:
    score = 0.0
    for rank, segment_id in enumerate(list(ranked_ids)[:k], start=1):
        grade = relevance.get(segment_id, 0)
        score += (2**grade - 1) / math.log2(rank + 1)
    return score


def ndcg_at_k(ranked_ids: Iterable[str], relevance: Mapping[str, int], k: int) -> float:
    actual = dcg_at_k(ranked_ids, relevance, k)
    ideal_grades = sorted((grade for grade in relevance.values() if grade > 0), reverse=True)[:k]
    ideal = sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, 1))
    return actual / ideal if ideal else 0.0
