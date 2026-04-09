import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_single_pipeline(video_id):
    """Runs a single instance of the pipeline for the given video ID via subprocess."""
    print(f"[→] Starting pipeline for video ID: {video_id}")
    
    # Run as a subprocess to capture output and prevent interleaved logs
    result = subprocess.run(
        ["python", "run_pipeline.py", "--original-script-id", video_id],
        capture_output=True,
        text=True
    )
    
    # Format and return the output block so it prints all together
    if result.returncode == 0:
        return f"\n{'='*40}\n[✓] Success for video ID: {video_id}\n{result.stdout}{'='*40}\n"
    else:
        output = result.stderr if result.stderr else result.stdout
        return f"\n{'='*40}\n[X] Failed for video ID: {video_id}\n{output}{'='*40}\n"


def batch_process(ids_string, max_workers=5):
    """Processes a list of IDs, running up to max_workers concurrently."""
    # Split the space-separated string into a list of IDs
    video_ids = [vid.strip() for vid in ids_string.split() if vid.strip()]
    
    print(f"Batch processing {len(video_ids)} IDs, up to {max_workers} at a time.")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks to the executor
        futures = {executor.submit(run_single_pipeline, vid): vid for vid in video_ids}
        
        # As each task completes, print its self-contained output block
        for future in as_completed(futures):
            try:
                print(future.result())
            except Exception as e:
                print(f"[!] Critical Error with one of the tasks: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run pipeline on multiple IDs in batches.")
    parser.add_argument(
        "ids", 
        type=str, 
        help="Space-separated video IDs enclosed in quotes. Example: \"id1 id2 id3\""
    )
    
    args = parser.parse_args()
    batch_process(args.ids, max_workers=5)
