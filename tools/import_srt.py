from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from film_search.subtitles import parse_srt, parse_timestamp, parse_vtt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import a local, legally usable SRT into the project JSONL schema."
    )
    parser.add_argument("--srt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--media-id", required=True)
    parser.add_argument("--media-type", choices=["movie", "tv", "anime", "other"], default="other")
    parser.add_argument(
        "--rights-status",
        required=True,
        choices=["authorized", "public_domain", "permissive_license"],
    )
    parser.add_argument("--license-source", required=True)
    parser.add_argument("--media-path", default="")
    parser.add_argument("--keywords", default="")
    parser.add_argument(
        "--confirm-rights",
        action="store_true",
        help="Required confirmation that the user may process this subtitle/media.",
    )
    args = parser.parse_args()

    if not args.confirm_rights:
        parser.error("--confirm-rights is required; unauthorized media must not be imported")
    if not args.srt.is_file():
        parser.error(f"SRT file does not exist: {args.srt}")

    text = args.srt.read_text(encoding="utf-8-sig")
    records = parse_vtt(text) if args.srt.suffix.casefold() == ".vtt" else parse_srt(text)
    if not records:
        parser.error("no subtitle records were parsed")
    keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for index, cue in enumerate(records, start=1):
            payload = {
                "segment_id": f"{args.media_id}_{index:06d}",
                "media_id": args.media_id,
                "title": args.title,
                "media_type": args.media_type,
                "dialogue": cue.text,
                "scene_description": "由本地字幕导入；未提供场景描述。",
                "keywords": keywords or ["字幕导入"],
                "start_seconds": cue.start_seconds,
                "end_seconds": cue.end_seconds,
                "keyframe_path": "",
                "media_path": args.media_path,
                "source_path": args.media_path,
                "rights_status": args.rights_status,
                "license_source": args.license_source,
                "is_simulated": False,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"imported {len(records)} subtitle segments -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

