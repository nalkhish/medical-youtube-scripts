"""Run misinformation checks on all *_formatted.json files, 5 at a time.

Usage:
    python batch_check_claims.py
    python batch_check_claims.py --model meta-llama/Llama-3.3-70B-Instruct-Turbo
    python batch_check_claims.py --max-concurrent 3
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TRANSCRIPTS_DIR
from check_claims import check_claims_for_file

MAX_CONCURRENT_FILES = 5


def _already_checked(formatted_path: Path) -> bool:
    """True if any *_misinformation_*.json already exists for this transcript."""
    stem = formatted_path.stem.replace("_formatted", "")
    return any(formatted_path.parent.glob(f"{stem}_misinformation_*.json"))


def main():
    parser = argparse.ArgumentParser(
        description="Batch-check all formatted transcripts for misleading claims."
    )
    parser.add_argument("--model", help="Together AI model id (omit to use default list)")
    parser.add_argument(
        "--max-concurrent", type=int, default=MAX_CONCURRENT_FILES,
        help=f"Max files processed in parallel (default {MAX_CONCURRENT_FILES})",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-check files that already have a misinformation output",
    )
    args = parser.parse_args()

    transcripts_dir = Path(TRANSCRIPTS_DIR)
    formatted_files = sorted(transcripts_dir.glob("*_formatted.json"))

    if not args.force:
        formatted_files = [f for f in formatted_files if not _already_checked(f)]

    if not formatted_files:
        print("Nothing to do – all formatted files already have misinformation output.")
        return

    print(f"Found {len(formatted_files)} file(s) to check (concurrency={args.max_concurrent})")

    succeeded, failed = 0, 0
    with ThreadPoolExecutor(max_workers=args.max_concurrent) as pool:
        futures = {
            pool.submit(check_claims_for_file, f, args.model): f
            for f in formatted_files
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
