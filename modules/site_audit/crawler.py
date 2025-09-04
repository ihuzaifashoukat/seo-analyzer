from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Set, List, Tuple, Optional
from urllib.parse import urlparse, urljoin, urldefrag
import time
import re
from bs4 import BeautifulSoup
import urllib.robotparser as robotparser
import requests


def _normalize_url(base: str, href: str) -> Optional[str]:
    if not href:
        return None
    href = href.strip()
    if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
        return None
    abs_url = urljoin(base, href)
    # drop fragments
    abs_url, _ = urldefrag(abs_url)
    return abs_url


def _is_html_response(resp: requests.Response) -> bool:
    ctype = resp.headers.get('Content-Type', '')
    return 'text/html' in ctype or 'application/xhtml+xml' in ctype


@dataclass
class CrawlConfig:
    max_pages: int = 100
    max_depth: int = 3
    rate_limit_rps: float = 0.0
    respect_robots: bool = True
    same_domain_only: bool = True
    include_subdomains: bool = False
    user_agent: str = 'Mozilla/5.0 (compatible; SEOAnalyzer/1.0)'
    include_paths: Optional[List[str]] = None   # list of path prefixes or regex
    exclude_paths: Optional[List[str]] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    extra_headers: Optional[dict] = None
    render_js: bool = False


class SiteCrawler:
    """
    Lightweight site crawler that discovers internal URLs to audit.
    """

    def __init__(self, start_url: str, session: Optional[requests.Session] = None, config: Optional[dict] = None):
        self.start_url = start_url
        self.parsed_start = urlparse(start_url)
        self.base_origin = f"{self.parsed_start.scheme}://{self.parsed_start.netloc}"

        cfg = config or {}
        self.cfg = CrawlConfig(
            max_pages=int(cfg.get('max_pages', 100)),
            max_depth=int(cfg.get('max_depth', 3)),
            rate_limit_rps=float(cfg.get('rate_limit_rps', 0.0)),
            respect_robots=bool(cfg.get('respect_robots', True)),
            same_domain_only=bool(cfg.get('same_domain_only', True)),
            include_subdomains=bool(cfg.get('include_subdomains', False)),
            user_agent=str(cfg.get('user_agent', 'Mozilla/5.0 (compatible; SEOAnalyzer/1.0)')),
            include_paths=cfg.get('include_paths'),
            exclude_paths=cfg.get('exclude_paths'),
            auth_username=cfg.get('auth_username'),
            auth_password=cfg.get('auth_password'),
            extra_headers=cfg.get('extra_headers'),
            render_js=bool(cfg.get('render_js', False)),
        )

        self.session = session or requests.Session()
        self.session.headers.setdefault('User-Agent', self.cfg.user_agent)
        if self.cfg.extra_headers:
            self.session.headers.update(self.cfg.extra_headers)
        if self.cfg.auth_username and self.cfg.auth_password:
            self.session.auth = (self.cfg.auth_username, self.cfg.auth_password)

        self.rp = None
        if self.cfg.respect_robots:
            self.rp = robotparser.RobotFileParser()
            self.rp.set_url(urljoin(self.base_origin, '/robots.txt'))
            try:
                self.rp.read()
            except Exception:
                self.rp = None

        self._last_request_ts = 0.0

    def _allowed_by_robots(self, url: str) -> bool:
        if not self.rp:
            return True
        try:
            return self.rp.can_fetch(self.cfg.user_agent, url)
        except Exception:
            return True

    def _domain_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if self.cfg.same_domain_only:
            if self.cfg.include_subdomains:
                return parsed.netloc.endswith(self.parsed_start.netloc.split(':')[0])
            return parsed.netloc == self.parsed_start.netloc
        return True

    def _path_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path or '/'
        inc = self.cfg.include_paths
        exc = self.cfg.exclude_paths
        allowed = True
        if inc:
            allowed = any((path.startswith(p) if not p.startswith('re:') else re.search(p[3:], path)) for p in inc)
        if exc and allowed:
            if any((path.startswith(p) if not p.startswith('re:') else re.search(p[3:], path)) for p in exc):
                allowed = False
        return allowed

    def _rate_limit(self):
        if self.cfg.rate_limit_rps and self.cfg.rate_limit_rps > 0:
            gap = 1.0 / self.cfg.rate_limit_rps
            now = time.time()
            sleep_for = self._last_request_ts + gap - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last_request_ts = time.time()

    def crawl(self) -> List[str]:
        queue: List[Tuple[str, int]] = [(self.start_url, 0)]
        visited: Set[str] = set()
        results: List[str] = []

        while queue and len(results) < self.cfg.max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            if depth > self.cfg.max_depth:
                continue
            if not self._domain_allowed(url):
                continue
            if not self._allowed_by_robots(url):
                continue

            try:
                self._rate_limit()
                if self.cfg.render_js:
                    try:
                        from .render import render_html
                        html = render_html(url, user_agent=self.cfg.user_agent)
                        if not html:
                            resp = self.session.get(url, timeout=10, allow_redirects=True)
                            content = resp.content if resp and resp.status_code < 400 else None
                        else:
                            content = html.encode('utf-8')
                            resp = None
                    except Exception:
                        resp = self.session.get(url, timeout=10, allow_redirects=True)
                        content = resp.content if resp and resp.status_code < 400 else None
                else:
                    resp = self.session.get(url, timeout=10, allow_redirects=True)
                    content = resp.content if resp and resp.status_code < 400 else None
            except requests.RequestException:
                continue

            if resp is not None:
                if not _is_html_response(resp) or resp.status_code >= 400:
                    continue
                content = resp.content

            # Path filters
            if not self._path_allowed(url):
                continue
            results.append(url)

            try:
                soup = BeautifulSoup(content, 'html.parser')
            except Exception:
                continue

            for a in soup.find_all('a', href=True):
                norm = _normalize_url(url, a['href'])
                if not norm:
                    continue
                if norm in visited:
                    continue
                if not self._domain_allowed(norm):
                    continue
                queue.append((norm, depth + 1))

            if len(results) >= self.cfg.max_pages:
                break

        return results
