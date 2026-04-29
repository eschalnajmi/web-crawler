"""
Additional comprehensive tests for edge cases and advanced behavior.

Covers:
- Advanced TF-IDF and IDF behavior in `InvertedIndex`
- TF-IDF ranking and query suggestions in `SearchEngine`
- Politeness window and error handling in `WebCrawler`
"""
import json
import math
import tempfile
import time
from unittest.mock import patch, Mock

import pytest

from web_crawler.src.indexer import InvertedIndex
from web_crawler.src.search import SearchEngine
from web_crawler.src.crawler import WebCrawler
from requests import RequestException


class TestIndexerAdvanced:
    def setup_method(self):
        self.index = InvertedIndex()

    def test_calculate_idf_empty(self):
        assert self.index.calculate_idf("anything") == 0.0

    def test_calculate_idf_relative_rarity(self):
        # two documents: 'apple' in both, 'banana' only in one
        self.index.index_document("https://a", "apple banana")
        self.index.index_document("https://b", "apple")

        idf_apple = self.index.calculate_idf("apple")
        idf_banana = self.index.calculate_idf("banana")

        assert idf_apple >= 0.0
        assert idf_banana > idf_apple

    def test_calculate_tf_idf_scores_basic(self):
        # create documents with different frequencies and lengths
        self.index.index_document("https://a", "apple apple apple orange")  # tf=3/4
        self.index.index_document("https://b", "apple")  # tf=1/1

        scores = self.index.calculate_tf_idf_scores("apple")

        assert "https://a" in scores and "https://b" in scores
        # If the word appears in all documents, IDF will be 0 and scores will be 0
        idf = self.index.calculate_idf("apple")
        if idf == 0.0:
            assert scores["https://a"] == 0.0 and scores["https://b"] == 0.0
        else:
            assert scores["https://a"] != scores["https://b"]

    def test_save_and_load_with_metadata_format(self):
        # Manually write file with metadata block to exercise load_from_file path
        data = {
            "index": {
                "hello": {"https://x": [0, 1]},
                "world": {"https://x": [2]}
            },
            "metadata": {
                "document_frequencies": {"hello": 1, "world": 1},
                "document_lengths": {"https://x": 3},
                "total_documents": 1
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json.dumps(data))
            tmp = f.name

        try:
            idx = InvertedIndex()
            idx.load_from_file(tmp)

            assert idx.total_documents == 1
            assert idx.get_word_frequency("hello", "https://x") == 2
        finally:
            pass


class TestSearchAdvanced:
    def setup_method(self):
        self.index = InvertedIndex()
        self.search = SearchEngine(self.index)

        # Add words to index for suggestion tests
        self.index.index_document("https://p1", "good goodness goodie")
        self.index.index_document("https://p2", "good good goodness")

    def test_get_query_suggestions(self):
        suggestions = self.search.get_query_suggestions("goodnes")
        # Expect 'goodness' to appear with high similarity
        words = [w for w, _ in suggestions]
        assert "goodness" in words

    def test_get_results_with_tf_idf_ordering(self):
        # Construct documents where one has higher normalized TF
        idx = InvertedIndex()
        idx.index_document("https://high", "rare rare rare")  # high tf, short doc
        idx.index_document("https://low", "rare common common common common")  # low tf

        search = SearchEngine(idx)
        results = search.get_results_with_tf_idf("rare")

        assert len(results) == 2
        # Expect the high TF short doc to rank above the low one
        assert results[0]['url'] == "https://high"


class TestCrawlerAdvanced:
    def setup_method(self):
        self.crawler = WebCrawler(base_url="https://example.com", politeness_delay_range=(1, 5))

    @patch('web_crawler.src.crawler.time.sleep')
    @patch('web_crawler.src.crawler.random.uniform', return_value=2)
    def test_wait_for_politeness_no_sleep_when_elapsed_large(self, mock_uniform, mock_sleep):
        # last request 10 seconds ago, uniform returns 2 -> no sleep expected
        self.crawler.last_request_time = time.time() - 10
        self.crawler._wait_for_politeness_window()

        mock_uniform.assert_called_once()
        mock_sleep.assert_not_called()

    @patch('web_crawler.src.crawler.requests.get')
    def test_fetch_page_raises_on_request_exception(self, mock_get):
        mock_get.side_effect = RequestException("network error")

        with pytest.raises(RequestException):
            self.crawler._fetch_page("https://example.com")

    def test_normalize_url_variants(self):
        assert self.crawler._normalize_url("page") == "https://example.com/page"
        assert self.crawler._normalize_url("/page") == "https://example.com/page"
        assert self.crawler._normalize_url("https://example.com/page") == "https://example.com/page"
