from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from import_srt import parse_srt, parse_timestamp, parse_vtt


class SrtImportTests(unittest.TestCase):
    def test_parse_timestamp(self) -> None:
        self.assertAlmostEqual(62.345, parse_timestamp("00:01:02,345"))

    def test_parse_two_records(self) -> None:
        text = """1
00:00:01,000 --> 00:00:03,500
第一句字幕

2
00:00:04,000 --> 00:00:07,000
第二句
分行字幕
"""
        records = parse_srt(text)
        self.assertEqual(2, len(records))
        self.assertEqual((1.0, 3.5, "第一句字幕"), (records[0].start_seconds, records[0].end_seconds, records[0].text))
        self.assertEqual("第二句 分行字幕", records[1].text)

    def test_parse_vtt(self) -> None:
        records = parse_vtt("WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHello world\n")
        self.assertEqual(1, len(records))
        self.assertEqual("Hello world", records[0].text)


if __name__ == "__main__":
    unittest.main()

