import json
import re
import os

def count_words_in_transcript(file_path):
    """
    Extracts words from a transcript JSON and returns the list of words.
    Supports both nested list of objects and a single string.
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = ""
    transcript_data = data.get("transcript", "")

    if isinstance(transcript_data, list):
        # Nested format: [{"text": "...", ...}, ...]
        text = " ".join(item.get("text", "") for item in transcript_data)
    else:
        # Simple format: "..."
        text = transcript_data

    # Tokenizer: find all sequences of characters that form a word
    # Using \b[\w']+\b to handle contractions like "don't"
    words = re.findall(r"\b[\w']+\b", text)
    return words

def main():
    files_to_process = [
        "transcripts/le1n8lJCGKw.json",
        "generated_script_20260328_225301.json"
    ]

    for file_path in files_to_process:
        words = count_words_in_transcript(file_path)
        count = len(words)
        
        # Display results separately
        print(f"--- {file_path} ---")
        print(f"Word Count: {count}")
        
        # Output text file with one word per line
        # Filename example: transcript_le1n8lJCGKw_words.txt
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = f"{base_name}_words.txt"
        
        with open(output_file, "w", encoding="utf-8") as out:
            out.write("\n".join(words))
            
        print(f"Word list saved to: {output_file}\n")

if __name__ == "__main__":
    main()
