import json
import re
import pandas as pd
import matplotlib.pyplot as plt

class TranscriptAnalyzer:
    """
    A Pandas-based module to analyze generated_script.json files.
    Currently supports analyzing and visualizing word frequencies in the transcript.
    """
    
    # Common English stop words to filter out so the plots are actually useful
    STOP_WORDS = {
        "the", "and", "to", "a", "of", "in", "it", "is", "that", "you",
        "for", "on", "was", "with", "as", "are", "be", "this", "at", "but",
        "not", "they", "we", "have", "from", "an", "what", "so", "if", "or",
        "there", "can", "out", "my", "by", "all", "up", "about", "who", "which",
        "their", "would", "like", "just", "do", "when", "your", "them", "some",
        "how", "me", "into", "its", "then", "than", "no", "now", "only", "well",
        "because", "very", "i", "im", "we", "dont", "were", "s", "t", "re",
        "ve", "ll", "m", "d", "don", "doesn", "didn"
    }

    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load_data()
        self.word_freq_df = None

    def _load_data(self):
        """Load JSON data into memory."""
        with open(self.filepath, 'r') as f:
            return json.load(f)

    def calculate_word_frequencies(self):
        """
        Tokenize the transcript, filter out stop words, and calculate word frequencies.
        Stores and returns the result as a Pandas DataFrame.
        """
        transcript = self.data.get('transcript', '')
        
        # Lowercase and extract alphanumeric words
        words = re.findall(r'\b[a-z0-9]+\b', transcript.lower())
        
        # Filter stop words
        filtered_words = [w for w in words if w not in self.STOP_WORDS]
        
        # Count frequencies
        word_counts = pd.Series(filtered_words).value_counts()
        
        # Convert to DataFrame
        self.word_freq_df = word_counts.reset_index()
        self.word_freq_df.columns = ['Word', 'Frequency']
        
        return self.word_freq_df

    def plot_top_words(self, top_n=20, start_n=0):
        """
        Calculate and plot the most frequent words within a given rank range (start_n to top_n).
        Designed to be called with a single line from a Jupyter Notebook.
        """
        if self.word_freq_df is None:
            self.calculate_word_frequencies()

        # Get word range slice
        top_df = self.word_freq_df.iloc[start_n:top_n].sort_values(by='Frequency', ascending=True)

        # Plotting - dynamic height based on number of words
        num_bars = len(top_df)
        fig_height = max(6, num_bars * 0.4)
        plt.figure(figsize=(10, fig_height))
        plt.barh(top_df['Word'], top_df['Frequency'], color='#4C72B0')
        plt.xlabel('Frequency')
        plt.ylabel('Word')

        # Adjust title based on whether a starting offset was provided
        if start_n == 0:
            title_prefix = f"Top {top_n} Words"
        else:
            title_prefix = f"Words Ranked {start_n+1} to {top_n}"

        plt.title(f"{title_prefix} in Transcript\nTitle: {self.data.get('title', 'Unknown')}")
        plt.tight_layout()
        plt.show()
