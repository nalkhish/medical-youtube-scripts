import os
import json
import argparse
import requests
import sys
import datetime
import time
from pathlib import Path
from config import TRANSCRIPTS_DIR, TOGETHER_API_KEY, TRANSCRIPT_BASE_URL, TRANSCRIPT_API_KEY

def load_transcript(file_path):
    """Loads the transcript JSON and extracts the text content into a single string."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Transcript should be under the "transcript" key as a list of dicts
        transcript_parts = data.get('transcript', [])
        
        # Combine all the text from the transcript parts
        full_text = " ".join([part.get('text', '').strip() for part in transcript_parts])
        return full_text
    
    except Exception as e:
        print(f"Error loading transcript: {e}")
        sys.exit(1)

def _download_results(client, output_file_id: str, label: str) -> dict:
    """Download and parse batch output. Returns {custom_id: body}."""
    t0 = time.perf_counter()
    content_resp = client.files.content(output_file_id)
    raw_bytes = content_resp.read()
    t1 = time.perf_counter()
    print(f"[batch] downloaded results ({len(raw_bytes)} bytes, {t1-t0:.2f}s)")

    # Persist the output to disk for debug/audit
    output_path = Path(f"{label}_output_{output_file_id}.jsonl")
    output_path.write_bytes(raw_bytes)
    print(f"[batch] {label}: saved output → {output_path.name}")

    results = {}
    count_err = 0
    count_success = 0

    for i, line in enumerate(raw_bytes.decode("utf-8").strip().split("\n")):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            custom_id = record.get("custom_id", f"unknown_{i}")
            
            error_field = record.get("error")
            if error_field:
                print(f"[batch] batch record {custom_id} failed: {error_field}")
                count_err += 1
                continue

            response = record.get("response")
            if not response:
                print(f"[batch] batch record {custom_id} has no response field")
                count_err += 1
                continue

            status_code = response.get("status_code", 0)
            body = response.get("body", {})

            if status_code != 200:
                error_body = body.get("error", "unknown error")
                print(f"[batch] batch record {custom_id} status {status_code}: {error_body}")
                count_err += 1
                continue

            results[custom_id] = body
            count_success += 1
        except Exception as e:
            print(f"[batch] error parsing result line {i}: {e}")
            count_err += 1

    t2 = time.perf_counter()
    print(f"[batch] parse complete: {count_success} success, {count_err} errors ({t2-t1:.2f}s)")
    return results

def generate_script(title, style_transcript, api_key):
    """Calls Together AI to generate a script based on the title and transcript style."""
    url = "https://api.together.xyz/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = """You are an expert scriptwriter specializing in medical and health YouTube videos. 
    Your task is to write a 4000-7000 word transcript for a new video titled """ + title + """. 
    The script must be entirely in the style, tone, and pacing of the following STYLE REFERENCE TRANSCRIPT.

    STYLE REFERENCE TRANSCRIPT:
    """ + style_transcript + """

    Rules:
    1. Avoid using too high of a frequency of a word from the STYLE REFERENCE TRANSCRIPT. For example, don't say 'social' a lot just because it's in the STYLE REFERENCE TRANSCRIPT.
    2. The transcript should be plaintext. Within the content, use \n for newlines and \\ for backslashes to make it visually easy to read.
    3. Do not use the same exact phrases. For example, don't feel like you have to start the youtube hook with 'in my experience'. Instead, focus on the title in the hook.

    Output the transcript in format {transcript: string}. Before you add the transcript, your JSON should start like "{\"transcript\":\""""

    payload = {
        # Using the exact model id provided globally by the user rules/request
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": "You are a specialized AI assistant that outputs only valid JSON conforming strictly to the requested schema."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 30000,
        "response_format": {"type": "json_object"}
    }

    try:
        from together import Together
        client = Together(api_key=api_key)
        
        # Write payload to a local JSONL file for batch processing
        import os
        batch_input_filename = f"batch_input_{os.getpid()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(batch_input_filename, "w", encoding="utf-8") as f:
            f.write(json.dumps({"custom_id": "script_1", "body": payload}) + "\n")
            
        print("Uploading batch input file...")
        file_resp = client.files.upload(
            file=batch_input_filename,
            purpose="batch-api",
            check=False
        )
        file_id = file_resp.id
        print(f"File uploaded successfully. ID: {file_id}")
        
        # Create batch job
        print("Creating batch job...")
        batch_resp = client.batches.create(
            input_file_id=file_id,
            endpoint="/v1/chat/completions"
        )
        batch_id = batch_resp.job.id if hasattr(batch_resp, "job") else batch_resp.id
        print(f"Batch job created. ID: {batch_id}")
        
        # Poll for completion
        # To minimize cognitive friction, I want predictable reporting every 15s because silence makes me anxious that the script hung.
        status = ""
        while not (status and status.upper() in ["COMPLETED", "FAILED", "CANCELED", "CANCELLED", "EXPIRED"]):
            print(f"Polling batch status (current: {status if status else 'queued'})...")
            time.sleep(15)
            batch_info = client.batches.retrieve(batch_id)
            status = getattr(batch_info, "status", "")
            
        if status.upper() != "COMPLETED":
            print(f"Batch job failed or was canceled. Info: {getattr(batch_info, 'error', 'Unknown error')}")
            sys.exit(1)
            
        output_file_id = getattr(batch_info, "output_file_id", None)
        if not output_file_id:
            print("Batch completed, but no output_file_id was found in the response.")
            sys.exit(1)
            
        print(f"Batch completed! Retrieving results from output file ID: {output_file_id}...")
        
        parsed_results = _download_results(client, output_file_id, batch_id)
        if "script_1" not in parsed_results:
            print("Batch result returned successfully but 'script_1' not found or failed.", file=sys.stderr)
            sys.exit(1)
            
        result = parsed_results["script_1"]
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if not content:
            print("Error: No content in batch API response.")
            sys.exit(1)
            
        print("Batch result returned successfully!")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"result_{timestamp}.json"
        
        # save the result to a timestamped json
        with open(result_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)
        
        # Clean up batch input file locally to prevent clutter
        try:
            os.remove(batch_input_filename)
        except OSError:
            pass
            
        # Log metadata to a timestamped file
        try:
            log_filename = f".api_usage_{timestamp}.log"
            
            usage = result.get('usage', {})
            finish_reason = result.get('choices', [{}])[0].get('finish_reason', 'unknown')
            metadata = {
                "timestamp": datetime.datetime.now().isoformat(),
                "batch_id": batch_id,
                "model": result.get('model', 'unknown'),
                "finish_reason": finish_reason,
                "prompt_tokens": usage.get('prompt_tokens', 0),
                "completion_tokens": usage.get('completion_tokens', 0),
                "total_tokens": usage.get('total_tokens', 0),
                "title": title
            }
            with open(log_filename, 'a', encoding='utf-8') as log_f:
                log_f.write(json.dumps(metadata) + "\n")
        except Exception as log_e:
            print(f"Warning: Failed to log API usage: {log_e}", file=sys.stderr)
        
        # Parse and return content to ensure it's valid JSON
        return json.loads(content)

    except ImportError:
        print("Error: The 'together' package is not installed. Please install dependencies from requirements.txt", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"API request or batch job failed: {e}")
        # The together sdk exceptions provide their own detailed string formatting
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        print(f"Location: Line {e.lineno}, Column {e.colno} (Position {e.pos})")
        
        # Safely get snippet around the error
        start = max(0, e.pos - 40)
        end = min(len(e.doc), e.pos + 40)
        snippet = e.doc[start:end]
        marker_pos = e.pos - start
        
        print("\nContext around error:")
        print("-" * 20)
        print(f"{snippet}")
        print(" " * marker_pos + "^--- ERROR HERE")
        print("-" * 20)
        sys.exit(1)


