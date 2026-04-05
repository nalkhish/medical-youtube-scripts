import json
import argparse
import os

def concatenate_transcript(input_path, output_path):
    """
    Reads a transcript JSON file and concatenates all text segments into a single string.
    """
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract text from each segment and join with spaces
    transcript_segments = data.get('transcript', [])
    full_text = " ".join([segment.get('text', '').strip() for segment in transcript_segments])

    # Create the output dictionary
    output_data = {
        "transcript": full_text
    }

    # Write to the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Successfully converted {input_path} to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatenate transcript segments into a single text field.")
    parser.add_argument("input", nargs="?", default="transcripts/le1n8lJCGKw.json", help="Path to the input transcript JSON file.")
    parser.add_argument("output", nargs="?", default="le1n8lJCGKw_concatenated.json", help="Path to the output JSON file.")

    args = parser.parse_args()
    concatenate_transcript(args.input, args.output)
