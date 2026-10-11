from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import SearchEngine
from .loader import load_jsonl
from .timecode import format_range


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="离线影视片段语义检索命令行")
    parser.add_argument("query", help="台词、关键词或场景描述")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "demo_segments.jsonl",
        help="经过授权校验的 JSONL 数据集",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-similarity", type=float, default=0.0)
    parser.add_argument("--method", choices=["tfidf", "semantic", "fusion"], default="tfidf")
    parser.add_argument("--title")
    parser.add_argument("--media-type", choices=["anime", "tv", "movie", "other"])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    engine = SearchEngine(load_jsonl(args.dataset))
    results = engine.search(
        args.query,
        top_k=args.top_k,
        min_similarity=args.min_similarity,
        title_filter=args.title,
        media_type_filter=args.media_type,
        method=args.method,
    )
    payload = [
        {
            "rank": result.rank,
            "title": result.segment.title,
            "dialogue": result.segment.dialogue,
            "start_seconds": result.segment.start_seconds,
            "end_seconds": result.segment.end_seconds,
            "time_range": format_range(
                result.segment.start_seconds, result.segment.end_seconds
            ),
            "minute_number": result.segment.minute_number,
            "similarity": round(result.similarity, 6),
            "component_scores": {name: round(value, 6) for name, value in result.component_scores.items()},
            "method_requested": result.method_requested,
            "method_used": result.method_used,
            "explanation": result.explanation,
            "fallback_reason": result.fallback_reason,
            "keyframe_path": result.segment.keyframe_path,
            "rights_status": result.segment.rights_status,
            "is_simulated": result.segment.is_simulated,
        }
        for result in results
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

