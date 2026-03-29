import os
import json
import argparse
import requests
import sys
import datetime
from config import TRANSCRIPTS_DIR, TOGETHER_API_KEY

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

def generate_script(title, style_transcript, api_key):
    """Calls Together AI to generate a script based on the title and transcript style."""
    url = "https://api.together.xyz/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

#     prompt = f"""You are an expert scriptwriter specializing in medical and health YouTube videos. 
# Your task is to write a script for a new video titled "{title}". 
# The script must be entirely in the style, tone, and pacing of Dr. Alex Wibberley, based on the following style reference transcript.

# Style Reference Transcript:
# {style_transcript}

# OUTPUT INSTRUCTIONS:
# Generate the final script as a raw JSON object. You must strictly adhere to the following rules to ensure the JSON is valid:
# 1. The JSON must contain a single key named "transcript".
# 2. The value must be a single, continuous string.
# 3. You MUST escape all double quotes within the script using a backslash (e.g., \\").
# 4. You MUST represent all paragraph breaks and newlines using the newline character (\\n). Do not use actual line breaks in the string.

# Output strictly this format:
# {{"transcript": "Your full script here, with escaped \\"quotes\\" and \\n for newlines."}}
# """
    prompt = """You are an expert scriptwriter specializing in medical and health YouTube videos. 
    Your task is to write a 5000-7000 word script for a new video titled """ + title + """. 
    The script must be entirely in the style, tone, and pacing of Dr. Alex Wibberley, based on the following style reference transcript.

    Style Reference Transcript:
    """ + style_transcript + """
    
    Output the transcript in json format with a field for transcript
    """

    payload = {
        # Using the exact model id provided globally by the user rules/request
        "model": "moonshotai/Kimi-K2.5",
        "messages": [
            {"role": "system", "content": "You are a specialized AI assistant that outputs only valid JSON conforming strictly to the requested schema."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 100000,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        print("result", result)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"result_{timestamp}.json"
        
        # save the result to a timestamped json
        with open(result_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)
        
        # Log metadata to a timestamped file
        try:
            log_filename = f".api_usage_{timestamp}.log"
            
            usage = result.get('usage', {})
            finish_reason = result.get('choices', [{}])[0].get('finish_reason', 'unknown')
            metadata = {
                "timestamp": datetime.datetime.now().isoformat(),
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

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        if e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        print(f"Raw output: {content}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Generate a Dr. Alex style YouTube script.")
    parser.add_argument("--title", help="Title or subject of the target script")
    parser.add_argument("--transcript-path", default=os.path.join(TRANSCRIPTS_DIR, "le1n8lJCGKw.json"), help="Path to the style reference transcript")
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
    except Exception as e:
        print(f"Error saving output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
