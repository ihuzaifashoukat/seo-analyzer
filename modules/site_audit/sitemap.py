from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import requests
from xml.etree import ElementTree as ET


def _fetch(url: str, timeout: int = 10) -> Tuple[Optional[requests.Response], Optional[str]]:
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        return resp, None
    except requests.RequestException as e:
        return None, str(e)


def parse_sitemap(base_domain_url: str, robots_txt_content: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
    """
    Attempts to find and parse sitemap(s), returning discovered URLs and fetch/format errors.
    """
    candidate_urls: List[str] = []
    if robots_txt_content:
        for line in robots_txt_content.splitlines():
            if line.strip().lower().startswith("sitemap:"):
                candidate_urls.append(line.strip().split(":", 1)[1].strip())
    if not candidate_urls:
        candidate_urls = [
            urljoin(base_domain_url, "/sitemap.xml"),
            urljoin(base_domain_url, "/sitemap_index.xml"),
        ]

    urls: List[str] = []
    errors: List[Dict[str, str]] = []
    parsed_any = False
    for s_url in candidate_urls:
        resp, err = _fetch(s_url, timeout=timeout)
        if not resp or resp.status_code != 200:
            if err:
                errors.append({"sitemap": s_url, "error": err})
            else:
                errors.append({"sitemap": s_url, "error": f"http_{resp.status_code if resp else 'fetch_error'}"})
            continue
        try:
            root = ET.fromstring(resp.content)
        except Exception as e:
            errors.append({"sitemap": s_url, "error": f"invalid_xml: {e}"})
            continue
        parsed_any = True
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        if root.tag.endswith('sitemapindex'):
            for sm in root.findall(f"{ns}sitemap"):
                loc = sm.find(f"{ns}loc")
                if loc is not None and loc.text:
                    sub_resp, sub_err = _fetch(loc.text.strip(), timeout=timeout)
                    if not sub_resp or sub_resp.status_code != 200:
                        errors.append({"sitemap": loc.text.strip(), "error": f"http_{sub_resp.status_code if sub_resp else 'fetch_error'}"})
                        continue
                    try:
                        sub_root = ET.fromstring(sub_resp.content)
                        for url_tag in sub_root.findall(f"{ns}url"):
                            loc2 = url_tag.find(f"{ns}loc")
                            if loc2 is not None and loc2.text:
                                urls.append(loc2.text.strip())
                    except Exception as se:
                        errors.append({"sitemap": loc.text.strip(), "error": f"invalid_xml: {se}"})
        else:
            for url_tag in root.findall(f"{ns}url"):
                loc = url_tag.find(f"{ns}loc")
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())

    return {
        "sitemapsChecked": candidate_urls,
        "parsedAnySitemap": parsed_any,
        "sitemapUrls": list(dict.fromkeys(urls)),
        "sitemapErrors": errors,
    }


def probe_url_statuses(urls: List[str], timeout: int = 10) -> Dict[str, Any]:
    buckets = {
        'ok_200': [],
        'redirect_3xx': [],
        'client_error_4xx': [],
        'forbidden_403': [],
        'server_error_5xx': [],
        'timeout': [],
        'error': [],
    }
    for u in urls:
        try:
            resp = requests.head(u, timeout=timeout, allow_redirects=False)
            if resp is None:
                buckets['error'].append(u)
                continue
            sc = resp.status_code
            if sc == 200:
                buckets['ok_200'].append(u)
            elif 300 <= sc < 400:
                buckets['redirect_3xx'].append(u)
            elif sc == 403:
                buckets['forbidden_403'].append(u)
            elif 400 <= sc < 500:
                buckets['client_error_4xx'].append(u)
            elif 500 <= sc < 600:
                buckets['server_error_5xx'].append(u)
            else:
                buckets['error'].append(u)
        except requests.Timeout:
            buckets['timeout'].append(u)
        except requests.RequestException:
            buckets['error'].append(u)
    return buckets

