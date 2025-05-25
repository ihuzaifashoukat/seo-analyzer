# modules/technical_seo_analyzer.py
import requests
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup, Doctype
import re
import json
import socket
from datetime import datetime # For TTFB
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    Image = None # type: ignore

from .base_module import SEOModule

class TechnicalSEOAnalyzer(SEOModule):
    """
    Analyzes technical SEO aspects of a given URL and its domain.
    """

    def __init__(self, config=None):
        super().__init__(config=config)
        self.tech_config = self.config 
        self.global_config = self.config.get("Global", {})
        self.request_timeout = self.global_config.get("request_timeout", 10)

    def _make_request(self, url, method="get", **kwargs):
        try:
            kwargs.setdefault('stream', True)
            start_time = datetime.now()
            response = requests.request(method, url, headers=self.headers, timeout=self.request_timeout, **kwargs)
            end_time = datetime.now()
            ttfb = (end_time - start_time).total_seconds()
            return response, ttfb
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {url} in TechnicalSEO: {e}")
            return None, None

    def analyze(self, url: str) -> dict:
        results = {
            "technical_seo_status": "pending",
            "url_analyzed": url
        }
        
        main_response, ttfb = self._make_request(url, allow_redirects=True)
        soup = None
        raw_html_content = ""

        if main_response:
            results["httpStatusCode"] = main_response.status_code
            raw_html_content = main_response.content
            results["htmlPageSize"] = len(raw_html_content) 
            results["htmlCompressionGzipTest"] = main_response.headers.get("Content-Encoding", "").lower()
            
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
            results["cdnUsageHeuristic"] = self._check_cdn_headers(main_response.headers)
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
            results.update(self._check_doctype(soup))
            results.update(self._check_character_encoding(soup))
            results.update(self._check_viewport_meta(soup))
            results.update(self._check_amp(soup, base_domain_url))
            results.update(self._check_language_and_hreflang(soup, base_domain_url))
            results.update(self._check_canonical_tag(soup, url))
            results.update(self._check_meta_robots(soup))
            results.update(self._check_structured_data(soup))
            results.update(self._check_google_analytics(str(soup)))
            results.update(self._check_mobile_friendliness_heuristics(soup, results.get("viewport", False)))
            results.update(self._check_mixed_content(soup, parsed_url.scheme))
            results.update(self._check_plaintext_emails(str(soup)))
            results.update(self._check_meta_refresh(soup))
            results["domSize"] = len(soup.find_all(True))
            results.update(super()._check_favicon(soup, base_domain_url))
        results.update(self._check_modern_image_formats_html(soup))
        
        # Image Metadata Test
        results.update(self._analyze_image_metadata(soup, base_domain_url))

        # Asset Caching Tests
        results.update(self._analyze_asset_caching(soup, base_domain_url, 'image'))
        results.update(self._analyze_asset_caching(soup, base_domain_url, 'javascript'))
        results.update(self._analyze_asset_caching(soup, base_domain_url, 'css'))

        # Asset Minification Tests
        results.update(self._analyze_asset_minification(soup, raw_html_content, base_domain_url, 'javascript'))
        results.update(self._analyze_asset_minification(soup, raw_html_content, base_domain_url, 'css'))

        results.update(self._check_https_usage(parsed_url))
        robots_check_result = self._check_robots_txt(base_domain_url)
        results.update(robots_check_result)
        results.update(self._check_sitemap_xml(base_domain_url, robots_check_result.get("robots_txt_content_full")))
        results["domainLength"] = len(domain_name)
        results.update(self._check_url_redirects(url))
        results.update(self._check_custom_404_page(base_domain_url))
        results.update(self._check_directory_browsing(base_domain_url))
        results.update(self._check_spf_records(domain_name))
        results.update(self._check_ads_txt(base_domain_url))

        # Placeholders for minification tests removed, will be implemented
        # results["javascriptMinificationTest"]
        # results["cssMinificationTest"]
        
        # Removed placeholders for features definitively requiring headless browser or specific external APIs not used.
        # (jsErrorTest, consoleErrorsTest, jsExecutionTimeTest, pageObjectsTest, renderBlockingResourcesTest, 
        # largestContentfulPaintTest, cumulativeLayoutShiftTest, safeBrowsingTest, mobileSnapshotTest)

        results["technical_seo_status"] = "completed"
        return {self.module_name: results}

    def _check_doctype(self, soup: BeautifulSoup) -> dict:
        doctype_item = None
        for item in soup.contents:
            if isinstance(item, Doctype):
                doctype_item = item
                break
        return {"isDoctype": bool(doctype_item)}

    def _check_character_encoding(self, soup: BeautifulSoup) -> dict:
        meta_charset = soup.find("meta", attrs={"charset": True})
        if meta_charset:
            return {"isCharacterEncode": True, "charsetValue": meta_charset.get("charset")}
        http_equiv = soup.find("meta", attrs={"http-equiv": re.compile("Content-Type", re.I)})
        if http_equiv and "charset=" in http_equiv.get("content", "").lower():
            return {"isCharacterEncode": True, "charsetValue": http_equiv.get("content").split("charset=")[-1].strip()}
        return {"isCharacterEncode": False, "charsetValue": None}

    def _check_https_usage(self, parsed_url: urlparse) -> dict:
        return {"hasHttps": parsed_url.scheme == "https"}

    def _check_robots_txt(self, base_domain_url: str) -> dict:
        robots_url = urljoin(base_domain_url, "/robots.txt")
        content = None; status = "not_found"; sitemap_urls = []; disallow_directives = []
        has_disallow_all_for_google = False; has_disallow_all_general = False
        current_user_agent = "*"
        response, _ = self._make_request(robots_url)
        if response and response.status_code == 200:
            content = response.text; status = "found"
            for line in content.splitlines():
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("#"): continue
                line_lower = line_strip.lower()
                if line_lower.startswith("user-agent:"): current_user_agent = line_strip.split(":", 1)[1].strip().lower()
                elif line_lower.startswith("sitemap:"): sitemap_urls.append(line_strip.split(":", 1)[1].strip())
                elif line_lower.startswith("disallow:"):
                    disallow_path = line_strip.split(":", 1)[1].strip()
                    disallow_directives.append({"user_agent": current_user_agent, "path": disallow_path})
                    if disallow_path == "/":
                        if current_user_agent == "*" : has_disallow_all_general = True
                        if "googlebot" in current_user_agent : has_disallow_all_for_google = True
        elif response is None: status = "error_accessing"
        return {"robotsTxtStatus": status, "robotsTxtSitemapUrls": sitemap_urls, 
                "robotsTxtDisallowDirectives": disallow_directives, 
                "robotsTxtDisallowsAllGeneral": has_disallow_all_general,
                "robotsTxtDisallowsAllForGoogle": has_disallow_all_for_google,
                "robots_txt_content_full": content}

    def _check_sitemap_xml(self, base_domain_url: str, robots_txt_content: str | None) -> dict:
        sitemap_urls_to_check = []
        if robots_txt_content:
             for line in robots_txt_content.splitlines():
                if line.strip().lower().startswith("sitemap:"): sitemap_urls_to_check.append(line.strip().split(":", 1)[1].strip())
        if not sitemap_urls_to_check:
            sitemap_urls_to_check.extend([urljoin(base_domain_url, "/sitemap.xml"), urljoin(base_domain_url, "/sitemap_index.xml")])
        has_sitemap = False; found_sitemap_url = None
        for s_url in sitemap_urls_to_check:
            response, _ = self._make_request(s_url, method="head")
            if response and response.status_code == 200: has_sitemap = True; found_sitemap_url = s_url; break
        return {"hasSitemap": has_sitemap, "sitemapUrlFound": found_sitemap_url}

    def _check_viewport_meta(self, soup: BeautifulSoup) -> dict:
        viewport_tag = soup.find("meta", attrs={"name": "viewport"})
        return {"viewport": bool(viewport_tag), "viewportContent": viewport_tag.get("content") if viewport_tag else None}

    def _check_amp(self, soup: BeautifulSoup, base_url: str) -> dict:
        amp_link_tag = soup.find("link", rel="amphtml", href=True)
        if amp_link_tag: return {"isAmp": True, "ampUrl": urljoin(base_url, amp_link_tag["href"])}
        html_tag = soup.find("html")
        if html_tag and (html_tag.has_attr("amp") or html_tag.has_attr("\u26A1")): return {"isAmp": True, "ampUrl": None}
        return {"isAmp": False, "ampUrl": None}

    def _check_language_and_hreflang(self, soup: BeautifulSoup, base_url: str) -> dict:
        html_tag = soup.find("html"); lang_attr = html_tag.get("lang") if html_tag else None
        hreflang_links_data = []; has_hreflang_tag = False
        for tag in soup.find_all("link", rel="alternate", hreflang=True, href=True):
            has_hreflang_tag = True; hreflang_links_data.append({"lang_code": tag["hreflang"], "url": urljoin(base_url, tag["href"])})
        return {"language": lang_attr.lower() if lang_attr else None, "hasHreflang": has_hreflang_tag, "hreflangLinks": hreflang_links_data}

    def _check_canonical_tag(self, soup: BeautifulSoup, current_url: str) -> dict:
        tag = soup.find("link", attrs={"rel": "canonical"}, href=True)
        return {"canonicalUrl": urljoin(current_url, tag["href"]) if tag else None, "hasCanonicalTag": bool(tag)}

    def _check_meta_robots(self, soup: BeautifulSoup) -> dict:
        tag = soup.find("meta", attrs={"name": re.compile(r"robots", re.I)})
        content = tag.get("content", "").lower() if tag else None
        return {"metaRobots": content, "hasMetaNoindex": "noindex" in (content or ""), "hasMetaNofollowDirective": "nofollow" in (content or "")}

    def _check_structured_data(self, soup: BeautifulSoup) -> dict:
        json_ld_list = []; microdata_list = []
        for script in soup.find_all("script", type="application/ld+json"):
            try: json_ld_list.append(json.loads(script.string))
            except: pass
        for item_scope in soup.find_all(attrs={"itemscope": True}):
            is_nested = False; parent = item_scope.parent
            while parent: 
                if parent.has_attr("itemscope") and parent != item_scope: is_nested = True; break
                parent = parent.parent
            if is_nested: continue
            details = {"type": item_scope.get("itemtype", "UnknownType"), "properties": {}}
            for prop_tag in item_scope.find_all(attrs={"itemprop": True}):
                is_direct = True; p_parent = prop_tag.parent
                while p_parent and p_parent != item_scope:
                    if p_parent.has_attr("itemscope"): is_direct = False; break
                    p_parent = p_parent.parent
                if not is_direct: continue
                name = prop_tag.get("itemprop"); value = None
                if prop_tag.has_attr("itemscope"): value = {"@type": "NestedItemscope", "itemtype": prop_tag.get("itemtype", "UnknownNestedType")}
                elif prop_tag.name == 'meta': value = prop_tag.get("content")
                elif prop_tag.name in ['a', 'link']: value = prop_tag.get("href")
                elif prop_tag.name in ['img', 'audio', 'video', 'embed', 'iframe', 'source', 'track']: value = prop_tag.get("src")
                elif prop_tag.name == 'time': value = prop_tag.get("datetime") or prop_tag.get_text(strip=True)
                elif prop_tag.name == 'data': value = prop_tag.get("value") or prop_tag.get_text(strip=True)
                elif prop_tag.name == 'object': value = prop_tag.get("data")
                else: value = prop_tag.get_text(strip=True)
                if name and value is not None:
                    if name in details["properties"]:
                        if not isinstance(details["properties"][name], list): details["properties"][name] = [details["properties"][name]]
                        details["properties"][name].append(value)
                    else: details["properties"][name] = value
            if details["properties"]: microdata_list.append(details)
        has_schema = any("schema.org" in str(t).lower() for t in soup.find_all(True, itemtype=True)) or bool(json_ld_list) or any("schema.org" in i.get("type","").lower() for i in microdata_list)
        return {"hasJsonLd": bool(json_ld_list), "jsonLdData": json_ld_list, "hasMicrodata": bool(microdata_list), "microdataItems": microdata_list, "hasSchema": has_schema}

    def _check_google_analytics(self, html_str: str) -> dict:
        patterns = {
            "isGoogleAnalyticsObject": r"window\.ga\s*=\s*window\.ga\s*\|\|\s*function\(\)",
            "isGoogleAnalyticsFunc": r"ga\s*\(\s*['\"]create['\"]\s*,",
            "hasGtagConfig": r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"](G|UA|AW)-",
            "hasGtagJs": r"https://www.googletagmanager.com/gtag/js\?id=(G|UA|AW)-"
        }
        results = {k: bool(re.search(v, html_str)) for k,v in patterns.items()}
        results["hasGoogleAnalytics"] = any(results.values())
        return results

    def _check_mobile_friendliness_heuristics(self, soup: BeautifulSoup, viewport_present: bool) -> dict:
        notes = []; responsive = viewport_present
        if not viewport_present: notes.append("Viewport meta tag missing.")
        fixed_widths = []
        for tag in ["body", "div", "main", "article", "section", "table"]:
            for el in soup.find_all(tag, style=True):
                if "width" in el['style']:
                    m = re.search(r"width\s*:\s*(\d{3,})px", el['style'])
                    if m and int(m.group(1)) > 380: fixed_widths.append(f"<{el.name}> fixed width {m.group(1)}px"); responsive = False; break
            if fixed_widths and not responsive: break
        if fixed_widths: notes.append(f"Large fixed-width elements found: {', '.join(fixed_widths[:2])}.")
        if viewport_present and not fixed_widths: notes.append("Viewport present, no large inline fixed-widths. Good.")
        media_queries = any("@media" in s.string for s in soup.find_all("style") if s.string)
        if media_queries: notes.append("Internal CSS media queries found.") 
        else: notes.append("No internal CSS media queries (may be external).")
        return {"mobileResponsive": responsive, "mobileFriendlinessNotes": notes, "hasInternalMediaQueries": media_queries}

    def _check_mixed_content(self, soup: BeautifulSoup, scheme: str) -> dict:
        items = []
        if scheme == "https":
            for tag, attr in [("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src"), ("video", "src"), ("audio", "src"), ("source", "src")]:
                for t in soup.find_all(tag, **{attr: re.compile(r"^http://", re.I)}): items.append({"tag": tag, "url": t[attr]})
        return {"mixedContentItems": items, "hasMixedContent": bool(items)}

    def _check_plaintext_emails(self, html_str: str) -> dict:
        emails = list(set(e for e in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html_str) if not any(ext in e.lower() for ext in ['.png','.jpg','.gif','.svg','.css','.js'])))
        return {"plaintextEmailsFound": emails, "hasPlaintextEmails": bool(emails)}

    def _check_meta_refresh(self, soup: BeautifulSoup) -> dict:
        tag = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
        return {"hasMetaRefresh": bool(tag), "metaRefreshContent": tag.get("content") if tag else None}

    def _check_url_redirects(self, url: str) -> dict:
        history = []; status_codes = []
        response, _ = self._make_request(url, allow_redirects=True)
        if response:
            if response.history:
                for r_hist in response.history: history.append({"url": r_hist.url, "status_code": r_hist.status_code}); status_codes.append(r_hist.status_code)
            history.append({"url": response.url, "status_code": response.status_code}); status_codes.append(response.status_code)
        else: history.append({"url": url, "error": "Request failed"})
        return {"redirectHistory": history, "hasRedirects": len(history) > 1 and any(s // 100 == 3 for s in status_codes)}

    def _check_custom_404_page(self, base_url: str) -> dict:
        url_404 = urljoin(base_url, f"/non_existent_page_{datetime.now().timestamp()}.html")
        is_custom = False; status = None; length = 0
        response, _ = self._make_request(url_404, allow_redirects=False)
        if response: status = response.status_code; length = len(response.content); is_custom = status == 404 and length > 1024
        return {"custom404PageTestStatus": status, "custom404PageLength": length, "hasCustom404PageHeuristic": is_custom}

    def _check_directory_browsing(self, base_url: str) -> dict:
        paths = []
        for d in ["/css/", "/js/", "/images/", "/uploads/"]:
            response, _ = self._make_request(urljoin(base_url, d))
            if response and response.status_code == 200:
                s = BeautifulSoup(response.content, 'html.parser')
                if s.title and "index of /" in s.title.string.lower(): paths.append(d)
        return {"directoryBrowsingEnabledPaths": paths, "hasDirectoryBrowsingEnabled": bool(paths)}

    def _check_spf_records(self, domain: str) -> dict:
        has_spf = False; records = []
        try:
            import dns.resolver
            for rdata in dns.resolver.resolve(domain, 'TXT'):
                for txt in rdata.strings:
                    if txt.decode().lower().startswith("v=spf1"): has_spf = True; records.append(txt.decode())
            status = "completed"
        except ImportError: status = "skipped_dnspython_not_installed"
        except Exception: status = "error_dns_lookup"
        return {"spfRecordTestStatus": status, "hasSpfRecord": has_spf, "spfRecords": records}

    def _check_ads_txt(self, base_url: str) -> dict:
        has_ads = False; content = None
        response, _ = self._make_request(urljoin(base_url, "/ads.txt"))
        if response and response.status_code == 200: has_ads = True; content = response.text[:1000]
        return {"hasAdsTxt": has_ads, "adsTxtPreview": content}

    def _check_cdn_headers(self, headers: requests.structures.CaseInsensitiveDict) -> dict:
        cdns = {
            "Cloudflare": any(h.lower() == "cf-ray" for h in headers) or "cloudflare" in headers.get("Server","").lower(),
            "Akamai": any(h.lower().startswith("x-akamai") for h in headers) or "akamaighost" in headers.get("Server","").lower(),
            "CloudFront": "cloudfront" in headers.get("Via","") or "cloudfront" in headers.get("X-Amz-Cf-Id","") or "cloudfront" in headers.get("Server","").lower(),
            "Fastly": "fastly" in headers.get("X-Served-By","") or "fastly" in headers.get("Server","").lower(),
            "Google": "gws" in headers.get("Server","").lower() or "google" in headers.get("Server","").lower(),
        }
        used = [cdn for cdn, present in cdns.items() if present]
        return {"usesCdn": bool(used), "detectedCdns": used}

    def _check_modern_image_formats_html(self, soup: BeautifulSoup) -> dict:
        webp = False; avif = False
        for pic in soup.find_all("picture"):
            if pic.find("source", attrs={"type": "image/webp"}): webp = True
            if pic.find("source", attrs={"type": "image/avif"}): avif = True
        for img in soup.find_all("img", src=True):
            src = img["src"].lower()
            if ".webp" in src: webp = True
            if ".avif" in src: avif = True
            if webp and avif: break
        return {"usesWebPInHtml": webp, "usesAvifInHtml": avif, "modernImageFormatNotes": "HTML check only."}

    def _extract_image_urls(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        image_urls = []
        for img_tag in soup.find_all("img", src=True):
            src = img_tag["src"]
            if src.startswith("data:image"): # Skip data URIs
                continue
            full_url = urljoin(base_url, src)
            image_urls.append(full_url)
        
        # Consider images in <picture><source srcset/src>
        for picture_tag in soup.find_all("picture"):
            for source_tag in picture_tag.find_all("source", srcset=True):
                srcs = [s.strip().split(" ")[0] for s in source_tag["srcset"].split(",")]
                for src in srcs:
                    if src.startswith("data:image"): continue
                    full_url = urljoin(base_url, src)
                    if full_url not in image_urls: image_urls.append(full_url)
            # Fallback img inside picture
            img_in_picture = picture_tag.find("img", src=True)
            if img_in_picture:
                src = img_in_picture["src"]
                if src.startswith("data:image"): continue
                full_url = urljoin(base_url, src)
                if full_url not in image_urls: image_urls.append(full_url)

        # Limit the number of images to check to avoid excessive requests
        # This limit can be configured if needed
        return list(set(image_urls))[:self.tech_config.get("max_images_to_check_metadata", 5)]


    def _get_asset_response(self, asset_url: str):
        """Fetches an asset, returns the response object."""
        try:
            # Using a shorter timeout for assets
            asset_timeout = self.global_config.get("asset_request_timeout", 5)
            response = requests.get(asset_url, headers=self.headers, timeout=asset_timeout, stream=True)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response
        except requests.exceptions.RequestException as e:
            # print(f"Failed to fetch asset {asset_url}: {e}")
            return None

    def _check_image_metadata(self, image_content: bytes) -> dict:
        metadata = {"has_exif": False, "has_iptc": False, "has_xmp": False, "format": None, "mode": None, "size": None, "details": {}}
        if not Image:
            return {"status": "skipped", "details": "Pillow library not installed."}
        try:
            img = Image.open(BytesIO(image_content))
            metadata["format"] = img.format
            metadata["mode"] = img.mode
            metadata["size"] = img.size

            if hasattr(img, '_getexif') and img._getexif(): # type: ignore
                metadata["has_exif"] = True
                # metadata["details"]["exif"] = {TAGS.get(k, k): v for k, v in img._getexif().items()} # Too verbose
            
            if img.info.get("icc_profile"): # A common place for IPTC/XMP but not exclusive
                 pass # Further parsing needed for specific IPTC/XMP, can be complex

            # Pillow doesn't directly parse XMP as a dict easily, often embedded in other metadata sections.
            # For simplicity, we're just checking presence via common means.
            # A more robust check would involve looking for XMP packet markers.
            if "xmp" in img.info or "photoshop" in img.info: # Heuristic
                metadata["has_xmp"] = True

            # IPTC is also tricky with Pillow alone, often needs specialized libraries or parsing exif.
            # For now, this is a basic check.
            if any(key in img.info for key in ["photoshop:Credit", "photoshop:Caption", "IptcApplicationRecord"]):
                 metadata["has_iptc"] = True

        except Exception as e:
            metadata["error"] = str(e)
        return metadata

    def _analyze_image_metadata(self, soup: BeautifulSoup, base_url: str) -> dict:
        if not Image:
            return {"imageMetadataTest": {"status": "skipped", "details": "Pillow library (PIL) not installed. Cannot analyze image metadata."}}

        image_urls = self._extract_image_urls(soup, base_url)
        if not image_urls:
            return {"imageMetadataTest": {"status": "no_images_found_or_analyzed", "details": "No suitable image URLs found on the page or limit reached."}}

        results = []
        processed_count = 0
        errors_count = 0

        for img_url in image_urls:
            response = self._get_asset_response(img_url)
            if response:
                try:
                    # Limit download size for safety
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.tech_config.get("max_image_size_bytes_for_metadata", 2 * 1024 * 1024): # 2MB limit
                        results.append({"url": img_url, "status": "skipped_too_large", "size_bytes": int(content_length)})
                        continue

                    img_content = response.content # Reads entire content, ensure stream=True was used in _get_asset_response
                    metadata = self._check_image_metadata(img_content)
                    results.append({"url": img_url, "status": "analyzed", **metadata})
                    processed_count +=1
                except Exception as e:
                    results.append({"url": img_url, "status": "error_processing_content", "error": str(e)})
                    errors_count += 1
                finally:
                    response.close() # Ensure connection is closed
            else:
                results.append({"url": img_url, "status": "error_fetching"})
                errors_count += 1
        
        overall_status = "completed"
        if errors_count > 0 and processed_count == 0:
            overall_status = "error_all_failed"
        elif errors_count > 0:
            overall_status = "completed_with_errors"

        return {"imageMetadataTest": {"status": overall_status, "images_analyzed_count": processed_count, "images_skipped_or_errors": len(image_urls) - processed_count, "details": results}}

    def _extract_css_urls(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        css_urls = []
        for link_tag in soup.find_all("link", rel="stylesheet", href=True):
            href = link_tag["href"]
            if href.startswith("data:"): continue
            full_url = urljoin(base_url, href)
            css_urls.append(full_url)
        return list(set(css_urls))[:self.tech_config.get("max_css_to_check_caching", 5)]

    def _extract_js_urls(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        js_urls = []
        for script_tag in soup.find_all("script", src=True):
            src = script_tag["src"]
            if src.startswith("data:"): continue
            full_url = urljoin(base_url, src)
            js_urls.append(full_url)
        return list(set(js_urls))[:self.tech_config.get("max_js_to_check_caching", 5)]

    def _check_asset_cache_headers(self, response_headers: requests.structures.CaseInsensitiveDict) -> dict:
        cache_control = response_headers.get("Cache-Control")
        expires = response_headers.get("Expires")
        pragma = response_headers.get("Pragma")
        etag = response_headers.get("ETag")
        last_modified = response_headers.get("Last-Modified")

        is_cacheable = False
        has_strong_caching = False
        notes = []

        if cache_control:
            if "no-store" in cache_control or "no-cache" in cache_control:
                notes.append("Cache-Control indicates not to cache or to revalidate.")
            elif "public" in cache_control or "private" in cache_control:
                is_cacheable = True
                if "max-age" in cache_control:
                    try:
                        max_age = int(re.search(r"max-age=(\d+)", cache_control).group(1)) # type: ignore
                        if max_age > 2592000: # 30 days
                            has_strong_caching = True
                            notes.append(f"Strong caching via Cache-Control max-age: {max_age}s.")
                        else:
                            notes.append(f"Cache-Control max-age: {max_age}s.")
                    except:
                        notes.append("Could not parse max-age from Cache-Control.")
                else:
                    notes.append("Cache-Control present but no max-age.")
            else:
                 notes.append("Cache-Control present with other directives.")
        
        if expires:
            notes.append(f"Expires header: {expires}.")
            # Comparing Expires with current time can be complex due to timezones
            # Generally, Cache-Control max-age is preferred over Expires
            if not cache_control or "max-age" not in cache_control : is_cacheable = True # if no max-age, expires can make it cacheable

        if pragma and "no-cache" in pragma.lower():
            notes.append("Pragma: no-cache found (legacy).")
            is_cacheable = False # Pragma: no-cache overrides

        if not is_cacheable and not notes:
            notes.append("No strong client-side caching headers found (Cache-Control max-age/Expires).")
        elif is_cacheable and not has_strong_caching and "Strong caching" not in " ".join(notes):
             notes.append("Asset is cacheable, but long-term caching (e.g., >30 days max-age) not explicitly set.")


        return {
            "is_cacheable_heuristic": is_cacheable,
            "has_strong_caching_heuristic": has_strong_caching,
            "headers": {
                "Cache-Control": cache_control,
                "Expires": expires,
                "Pragma": pragma,
                "ETag": etag,
                "Last-Modified": last_modified,
            },
            "notes": notes
        }

    def _analyze_asset_caching(self, soup: BeautifulSoup, base_url: str, asset_type: str) -> dict:
        # asset_type can be 'image', 'javascript', 'css'
        test_name = f"{asset_type}CachingTest"
        
        asset_urls = []
        if asset_type == 'image':
            asset_urls = self._extract_image_urls(soup, base_url) # Uses its own limit from config
        elif asset_type == 'javascript':
            asset_urls = self._extract_js_urls(soup, base_url)
        elif asset_type == 'css':
            asset_urls = self._extract_css_urls(soup, base_url)
        else:
            return {test_name: {"status": "error_internal", "details": "Invalid asset type specified."}}

        if not asset_urls:
            return {test_name: {"status": f"no_{asset_type}_found_or_analyzed", "details": f"No suitable {asset_type} URLs found on the page or limit reached."}}

        results_list = []
        processed_count = 0
        errors_count = 0
        cacheable_count = 0
        strong_caching_count = 0

        for asset_url in asset_urls:
            # For caching, we only need headers, so use HEAD request if possible, fallback to GET
            response = None
            try:
                asset_timeout = self.global_config.get("asset_request_timeout", 5)
                # Try HEAD first
                head_response = requests.head(asset_url, headers=self.headers, timeout=asset_timeout, allow_redirects=True)
                head_response.raise_for_status()
                response = head_response
            except requests.exceptions.RequestException:
                # Fallback to GET if HEAD fails or is not allowed (some servers disallow HEAD)
                response = self._get_asset_response(asset_url) # This is a GET request

            if response:
                try:
                    cache_info = self._check_asset_cache_headers(response.headers)
                    results_list.append({"url": asset_url, "status": "analyzed", **cache_info})
                    processed_count += 1
                    if cache_info["is_cacheable_heuristic"]: cacheable_count +=1
                    if cache_info["has_strong_caching_heuristic"]: strong_caching_count +=1
                except Exception as e:
                    results_list.append({"url": asset_url, "status": "error_processing_headers", "error": str(e)})
                    errors_count += 1
                finally:
                    if hasattr(response, 'close'): response.close()
            else:
                results_list.append({"url": asset_url, "status": "error_fetching"})
                errors_count += 1
        
        overall_status = "completed"
        if errors_count > 0 and processed_count == 0:
            overall_status = "error_all_failed"
        elif errors_count > 0:
            overall_status = "completed_with_errors"
        
        summary = f"{processed_count} {asset_type} assets checked. {cacheable_count} appear cacheable, {strong_caching_count} have strong caching directives."
        if len(asset_urls) > processed_count:
            summary += f" {len(asset_urls) - processed_count} were skipped or had errors."

        return {test_name: {"status": overall_status, 
                            "assets_analyzed_count": processed_count, 
                            "assets_cacheable_count": cacheable_count,
                            "assets_strong_caching_count": strong_caching_count,
                            "summary": summary,
                            "details": results_list}}

    def _extract_inline_css_content(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        inline_css = []
        for i, style_tag in enumerate(soup.find_all("style")):
            content = style_tag.string
            if content and content.strip():
                inline_css.append({"source": f"inline_style_tag_{i+1}", "content": content.strip()})
        # Limit can be added from config if needed: [:self.tech_config.get("max_inline_css_to_check_minification", 3)]
        return inline_css[:self.tech_config.get("max_inline_css_to_check_minification", 3)]

    def _extract_inline_js_content(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        inline_js = []
        for i, script_tag in enumerate(soup.find_all("script")):
            if not script_tag.has_attr("src"): # Only inline scripts
                content = script_tag.string
                if content and content.strip():
                    inline_js.append({"source": f"inline_script_tag_{i+1}", "content": content.strip()})
        # Limit can be added from config if needed: [:self.tech_config.get("max_inline_js_to_check_minification", 3)]
        return inline_js[:self.tech_config.get("max_inline_js_to_check_minification", 3)]

    def _check_content_minification(self, content: str, asset_type: str = "unknown") -> dict:
        """
        Heuristic check for minification.
        A simple heuristic: if whitespace is less than X% of total, it's likely minified.
        And if average line length is high.
        """
        if not content:
            return {"is_minified_heuristic": False, "reason": "No content", "whitespace_ratio": 0, "avg_line_length": 0, "line_count":0, "char_count":0}

        lines = content.splitlines()
        line_count = len(lines)
        char_count = len(content)
        
        whitespace_chars = len(re.findall(r"\s", content))
        non_whitespace_chars = char_count - whitespace_chars
        
        whitespace_ratio = 0
        if char_count > 0:
            whitespace_ratio = whitespace_chars / char_count
            
        avg_line_length = 0
        if line_count > 0:
            avg_line_length = char_count / line_count

        # Thresholds (can be made configurable)
        # Lower whitespace_ratio_threshold means stricter minification check
        whitespace_ratio_threshold = self.tech_config.get(f"minification_whitespace_ratio_threshold_{asset_type}", 0.15) # e.g. < 15% whitespace
        # Higher avg_line_length_threshold means stricter minification check (for files that are not one-liners)
        avg_line_length_threshold = self.tech_config.get(f"minification_avg_line_length_threshold_{asset_type}", 200) # e.g. > 200 chars per line on average
        # If a file is just one very long line, it's almost certainly minified.
        single_long_line_threshold = self.tech_config.get(f"minification_single_long_line_threshold_{asset_type}", 500)


        is_minified = False
        reason = []

        if line_count == 1 and char_count > single_long_line_threshold:
            is_minified = True
            reason.append(f"Single line with {char_count} chars (>{single_long_line_threshold}).")
        elif line_count > 1 : # For multi-line files
            if whitespace_ratio < whitespace_ratio_threshold :
                is_minified = True # Primary indicator
                reason.append(f"Whitespace ratio {whitespace_ratio:.2f} < {whitespace_ratio_threshold:.2f}.")
            if avg_line_length > avg_line_length_threshold:
                if is_minified: # Already true, just add reason
                     reason.append(f"Avg line length {avg_line_length:.0f} > {avg_line_length_threshold:.0f}.")
                else: # If whitespace ratio wasn't enough, high avg line length can also indicate minification
                    is_minified = True
                    reason.append(f"Avg line length {avg_line_length:.0f} > {avg_line_length_threshold:.0f} (whitespace ratio was {whitespace_ratio:.2f}).")
            elif not is_minified:
                 reason.append(f"Whitespace ratio {whitespace_ratio:.2f} >= {whitespace_ratio_threshold:.2f} and Avg line length {avg_line_length:.0f} <= {avg_line_length_threshold:.0f}.")
        elif not is_minified: # Single line but not long enough
            reason.append(f"Single line with {char_count} chars (<={single_long_line_threshold}). Whitespace ratio {whitespace_ratio:.2f}.")


        return {
            "is_minified_heuristic": is_minified,
            "reason": " ".join(reason) if reason else "Not enough indicators for minification.",
            "whitespace_ratio": round(whitespace_ratio, 3),
            "avg_line_length": round(avg_line_length, 1),
            "line_count": line_count,
            "char_count": char_count
        }

    def _analyze_asset_minification(self, soup: BeautifulSoup, raw_html_content:str, base_url: str, asset_type: str) -> dict:
        # asset_type can be 'javascript', 'css'
        test_name = f"{asset_type}MinificationTest"
        
        external_asset_urls = []
        inline_assets_content = [] # list of dicts: [{"source": "inline_script_1", "content": "..."}]

        if asset_type == 'javascript':
            external_asset_urls = self._extract_js_urls(soup, base_url) # Uses its own limit from config
            inline_assets_content = self._extract_inline_js_content(soup) # Uses its own limit
        elif asset_type == 'css':
            external_asset_urls = self._extract_css_urls(soup, base_url) # Uses its own limit
            inline_assets_content = self._extract_inline_css_content(soup) # Uses its own limit
        else:
            return {test_name: {"status": "error_internal", "details": "Invalid asset type specified."}}

        if not external_asset_urls and not inline_assets_content:
            return {test_name: {"status": f"no_{asset_type}_found_or_analyzed", "details": f"No suitable external or inline {asset_type} found on the page or limit reached."}}

        results_list = []
        processed_count = 0
        errors_count = 0
        minified_count = 0
        
        # Analyze external assets
        for asset_url in external_asset_urls:
            response = self._get_asset_response(asset_url) # This is a GET request
            if response:
                try:
                    # Limit download size for safety
                    content_length = response.headers.get('Content-Length')
                    max_size = self.tech_config.get(f"max_{asset_type}_size_bytes_for_minification", 1 * 1024 * 1024) # 1MB limit
                    if content_length and int(content_length) > max_size:
                        results_list.append({"source_url": asset_url, "type": "external", "status": "skipped_too_large", "size_bytes": int(content_length)})
                        continue
                    
                    asset_content = response.text # Use .text for text-based assets like JS/CSS
                    minification_info = self._check_content_minification(asset_content, asset_type)
                    results_list.append({"source_url": asset_url, "type": "external", "status": "analyzed", **minification_info})
                    processed_count += 1
                    if minification_info["is_minified_heuristic"]: minified_count +=1
                except Exception as e:
                    results_list.append({"source_url": asset_url, "type": "external", "status": "error_processing_content", "error": str(e)})
                    errors_count += 1
                finally:
                    if hasattr(response, 'close'): response.close()
            else:
                results_list.append({"source_url": asset_url, "type": "external", "status": "error_fetching"})
                errors_count += 1
        
        # Analyze inline assets
        for inline_asset in inline_assets_content:
            try:
                content = inline_asset["content"]
                source_name = inline_asset["source"]
                if len(content) > self.tech_config.get(f"max_inline_{asset_type}_size_bytes_for_minification", 100 * 1024): # 100KB limit for inline
                    results_list.append({"source": source_name, "type": "inline", "status": "skipped_too_large", "size_bytes": len(content)})
                    continue

                minification_info = self._check_content_minification(content, asset_type)
                results_list.append({"source": source_name, "type": "inline", "status": "analyzed", **minification_info})
                processed_count += 1
                if minification_info["is_minified_heuristic"]: minified_count +=1
            except Exception as e:
                results_list.append({"source": source_name, "type": "inline", "status": "error_processing_content", "error": str(e)})
                errors_count += 1

        overall_status = "completed"
        if errors_count > 0 and processed_count == 0:
            overall_status = "error_all_failed"
        elif errors_count > 0:
            overall_status = "completed_with_errors"
        
        total_considered = len(external_asset_urls) + len(inline_assets_content)
        summary = f"{processed_count} {asset_type} assets (external & inline) checked. {minified_count} appear minified."
        if total_considered > processed_count:
            summary += f" {total_considered - processed_count} were skipped or had errors."

        return {test_name: {"status": overall_status, 
                            "assets_analyzed_count": processed_count, 
                            "assets_minified_count": minified_count,
                            "summary": summary,
                            "details": results_list}}


if __name__ == '__main__':
    pass
