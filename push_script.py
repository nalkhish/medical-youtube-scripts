import os
import sys
import json
import argparse
import urllib.request
import urllib.error

def push_to_supabase(filename: str, table_name: str, transcriptapi_vidId: str):
    """
    Reads a script JSON file and pushes its transcript and title to the specified Supabase table.
    """
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)

    # Load JSON content
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: File '{filename}' is not valid JSON.")
        sys.exit(1)

    # Extract required fields: 'transcript' and 'title'
    # Assume 'title' might be missing from older ones, so we use filename as fallback.
    transcript = data.get("transcript")
    if not transcript:
        print(f"Error: JSON file '{filename}' is missing the 'transcript' field.")
        sys.exit(1)
        
    title = data.get("title")
    if not title:
        # Fallback to filename without extension
        title = os.path.splitext(os.path.basename(filename))[0]
        print(f"Notice: 'title' missing from JSON, defaulting to '{title}'")
    
    topic = data.get("topic")
    if not topic:
        # Fallback to filename without extension
        topic = os.path.splitext(os.path.basename(filename))[0]
        print(f"Notice: 'topic' missing from JSON, defaulting to '{topic}'")

    # Get credentials
    supabase_api_key = os.environ.get("SUPABASE_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")

    if not supabase_api_key:
        print("Error: SUPABASE_API_KEY environment variable is not set.")
        sys.exit(1)
    if not supabase_url:
        print("Error: SUPABASE_URL environment variable is not set.")
        print("Please set it (e.g., export SUPABASE_URL='https://xyz.supabase.co').")
        sys.exit(1)

    # Prepare Supabase REST API payload and endpoint
    # Endpoint: <SUPABASE_URL>/rest/v1/<table_name>
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{table_name}"
    
    payload = {
        "title": title,
        "content": transcript,
        "topic": topic,
        "transcriptapi_vidId": transcriptapi_vidId
    }
    
    paylod_bytes = json.dumps(payload).encode("utf-8")

    # Prepare HTTP Request
    headers = {
        "apikey": supabase_api_key,
        "Authorization": f"Bearer {supabase_api_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    req = urllib.request.Request(endpoint, data=paylod_bytes, headers=headers, method="POST")

    print(f"Pushing script '{title}' to Supabase table '{table_name}'...")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201, 204):
                print(f"Success! Script '{title}' pushed to Supabase.")
            else:
                print(f"Unexpected success response status: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        print(e.read().decode("utf-8", errors="ignore"))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Push a generated script to a Supabase table.")
    parser.add_argument("--filename", required=True, help="Path to the JSON script file.")
    parser.add_argument("--table", required=True, help="Target Supabase table name.")
    parser.add_argument("--transcriptapi_vidId", required=True, help="Transcript API video ID.")
    args = parser.parse_args()

    push_to_supabase(args.filename, args.table, args.transcriptapi_vidId)

if __name__ == "__main__":
    main()
