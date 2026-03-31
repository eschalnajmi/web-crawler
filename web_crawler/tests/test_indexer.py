"""
Tests for the indexer module.
"""
import pytest
import os
import json
import tempfile
from web_crawler.src.indexer import InvertedIndex


class TestInvertedIndex:
    """Test cases for the InvertedIndex class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.index = InvertedIndex()
    
    def test_index_initialization(self):
        """Test index initialization."""
        assert len(self.index.index) == 0
    
    def test_tokenize(self):
        """Test text tokenization."""
        text = "Hello world. This is a test."
        tokens = self.index._tokenize(text)
        
        # Should have 6 tokens (hello, world, this, is, a, test)
        assert len(tokens) == 6
        # All words should be lowercase
        assert all(word.islower() for _, word in tokens)
        # Check specific words
        words = [word for _, word in tokens]
        assert "hello" in words
        assert "world" in words
        assert "test" in words
    
    def test_tokenize_case_insensitive(self):
        """Test that tokenization is case-insensitive."""
        text1 = "Hello WORLD"
        text2 = "hello world"
        
        tokens1 = self.index._tokenize(text1)
        tokens2 = self.index._tokenize(text2)
        
        words1 = [word for _, word in tokens1]
        words2 = [word for _, word in tokens2]
        
        assert words1 == words2
    
    def test_index_document(self):
        """Test indexing a single document."""
        url = "https://example.com/page1"
        text = "Hello world. Hello universe."
        
        self.index.index_document(url, text)
        
        assert "hello" in self.index.index
        assert "world" in self.index.index
        assert "universe" in self.index.index
    
    def test_get_word_index(self):
        """Test retrieving word index."""
        url = "https://example.com/page1"
        text = "Hello world. Hello universe."
        
        self.index.index_document(url, text)
        
        word_index = self.index.get_word_index("hello")
        
        assert url in word_index
        assert len(word_index[url]) == 2  # "hello" appears twice
    
    def test_get_documents_for_word(self):
        """Test finding documents containing a word."""
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"
        
        self.index.index_document(url1, "Hello world")
        self.index.index_document(url2, "Hello there")
        
        docs = self.index.get_documents_for_word("hello")
        
        assert len(docs) == 2
        assert url1 in docs
        assert url2 in docs
    
    def test_word_not_found(self):
        """Test searching for a word that doesn't exist."""
        self.index.index_document("https://example.com/page1", "Hello world")
        
        docs = self.index.get_documents_for_word("nonexistent")
        
        assert len(docs) == 0
    
    def test_get_word_frequency(self):
        """Test word frequency calculation."""
        url = "https://example.com/page1"
        text = "Test test test"
        
        self.index.index_document(url, text)
        
        frequency = self.index.get_word_frequency("test", url)
        
        assert frequency == 3
    
    def test_get_statistics(self):
        """Test getting detailed statistics for a word."""
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"
        
        self.index.index_document(url1, "apple apple banana")
        self.index.index_document(url2, "apple cherry")
        
        stats = self.index.get_statistics("apple")
        
        assert len(stats) == 2
        assert stats[url1]['frequency'] == 2
        assert stats[url2]['frequency'] == 1
        assert isinstance(stats[url1]['positions'], list)
    
    def test_get_all_words(self):
        """Test retrieving all indexed words."""
        self.index.index_document("https://example.com/page1", "apple banana cherry")
        
        words = self.index.get_all_words()
        
        assert "apple" in words
        assert "banana" in words
        assert "cherry" in words
        assert len(words) == 3
    
    def test_get_size_statistics(self):
        """Test getting size statistics."""
        self.index.index_document("https://example.com/page1", "apple banana")
        self.index.index_document("https://example.com/page2", "apple cherry")
        
        size = self.index.get_size()
        
        assert size['unique_words'] == 3
        assert size['unique_documents'] == 2
        assert size['total_occurrences'] == 4
    
    def test_save_to_file(self):
        """Test saving index to file."""
        self.index.index_document("https://example.com/page1", "Hello world")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.index.save_to_file(temp_file)
            assert os.path.exists(temp_file)
            
            # Verify file content
            with open(temp_file, 'r') as f:
                data = json.load(f)
            
            assert "hello" in data
            assert "world" in data
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_load_from_file(self):
        """Test loading index from file."""
        # Create and save an index
        index1 = InvertedIndex()
        index1.index_document("https://example.com/page1", "Hello world")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            index1.save_to_file(temp_file)
            
            # Load into a new index
            index2 = InvertedIndex()
            index2.load_from_file(temp_file)
            
            # Verify content
            assert "hello" in index2.index
            assert "world" in index2.index
            docs = index2.get_documents_for_word("hello")
            assert "https://example.com/page1" in docs
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_multiple_documents(self):
        """Test indexing multiple documents."""
        urls = [f"https://example.com/page{i}" for i in range(5)]
        
        for i, url in enumerate(urls):
            self.index.index_document(url, f"word{i} common")
        
        # Test common word appears in all documents
        common_docs = self.index.get_documents_for_word("common")
        assert len(common_docs) == 5
        
        # Test specific word appears in only one document
        word0_docs = self.index.get_documents_for_word("word0")
        assert len(word0_docs) == 1
    
    def test_special_characters_ignored(self):
        """Test that special characters are properly handled."""
        self.index.index_document("https://example.com", "hello@world #test! $special")
        
        words = self.index.get_all_words()
        
        # Should only have alphanumeric words
        assert "hello" in words
        assert "world" in words
        assert "test" in words
        assert "special" in words
