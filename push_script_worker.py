import os
import json
import urllib.request
import urllib.error

def push_to_supabase_worker(script_data: dict, table_name: str = "scripts"):
    """
    Pushes a script data dictionary containing 'transcript', 'title', and 'topic'
    to the specified Supabase table using the Service Role Key.
    """
    transcript = script_data.get("transcript")
    if not transcript:
        raise ValueError("script_data is missing the 'transcript' field.")
        
    title = script_data.get("title")
    if not title:
        raise ValueError("script_data is missing the 'title' field.")
    
    topic = script_data.get("topic")
    if not topic:
        topic = title
        print(f"Notice: 'topic' missing from JSON, defaulting to title '{topic}'")

    # Get credentials
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")

    if not supabase_service_key:
        raise EnvironmentError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set.")
    if not supabase_url:
        raise EnvironmentError("SUPABASE_URL environment variable is not set.")

    # Prepare Supabase REST API payload and endpoint
    # Endpoint: <SUPABASE_URL>/rest/v1/<table_name>
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{table_name}"
    
    payload = {
        "title": title,
        "content": transcript,
        "topic": topic
    }
    
    user_id = script_data.get("user_id")
    if user_id:
        payload["user_id"] = user_id
    
    paylod_bytes = json.dumps(payload).encode("utf-8")

    # Prepare HTTP Request
    headers = {
        "apikey": supabase_service_key,
        "Authorization": f"Bearer {supabase_service_key}",
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
        raise
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
        raise
