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
from collections import defaultdict
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLITENESS_DELAY_MIN = 6
POLITENESS_DELAY_MAX = 20
BASE_URL = "https://quotes.toscrape.com"


class WebCrawler:
    """Crawls websites while respecting politeness constraints."""
    
    def __init__(self, base_url: str = BASE_URL,
                 politeness_delay_range: Tuple[int, int] = (POLITENESS_DELAY_MIN, POLITENESS_DELAY_MAX),
                 max_pages: int = 100, max_depth: int = 20, max_crawl_time: int = 600):
        """
        Initialize the web crawler.
        
        Args:
            base_url: The base URL to start crawling from
            politeness_delay_range: Inclusive min/max seconds between successive requests
            max_pages: Maximum number of pages to crawl (default: 100)
            max_depth: Maximum depth in page hierarchy from start URL (default: 20).
                      Prevents infinite exploration of fictitious resources by limiting
                      how deep the crawler traverses the directory/path hierarchy.
            max_crawl_time: Maximum crawl time in seconds (default: 600)
        """
        self.base_url = base_url
        self.politeness_delay_range = politeness_delay_range
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.max_crawl_time = max_crawl_time
        self.visited_urls: Set[str] = set()
        # Per-host state to enforce single concurrent fetch and politeness
        self.host_queues: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.last_request_time: Dict[str, float] = defaultdict(lambda: 0.0)
        self.user_agent = "WebCrawler/1.0 (+https://example.com/contact)"
        # Robots parsers per host
        self.robots_parsers: Dict[str, RobotFileParser] = {}
        self.robots_loaded: Dict[str, bool] = defaultdict(lambda: False)
        # If robots.txt provides a Crawl-delay, store it per host (seconds)
        self.host_crawl_delay: Dict[str, float] = {}
        # Track max depth reached per host to prevent infinite exploration
        self.host_max_depth: Dict[str, int] = {}

    def _load_robots_for_host(self, host: str) -> None:
        """Load and parse robots.txt for a specific host."""
        if host in self.robots_parsers:
            return

        robots_url = f"https://{host}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            headers = {'User-Agent': self.user_agent}
            # Respect a small wait before fetching robots to avoid burst
            min_delay, _ = self.politeness_delay_range
            elapsed = time.time() - self.last_request_time.get(host, 0.0)
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)

            response = requests.get(robots_url, headers=headers, timeout=10)
            response.raise_for_status()
            parser.parse(response.text.splitlines())
            self.robots_parsers[host] = parser
            self.robots_loaded[host] = True
            crawl_delay = parser.crawl_delay(self.user_agent)
            if crawl_delay is not None:
                self.host_crawl_delay[host] = float(crawl_delay)
            logger.info(f"Loaded robots.txt from {robots_url} (crawl-delay={self.host_crawl_delay.get(host)})")
        except requests.RequestException:
            logger.warning(f"Could not load robots.txt at {robots_url}; proceeding without robots rules for {host}.")
            self.robots_parsers[host] = parser
            self.robots_loaded[host] = False

    def _is_allowed_by_robots(self, url: str) -> bool:
        """Check whether a URL is allowed by robots.txt rules for its host."""
        host = urlparse(url).netloc
        self._load_robots_for_host(host)
        parser = self.robots_parsers.get(host)
        if not self.robots_loaded.get(host, False):
            return True
        return parser.can_fetch(self.user_agent, url)
        
    def _wait_for_host_politeness(self, host: str) -> None:
        """Wait until the host-specific politeness window has elapsed.

        Uses `Crawl-delay` from robots.txt when available, otherwise uses
        the configured minimum politeness delay.
        """
        elapsed = time.time() - self.last_request_time.get(host, 0.0)
        # Prefer explicit crawl-delay from robots.txt if available
        delay = self.host_crawl_delay.get(host, None)
        if delay is None:
            delay = self.politeness_delay_range[0]

        if elapsed < delay:
            to_wait = delay - elapsed
            logger.info(f"Waiting {to_wait:.1f}s for host {host} politeness...")
            time.sleep(to_wait)
    
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

    def _get_host(self, url: str) -> str:
        return urlparse(url).netloc
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of page content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_hash_for_url(self, url: str, known_hashes: Dict[str, str]) -> str:
        """Get the stored hash for a URL, or empty string if not found."""
        return known_hashes.get(url, "")
    
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
        host = self._get_host(url)

        # Ensure at least the host politeness window has passed
        self._wait_for_host_politeness(host)

        headers = {'User-Agent': self.user_agent}
        backoff = 1.0
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                # On HTTP error, raise for status to be handled below
                response.raise_for_status()
                # Record host last request time
                self.last_request_time[host] = time.time()
                # After successful request, add a small randomized additional wait
                extra = random.uniform(self.politeness_delay_range[0], self.politeness_delay_range[1])
                time.sleep(min(extra, 0.5))
                return response.text
            except requests.HTTPError as e:
                status = getattr(e.response, 'status_code', None)
                logger.warning(f"HTTP error fetching {url}: {status} (attempt {attempt})")
                # Retry on 429 or 5xx
                if status == 429 or (status is not None and 500 <= status < 600):
                    if attempt == max_retries:
                        logger.error(f"Max retries reached for {url}")
                        raise
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    raise
            except requests.RequestException as e:
                logger.error(f"Failed to fetch {url}: {e} (attempt {attempt})")
                if attempt == max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
                continue
    
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
    
    def crawl(self, start_url: str = None, known_hashes: Dict[str, str] = None) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Crawl the website starting from the base URL or a specific URL.
        
        Args:
            start_url: Optional specific URL to start from
            known_hashes: Optional dict of URL -> hash for incremental crawling.
                         Pages with matching hashes will be skipped.
            
        Returns:
            Tuple of (pages dict, updated_hashes dict)
            - pages: Dictionary mapping URLs to their text content (new/changed pages only)
            - updated_hashes: Dictionary mapping URLs to their SHA256 hashes (all crawled pages)
        """
        if start_url is None:
            start_url = self.base_url
        
        if known_hashes is None:
            known_hashes = {}

        if not self._is_allowed_by_robots(start_url):
            logger.warning(f"Start URL blocked by robots.txt: {start_url}")
            return {}
        
        crawl_start_time = time.time()
        pages = {}
        updated_hashes = {}  # Track all page hashes for incremental crawling
        # Distribute initial URL into host queue
        start_host = self._get_host(start_url)
        self.host_queues[start_host].append((start_url, 0))

        def any_queues_nonempty() -> bool:
            return any(q for q in self.host_queues.values())

        while any_queues_nonempty():
            # Check time limit
            elapsed_time = time.time() - crawl_start_time
            if elapsed_time > self.max_crawl_time:
                logger.warning(f"Crawl time limit ({self.max_crawl_time}s) exceeded. Stopping crawl.")
                break
            
            # Check page limit
            if len(pages) >= self.max_pages:
                logger.warning(f"Page limit ({self.max_pages}) reached. Stopping crawl.")
                break
            
            # Find a host queue eligible for fetching (respect per-host politeness)
            now = time.time()
            eligible_host = None
            earliest_time = None
            for host, queue in self.host_queues.items():
                if not queue:
                    continue
                last = self.last_request_time.get(host, 0.0)
                # Use explicit crawl-delay if present, otherwise use configured min_delay
                politeness = self.host_crawl_delay.get(host, self.politeness_delay_range[0])
                next_allowed = last + politeness
                if next_allowed <= now:
                    eligible_host = host
                    break
                if earliest_time is None or next_allowed < earliest_time:
                    earliest_time = next_allowed

            if eligible_host is None:
                # No host is ready; sleep until the earliest next_allowed (bounded small)
                if earliest_time is not None:
                    to_sleep = max(0.1, earliest_time - now)
                    time.sleep(to_sleep)
                    continue
                else:
                    break

            current_url, current_depth = self.host_queues[eligible_host].pop(0)
            
            # Skip if depth exceeds limit (prevents infinite exploration of fictitious resources)
            if current_depth > self.max_depth:
                logger.info(f"Skipping {current_url} (depth {current_depth} exceeds max depth {self.max_depth})")
                # Track the maximum depth reached for this host
                if eligible_host not in self.host_max_depth or current_depth > self.host_max_depth[eligible_host]:
                    self.host_max_depth[eligible_host] = current_depth
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
                
                # Compute hash for change detection
                content_hash = self._compute_hash(text)
                updated_hashes[current_url] = content_hash
                
                # Check if content has changed
                known_hash = self._get_hash_for_url(current_url, known_hashes)
                if known_hash == content_hash:
                    logger.info(f"Skipping {current_url} - content unchanged (hash match)")
                else:
                    # Content is new or changed - add to results
                    if known_hash:
                        logger.info(f"Updating {current_url} - content changed")
                    pages[current_url] = text
                
                # Extract and queue new links
                links = self._extract_links(html, current_url)
                for link in links:
                    if link not in self.visited_urls:
                        host = self._get_host(link)
                        # Avoid duplicate queued entries
                        if link not in [url for url, _ in self.host_queues[host]]:
                            self.host_queues[host].append((link, current_depth + 1))
                
            except requests.RequestException:
                logger.warning(f"Could not crawl {current_url}, skipping...")
                continue
        
        logger.info(f"Crawling complete. Found {len(pages)} new/updated pages. Total crawled: {len(updated_hashes)}. Time: {time.time() - crawl_start_time:.1f}s")
        return pages, updated_hashes
