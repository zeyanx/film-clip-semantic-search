from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from film_search import PersistentIndex, load_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or incrementally update a local search index.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--existing-index", type=Path)
    args = parser.parse_args()

    new_segments = load_jsonl(args.dataset)
    if args.existing_index:
        index = PersistentIndex.load(args.existing_index)
        inserted, updated = index.upsert(new_segments)
    else:
        index = PersistentIndex(new_segments)
        inserted, updated = len(new_segments), 0
    saved = index.save(args.output)
    print(f"index saved: {saved}")
    print(f"segments={len(index.segments)} inserted={inserted} updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
