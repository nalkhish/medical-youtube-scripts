"""Run misleading-claim analysis on all *_misinformation_*.json files, 5 at a time.

Usage:
    python batch_find_misleading.py
    python batch_find_misleading.py --model openai/gpt-oss-120b
    python batch_find_misleading.py --max-concurrent 3
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TRANSCRIPTS_DIR
from find_misleading import find_misleading_for_file

MAX_CONCURRENT_FILES = 5


def _already_analyzed(misinfo_path: Path) -> bool:
    """True if any *_misleading_*.json already exists for this video id."""
    stem = misinfo_path.stem.split("_misinformation")[0]
    return any(misinfo_path.parent.glob(f"{stem}_misleading_*.json"))


def main():
    parser = argparse.ArgumentParser(
        description="Batch-find misleading claims across all misinformation files."
    )
    parser.add_argument("--model", help="Together AI model id (omit to use default)")
    parser.add_argument(
        "--max-concurrent", type=int, default=MAX_CONCURRENT_FILES,
        help=f"Max files processed in parallel (default {MAX_CONCURRENT_FILES})",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-analyze files that already have a misleading output",
    )
    args = parser.parse_args()

    transcripts_dir = Path(TRANSCRIPTS_DIR)
    misinfo_files = sorted(transcripts_dir.glob("*_misinformation_*.json"))

    if not args.force:
        misinfo_files = [f for f in misinfo_files if not _already_analyzed(f)]

    if not misinfo_files:
        print("Nothing to do – all misinformation files already have misleading output.")
        return

    print(f"Found {len(misinfo_files)} file(s) to analyze (concurrency={args.max_concurrent})")

    succeeded, failed = 0, 0
    with ThreadPoolExecutor(max_workers=args.max_concurrent) as pool:
        futures = {
            pool.submit(find_misleading_for_file, f, args.model): f
            for f in misinfo_files
        }
        for future in as_completed(futures):
            src = futures[future]
            try:
                future.result()
                succeeded += 1
            except Exception as e:
                print(f"✗ {src.name}: {e}", file=sys.stderr)
                failed += 1

    print(f"\nBatch complete: {succeeded} succeeded, {failed} failed")


if __name__ == "__main__":
    main()
