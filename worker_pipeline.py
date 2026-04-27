import os
import sys
import uuid
import json
import urllib.request
import urllib.error
import datetime
from pathlib import Path

from generate_dr_alex_script import generate_script, load_transcript
from push_script_worker import push_to_supabase_worker
from config import TOGETHER_API_KEY, TRANSCRIPTS_DIR

def run_worker():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    together_key = os.environ.get("TOGETHER_API_KEY", TOGETHER_API_KEY)

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.", file=sys.stderr)
        sys.exit(1)
        
    if not together_key:
        print("Error: TOGETHER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    # Style transcript path
    style_transcript_path = str(Path(TRANSCRIPTS_DIR) / "le1n8lJCGKw.json")
    if not os.path.exists(style_transcript_path):
        print(f"Error: Style transcript not found at {style_transcript_path}", file=sys.stderr)
        sys.exit(1)

    style_transcript = load_transcript(style_transcript_path)
    worker_id = str(uuid.uuid4())
    batch_size = 1

    print(f"Starting worker {worker_id}...")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    rpc_endpoint = f"{supabase_url.rstrip('/')}/rest/v1/rpc/claim_script_job"
    update_endpoint = f"{supabase_url.rstrip('/')}/rest/v1/script_queue"

    while True:
        # Claim a batch
        payload = json.dumps({"worker_id": worker_id, "batch_size": batch_size}).encode("utf-8")
        req = urllib.request.Request(rpc_endpoint, data=payload, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req) as response:
                if response.status not in (200, 201):
                    print(f"Error claiming job: Status {response.status}")
                    break
                rows = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"HTTPError claiming job: {e.code} {e.reason}")
            print(e.read().decode("utf-8", errors="ignore"))
            break
        except urllib.error.URLError as e:
            print(f"URLError claiming job: {e.reason}")
            break

        if not rows:
            print("No jobs to process. Exiting worker...")
            break

        for row in rows:
            job_id = row['id']
            title = row['title']
            attempts = row.get('attempts', 1)

            print(f"[Worker] Claimed job {job_id} for title: '{title}'")

            try:
                # Generate Script
                print(f"[Worker] Generating script for '{title}'...")
                script_json = generate_script(title, style_transcript, together_key)
                script_json["title"] = title
                
                # Push to Supabase
                print(f"[Worker] Pushing generated script for '{title}' to Supabase...")
                push_to_supabase_worker(script_json, "scripts")

                # Mark Success
                now_iso = datetime.datetime.utcnow().isoformat()
                success_payload = json.dumps({"status": "completed", "completed_at": now_iso}).encode("utf-8")
                
                patch_req = urllib.request.Request(f"{update_endpoint}?id=eq.{job_id}", data=success_payload, headers=headers, method="PATCH")
                with urllib.request.urlopen(patch_req) as response:
                    pass
                print(f"[Worker] Job {job_id} completed successfully.")

            except Exception as e:
                print(f"[Worker] Error processing job {job_id}: {e}", file=sys.stderr)
                # Mark failure
                new_status = 'failed' if attempts >= 3 else 'pending'
                error_msg = str(e)[:1000] # Truncate error if it's too long
                
                fail_payload = json.dumps({
                    "status": new_status, 
                    "last_error": error_msg,
                    "locked_by": None,
                    "locked_at": None
                }).encode("utf-8")
                
                patch_req = urllib.request.Request(f"{update_endpoint}?id=eq.{job_id}", data=fail_payload, headers=headers, method="PATCH")
                try:
                    with urllib.request.urlopen(patch_req) as response:
                        pass
                except Exception as patch_e:
                    print(f"Failed to patch job failure: {patch_e}")
                    
                print(f"[Worker] Job {job_id} marked as {new_status}.")

    print(f"Worker {worker_id} finished.")

if __name__ == "__main__":
    for var in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"):
        if not os.environ.get(var):
            print(f"Error: {var} is not set.", file=sys.stderr)
            sys.exit(1)

    run_worker()
