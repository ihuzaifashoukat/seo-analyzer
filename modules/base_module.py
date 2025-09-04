# modules/base_module.py
from abc import ABC, abstractmethod
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except Exception:
    # Fallback shim if urllib3 Retry isn't importable in environment
    Retry = None
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class SEOModule(ABC):
    """
    Abstract base class for all SEO analysis modules.
    Each module will implement its own 'analyze' method.
    """

    def __init__(self, config=None): # Add config to constructor
        self.module_name = self.__class__.__name__
        self.config = config if config else {} # Store module-specific config
        self.global_config = self.config.get("Global", {}) # Get global config if passed down

        # Headers and HTTP session with retries
        default_ua = self.global_config.get(
            "user_agent",
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        accept_lang = self.global_config.get("accept_language", "en-US,en;q=0.8")
        self.headers = {
            'User-Agent': default_ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': accept_lang,
        }

        self.session = requests.Session()
        # Configure retries if possible
        retries_total = int(self.global_config.get("http_retries_total", 2))
        backoff = float(self.global_config.get("http_backoff_factor", 0.2))
        status_forcelist = self.global_config.get("http_status_forcelist", [429, 500, 502, 503, 504])
        allowed_methods = self.global_config.get("http_allowed_retry_methods", ["HEAD", "GET", "OPTIONS"])
        if Retry is not None and retries_total > 0:
            retry_cfg = Retry(
                total=retries_total,
                connect=retries_total,
                read=retries_total,
                backoff_factor=backoff,
                status_forcelist=status_forcelist,
                allowed_methods=set(m.upper() for m in allowed_methods),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_cfg)
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        # Update session headers
        self.session.headers.update(self.headers)
        # Potentially add common configuration here, e.g., API keys if shared

    @abstractmethod
    def analyze(self, url: str) -> dict:
        """
        Analyzes the given URL for specific SEO attributes related to the module.

        Args:
            url (str): The URL to analyze.

        Returns:
            dict: A dictionary containing the analysis results for this module.
                  Keys should be descriptive of the SEO attribute being checked.
        """
        pass

    def fetch_html(self, url: str) -> BeautifulSoup | None:
        """
        Fetches the HTML content of a URL and returns a BeautifulSoup object.

        Args:
            url (str): The URL to fetch.

        Returns:
            BeautifulSoup | None: A BeautifulSoup object if successful, None otherwise.
        """
        timeout = self.global_config.get("request_timeout", 10) # Use configured timeout
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            if self.global_config.get("debug"):
                print(f"Error fetching URL {url} in {self.module_name}: {e}")
            return None
        except Exception as e:
            if self.global_config.get("debug"):
                print(f"An unexpected error occurred while fetching {url} in {self.module_name}: {e}")
            return None

    def request(self, method: str, url: str, **kwargs):
        """
        Thin wrapper around session.request adding default timeout and returning (response, elapsed_seconds).
        """
        timeout = kwargs.pop("timeout", self.global_config.get("request_timeout", 10))
        try:
            from datetime import datetime
            start = datetime.now()
            resp = self.session.request(method=method, url=url, timeout=timeout, **kwargs)
            elapsed = (datetime.now() - start).total_seconds()
            return resp, elapsed
        except requests.exceptions.RequestException as e:
            if self.global_config.get("debug"):
                print(f"Request error for {url} in {self.module_name}: {e}")
            return None, None

    def head(self, url: str, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def get_module_name(self) -> str:
        """Returns the name of the module."""
        return self.module_name

    def _check_favicon(self, soup: BeautifulSoup, base_url: str) -> dict:
        """
        Checks for the presence of a favicon link.
        This is a common utility that can be used by multiple modules.
        """
        favicon_link_url = None
        # Common rel values for favicons
        possible_rels = ["icon", "shortcut icon", "apple-touch-icon"]
        
        for rel_val in possible_rels:
            # Try with specific rel value
            tag = soup.find("link", rel=rel_val, href=True)
            if tag:
                favicon_link_url = urljoin(base_url, tag["href"])
                break
            # Try with rel as a list containing the value (some parsers might do this)
            tag = soup.find("link", rel=lambda r: r and rel_val in r, href=True)
            if tag:
                favicon_link_url = urljoin(base_url, tag["href"])
                break
        
        # Fallback: check for /favicon.ico (less reliable without actual request, but indicates intent)
        # For this base method, we only check the link declaration.
        # Actual fetching of favicon.ico could be a separate, more intensive check.
        if not favicon_link_url:
            # Check if a default /favicon.ico is linked, even if not explicitly with rel="icon"
            default_favicon_tag = soup.find("link", href="/favicon.ico")
            if default_favicon_tag:
                 favicon_link_url = urljoin(base_url, "/favicon.ico")
            # else:
                # parsed_base_url = urlparse(base_url)
                # potential_favicon_url = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}/favicon.ico"
                # This would require an actual request to confirm, so we omit it from simple link check.

        status = "detected" if favicon_link_url else "not_detected"
        recommendation = "A favicon helps with brand recognition in browser tabs and bookmarks." if status == "not_detected" else "Favicon link detected."
        
        return {
            "favicon_url_detected": favicon_link_url,
            "favicon_status": status,
            "favicon_recommendation": recommendation
        }


if __name__ == '__main__':
    # This part is for testing or direct execution if needed,
    # but modules are typically used by the main analyzer.
    print("This is the base SEOModule class. It should be subclassed by specific analyzer modules.")
