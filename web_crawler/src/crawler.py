"""
Web crawler module for scraping quotes.toscrape.com while respecting politeness window.
"""
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLITENESS_DELAY = 6  # seconds between requests
BASE_URL = "https://quotes.toscrape.com"


class WebCrawler:
    """Crawls websites while respecting politeness constraints."""
    
    def __init__(self, base_url: str = BASE_URL, politeness_delay: int = POLITENESS_DELAY):
        """
        Initialize the web crawler.
        
        Args:
            base_url: The base URL to start crawling from
            politeness_delay: Minimum seconds between successive requests
        """
        self.base_url = base_url
        self.politeness_delay = politeness_delay
        self.visited_urls: Set[str] = set()
        self.last_request_time = 0
        
    def _wait_for_politeness_window(self) -> None:
        """Enforce the politeness window before making a request."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.politeness_delay:
            wait_time = self.politeness_delay - elapsed
            logger.info(f"Waiting {wait_time:.1f}s to respect politeness window...")
            time.sleep(wait_time)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the domain."""
        if not url:
            return False
        if url.startswith('/'):
            return True
        if url.startswith(self.base_url):
            return True
        return False
    
    def _normalize_url(self, url: str) -> str:
        """Convert relative URLs to absolute URLs."""
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if url.startswith('/'):
            return self.base_url + url
        return self.base_url + '/' + url
    
    def _fetch_page(self, url: str) -> str:
        """
        Fetch a single page with error handling.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content of the page
            
        Raises:
            requests.RequestException: If the request fails
        """
        self._wait_for_politeness_window()
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; WebCrawler/1.0)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            self.last_request_time = time.time()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise
    
    def _extract_links(self, html: str, current_url: str) -> List[str]:
        """
        Extract all links from HTML content.
        
        Args:
            html: HTML content
            current_url: Current URL (for resolving relative links)
            
        Returns:
            List of absolute URLs
        """
        links = []
        soup = BeautifulSoup(html, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Remove fragment identifiers
            if '#' in href:
                href = href[:href.index('#')]
            
            if self._is_valid_url(href):
                absolute_url = self._normalize_url(href)
                links.append(absolute_url)
        
        return links
    
    def _extract_text(self, html: str) -> str:
        """
        Extract text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Text content
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def crawl(self, start_url: str = None) -> Dict[str, str]:
        """
        Crawl the website starting from the base URL or a specific URL.
        
        Args:
            start_url: Optional specific URL to start from
            
        Returns:
            Dictionary mapping URLs to their text content
        """
        if start_url is None:
            start_url = self.base_url
        
        pages = {}
        to_visit = [start_url]
        
        while to_visit:
            current_url = to_visit.pop(0)
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
            
            # Skip non-main content pages
            if 'tag' in current_url and current_url != self.base_url:
                continue
            if 'login' in current_url or 'logout' in current_url:
                continue
            
            self.visited_urls.add(current_url)
            
            try:
                logger.info(f"Crawling: {current_url}")
                html = self._fetch_page(current_url)
                text = self._extract_text(html)
                pages[current_url] = text
                
                # Extract and queue new links
                links = self._extract_links(html, current_url)
                for link in links:
                    if link not in self.visited_urls and link not in to_visit:
                        to_visit.append(link)
                
            except requests.RequestException:
                logger.warning(f"Could not crawl {current_url}, skipping...")
                continue
        
        logger.info(f"Crawling complete. Found {len(pages)} pages.")
        return pages
