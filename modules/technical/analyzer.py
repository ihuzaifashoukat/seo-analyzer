from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ..base_module import SEOModule
from .network import make_request
from .html_core import (
    check_doctype,
    check_character_encoding,
    check_viewport_meta,
    check_amp,
    check_language_and_hreflang,
    check_canonical_tag,
    check_meta_robots,
    check_structured_data,
)
from .metrics import (
    check_google_analytics,
    check_mobile_friendliness_heuristics,
    check_mixed_content,
    check_plaintext_emails,
    check_meta_refresh,
    check_modern_image_formats_html,
)
from .site_checks import (
    check_https_usage,
    check_robots_txt,
    check_sitemap_xml,
    check_url_redirects,
    check_custom_404_page,
    check_directory_browsing,
    check_spf_records,
    check_ads_txt,
    check_cdn_headers,
)
from .llms_txt import (
    check_llms_txt,
)
from .assets import (
    analyze_asset_caching,
    analyze_asset_minification,
)
from .performance_api import fetch_pagespeed_insights


class TechnicalSEOAnalyzer(SEOModule):
    """Analyzes technical SEO aspects of a given URL and its domain."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.tech_config = self.config
        self.request_timeout = self.global_config.get("request_timeout", 10)
        self.enable_psi = bool(self.tech_config.get("enable_pagespeed_insights", False))
        self.psi_api_key = self.tech_config.get("psi_api_key")
        self.psi_strategy = self.tech_config.get("psi_strategy", "desktop")

    def analyze(self, url: str) -> dict:
        results = {"technical_seo_status": "pending", "url_analyzed": url}

        main_response, ttfb = make_request(url, headers=self.headers, timeout=self.request_timeout, allow_redirects=True)
        soup = None
        raw_html_content = b""
        if main_response:
            results["httpStatusCode"] = main_response.status_code
            raw_html_content = main_response.content
            results["htmlPageSize"] = len(raw_html_content)
            results["htmlCompressionGzipTest"] = main_response.headers.get("Content-Encoding", "").lower()
            results["xRobotsTag"] = main_response.headers.get("X-Robots-Tag")
            http_version_str = "Unknown"
            if hasattr(main_response.raw, 'version'):
                if main_response.raw.version == 10: http_version_str = "HTTP/1.0"
                elif main_response.raw.version == 11: http_version_str = "HTTP/1.1"
                elif main_response.raw.version == 20: http_version_str = "HTTP/2.0"
            results["httpVersion"] = http_version_str
            results["hstsHeader"] = main_response.headers.get("Strict-Transport-Security")
            results["serverSignature"] = main_response.headers.get("Server")
            results["pageCacheHeaders"] = {
                "Cache-Control": main_response.headers.get("Cache-Control"),
                "Expires": main_response.headers.get("Expires"),
                "Pragma": main_response.headers.get("Pragma"),
                "ETag": main_response.headers.get("ETag"),
                "Last-Modified": main_response.headers.get("Last-Modified"),
            }
            results["cdnUsageHeuristic"] = check_cdn_headers(main_response.headers)
            results["siteLoadingSpeedTest"] = {"ttfb_seconds": round(ttfb, 3) if ttfb is not None else None, "details": "TTFB only. Full speed test requires browser-based tools."}
            try:
                soup = BeautifulSoup(raw_html_content, 'html.parser')
            except Exception as e:
                results["soup_parsing_error"] = str(e)
        else:
            results["initial_request_failed"] = True
            results["siteLoadingSpeedTest"] = {"ttfb_seconds": None, "details": "Initial request failed."}
            return {self.module_name: results}

        parsed_url = urlparse(url)
        base_domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        domain_name = parsed_url.netloc

        if soup:
            results.update(check_doctype(soup))
            results.update(check_character_encoding(soup))
            results.update(check_viewport_meta(soup))
            results.update(check_amp(soup, base_domain_url))
            results.update(check_language_and_hreflang(soup, base_domain_url))
            results.update(check_canonical_tag(soup, url))
            results.update(check_meta_robots(soup))
            results.update(check_structured_data(soup))
            results.update(check_google_analytics(str(soup)))
            results.update(check_mobile_friendliness_heuristics(soup, results.get("viewport", False)))
            results.update(check_mixed_content(soup, parsed_url.scheme))
            results.update(check_plaintext_emails(str(soup)))
            results.update(check_meta_refresh(soup))
            results["domSize"] = len(soup.find_all(True))
            results.update(super()._check_favicon(soup, base_domain_url))
            results.update(check_modern_image_formats_html(soup))

            # Canonical target probe (HEAD)
            try:
                can_url = results.get("canonicalUrl")
                if can_url:
                    probe = {"status": "skipped"}
                    # No redirects to classify the target itself
                    resp, _ = make_request(can_url, headers=self.headers, timeout=self.request_timeout, method="head", allow_redirects=False)
                    if resp is not None:
                        sc = resp.status_code
                        probe.update({
                            "status": "ok",
                            "status_code": sc,
                            "is_redirect": 300 <= sc < 400,
                            "location": resp.headers.get("Location"),
                        })
                    else:
                        probe.update({"status": "error"})
                    results["canonicalTargetProbe"] = probe
            except Exception as _e:
                results["canonicalTargetProbe"] = {"status": "error"}

        # Asset Caching & Minification
        limits = {
            'max_images_to_check_cache': self.tech_config.get('max_images_to_check_cache', 10),
            'max_js_to_check_cache': self.tech_config.get('max_js_to_check_cache', 10),
            'max_css_to_check_cache': self.tech_config.get('max_css_to_check_cache', 10),
        }
        results.update(analyze_asset_caching(soup, base_domain_url, 'image', make_request, self.headers, self.request_timeout, limits))
        results.update(analyze_asset_caching(soup, base_domain_url, 'javascript', make_request, self.headers, self.request_timeout, limits))
        results.update(analyze_asset_caching(soup, base_domain_url, 'css', make_request, self.headers, self.request_timeout, limits))

        results.update(analyze_asset_minification(soup, base_domain_url, 'javascript', make_request, self.headers, self.request_timeout, self.tech_config))
        results.update(analyze_asset_minification(soup, base_domain_url, 'css', make_request, self.headers, self.request_timeout, self.tech_config))

        # Optional PageSpeed Insights (Lighthouse/CrUX)
        if self.enable_psi:
            psi = fetch_pagespeed_insights(url, api_key=self.psi_api_key, strategy=self.psi_strategy, timeout=min(30, self.request_timeout + 20))
            results["pageSpeedInsights"] = psi

        # Site-level checks
        results.update(check_https_usage(parsed_url))
        robots_check_result = check_robots_txt(base_domain_url, make_request, self.headers, self.request_timeout)
        results.update(robots_check_result)
        results.update(check_sitemap_xml(base_domain_url, robots_check_result.get("robots_txt_content_full"), make_request, self.headers, self.request_timeout))
        results["domainLength"] = len(domain_name)
        results.update(check_url_redirects(url, make_request, self.headers, self.request_timeout))
        results.update(check_custom_404_page(base_domain_url, make_request, self.headers, self.request_timeout))
        results.update(check_directory_browsing(base_domain_url, make_request, self.headers, self.request_timeout))
        results.update(check_spf_records(domain_name))
        results.update(check_ads_txt(base_domain_url, make_request, self.headers, self.request_timeout))
        # LLMs/AI crawler guidance file (llms.txt / ai.txt)
        results.update(check_llms_txt(base_domain_url, make_request, self.headers, self.request_timeout))

        results["technical_seo_status"] = "completed"
        return {self.module_name: results}
