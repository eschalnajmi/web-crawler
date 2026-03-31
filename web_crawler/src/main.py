"""
Main command-line interface for the search tool.
"""
import os
import sys
import json
from pathlib import Path
from web_crawler.src.crawler import WebCrawler
from web_crawler.src.indexer import InvertedIndex
from web_crawler.src.search import SearchEngine


# Configuration
INDEX_FILE = 'data/index.json'
DATA_DIR = 'data'


class SearchTool:
    """Command-line interface for the search tool."""
    
    def __init__(self):
        """Initialize the search tool."""
        self.index = InvertedIndex()
        self.search_engine = None
        self.ensure_data_directory()
    
    def ensure_data_directory(self) -> None:
        """Create the data directory if it doesn't exist."""
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def build(self) -> None:
        """Build the index by crawling the website."""
        print("Building index...")
        print("This may take several minutes due to the politeness window.")
        
        crawler = WebCrawler()
        pages = crawler.crawl()
        
        print(f"Crawled {len(pages)} pages")
        
        # Index all pages
        for url, text in pages.items():
            print(f"Indexing: {url}")
            self.index.index_document(url, text)
        
        # Save the index
        self.index.save_to_file(INDEX_FILE)
        print(f"Index saved to {INDEX_FILE}")
        
        # Print statistics
        stats = self.index.get_size()
        print(f"\nIndex Statistics:")
        print(f"  Unique words: {stats['unique_words']}")
        print(f"  Unique documents: {stats['unique_documents']}")
        print(f"  Total occurrences: {stats['total_occurrences']}")
    
    def load(self) -> None:
        """Load the index from the file system."""
        if not os.path.exists(INDEX_FILE):
            print(f"Error: Index file not found at {INDEX_FILE}")
            print("Please run 'build' command first.")
            return
        
        print(f"Loading index from {INDEX_FILE}...")
        self.index.load_from_file(INDEX_FILE)
        self.search_engine = SearchEngine(self.index)
        
        stats = self.index.get_size()
        print(f"Index loaded successfully!")
        print(f"  Unique words: {stats['unique_words']}")
        print(f"  Unique documents: {stats['unique_documents']}")
        print(f"  Total occurrences: {stats['total_occurrences']}")
    
    def print_word(self, word: str) -> None:
        """
        Print the inverted index for a particular word.
        
        Args:
            word: The word to print
        """
        if self.search_engine is None:
            print("Error: Index not loaded. Please run 'load' command first.")
            return
        
        details = self.search_engine.get_word_details(word)
        
        if not details['found']:
            print(f"Word '{word}' not found in index.")
            return
        
        print(f"\nIndex for word: '{word}'")
        print(f"Found in {details['document_count']} documents")
        print(f"Total occurrences: {details['total_occurrences']}\n")
        
        for url, stats in details['documents'].items():
            print(f"  URL: {url}")
            print(f"    Frequency: {stats['frequency']}")
            print(f"    Positions: {stats['positions']}")
    
    def find(self, *words) -> None:
        """
        Find pages containing the given search terms.
        
        Args:
            words: Variable number of words to search for
        """
        if self.search_engine is None:
            print("Error: Index not loaded. Please run 'load' command first.")
            return
        
        if not words:
            print("Error: Please provide at least one word to search for.")
            return
        
        query = ' '.join(words)
        print(f"\nSearching for: '{query}'")
        
        # Get results with frequency information
        results = self.search_engine.get_results_with_frequency(query)
        
        if not results:
            print("No pages found containing all search terms.")
            return
        
        print(f"Found in {len(results)} page(s):\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['url']}")
            if len(words) > 1:
                for word, freq in result['frequencies'].items():
                    print(f"   - '{word}': {freq} occurrences")
    
    def print_help(self) -> None:
        """Print help information."""
        help_text = """
Search Tool Commands:

  build                 - Crawl the website and build the index
  load                  - Load the previously built index from disk
  print <word>          - Print the inverted index for a word
  find <words...>       - Find pages containing the search terms
  help                  - Show this help message
  exit                  - Exit the program

Examples:
  > build
  > load
  > print nonsense
  > find good friends
  > find indifference
"""
        print(help_text)
    
    def run(self) -> None:
        """Run the interactive command-line interface."""
        print("=" * 60)
        print("             Search Engine Tool")
        print("=" * 60)
        print("Type 'help' for available commands.\n")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:]
                
                if command == 'build':
                    self.build()
                elif command == 'load':
                    self.load()
                elif command == 'print':
                    if args:
                        self.print_word(args[0])
                    else:
                        print("Error: Please provide a word to print.")
                elif command == 'find':
                    if args:
                        self.find(*args)
                    else:
                        print("Error: Please provide search terms.")
                elif command == 'help':
                    self.print_help()
                elif command == 'exit':
                    print("Goodbye!")
                    break
                else:
                    print(f"Unknown command: '{command}'. Type 'help' for available commands.")
            
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    tool = SearchTool()
    
    # If arguments provided, process them and exit
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        args = sys.argv[2:]
        
        if command == 'build':
            tool.build()
        elif command == 'load':
            tool.load()
        elif command == 'print':
            tool.load()
            if args:
                tool.print_word(args[0])
        elif command == 'find':
            tool.load()
            if args:
                tool.find(*args)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    else:
        # Run interactive mode
        tool.run()


if __name__ == '__main__':
    main()
