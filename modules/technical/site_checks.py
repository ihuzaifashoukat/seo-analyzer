from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

def check_https_usage(parsed_url: urlparse) -> dict:
    return {"hasHttps": parsed_url.scheme == "https"}

def check_robots_txt(base_domain_url: str, make_request_fn, headers: dict, timeout: int) -> dict:
    robots_url = urljoin(base_domain_url, "/robots.txt")
    content = None; status = "not_found"; sitemap_urls = []; disallow_directives = []
    has_disallow_all_for_google = False; has_disallow_all_general = False
    current_user_agent = "*"
    response, _ = make_request_fn(robots_url, headers=headers, timeout=timeout)
    if response and response.status_code == 200:
        content = response.text; status = "found"
        for line in content.splitlines():
            line_strip = line.strip()
            if not line_strip or line_strip.startswith("#"):
                continue
            line_lower = line_strip.lower()
            if line_lower.startswith("user-agent:"):
                current_user_agent = line_strip.split(":", 1)[1].strip().lower()
            elif line_lower.startswith("sitemap:"):
                sitemap_urls.append(line_strip.split(":", 1)[1].strip())
            elif line_lower.startswith("disallow:"):
                disallow_path = line_strip.split(":", 1)[1].strip()
                disallow_directives.append({"user_agent": current_user_agent, "path": disallow_path})
                if disallow_path == "/":
                    if current_user_agent == "*":
                        has_disallow_all_general = True
                    if "googlebot" in current_user_agent:
                        has_disallow_all_for_google = True
    elif response is None:
        status = "error_accessing"
    return {"robotsTxtStatus": status, "robotsTxtSitemapUrls": sitemap_urls,
            "robotsTxtDisallowDirectives": disallow_directives,
            "robotsTxtDisallowsAllGeneral": has_disallow_all_general,
            "robotsTxtDisallowsAllForGoogle": has_disallow_all_for_google,
            "robots_txt_content_full": content}

def check_sitemap_xml(base_domain_url: str, robots_txt_content: str | None, make_request_fn, headers: dict, timeout: int) -> dict:
    sitemap_urls_to_check = []
    if robots_txt_content:
        for line in robots_txt_content.splitlines():
            if line.strip().lower().startswith("sitemap:"):
                sitemap_urls_to_check.append(line.strip().split(":", 1)[1].strip())
    if not sitemap_urls_to_check:
        sitemap_urls_to_check.extend([urljoin(base_domain_url, "/sitemap.xml"), urljoin(base_domain_url, "/sitemap_index.xml")])
    has_sitemap = False; found_sitemap_url = None
    for s_url in sitemap_urls_to_check:
        response, _ = make_request_fn(s_url, headers=headers, timeout=timeout, method="head")
        if response and response.status_code in (200, 301, 302):
            has_sitemap = True; found_sitemap_url = s_url; break
    return {"hasSitemap": has_sitemap, "sitemapUrlDetected": found_sitemap_url}

def check_url_redirects(url: str, make_request_fn, headers: dict, timeout: int) -> dict:
    history = []; status_codes = []
    response, _ = make_request_fn(url, headers=headers, timeout=timeout, allow_redirects=True)
    if response:
        if response.history:
            for r_hist in response.history:
                history.append({"url": r_hist.url, "status_code": r_hist.status_code})
                status_codes.append(r_hist.status_code)
        history.append({"url": response.url, "status_code": response.status_code})
        status_codes.append(response.status_code)
    else:
        history.append({"url": url, "error": "Request failed"})
    return {"redirectHistory": history, "hasRedirects": len(history) > 1 and any(s // 100 == 3 for s in status_codes)}

def check_custom_404_page(base_url: str, make_request_fn, headers: dict, timeout: int) -> dict:
    from datetime import datetime
    url_404 = urljoin(base_url, f"/non_existent_page_{datetime.now().timestamp()}.html")
    is_custom = False; status = None; length = 0
    response, _ = make_request_fn(url_404, headers=headers, timeout=timeout, allow_redirects=False)
    if response:
        status = response.status_code; length = len(response.content); is_custom = status == 404 and length > 1024
    return {"custom404PageTestStatus": status, "custom404PageLength": length, "hasCustom404PageHeuristic": is_custom}

def check_directory_browsing(base_url: str, make_request_fn, headers: dict, timeout: int) -> dict:
    paths = []
    for d in ["/css/", "/js/", "/images/", "/uploads/"]:
        response, _ = make_request_fn(urljoin(base_url, d), headers=headers, timeout=timeout)
        if response and response.status_code == 200:
            s = BeautifulSoup(response.content, 'html.parser')
            if s.title and "index of /" in s.title.string.lower():
                paths.append(d)
    return {"directoryBrowsingEnabledPaths": paths, "hasDirectoryBrowsingEnabled": bool(paths)}

def check_spf_records(domain: str) -> dict:
    has_spf = False; records = []
    try:
        import dns.resolver
        for rdata in dns.resolver.resolve(domain, 'TXT'):
            for txt in rdata.strings:
                if txt.decode().lower().startswith("v=spf1"):
                    has_spf = True; records.append(txt.decode())
        status = "completed"
    except ImportError:
        status = "skipped_dnspython_not_installed"
    except Exception:
        status = "error_dns_lookup"
    return {"spfRecordTestStatus": status, "hasSpfRecord": has_spf, "spfRecords": records}

def check_ads_txt(base_url: str, make_request_fn, headers: dict, timeout: int) -> dict:
    has_ads = False; content = None
    response, _ = make_request_fn(urljoin(base_url, "/ads.txt"), headers=headers, timeout=timeout)
    if response and response.status_code == 200:
        has_ads = True; content = response.text[:1000]
    return {"hasAdsTxt": has_ads, "adsTxtPreview": content}

def check_cdn_headers(headers: requests.structures.CaseInsensitiveDict) -> dict:
    cdns = {
        "Cloudflare": any(h.lower() == "cf-ray" for h in headers) or "cloudflare" in headers.get("Server","").lower(),
        "Akamai": any(h.lower().startswith("x-akamai") for h in headers) or "akamaighost" in headers.get("Server","").lower(),
        "CloudFront": "cloudfront" in headers.get("Via","") or "cloudfront" in headers.get("X-Amz-Cf-Id","") or "cloudfront" in headers.get("Server","").lower(),
        "Fastly": "fastly" in headers.get("X-Served-By","") or "fastly" in headers.get("Server","").lower(),
        "Google": "gws" in headers.get("Server","").lower() or "google" in headers.get("Server","").lower(),
    }
    used = [cdn for cdn, present in cdns.items() if present]
    return {"usesCdn": bool(used), "detectedCdns": used}

