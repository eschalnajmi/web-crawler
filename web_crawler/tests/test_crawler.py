"""
Tests for the crawler module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from web_crawler.src.crawler import WebCrawler


class TestWebCrawler:
    """Test cases for the WebCrawler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.crawler = WebCrawler(base_url="https://example.com", politeness_delay=1)
    
    def test_crawler_initialization(self):
        """Test crawler initialization."""
        assert self.crawler.base_url == "https://example.com"
        assert self.crawler.politeness_delay == 1
        assert len(self.crawler.visited_urls) == 0
        assert self.crawler.last_request_time == 0
    
    def test_is_valid_url(self):
        """Test URL validation."""
        # Valid URLs
        assert self.crawler._is_valid_url("/page")
        assert self.crawler._is_valid_url("https://example.com/page")
        assert self.crawler._is_valid_url("/path/to/page")
        
        # Invalid URLs
        assert not self.crawler._is_valid_url("")
        assert not self.crawler._is_valid_url("https://other.com/page")
    
    def test_normalize_url(self):
        """Test URL normalization."""
        assert self.crawler._normalize_url("/page") == "https://example.com/page"
        assert self.crawler._normalize_url("https://example.com/page") == "https://example.com/page"
        assert self.crawler._normalize_url("http://example.com/page") == "http://example.com/page"
    
    def test_politeness_window(self):
        """Test that politeness window is enforced."""
        self.crawler.last_request_time = time.time()
        
        start = time.time()
        self.crawler._wait_for_politeness_window()
        elapsed = time.time() - start
        
        # Should wait at least the politeness delay minus some tolerance
        assert elapsed >= 0.9  # Allow for timing variations
    
    def test_extract_links(self):
        """Test link extraction from HTML."""
        html = """
        <html>
            <a href="/page1">Link 1</a>
            <a href="/page2">Link 2</a>
            <a href="https://example.com/page3">Link 3</a>
            <a href="https://other.com/page">Bad Link</a>
        </html>
        """
        
        links = self.crawler._extract_links(html, "https://example.com")
        
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert "https://example.com/page3" in links
        assert "https://other.com/page" not in links
    
    def test_extract_links_with_fragments(self):
        """Test that URL fragments are removed."""
        html = '<a href="/page#section">Link</a>'
        
        links = self.crawler._extract_links(html, "https://example.com")
        
        assert "https://example.com/page" in links
        assert "#section" not in links[0]
    
    def test_extract_text(self):
        """Test text extraction from HTML."""
        html = """
        <html>
            <script>var x = 1;</script>
            <p>Hello World</p>
            <style>.class { color: red; }</style>
            <p>Another paragraph</p>
        </html>
        """
        
        text = self.crawler._extract_text(html)
        
        assert "Hello World" in text
        assert "Another paragraph" in text
        assert "var x = 1" not in text
        assert ".class" not in text
    
    @patch('web_crawler.src.crawler.requests.get')
    def test_fetch_page_success(self, mock_get):
        """Test successful page fetching."""
        mock_response = Mock()
        mock_response.text = "<html>Test</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        html = self.crawler._fetch_page("https://example.com")
        
        assert html == "<html>Test</html>"
        assert self.crawler.last_request_time > 0

    @patch('web_crawler.src.crawler.requests.get')
    def test_load_robots_txt_success(self, mock_get):
        """Test successful robots.txt loading."""
        mock_response = Mock()
        mock_response.text = "User-agent: *\nDisallow: /private"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        self.crawler._load_robots_txt()

        assert self.crawler.robots_checked is True
        assert self.crawler._is_allowed_by_robots("https://example.com/")
        assert not self.crawler._is_allowed_by_robots("https://example.com/private")

    @patch('web_crawler.src.crawler.requests.get')
    def test_load_robots_txt_failure_defaults_allow(self, mock_get):
        """If robots.txt cannot be loaded, crawler should continue by default."""
        import requests
        mock_get.side_effect = requests.RequestException("robots unavailable")

        self.crawler._load_robots_txt()

        assert self.crawler.robots_checked is True
        assert self.crawler._is_allowed_by_robots("https://example.com/anything")
    
    @patch('web_crawler.src.crawler.requests.get')
    def test_fetch_page_error(self, mock_get):
        """Test page fetch error handling."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with pytest.raises(requests.RequestException):
            self.crawler._fetch_page("https://example.com")
    
    def test_extract_text_cleans_whitespace(self):
        """Test that extracted text properly cleans whitespace."""
        html = "<p>Too    many    spaces</p>"
        
        text = self.crawler._extract_text(html)
        
        assert "Too many spaces" in text
        assert "    " not in text


class TestCrawlerIntegration:
    """Integration tests for the crawler."""
    
    @patch('web_crawler.src.crawler.requests.get')
    def test_crawl_integration(self, mock_get):
        """Test basic crawling flow."""
        robots_txt = """
        User-agent: *
        Disallow:
        """

        # Mock the HTTP responses
        main_html = """
        <html>
            <a href="/page1">Page 1</a>
            <p>Welcome to the site</p>
        </html>
        """
        
        page1_html = """
        <html>
            <p>Page 1 content</p>
            <a href="/">Back to main</a>
        </html>
        """
        
        responses = [
            {"text": robots_txt},
            {"text": main_html},
            {"text": page1_html},
            {"text": main_html},  # Extra response in case of revisit
        ]
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        
        def side_effect(*args, **kwargs):
            if responses:
                mock_response.text = responses.pop(0)["text"]
            return mock_response
        
        mock_get.side_effect = side_effect
        
        crawler = WebCrawler(base_url="https://example.com", politeness_delay=0)
        crawler.crawl()
        
        # Should have visited main page and page1
        assert len(crawler.visited_urls) >= 1

    @patch('web_crawler.src.crawler.requests.get')
    def test_crawl_respects_robots_txt(self, mock_get):
        """Crawler should skip URLs blocked by robots.txt."""
        robots_txt = """
        User-agent: *
        Disallow: /private
        """
        main_html = """
        <html>
            <a href="/private">Private</a>
            <a href="/public">Public</a>
            <p>Welcome to the site</p>
        </html>
        """
        public_html = """
        <html>
            <p>Public content</p>
        </html>
        """

        responses = [
            {"text": robots_txt},
            {"text": main_html},
            {"text": public_html},
        ]

        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        def side_effect(*args, **kwargs):
            if responses:
                mock_response.text = responses.pop(0)["text"]
            return mock_response

        mock_get.side_effect = side_effect

        crawler = WebCrawler(base_url="https://example.com", politeness_delay=0)
        pages = crawler.crawl()

        assert "https://example.com/private" not in pages
        assert "https://example.com/public" in pages
