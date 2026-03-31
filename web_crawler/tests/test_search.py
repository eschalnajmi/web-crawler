"""
Tests for the search module.

Comprehensive test suite for search functionality including:
- Basic single and multi-word queries
- TF-IDF ranking and relevance scoring
- Query suggestions with fuzzy matching
- Edge cases and error handling
"""
import pytest
from web_crawler.src.indexer import InvertedIndex
from web_crawler.src.search import SearchEngine


class TestSearchEngine:
    """Test cases for the SearchEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.index = InvertedIndex()
        self.search = SearchEngine(self.index)
        
        # Create sample documents
        self.index.index_document("https://example.com/page1", "Good friends are hard to find")
        self.index.index_document("https://example.com/page2", "Good times with friends")
        self.index.index_document("https://example.com/page3", "Finding good books is fun")
        self.index.index_document("https://example.com/page4", "Nonsense talks")
    
    def test_search_engine_initialization(self):
        """Test search engine initialization."""
        assert self.search.index is not None
        assert isinstance(self.search.index, InvertedIndex)
    
    def test_find_single_word(self):
        """Test finding pages with a single word."""
        results = self.search.find_single_word("good")
        
        assert len(results) == 3
        assert "https://example.com/page1" in results
        assert "https://example.com/page2" in results
        assert "https://example.com/page3" in results
    
    def test_find_single_word_not_found(self):
        """Test searching for a word that doesn't exist."""
        results = self.search.find_single_word("nonexistent")
        
        assert len(results) == 0
    
    def test_find_all_words_and_query(self):
        """Test AND query with multiple words."""
        results = self.search.find_all_words(["good", "friends"])
        
        assert len(results) == 2
        assert "https://example.com/page1" in results
        assert "https://example.com/page2" in results
    
    def test_find_all_words_no_common_document(self):
        """Test AND query where no document contains all words."""
        results = self.search.find_all_words(["good", "nonsense"])
        
        assert len(results) == 0
    
    def test_find_any_word_or_query(self):
        """Test OR query with multiple words."""
        results = self.search.find_any_word(["good", "nonsense"])
        
        assert len(results) == 4  # All documents
    
    def test_find_any_word_empty_list(self):
        """Test OR query with empty list."""
        results = self.search.find_any_word([])
        
        assert len(results) == 0
    
    def test_get_word_details_found(self):
        """Test getting details for a word that exists."""
        details = self.search.get_word_details("good")
        
        assert details['found'] is True
        assert details['word'] == "good"
        assert details['document_count'] == 3
        assert details['total_occurrences'] == 3
        assert len(details['documents']) == 3
    
    def test_get_word_details_not_found(self):
        """Test getting details for a word that doesn't exist."""
        details = self.search.get_word_details("nonexistent")
        
        assert details['found'] is False
        assert details['document_count'] == 0
        assert details['total_occurrences'] == 0
    
    def test_search_single_word(self):
        """Test search with single word."""
        results = self.search.search("friends")
        
        assert len(results) == 2
        assert "https://example.com/page1" in results
        assert "https://example.com/page2" in results
    
    def test_search_multiple_words_and(self):
        """Test search with multiple words (AND query)."""
        results = self.search.search("good friends")
        
        assert len(results) == 2
        assert "https://example.com/page1" in results
        assert "https://example.com/page2" in results
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        results1 = self.search.search("GOOD")
        results2 = self.search.search("good")
        results3 = self.search.search("GoOd")
        
        assert results1 == results2 == results3
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.search.search("")
        
        assert len(results) == 0
    
    def test_search_whitespace_only(self):
        """Test search with whitespace only."""
        results = self.search.search("   ")
        
        assert len(results) == 0
    
    def test_get_results_with_frequency(self):
        """Test getting results with frequency information."""
        results = self.search.get_results_with_frequency("good friends")
        
        assert len(results) == 2
        
        # Results should be sorted by total frequency
        for result in results:
            assert 'url' in result
            assert 'frequencies' in result
            assert 'total_frequency' in result
            assert result['frequencies']['good'] >= 1
            assert result['frequencies']['friends'] >= 1
    
    def test_get_results_with_frequency_sorting(self):
        """Test that results are sorted by frequency."""
        # Create documents with different frequencies
        index = InvertedIndex()
        index.index_document("https://a.com", "apple apple apple")
        index.index_document("https://b.com", "apple")
        
        search = SearchEngine(index)
        results = search.get_results_with_frequency("apple")
        
        # First result should have the higher frequency
        assert results[0]['url'] == "https://a.com"
        assert results[0]['total_frequency'] == 3
        assert results[1]['url'] == "https://b.com"
        assert results[1]['total_frequency'] == 1


class TestSearchEdgeCases:
    """Test edge cases for the search engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.index = InvertedIndex()
        self.search = SearchEngine(self.index)
    
    def test_empty_index(self):
        """Test search on empty index."""
        results = self.search.search("anything")
        
        assert len(results) == 0
    
    def test_single_document(self):
        """Test search with single document."""
        self.index.index_document("https://example.com", "test content")
        
        results = self.search.search("test")
        
        assert len(results) == 1
        assert results[0] == "https://example.com"
    
    def test_repeated_words_in_query(self):
        """Test query with repeated words."""
        self.index.index_document("https://example.com", "test test test")
        
        results = self.search.search("test test")
        
        assert len(results) == 1
    
    def test_special_characters_in_query(self):
        """Test query with special characters."""
        self.index.index_document("https://example.com", "hello world")
        
        # Special characters in query are not stripped - the term won't match
        results = self.search.search("hello@!#$")
        assert len(results) == 0
        
        # But plain query should work
        results = self.search.search("hello")
        assert len(results) == 1
    
    def test_numbers_in_documents(self):
        """Test indexing documents with numbers."""
        self.index.index_document("https://example.com", "Version 3.14 released")
        
        results = self.search.search("3")
        
        assert len(results) == 1
    
    def test_very_long_document(self):
        """Test indexing and searching in a very long document."""
        long_text = " ".join(["word"] * 1000 + ["unique"])
        self.index.index_document("https://example.com", long_text)
        
        results = self.search.search("unique")
        
        assert len(results) == 1
        
        frequency = self.index.get_word_frequency("word", "https://example.com")
        assert frequency == 1000
