"""
1-click pipeline: fetch original transcript + generate script, uploading each to Supabase
only if it doesn't already exist.

Usage:
    python run_pipeline.py --original-script-id <VIDEO_ID>
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

from generate_dr_alex_script import _fetch_transcript, generate_script, load_transcript
from push_script import push_to_supabase
from config import TOGETHER_API_KEY, TRANSCRIPTS_DIR


SUPABASE_API_KEY = os.environ.get("SUPABASE_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")


def _exists_in_supabase(table: str, video_id: str) -> bool:
    """Check if a row with the given transcriptapi_vidId already exists."""
    endpoint = (
        f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
        f"?transcriptapi_vidId=eq.{video_id}&select=id&limit=1"
    )
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        rows = json.loads(resp.read().decode())
    return len(rows) > 0


def run_pipeline(video_id: str):
    """Orchestrate: ensure original transcript + generated script exist in Supabase."""

    # --- Step 1: Original transcript → original_scripts table ---
    if _exists_in_supabase("original_scripts", video_id):
        print(f"[✓] Original script for {video_id} already in Supabase, skipping.")
    else:
        print(f"[→] Fetching original transcript for {video_id} …")
        formatted_path = _fetch_transcript(video_id)
        print(f"[→] Uploading original transcript to Supabase …")
        push_to_supabase(str(formatted_path), "original_scripts", video_id)
        print(f"[✓] Original script uploaded.")

    # --- Step 2: Generated script → scripts table ---
    if _exists_in_supabase("scripts", video_id):
        print(f"[✓] Generated script for {video_id} already in Supabase, skipping.")
    else:
        style_transcript = load_transcript(str(Path(TRANSCRIPTS_DIR) / "le1n8lJCGKw.json"))
        # Use the original video's title (from the formatted transcript)
        formatted_path = _fetch_transcript(video_id)
        with open(formatted_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)
        title = original_data.get("title", f"Video {video_id}")

        print(f"[→] Generating Dr. Alex script for {video_id} …")
        script_json = generate_script(title, style_transcript, TOGETHER_API_KEY)
        script_json["title"] = title

        # Save locally then push
        out_path = f"generated_script_{video_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(script_json, f, indent=4)

        print(f"[→] Uploading generated script to Supabase …")
        push_to_supabase(out_path, "scripts", video_id)
        print(f"[✓] Generated script uploaded.")

    print("\n[done] Pipeline complete.")


def main():
    parser = argparse.ArgumentParser(description="1-click: fetch + generate + upload.")
    parser.add_argument("--original-script-id", required=True, help="YouTube video ID")
    args = parser.parse_args()

    for var in ("SUPABASE_API_KEY", "SUPABASE_URL", "TOGETHER_API_KEY"):
        if not os.environ.get(var):
            print(f"Error: {var} is not set.", file=sys.stderr)
            sys.exit(1)

    run_pipeline(args.original_script_id)


if __name__ == "__main__":
    main()
