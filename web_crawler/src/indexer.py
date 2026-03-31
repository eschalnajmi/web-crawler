"""
Indexer module for creating and managing inverted indices.
"""
import json
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import re


class InvertedIndex:
    """Stores and manages an inverted index of word occurrences."""
    
    def __init__(self):
        """Initialize the inverted index."""
        self.index: Dict[str, Dict[str, List[int]]] = defaultdict(dict)
        # Structure: {word: {url: [positions]}}
    
    def _tokenize(self, text: str) -> List[Tuple[int, str]]:
        """
        Tokenize text into words with their positions.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tuples (position, word)
        """
        # Convert to lowercase for case-insensitive indexing
        text = text.lower()
        
        # Find all words (sequences of alphanumeric characters)
        tokens = []
        position = 0
        
        for match in re.finditer(r'\b\w+\b', text):
            word = match.group()
            tokens.append((position, word))
            position += 1
        
        return tokens
    
    def index_document(self, url: str, text: str) -> None:
        """
        Index a document into the inverted index.
        
        Args:
            url: The URL/identifier for the document
            text: The text content to index
        """
        tokens = self._tokenize(text)
        
        # Group positions by word
        word_positions: Dict[str, List[int]] = defaultdict(list)
        for position, word in tokens:
            word_positions[word].append(position)
        
        # Add to index
        for word, positions in word_positions.items():
            self.index[word][url] = positions
    
    def get_word_index(self, word: str) -> Dict[str, List[int]]:
        """
        Get the complete index entry for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            Dictionary mapping URLs to position lists
        """
        word_lower = word.lower()
        return dict(self.index.get(word_lower, {}))
    
    def get_documents_for_word(self, word: str) -> Set[str]:
        """
        Get all documents containing a word.
        
        Args:
            word: The word to search for
            
        Returns:
            Set of URLs containing the word
        """
        word_lower = word.lower()
        return set(self.index.get(word_lower, {}).keys())
    
    def get_word_frequency(self, word: str, url: str) -> int:
        """
        Get the frequency of a word in a specific document.
        
        Args:
            word: The word to search for
            url: The document URL
            
        Returns:
            Number of occurrences
        """
        word_lower = word.lower()
        if word_lower in self.index and url in self.index[word_lower]:
            return len(self.index[word_lower][url])
        return 0
    
    def get_statistics(self, word: str) -> Dict[str, Dict]:
        """
        Get detailed statistics for a word.
        
        Args:
            word: The word to get statistics for
            
        Returns:
            Dictionary with statistics for each document
        """
        word_lower = word.lower()
        if word_lower not in self.index:
            return {}
        
        stats = {}
        for url, positions in self.index[word_lower].items():
            stats[url] = {
                'frequency': len(positions),
                'positions': positions
            }
        
        return stats
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save the index to a JSON file.
        
        Args:
            filepath: Path to save the index to
        """
        # Convert defaultdict to regular dict for JSON serialization
        index_dict = {
            word: dict(docs) for word, docs in self.index.items()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(index_dict, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load the index from a JSON file.
        
        Args:
            filepath: Path to load the index from
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            index_dict = json.load(f)
        
        # Convert back to nested defaultdict
        self.index = defaultdict(dict)
        for word, docs in index_dict.items():
            for url, positions in docs.items():
                self.index[word][url] = positions
    
    def get_all_words(self) -> Set[str]:
        """
        Get all indexed words.
        
        Returns:
            Set of all words in the index
        """
        return set(self.index.keys())
    
    def get_size(self) -> Dict[str, int]:
        """
        Get size statistics of the index.
        
        Returns:
            Dictionary with statistics
        """
        total_words = len(self.index)
        total_entries = sum(len(docs) for docs in self.index.values())
        unique_documents = set()
        total_occurrences = 0
        
        for docs in self.index.values():
            unique_documents.update(docs.keys())
            for positions in docs.values():
                total_occurrences += len(positions)
        
        return {
            'unique_words': total_words,
            'total_entries': total_entries,
            'unique_documents': len(unique_documents),
            'total_occurrences': total_occurrences
        }
