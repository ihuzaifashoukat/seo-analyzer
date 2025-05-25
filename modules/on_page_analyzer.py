# modules/on_page_analyzer.py
from urllib.parse import urlparse, urljoin, unquote
from bs4 import BeautifulSoup, Comment
from collections import Counter
import re
import requests

from .base_module import SEOModule

class OnPageAnalyzer(SEOModule):
    """
    Analyzes on-page SEO elements of a given URL.
    """

    def __init__(self, config=None):
        super().__init__(config=config) # Pass config to base
        # Default thresholds (can be overridden by config)
        self.title_min_len = self.config.get("title_min_length", 20)
        self.title_max_len = self.config.get("title_max_length", 70)
        self.desc_min_len = self.config.get("desc_min_length", 70)
        self.desc_max_len = self.config.get("desc_max_length", 160)
        self.content_min_words = self.config.get("content_min_words", 300)
        self.links_min_count = self.config.get("links_min_count", 5)
        self.active_check_limit = self.config.get("active_check_limit", 10)
        self.url_max_length = self.config.get("url_max_length", 100) # SEO friendly URL length
        self.url_max_depth = self.config.get("url_max_depth", 4) # SEO friendly URL depth

        self.deprecated_tags = [
            "applet", "acronym", "bgsound", "dir", "frame", "frameset", 
            "noframes", "isindex", "listing", "xmp", "nextid", "plaintext",
            "rb", "rtc", "strike", "basefont", "big", "blink", "center", 
            "font", "marquee", "multicol", "nobr", "spacer", "tt"
        ]


    def analyze(self, url: str) -> dict:
        results = {
            "on_page_analysis_status": "pending",
            "url": url,
            "isLoaded": False
        }
        soup = self.fetch_html(url)

        if not soup:
            results["on_page_analysis_status"] = "failed_to_fetch_html"
            results["error_message"] = f"Could not retrieve or parse HTML from {url}"
            return {self.module_name: results}
        
        results["isLoaded"] = True

        text_soup = BeautifulSoup(str(soup), 'html.parser')
        for element in text_soup(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
            element.decompose()
        for comment in text_soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        page_text_content = text_soup.get_text(separator=" ", strip=True)

        results.update(self._check_title(soup)) # Removed url param, not needed
        results.update(self._check_meta_description(soup))
        results.update(self._check_headings(soup))
        results.update(self._check_images(soup, url))
        results.update(self._check_links(soup, url))
        results.update(self._check_content_stats(page_text_content, soup))
        results.update(self._check_iframes(soup)) # isNotIframe, iframes count
        results.update(self._check_apple_touch_icon(soup, url))
        results.update(self._check_script_and_css_files(soup))
        results.update(self._check_strong_tags(soup))
        results.update(self._check_open_graph(soup))
        results.update(self._check_twitter_cards(soup))
        
        # New tests from the list
        results.update(self._check_seo_friendly_url(url))
        results.update(self._check_inline_css(soup))
        results.update(self._check_deprecated_html_tags(soup))
        results.update(self._check_flash_content(soup))
        results.update(self._check_nested_tables(soup))
        results.update(self._check_frameset(soup))
        # Favicon is in base, but let's ensure it's called if not covered by TechnicalSEO
        # results.update(super()._check_favicon(soup, url)) # Already called in previous version, ensure it's still there if needed

        results["on_page_analysis_status"] = "completed"
        return {self.module_name: results}

    def _check_title(self, soup: BeautifulSoup) -> dict: # Removed url param
        title_tag = soup.find("title")
        title_text = title_tag.string.strip() if title_tag and title_tag.string else None
        title_length = len(title_text) if title_text else 0
        
        status = "good"
        if not title_text:
            status = "missing"
        elif title_length < self.title_min_len:
            status = "too_short"
        elif title_length > self.title_max_len:
            status = "too_long"

        duplicate_words_count = 0
        if title_text:
            words = re.findall(r'\b\w+\b', title_text.lower())
            counts = Counter(words)
            duplicate_words_count = sum(1 for word, count in counts.items() if count > 1 and len(word) > 2)

        return {
            "title": title_text,
            "isTitle": bool(title_text),
            "titleLength": title_length,
            "isTitleEnoughLong": status == "good" if title_text else False,
            "titleDuplicateWords": duplicate_words_count
        }

    def _check_meta_description(self, soup: BeautifulSoup) -> dict:
        meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        meta_desc_text = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None
        meta_desc_length = len(meta_desc_text) if meta_desc_text else 0

        status = "good"
        if not meta_desc_text:
            status = "missing"
        elif meta_desc_length < self.desc_min_len:
            status = "too_short"
        elif meta_desc_length > self.desc_max_len:
            status = "too_long"
            
        return {
            "metaDescription": meta_desc_text,
            "isMetaDescription": bool(meta_desc_text),
            "descriptionLength": meta_desc_length,
            "isMetaDescriptionEnoughLong": status == "good" if meta_desc_text else False,
        }

    def _check_headings(self, soup: BeautifulSoup) -> dict:
        # This is "Heading Tags Test"
        headings_data = {"h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}
        for i in range(1, 7):
            for h_tag in soup.find_all(f"h{i}"):
                headings_data[f"h{i}"].append(h_tag.get_text(strip=True))
        
        h1_content_list = headings_data["h1"]
        h1_count = len(h1_content_list)
        
        return {
            "isH1": h1_count > 0,
            "h1": h1_content_list, # Return list of H1s
            "h1Count": h1_count,
            "isH1OnlyOne": h1_count == 1,
            "isH2": len(headings_data["h2"]) > 0,
            "h2": headings_data["h2"], "h3": headings_data["h3"], "h4": headings_data["h4"], 
            "h5": headings_data["h5"], "h6": headings_data["h6"],
            "h2Count": len(headings_data["h2"]), "h3Count": len(headings_data["h3"]), 
            "h4Count": len(headings_data["h4"]), "h5Count": len(headings_data["h5"]), 
            "h6Count": len(headings_data["h6"]),
        }

    def _check_images(self, soup: BeautifulSoup, base_url: str) -> dict:
        # Covers "Image Alt Test", "Responsive Image Test" (partially by checking for common patterns), "Image Aspect Ratio Test" (placeholder)
        images = soup.find_all("img")
        not_optimized_imgs_src = [] # Missing alt
        broken_images_details = []
        responsive_image_issues = []
        aspect_ratio_issues = [] # Placeholder

        images_to_actively_check = images[:self.active_check_limit]
        
        # Active check for broken images
        if images_to_actively_check:
            print(f"Actively checking up to {len(images_to_actively_check)} images for broken status (total on page: {len(images)})...")
            for img_tag in images_to_actively_check:
                src = img_tag.get("src")
                if src and not src.startswith(('data:', 'blob:')):
                    full_img_url = urljoin(base_url, src)
                    try:
                        response = requests.head(full_img_url, timeout=self.global_config.get("request_timeout", 10) / 2, allow_redirects=True, headers=self.headers) # Shorter timeout for images
                        if response.status_code >= 400:
                            broken_images_details.append({"url": full_img_url, "status_code": response.status_code})
                    except requests.exceptions.Timeout:
                        broken_images_details.append({"url": full_img_url, "status_code": "timeout"})
                    except requests.exceptions.RequestException: # Catching generic request exception
                        broken_images_details.append({"url": full_img_url, "status_code": "request_error"})
        
        # Alt text, responsive patterns, aspect ratio (for all images)
        for img in images:
            # Alt text
            alt_text = img.get("alt", "").strip()
            if not alt_text:
                img_src_for_alt = img.get("src", "N/A")
                if not img_src_for_alt.startswith(('data:', 'blob:')):
                     not_optimized_imgs_src.append(img_src_for_alt)
            
            # Responsive Image Test (basic heuristics)
            has_srcset = img.has_attr("srcset")
            has_sizes = img.has_attr("sizes")
            in_picture = bool(img.find_parent("picture"))
            if not (has_srcset or in_picture):
                # Check for common fluid image CSS if possible (very basic)
                style = img.get("style", "").lower()
                if "max-width" not in style and "width: 100%" not in style and "height: auto" not in style:
                     responsive_image_issues.append(img.get("src", "N/A"))
            
            # Image Aspect Ratio Test (placeholder - requires knowing dimensions)
            # if img.has_attr("width") and img.has_attr("height"):
            #     pass # Good, explicit dimensions
            # else:
            #    aspect_ratio_issues.append(img.get("src", "N/A")) # Missing explicit dimensions

        return {
            "total_images_on_page": len(images),
            "notOptimizedImgs": not_optimized_imgs_src, 
            "notOptimizedImagesCount": len(not_optimized_imgs_src), # Image Alt Test
            "brokenImages": broken_images_details, 
            "brokenImagesCount": len(broken_images_details),
            "imagesCheckedForBrokenStatus": len(images_to_actively_check),
            "responsiveImageIssues": responsive_image_issues, # Responsive Image Test
            "responsiveImageIssuesCount": len(responsive_image_issues),
            "aspectRatioIssuesCount": len(aspect_ratio_issues), # Placeholder
        }

    def _check_links(self, soup: BeautifulSoup, base_url: str) -> dict:
        internal_links_list = []
        external_links_list = []
        internal_nofollow_links_list = []
        broken_links_details = [] 
        unsafe_cross_origin_links = []
        
        total_anchor_text_length = 0
        valid_links_for_anchor_avg = 0
        base_domain = urlparse(base_url).netloc

        all_a_tags = soup.find_all("a", href=True)

        for a_tag in all_a_tags:
            href = a_tag["href"]
            anchor_text = a_tag.get_text(strip=True)

            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            full_url = urljoin(base_url, href)
            link_domain = urlparse(full_url).netloc
            is_nofollow = "nofollow" in a_tag.get("rel", [])

            if anchor_text:
                total_anchor_text_length += len(anchor_text)
                valid_links_for_anchor_avg +=1

            if link_domain == base_domain:
                internal_links_list.append(full_url)
                if is_nofollow:
                    internal_nofollow_links_list.append(full_url)
            else: # External link
                external_links_list.append(full_url)
                # Unsafe Cross-Origin Links Test
                # Check if external links that open in a new tab have rel="noopener" or rel="noreferrer"
                if a_tag.get("target") == "_blank" and not ("noopener" in a_tag.get("rel", []) or "noreferrer" in a_tag.get("rel", [])):
                    unsafe_cross_origin_links.append(full_url)
        
        # Active check for broken links
        all_discovered_links = internal_links_list + external_links_list
        links_to_actively_check = all_discovered_links[:self.active_check_limit]
        
        if links_to_actively_check:
            print(f"Actively checking up to {len(links_to_actively_check)} links for broken status (total on page: {len(all_discovered_links)})...")
            for link_url_to_check in links_to_actively_check:
                try:
                    response = requests.head(link_url_to_check, timeout=self.global_config.get("request_timeout", 10) / 2, allow_redirects=True, headers=self.headers)
                    if response.status_code >= 400:
                        broken_links_details.append({"url": link_url_to_check, "status_code": response.status_code})
                except requests.exceptions.Timeout:
                     broken_links_details.append({"url": link_url_to_check, "status_code": "timeout"})
                except requests.exceptions.RequestException:
                     broken_links_details.append({"url": link_url_to_check, "status_code": "request_error"})

        links_count_total = len(all_discovered_links)
        avg_anchor_len = (total_anchor_text_length / valid_links_for_anchor_avg) if valid_links_for_anchor_avg > 0 else 0

        return {
            "linksCount": links_count_total,
            "isTooEnoughlinks": links_count_total >= self.links_min_count, 
            "internalLinks": internal_links_list, 
            "internalLinksCount": len(internal_links_list),
            "externalLinks": external_links_list, 
            "externalLinksCount": len(external_links_list),
            "internalNoFollowLinks": internal_nofollow_links_list,
            "internalNoFollowLinksCount": len(internal_nofollow_links_list),
            "averageAnchorTextLength": round(avg_anchor_len, 2),
            "brokenLinks": broken_links_details,
            "brokenLinksCount": len(broken_links_details),
            "linksCheckedForBrokenStatus": len(links_to_actively_check),
            "unsafeCrossOriginLinks": unsafe_cross_origin_links,
            "unsafeCrossOriginLinksCount": len(unsafe_cross_origin_links)
        }

    def _check_content_stats(self, page_text_content: str, soup: BeautifulSoup) -> dict:
        words = re.findall(r'\b\w+\b', page_text_content.lower())
        word_count = len(words)
        paragraphs_count = len(soup.find_all("p"))
        has_lorem_ipsum = "lorem ipsum" in page_text_content.lower()
        
        return {
            "wordsCount": word_count,
            "isContentEnoughLong": word_count >= self.content_min_words,
            "paragraphs": paragraphs_count,
            "loremIpsum": has_lorem_ipsum,
        }

    def _check_iframes(self, soup: BeautifulSoup) -> dict:
        iframes = soup.find_all("iframe")
        return {
            "isNotIframe": len(iframes) == 0,
            "iframes": len(iframes)
        }

    def _check_apple_touch_icon(self, soup: BeautifulSoup, base_url: str) -> dict:
        icon_tag = soup.find("link", rel=re.compile(r"apple-touch-icon", re.I))
        icon_url = urljoin(base_url, icon_tag["href"]) if icon_tag and icon_tag.get("href") else None
        return {
            "appleTouchIcon": bool(icon_url),
            "appleTouchIconUrl": icon_url
        }

    def _check_script_and_css_files(self, soup: BeautifulSoup) -> dict:
        js_files = len(soup.find_all("script", src=True))
        css_files = len(soup.find_all("link", rel="stylesheet", href=True))
        return {
            "javascriptFiles": js_files,
            "cssFiles": css_files,
        }

    def _check_strong_tags(self, soup: BeautifulSoup) -> dict:
        strong_tags = len(soup.find_all("strong"))
        b_tags = len(soup.find_all("b"))
        return {
            "strongTags": strong_tags + b_tags,
        }

    def _check_open_graph(self, soup: BeautifulSoup) -> dict:
        # Part of "Social Media Meta Tags Test"
        og_tags = {}
        for tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:", re.I)}):
            prop = tag.get("property")
            content = tag.get("content")
            if prop and content:
                og_tags[prop] = content
        return {
            "hasOpenGraph": bool(og_tags),
            "openGraphTags": og_tags
        }

    def _check_twitter_cards(self, soup: BeautifulSoup) -> dict:
        # Part of "Social Media Meta Tags Test"
        twitter_tags = {}
        for tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
            name = tag.get("name")
            content = tag.get("content")
            if name and content:
                twitter_tags[name] = content
        return {
            "hasTwitterCards": bool(twitter_tags),
            "twitterCardTags": twitter_tags
        }
    
    def _check_favicon(self, soup: BeautifulSoup, base_url: str) -> dict:
        # "Favicon Test"
        base_favicon_check = super()._check_favicon(soup, base_url) # Call from base_module
        return {
            "favicon": base_favicon_check.get("favicon_status") == "detected", # Boolean as per list
            "faviconUrl": base_favicon_check.get("favicon_url_detected")
        }

    # --- New Tests from the List ---
    def _check_seo_friendly_url(self, url: str) -> dict:
        # "SEO Friendly URL Test"
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path) # Decode URL-encoded characters
        is_seo_friendly = True
        issues = []

        if len(url) > self.url_max_length:
            is_seo_friendly = False
            issues.append(f"URL is too long (>{self.url_max_length} chars).")
        
        path_segments = [seg for seg in path.split('/') if seg]
        if len(path_segments) > self.url_max_depth:
            is_seo_friendly = False
            issues.append(f"URL path is too deep (>{self.url_max_depth} segments).")

        if not re.match(r"^[a-zA-Z0-9\-\/._~%!$&'()*+,;=:@]*$", path): # Check for weird characters, allow common ones
            # This regex might be too strict or too loose depending on needs.
            # Generally, prefer hyphens over underscores, avoid special chars.
            # For simplicity, this is a basic check.
            # is_seo_friendly = False # Commenting out as it might be too aggressive
            # issues.append("URL path contains potentially unfriendly characters (spaces, underscores, or excessive special chars).")
            pass

        if any(char.isupper() for char in path):
            # is_seo_friendly = False # Case sensitivity can cause duplicate content issues
            issues.append("URL path contains uppercase characters. Prefer lowercase.")
            
        # Check for common file extensions in path (e.g. .php, .asp) - often not user-friendly
        if re.search(r"\.(php|asp|aspx|jsp|html|htm)$", path.lower()) and path != "/" and path_segments:
             issues.append("URL contains file extensions. Consider using clean URLs.")


        return {
            "isSeoFriendlyUrl": is_seo_friendly,
            "seoFriendlyUrlIssues": issues
        }

    def _check_inline_css(self, soup: BeautifulSoup) -> dict:
        # "Inline CSS Test"
        inline_css_count = 0
        for tag in soup.find_all(style=True):
            inline_css_count += 1
        return {
            "inlineCssCount": inline_css_count,
            "hasInlineCss": inline_css_count > 0
        }

    def _check_deprecated_html_tags(self, soup: BeautifulSoup) -> dict:
        # "Deprecated HTML Tags Test"
        found_deprecated = {}
        for dep_tag_name in self.deprecated_tags:
            tags = soup.find_all(dep_tag_name)
            if tags:
                found_deprecated[dep_tag_name] = len(tags)
        return {
            "deprecatedHtmlTagsFound": found_deprecated,
            "hasDeprecatedHtmlTags": bool(found_deprecated)
        }

    def _check_flash_content(self, soup: BeautifulSoup) -> dict:
        # "Flash Test"
        # Basic check for <object> or <embed> tags that might be Flash
        # More reliable detection would inspect 'type' or 'classid' attributes
        flash_objects = soup.find_all(['object', 'embed'], 
                                     attrs={'type': re.compile(r'application/x-shockwave-flash', re.I)})
        
        # Also check for common classids
        flash_objects_classid = soup.find_all('object', 
                                     attrs={'classid': re.compile(r'clsid:D27CDB6E-AE6D-11cf-96B8-444553540000', re.I)})
        
        has_flash = bool(flash_objects or flash_objects_classid)
        return {"hasFlashContent": has_flash}

    def _check_nested_tables(self, soup: BeautifulSoup) -> dict:
        # "Nested Tables Test"
        nested_tables_count = 0
        for table in soup.find_all("table"):
            if table.find("table"): # Check if this table contains another table
                nested_tables_count += 1
        return {
            "nestedTablesCount": nested_tables_count,
            "hasNestedTables": nested_tables_count > 0
        }

    def _check_frameset(self, soup: BeautifulSoup) -> dict:
        # "Frameset Test"
        has_frameset = bool(soup.find("frameset"))
        return {"hasFrameset": has_frameset}

if __name__ == '__main__':
    pass
