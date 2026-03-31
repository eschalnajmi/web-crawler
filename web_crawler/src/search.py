"""
Search module for querying the inverted index with advanced ranking.

This module implements full-text search with TF-IDF based relevance ranking
and query suggestions. It supports both single and multi-word queries with
AND semantics.

Time Complexity:
    - Single-word search: O(1) lookup + O(d) ranking where d = matching documents
    - Multi-word search: O(w*d) where w = words, d = average matching documents
    - Query suggestions: O(n*m) where n = words, m = query length for similarity
"""
from typing import List, Set, Dict, Tuple
from difflib import SequenceMatcher
from web_crawler.src.indexer import InvertedIndex


class SearchEngine:
    """Performs search queries on the inverted index."""
    
    def __init__(self, index: InvertedIndex) -> None:
        """
        Initialize the search engine.
        
        Args:
            index: The InvertedIndex to search (must be initialized)
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
    
    def get_results_with_tf_idf(self, query: str) -> List[Dict]:
        """
        Search and return results ranked by TF-IDF scores.
        
        Time Complexity: O(w*d*log(d)) where w = words in query, d = avg matching docs
        
        For multi-word queries, calculates combined TF-IDF as average of all words.
        Results are sorted by relevance (highest TF-IDF first).
        
        Args:
            query: The search query (space-separated words)
            
        Returns:
            List of dicts with 'url', 'tf_idf_score', and 'frequencies'
            Sorted by TF-IDF score in descending order
        """
        query = query.strip().lower()
        
        if not query:
            return []
        
        words = query.split()
        urls = self.search(query)  # Get matching URLs
        
        if not urls:
            return []
        
        results: List[Dict] = []
        
        for url in urls:
            # Calculate average TF-IDF score across all query words
            scores: List[float] = []
            for word in words:
                idf_scores = self.index.calculate_tf_idf_scores(word)
                if url in idf_scores:
                    scores.append(idf_scores[url])
            
            avg_tf_idf = sum(scores) / len(scores) if scores else 0.0
            
            # Get frequency info
            frequencies = {word: self.index.get_word_frequency(word, url) for word in words}
            
            results.append({
                'url': url,
                'tf_idf_score': avg_tf_idf,
                'frequencies': frequencies,
                'total_frequency': sum(frequencies.values())
            })
        
        # Sort by TF-IDF score descending
        results.sort(key=lambda x: x['tf_idf_score'], reverse=True)
        
        return results
    
    def get_query_suggestions(self, query: str, max_suggestions: int = 5) -> List[Tuple[str, float]]:
        """
        Suggest similar words based on the query.
        
        Time Complexity: O(n*m) where n = indexed words, m = query length
        Uses SequenceMatcher for fuzzy string matching.
        
        Args:
            query: The search query word
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of tuples (word, similarity_score) sorted by similarity
            Similarity score ranges from 0.0 to 1.0
        """
        query_lower = query.strip().lower()
        
        if not query_lower or len(query_lower) < 2:
            return []
        
        all_words = self.index.get_all_words()
        similarities: List[Tuple[str, float]] = []
        
        # Calculate similarity for each indexed word
        for word in all_words:
            similarity = SequenceMatcher(None, query_lower, word).ratio()
            # Only include if reasonably similar (>0.6 threshold)
            if similarity > 0.6:
                similarities.append((word, similarity))
        
        # Sort by similarity descending and return top suggestions
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:max_suggestions]
    
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