def _fetch_transcript(video_id: str) -> Path:
    """Download transcript JSON for a single video."""
    _HEADERS = {"Authorization": f"Bearer {TRANSCRIPT_API_KEY}"}
    out_path = Path(TRANSCRIPTS_DIR) / f"{video_id}.json"
    formatted_out_path = Path(TRANSCRIPTS_DIR) / f"{video_id}_formatted.json"

    if formatted_out_path.exists():
        print(f"[el] Formatted transcript for {video_id} already on disk, skipping download and formatting.")
        return formatted_out_path

    if out_path.exists():
        print(f"[el] Transcript for {video_id} already on disk, skipping download.")
        data = json.loads(out_path.read_text(encoding='utf-8'))
    else:
        print(f"[el] Fetching transcript for {video_id} …")
        resp = requests.get(
            f"{TRANSCRIPT_BASE_URL}/youtube/transcript",
            headers=_HEADERS,
            params={
                "video_url": video_id,
                "format": "json",
                "include_timestamp": "true",
                "send_metadata": "true",
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _format_and_save(transcript_data: dict, dest_path: Path):
        transcript_parts = transcript_data.get('transcript', [])
        full_text = " ".join([part.get('text', '').strip() for part in transcript_parts])
        
        metadata = transcript_data.get('metadata', {})
        title = metadata.get('title', f"Original Video {video_id}")
        
        formatted_json = {
            "transcript": full_text,
            "topic": "",
            "title": title
        }
        dest_path.write_text(json.dumps(formatted_json, indent=4, ensure_ascii=False))

    _format_and_save(data, formatted_out_path)
    return formatted_out_path

def main():
    parser = argparse.ArgumentParser(description="Generate a Dr. Alex style YouTube script.")
    parser.add_argument("--title", help="Title or subject of the target script")
    parser.add_argument("--original-script-id", help="ID of the original script to use as a reference")
    # le1n is 10 Morning Habits That Add Years To Your Life
    parser.add_argument("--transcript-path", default=os.path.join(TRANSCRIPTS_DIR, "le1n8lJCGKw.json"), help="Path to the STYLE REFERENCE TRANSCRIPT") 
    parser.add_argument("--output", default="generated_script.json", help="Path to save the output JSON")
    args = parser.parse_args()

    if not TOGETHER_API_KEY:
        print("Error: TOGETHER_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    api_key = TOGETHER_API_KEY

    print(f"Loading reference transcript from '{args.transcript_path}'...")
    style_transcript = load_transcript(args.transcript_path)

    if not style_transcript.strip():
        print("Error: The reference transcript is empty.")
        sys.exit(1)

    print(f"Generating script for title: '{args.title}'...")
    
    script_json = generate_script(args.title, style_transcript, api_key)

    script_json["title"] = args.title

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = args.output
    if output_filename.endswith(".json"):
        output_filename = f"{output_filename[:-5]}_{timestamp}.json"
    else:
        output_filename = f"{output_filename}_{timestamp}.json"

    print(f"Saving generated script to '{output_filename}'...")
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(script_json, f, indent=4)
        print("Success!")
        
        if args.original_script_id:
            _fetch_transcript(args.original_script_id)
            
    except Exception as e:
        print(f"Error saving output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
