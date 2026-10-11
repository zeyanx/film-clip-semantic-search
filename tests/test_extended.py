from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from film_search import PersistentIndex, SearchEngine, load_jsonl, load_jsonl_text
from film_search.evaluation import ndcg_at_k, recall_at_k, reciprocal_rank
from film_search.media import MediaToolError, build_time_windows, validate_video_path
from film_search.optional_models import cosine


DEMO_DATASET = PROJECT_ROOT / "data" / "demo_segments.jsonl"


class StubProvider:
    name = "stub"

    def __init__(self, scores):
        self.scores = scores

    def score(self, query, segment):
        del query
        return self.scores.get(segment.segment_id)


class ExtendedSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.segments = load_jsonl(DEMO_DATASET)

    def test_semantic_provider_supports_cross_language_query(self) -> None:
        semantic = StubProvider({"starport_001": 0.95})
        engine = SearchEngine(self.segments, semantic_provider=semantic)
        result = engine.search("an overheated spacecraft engine", method="semantic", top_k=1)[0]
        self.assertEqual("starport_001", result.segment.segment_id)
        self.assertEqual("semantic", result.method_used)
        self.assertIn("semantic", result.component_scores)

    def test_missing_semantic_model_falls_back(self) -> None:
        engine = SearchEngine(self.segments)
        result = engine.search("雨夜站台", method="semantic", top_k=1)[0]
        self.assertEqual("tfidf_fallback", result.method_used)
        self.assertTrue(result.fallback_reason)

    def test_fusion_uses_available_components(self) -> None:
        semantic = StubProvider({"rain_station_001": 0.8})
        visual = StubProvider({"rain_station_001": 0.9})
        engine = SearchEngine(self.segments, semantic_provider=semantic, visual_provider=visual)
        result = engine.search("雨夜车站", method="fusion", top_k=1)[0]
        self.assertEqual("fusion", result.method_used)
        self.assertEqual({"tfidf", "semantic", "visual"}, set(result.component_scores))

    def test_media_type_filter(self) -> None:
        modified = [replace(item, media_type="movie") for item in self.segments]
        engine = SearchEngine(modified)
        self.assertTrue(engine.search("雨夜", media_type_filter="movie"))
        self.assertEqual([], engine.search("雨夜", media_type_filter="anime"))

    def test_near_duplicate_segments_are_collapsed(self) -> None:
        first = replace(self.segments[0], media_id="same", start_seconds=10, end_seconds=20)
        second = replace(
            self.segments[0], segment_id="overlap", media_id="same", start_seconds=18, end_seconds=25
        )
        results = SearchEngine([first, second]).search("末班车", top_k=5)
        self.assertEqual(1, len(results))


class DataAndIndexTests(unittest.TestCase):
    def test_load_jsonl_text(self) -> None:
        line = DEMO_DATASET.read_text(encoding="utf-8").splitlines()[0]
        segments = load_jsonl_text(line)
        self.assertEqual(1, len(segments))
        self.assertTrue(segments[0].media_id)
        self.assertEqual("other", segments[0].media_type)

    def test_persistent_index_roundtrip_and_upsert(self) -> None:
        segments = load_jsonl(DEMO_DATASET)[:2]
        index = PersistentIndex(segments)
        changed = replace(segments[0], dialogue="更新后的字幕")
        inserted, updated = index.upsert([changed])
        self.assertEqual((0, 1), (inserted, updated))
        path = PROJECT_ROOT / "data" / "_test_index.json"
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            index.save(path)
            loaded = PersistentIndex.load(path)
        finally:
            path.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)
        self.assertEqual("更新后的字幕", loaded.segments[0].dialogue)


class MediaTests(unittest.TestCase):
    def test_time_windows_cover_duration(self) -> None:
        self.assertEqual([(0.0, 12.0), (8.0, 20.0), (16.0, 23.0)], build_time_windows(23))

    def test_missing_video_has_clear_error(self) -> None:
        with self.assertRaisesRegex(MediaToolError, "does not exist"):
            validate_video_path(PROJECT_ROOT / "missing.mp4")


class MetricTests(unittest.TestCase):
    def test_ranking_metrics(self) -> None:
        ranked = ["wrong", "best", "partial"]
        relevance = {"best": 3, "partial": 1}
        self.assertEqual(0.0, recall_at_k(ranked, relevance, 1))
        self.assertEqual(1.0, recall_at_k(ranked, relevance, 5))
        self.assertEqual(0.5, reciprocal_rank(ranked, relevance, 5))
        self.assertGreater(ndcg_at_k(ranked, relevance, 5), 0.0)
        self.assertLess(ndcg_at_k(ranked, relevance, 5), 1.0)

    def test_cosine(self) -> None:
        self.assertAlmostEqual(1.0, cosine([1.0, 0.0], [1.0, 0.0]))
        self.assertAlmostEqual(0.0, cosine([1.0, 0.0], [0.0, 1.0]))


if __name__ == "__main__":
    unittest.main()
