"""
Search module for querying the inverted index.
"""
from typing import List, Set, Dict
from web_crawler.src.indexer import InvertedIndex


class SearchEngine:
    """Performs search queries on the inverted index."""
    
    def __init__(self, index: InvertedIndex):
        """
        Initialize the search engine.
        
        Args:
            index: The InvertedIndex to search
        """
        self.index = index
    
    def find_single_word(self, word: str) -> List[str]:
        """
        Find all documents containing a single word.
        
        Args:
            word: The word to search for
            
        Returns:
            List of URLs containing the word
        """
        results = self.index.get_documents_for_word(word)
        return sorted(list(results))
    
    def find_all_words(self, words: List[str]) -> List[str]:
        """
        Find all documents containing ALL of the given words (AND query).
        
        Args:
            words: List of words to search for
            
        Returns:
            List of URLs containing all words
        """
        if not words:
            return []
        
        # Start with documents containing the first word
        results: Set[str] = self.index.get_documents_for_word(words[0])
        
        # Intersect with documents containing each subsequent word
        for word in words[1:]:
            results = results.intersection(
                self.index.get_documents_for_word(word)
            )
        
        return sorted(list(results))
    
    def find_any_word(self, words: List[str]) -> List[str]:
        """
        Find all documents containing ANY of the given words (OR query).
        
        Args:
            words: List of words to search for
            
        Returns:
            List of URLs containing at least one word
        """
        if not words:
            return []
        
        results: Set[str] = set()
        
        for word in words:
            results = results.union(
                self.index.get_documents_for_word(word)
            )
        
        return sorted(list(results))
    
    def get_word_details(self, word: str) -> Dict:
        """
        Get detailed information about a word's occurrences.
        
        Args:
            word: The word to get details for
            
        Returns:
            Dictionary with detailed statistics
        """
        word_lower = word.lower()
        statistics = self.index.get_statistics(word_lower)
        
        if not statistics:
            return {
                'word': word_lower,
                'found': False,
                'document_count': 0,
                'total_occurrences': 0,
                'documents': {}
            }
        
        total_occurrences = sum(
            stats['frequency'] for stats in statistics.values()
        )
        
        return {
            'word': word_lower,
            'found': True,
            'document_count': len(statistics),
            'total_occurrences': total_occurrences,
            'documents': statistics
        }
    
    def search(self, query: str) -> List[str]:
        """
        Parse and execute a search query.
        
        By default, multiple words are treated as AND queries (all words must be present).
        Returns a list of URLs containing all search terms.
        
        Args:
            query: The search query (space-separated words)
            
        Returns:
            List of URLs matching the query
        """
        # Normalize and tokenize the query
        query = query.strip().lower()
        
        if not query:
            return []
        
        words = query.split()
        
        if len(words) == 1:
            return self.find_single_word(words[0])
        else:
            # Multi-word queries: find ALL words (AND query)
            return self.find_all_words(words)
    
    def get_results_with_frequency(self, query: str) -> List[Dict]:
        """
        Search and return results with frequency information.
        
        Args:
            query: The search query
            
        Returns:
            List of dictionaries with URL and frequency info
        """
        query = query.strip().lower()
        
        if not query:
            return []
        
        words = query.split()
        urls = self.search(query)
        
        results = []
        for url in urls:
            frequencies = {word: self.index.get_word_frequency(word, url) for word in words}
            results.append({
                'url': url,
                'frequencies': frequencies,
                'total_frequency': sum(frequencies.values())
            })
        
        # Sort by total frequency descending
        results.sort(key=lambda x: x['total_frequency'], reverse=True)
        
        return results
