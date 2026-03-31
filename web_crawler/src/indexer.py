"""
Indexer module for creating and managing inverted indices with TF-IDF ranking.

This module implements an inverted index data structure for efficient full-text search.
It supports advanced ranking algorithms including TF-IDF scoring for relevance ranking.

Time Complexity:
    - Indexing a document: O(n) where n = total words in document
    - Single word lookup: O(1) average case
    - Range queries: O(k) where k = matching documents
    
Space Complexity:
    - Overall: O(m) where m = total unique word-document pairs
    - Typical index: ~50 bytes per unique word occurrence
"""
import json
import math
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import re


class InvertedIndex:
    """Stores and manages an inverted index of word occurrences."""
    
    def __init__(self) -> None:
        """Initialize the inverted index."""
        self.index: Dict[str, Dict[str, List[int]]] = defaultdict(dict)
        # Structure: {word: {url: [positions]}}
        self.document_frequencies: Dict[str, int] = defaultdict(int)
        self.document_lengths: Dict[str, int] = defaultdict(int)
        self.total_documents: int = 0
    
    def _tokenize(self, text: str) -> List[Tuple[int, str]]:
        """
        Tokenize text into words with their positions.
        
        Time Complexity: O(n) where n = length of text
        Uses regex for efficient matching: O(n) with Boyer-Moore-Horspool algorithm
        
        Args:
            text: Text to tokenize (non-empty string)
            
        Returns:
            List of tuples (position, word) in order of occurrence
            
        Example:
            >>> tokens = index._tokenize("Hello world")
            >>> tokens == [(0, 'hello'), (1, 'world')]
            True
        """
        # Convert to lowercase for case-insensitive indexing
        text = text.lower()
        
        # Find all words (sequences of alphanumeric characters)
        # Regex: \b word boundary, \w+ one or more word characters
        tokens: List[Tuple[int, str]] = []
        position: int = 0
        
        for match in re.finditer(r'\b\w+\b', text):
            word: str = match.group()
            tokens.append((position, word))
            position += 1
        
        return tokens
    
    def index_document(self, url: str, text: str) -> None:
        """
        Index a document by adding it to the inverted index.
        
        Time Complexity: O(n) where n = number of words in document
        
        Args:
            url: Document URL (unique identifier)
            text: Document text to index
            
        Raises:
            ValueError: If URL is empty or None
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        tokens: List[Tuple[int, str]] = self._tokenize(text)
        
        # Group positions by word
        word_positions: Dict[str, List[int]] = defaultdict(list)
        for position, word in tokens:
            word_positions[word].append(position)
        
        # Track document frequency and length for TF-IDF
        unique_words_in_doc = set(word_positions.keys())
        self.document_lengths[url] = len(tokens)
        
        # Add to index and update document frequencies
        for word, positions in word_positions.items():
            self.index[word][url] = positions
            self.document_frequencies[word] += 1
        
        self.total_documents += 1
    
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
    
    def get_all_words(self) -> Set[str]:
        """
        Get all indexed words.
        
        Time Complexity: O(m) where m = unique words
        
        Returns:
            Set of all indexed words
        """
        return set(self.index.keys())
    
    def get_size_statistics(self) -> Dict[str, int]:
        """
        Get index size statistics.
        
        Returns:
            Dictionary with 'unique_words', 'unique_documents', and 'total_occurrences'
        """
        total_words = len(self.index)
        unique_documents = set()
        total_occurrences = 0
        
        for docs in self.index.values():
            unique_documents.update(docs.keys())
            for positions in docs.values():
                total_occurrences += len(positions)
        
        return {
            'unique_words': total_words,
            'unique_documents': len(unique_documents),
            'total_occurrences': total_occurrences
        }
    
    def get_size(self) -> Dict[str, int]:
        """Alias for get_size_statistics for backward compatibility."""
        return self.get_size_statistics()
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save the index to a JSON file.
        
        Time Complexity: O(w) where w = total word-document pairs
        
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
        
        Time Complexity: O(w) where w = total word-document pairs
        
        Args:
            filepath: Path to load the index from
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reset state
        self.index = defaultdict(dict)
        self.document_frequencies = defaultdict(int)
        self.document_lengths = defaultdict(int)
        self.total_documents = 0
        
        # Handle both old flat format and new format with metadata
        if 'index' in data:
            # New format with metadata
            index_dict = data.get('index', {})
            metadata = data.get('metadata', {})
            self.document_frequencies = defaultdict(int, metadata.get('document_frequencies', {}))
            self.document_lengths = defaultdict(int, metadata.get('document_lengths', {}))
            self.total_documents = metadata.get('total_documents', 0)
        else:
            # Old flat format - reconstruct metadata
            index_dict = data
        
        # Load the index
        for word, docs in index_dict.items():
            for url, positions in docs.items():
                self.index[word][url] = positions
        
        # Recalculate metadata if not in file
        if not self.total_documents:
            unique_urls = set()
            for word, docs in self.index.items():
                for url in docs.keys():
                    unique_urls.add(url)
                self.document_frequencies[word] = len(docs)
            
            self.total_documents = len(unique_urls)
            
            # Calculate document lengths
            for url in unique_urls:
                positions = []
                for word, docs in self.index.items():
                    if url in docs:
                        positions.extend(docs[url])
                self.document_lengths[url] = max(positions) + 1 if positions else 1
    
    def calculate_idf(self, word: str) -> float:
        """
        Calculate Inverse Document Frequency for a word.
        
        Time Complexity: O(1)
        IDF = log10(total_documents / documents_containing_word)
        
        Args:
            word: The word to calculate IDF for
            
        Returns:
            IDF score (float). Higher score means rarer word.
            Returns 0 if word not in index.
        """
        word_lower = word.lower()
        if word_lower not in self.index or self.total_documents == 0:
            return 0.0
        
        doc_count = len(self.index[word_lower])
        # Add 1 to avoid division by zero, use log10 for stability
        return math.log10((self.total_documents + 1) / (doc_count + 1))
    
    def calculate_tf_idf_scores(self, word: str) -> Dict[str, float]:
        """
        Calculate TF-IDF scores for all documents containing a word.
        
        Time Complexity: O(d) where d = documents containing word
        Formula: TF-IDF = (word_frequency / document_length) * IDF
        
        Args:
            word: The word to calculate scores for
            
        Returns:
            Dictionary mapping URLs to TF-IDF scores
        """
        word_lower = word.lower()
        if word_lower not in self.index:
            return {}
        
        idf = self.calculate_idf(word_lower)
        scores: Dict[str, float] = {}
        
        for url, positions in self.index[word_lower].items():
            tf = len(positions) / max(self.document_lengths.get(url, 1), 1)
            scores[url] = tf * idf
        
        return scores
