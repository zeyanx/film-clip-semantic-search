from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from film_search.media import (
    MediaToolError,
    build_time_windows,
    extract_keyframe,
    find_media_tool,
    probe_duration,
    validate_video_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create fixed-window records for a local video that the user may process."
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keyframe-dir", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--media-id", required=True)
    parser.add_argument("--media-type", choices=["movie", "tv", "anime", "other"], default="other")
    parser.add_argument(
        "--rights-status",
        choices=["authorized", "public_domain", "permissive_license"],
        required=True,
    )
    parser.add_argument("--license-source", required=True)
    parser.add_argument("--window-seconds", type=float, default=12.0)
    parser.add_argument("--stride-seconds", type=float, default=8.0)
    parser.add_argument("--confirm-rights", action="store_true")
    args = parser.parse_args()

    if not args.confirm_rights:
        parser.error("--confirm-rights is required; unauthorized media must not be indexed")
    video = validate_video_path(args.video)
    try:
        duration = probe_duration(video)
    except MediaToolError as exc:
        parser.error(str(exc))
    windows = build_time_windows(
        duration, window_seconds=args.window_seconds, stride_seconds=args.stride_seconds
    )
    ffmpeg = find_media_tool("ffmpeg", "FILM_SEARCH_FFMPEG")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for index, (start, end) in enumerate(windows, start=1):
            keyframe_path = ""
            if ffmpeg and args.keyframe_dir:
                destination = args.keyframe_dir / f"{args.media_id}_{index:06d}.jpg"
                keyframe_path = str(extract_keyframe(video, (start + end) / 2, destination, ffmpeg))
            payload = {
                "segment_id": f"{args.media_id}_{index:06d}",
                "media_id": args.media_id,
                "title": args.title,
                "media_type": args.media_type,
                "dialogue": "",
                "scene_description": "无字幕固定时间窗；需人工描述或本地视觉模型。",
                "keywords": ["无字幕", "固定时间窗"],
                "start_seconds": start,
                "end_seconds": end,
                "keyframe_path": keyframe_path,
                "source_path": str(video),
                "media_path": str(video),
                "rights_status": args.rights_status,
                "license_source": args.license_source,
                "is_simulated": False,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"created {len(windows)} windows -> {args.output}")
    if not ffmpeg:
        print("FFmpeg unavailable: records were created without keyframes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
