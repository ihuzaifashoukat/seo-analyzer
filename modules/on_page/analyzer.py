from bs4 import BeautifulSoup
from ..base_module import SEOModule
from .text_utils import extract_visible_text
from .title_meta import check_title, check_meta_description
from .headings_links_images import check_headings, check_images, check_links
from .advanced import (
    analyze_keyword_placement,
    check_url_slug_quality,
    analyze_images_keywords,
    detect_breadcrumbs,
    detect_share_buttons,
    extract_content_dates,
    analyze_forms,
    )
from .social_misc import (
    check_content_stats,
    check_iframes,
    check_apple_touch_icon,
    check_script_and_css_files,
    check_strong_tags,
    check_open_graph,
    check_twitter_cards,
    check_seo_friendly_url,
    check_inline_css,
    check_deprecated_html_tags,
    check_flash_content,
    check_nested_tables,
    check_frameset,
)


class OnPageAnalyzer(SEOModule):
    """Analyzes on-page SEO elements of a given URL."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.title_min_len = self.config.get("title_min_length", 20)
        self.title_max_len = self.config.get("title_max_length", 70)
        self.desc_min_len = self.config.get("desc_min_length", 70)
        self.desc_max_len = self.config.get("desc_max_length", 160)
        self.content_min_words = self.config.get("content_min_words", 300)
        self.links_min_count = self.config.get("links_min_count", 5)
        self.active_check_limit = self.config.get("active_check_limit", 10)
        self.url_max_length = self.config.get("url_max_length", 100)
        self.url_max_depth = self.config.get("url_max_depth", 4)
        self.target_keywords = self.config.get("target_keywords", [])

        self.deprecated_tags = [
            "applet", "acronym", "bgsound", "dir", "frame", "frameset",
            "noframes", "isindex", "listing", "xmp", "nextid", "plaintext",
            "rb", "rtc", "strike", "basefont", "big", "blink", "center",
            "font", "marquee", "multicol", "nobr", "spacer", "tt"
        ]

    def analyze(self, url: str) -> dict:
        results = {"on_page_analysis_status": "pending", "url": url, "isLoaded": False}
        soup = self.fetch_html(url)
        if not soup:
            results["on_page_analysis_status"] = "failed_to_fetch_html"
            results["error_message"] = f"Could not retrieve or parse HTML from {url}"
            return {self.module_name: results}

        results["isLoaded"] = True
        visible_text = extract_visible_text(soup)

        # Core checks
        results.update(check_title(soup, self.title_min_len, self.title_max_len, self.target_keywords))
        results.update(check_meta_description(soup, self.desc_min_len, self.desc_max_len, self.target_keywords))
        primary_kw = self.target_keywords[0] if self.target_keywords else None
        results.update(check_headings(soup, primary_kw))
        results.update(check_images(soup, url, self.headers, self.global_config.get("request_timeout", 10), self.active_check_limit))
        results.update(check_links(soup, url, self.headers, self.global_config.get("request_timeout", 10), self.active_check_limit, self.links_min_count))
        results.update(check_content_stats(visible_text, soup, self.content_min_words))
        results.update(check_iframes(soup))
        results.update(check_apple_touch_icon(soup, url))
        results.update(check_script_and_css_files(soup))
        results.update(check_strong_tags(soup))
        results.update(check_open_graph(soup))
        results.update(check_twitter_cards(soup))

        # Additional checks
        results.update(check_seo_friendly_url(url, self.url_max_length, self.url_max_depth))
        results.update(check_inline_css(soup))
        results.update(check_deprecated_html_tags(soup, self.deprecated_tags))
        results.update(check_flash_content(soup))
        results.update(check_nested_tables(soup))
        results.update(check_frameset(soup))

        # Advanced keyword placement & URL slug quality
        results.update(analyze_keyword_placement(soup, visible_text, self.target_keywords))
        results.update(check_url_slug_quality(url, primary_kw))
        results.update(analyze_images_keywords(soup, primary_kw))
        results.update(detect_breadcrumbs(soup))
        results.update(detect_share_buttons(soup))
        results.update(extract_content_dates(soup, self.head, url, self.global_config.get("request_timeout", 10)))
        results.update(analyze_forms(soup))

        results["on_page_analysis_status"] = "completed"
        # Provide optional text sample and simple hash for site-wide duplicate detection
        try:
            sample = visible_text[:1500]
            import hashlib
            results["visibleTextSample"] = sample
            results["visibleTextHash"] = hashlib.md5(sample.encode('utf-8', errors='ignore')).hexdigest()
        except Exception:
            pass
        return {self.module_name: results}
