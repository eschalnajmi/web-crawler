"""
Web crawler module for scraping quotes.toscrape.com while respecting a randomized politeness window.
"""
import requests
from bs4 import BeautifulSoup
import random
import time
from typing import List, Dict, Set, Tuple
import logging
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLITENESS_DELAY_MIN = 6
POLITENESS_DELAY_MAX = 20
BASE_URL = "https://quotes.toscrape.com"


class WebCrawler:
    """Crawls websites while respecting politeness constraints."""
    
    def __init__(self, base_url: str = BASE_URL,
                 politeness_delay_range: Tuple[int, int] = (POLITENESS_DELAY_MIN, POLITENESS_DELAY_MAX),
                 max_pages: int = 100, max_depth: int = 5, max_crawl_time: int = 600):
        """
        Initialize the web crawler.
        
        Args:
            base_url: The base URL to start crawling from
            politeness_delay_range: Inclusive min/max seconds between successive requests
            max_pages: Maximum number of pages to crawl (default: 100)
            max_depth: Maximum depth to crawl from start URL (default: 5)
            max_crawl_time: Maximum crawl time in seconds (default: 600)
        """
        self.base_url = base_url
        self.politeness_delay_range = politeness_delay_range
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.max_crawl_time = max_crawl_time
        self.visited_urls: Set[str] = set()
        self.last_request_time = 0
        self.user_agent = "WebCrawler/1.0"
        self.robots_parser = RobotFileParser()
        self.robots_checked = False
        self.robots_loaded = False

    def _load_robots_txt(self) -> None:
        """Load and parse robots.txt once per crawler instance."""
        if self.robots_checked:
            return

        robots_url = self._normalize_url('/robots.txt')
        self.robots_parser.set_url(robots_url)

        try:
            self._wait_for_politeness_window()
            headers = {'User-Agent': self.user_agent}
            response = requests.get(robots_url, headers=headers, timeout=10)
            response.raise_for_status()
            self.last_request_time = time.time()
            self.robots_parser.parse(response.text.splitlines())
            self.robots_loaded = True
            logger.info(f"Loaded robots.txt from {robots_url}")
        except requests.RequestException:
            # If robots.txt is unavailable, proceed with crawling.
            logger.warning(f"Could not load robots.txt at {robots_url}; proceeding without robots rules.")
            self.robots_loaded = False
        finally:
            self.robots_checked = True

    def _is_allowed_by_robots(self, url: str) -> bool:
        """Check whether a URL is allowed by robots.txt rules."""
        self._load_robots_txt()
        if not self.robots_loaded:
            return True
        return self.robots_parser.can_fetch(self.user_agent, url)
        
    def _wait_for_politeness_window(self) -> None:
        """Enforce the politeness window before making a request."""
        elapsed = time.time() - self.last_request_time
        min_delay, max_delay = self.politeness_delay_range
        wait_time = random.uniform(min_delay, max_delay)

        if elapsed < wait_time:
            wait_time -= elapsed
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
            normalized = url
        elif url.startswith('/'):
            normalized = self.base_url + url
        else:
            normalized = self.base_url + '/' + url
        
        # Strip query parameters and fragments to avoid URL explosion
        parsed = urlparse(normalized)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
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
                'User-Agent': self.user_agent
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
    
    def _get_url_depth(self, url: str, base: str) -> int:
        """Calculate the depth of a URL relative to the base URL."""
        # Remove base from url and count path segments
        if url.startswith(base):
            relative_path = url[len(base):]
        else:
            return 0
        
        # Count slashes in relative path
        depth = relative_path.count('/') - 1  # -1 because path starts with /
        return max(0, depth)
    
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

        if not self._is_allowed_by_robots(start_url):
            logger.warning(f"Start URL blocked by robots.txt: {start_url}")
            return {}
        
        crawl_start_time = time.time()
        pages = {}
        to_visit: List[Tuple[str, int]] = [(start_url, 0)]  # (url, depth)
        
        while to_visit:
            # Check time limit
            elapsed_time = time.time() - crawl_start_time
            if elapsed_time > self.max_crawl_time:
                logger.warning(f"Crawl time limit ({self.max_crawl_time}s) exceeded. Stopping crawl.")
                break
            
            # Check page limit
            if len(pages) >= self.max_pages:
                logger.warning(f"Page limit ({self.max_pages}) reached. Stopping crawl.")
                break
            
            current_url, current_depth = to_visit.pop(0)
            
            # Skip if depth exceeds limit
            if current_depth > self.max_depth:
                logger.info(f"Skipping {current_url} (depth {current_depth} > max {self.max_depth})")
                continue
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue

            if not self._is_allowed_by_robots(current_url):
                logger.info(f"Skipping blocked URL by robots.txt: {current_url}")
                continue
            
            # Skip non-main content pages
            if 'tag' in current_url and current_url != self.base_url:
                continue
            if 'login' in current_url or 'logout' in current_url:
                continue
            
            self.visited_urls.add(current_url)
            
            try:
                logger.info(f"Crawling: {current_url} (depth: {current_depth})")
                html = self._fetch_page(current_url)
                text = self._extract_text(html)
                pages[current_url] = text
                
                # Extract and queue new links
                links = self._extract_links(html, current_url)
                for link in links:
                    if link not in self.visited_urls and link not in [url for url, _ in to_visit]:
                        to_visit.append((link, current_depth + 1))
                
            except requests.RequestException:
                logger.warning(f"Could not crawl {current_url}, skipping...")
                continue
        
        logger.info(f"Crawling complete. Found {len(pages)} pages. Time: {time.time() - crawl_start_time:.1f}s")
        return pages
