import pathlib

def list_all_transcript_files():
    """
    Lists all filenames in the transcripts directory,
    sorted alphabetically without truncating the output.
    """
    transcripts_dir = pathlib.Path("transcripts")
    
    if not transcripts_dir.exists() or not transcripts_dir.is_dir():
        print(f"Directory '{transcripts_dir}' not found.")
        return

    # Extract just the filenames for all files in the directory
    filenames = [file_path.name for file_path in transcripts_dir.iterdir() if file_path.is_file()]
    
    # Sort alphabetically
    filenames.sort()
    
    # Print all filenames, ensuring no truncation
    for filename in filenames:
        print(filename)

if __name__ == "__main__":
    list_all_transcript_files()
