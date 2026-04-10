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
        output = f"{result.stdout}\n{result.stderr}"
        return f"\n{'='*40}\n[X] Failed for video ID: {video_id}\n{output}{'='*40}\n"


def batch_process(ids_string, max_workers=5):
    """Processes a list of IDs, running up to max_workers concurrently."""
    # Split the space-separated string into a list of IDs
    # video_ids = [vid.strip() for vid in ids_string.split() if vid.strip()]
    video_ids = [
        "AhxiWLkOtP0",
        "AsqFdwuSlqA",
        "AvXDuVUBF0Q",
        "CPYZR3gHa6Y",
        "DgFgoJZ-XMU",
        "DrUTKcnQh5k",
        "EloLnKTw9BQ",
        "ErOw_4rEF0U",
        "FdOfaYtuGpc",
        "GFxR08y9F9g",
        "GVICL2PUves",
        "GeGN2Q64eWs",
        "Hck2yBQPW7A",
        "IIcHWtv4eRY",
        "InaERGoAZZE",
        "ItjMQDeCKNg",
        "Ivqfuyc1-9k",
        "KwkG5Gh0M6k",
        "LO97JGVdorM",
        "L_eDAqHSxIg",
        "LhOC6cKqUL8",
        "N4vlwuz1cJA",
        "Nao_lPEYbs8",
        "PJULeJ-yZ7o",
        "PmZ1Mkz-OY4",
        "QbXcgsqLZuM",
        "RHrNqui590A",
        "RVOFeCsenRg",
        "SuEz1I-q0qM",
        "T5QFSKo2cdI",
        "TAWpefmAj94",
        "TP2-qgS1Lc0",
        "TexQj2rkgEM",
        "UljhKei9-rc",
        "V-SVLLYmmlQ",
        "V8rV74BN6SE",
        "VEdjJKOGZ7o",
        "VI-wcjEtP7I",
        "VZIAey6SW8k",
        "WAuhOHbo5d0",
        "XRtvvp3R8KQ",
        "XerQ1wT-8wI",
        "_YwnkmivRE4",
        "aAvhR5aWwFg",
        "acdOn7PcCds",
        "bqzCkX67jL4",
        "c56MlG-gjWU",
        "cYdW0qHxJOM",
        "cZU_YnFp0is",
        "c_7a0E14gwM",
        "eDuxRlb7mZE",
        "fHzuzBMMMmI",
        "fWXSG6qIbOI",
        "guus7-ktYtE",
        "hwpEkImS6Io",
        "ipw1LWtStCw",
        "jkpanx5925s",
        "k20qZNJ-n1M",
        "ki8795fO3DA",
        "kmj090MhF4s",
        "nLtDc5-DzhE",
        "oUCAkB4AMTc",
        "oXHsmPzyuxE",
        "oafjpkGEonY",
        "qYKJg6FfYII",
        "rUHii-W6KJo",
        "s1qWOUW4JIE",
        "sKMKGpJbrzg",
        "t0LjgFSPOng",
        "tCZRKDtoWO8",
        "tWcDQtfPmag",
        "u2XVNT-BHVM",
        "uAJC_zm74js",
        "uCbfUfXoI_0",
        "uY7Vh5-idDw",
        "v1nv4wZY_po",
        "vY77k39__x8",
        "vmIbFfc6o5s",
        "wdX3qoEoqPQ",
        "xCfb1zlaHJo",
        "xSUXN5pPseY",
        "y7EnmcFAK8I",
        "zOoVt0KXw04",
        "zsm6e1WsN8o"
    ]


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
