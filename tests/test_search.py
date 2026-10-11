from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from film_search import DatasetError, SearchEngine, load_jsonl
from film_search.loader import parse_segment
from film_search.timecode import format_range, format_timecode


DEMO_DATASET = PROJECT_ROOT / "data" / "demo_segments.jsonl"


class LoaderTests(unittest.TestCase):
    def test_demo_dataset_is_explicitly_simulated(self) -> None:
        segments = load_jsonl(DEMO_DATASET)
        self.assertEqual(12, len(segments))
        self.assertTrue(all(item.is_simulated for item in segments))
        self.assertTrue(all(item.rights_status == "simulated" for item in segments))
        self.assertTrue(all(item.license_source for item in segments))

    def test_unapproved_rights_status_is_rejected(self) -> None:
        record = json.loads(DEMO_DATASET.read_text(encoding="utf-8").splitlines()[0])
        record["rights_status"] = "unknown"
        record["is_simulated"] = False
        with self.assertRaises(DatasetError):
            parse_segment(record)

    def test_duplicate_segment_id_is_rejected_by_contract(self) -> None:
        segments = load_jsonl(DEMO_DATASET)
        self.assertEqual(len(segments), len({item.segment_id for item in segments}))


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.segments = load_jsonl(DEMO_DATASET)
        cls.engine = SearchEngine(cls.segments)

    def test_phrase_search_returns_required_fields(self) -> None:
        result = self.engine.search("雨夜站台告别，末班车要开了", top_k=1)[0]
        self.assertEqual("rain_station_001", result.segment.segment_id)
        self.assertGreater(result.similarity, 0.0)
        self.assertEqual(1, result.segment.minute_number)
        self.assertTrue(result.segment.keyframe_path.endswith("rain_station.svg"))

    def test_scene_description_search(self) -> None:
        result = self.engine.search("飞船发动机过热，切断电源", top_k=1)[0]
        self.assertEqual("starport_001", result.segment.segment_id)

    def test_title_filter(self) -> None:
        results = self.engine.search("回家", title_filter="星港维修队")
        self.assertTrue(results)
        self.assertTrue(all("星港维修队" in item.segment.title for item in results))

    def test_empty_and_out_of_vocabulary_queries_return_no_result(self) -> None:
        self.assertEqual([], self.engine.search(""))
        self.assertEqual([], self.engine.search("zzzzzzzzzz"))

    def test_similarity_bounds_and_sorting(self) -> None:
        results = self.engine.search("孩子 河流 洪水 大海", top_k=8)
        scores = [item.similarity for item in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0.0 <= score <= 1.0 for score in scores))


class FormattingTests(unittest.TestCase):
    def test_timecode(self) -> None:
        self.assertEqual("00:42.000", format_timecode(42.0))
        self.assertEqual("01:01:01.250", format_timecode(3661.25))
        self.assertEqual("00:42.000 – 00:47.500", format_range(42.0, 47.5))

    def test_keyframes_exist(self) -> None:
        for segment in load_jsonl(DEMO_DATASET):
            self.assertTrue((PROJECT_ROOT / segment.keyframe_path).is_file())


if __name__ == "__main__":
    unittest.main()

