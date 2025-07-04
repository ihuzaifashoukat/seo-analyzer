# modules/scoring_module.py
from .base_module import SEOModule
import math

class ScoringModule(SEOModule):
    def __init__(self, config=None):
        super().__init__(config=config)
        self.scoring_config = self.config.get(self.module_name, {})
        self.default_weights = {
            # --- On-Page Factors ---
            "title_score": {"max_points": 10, "weight": 1.5}, # Meta Title Test
            "meta_description_score": {"max_points": 8, "weight": 1.2}, # Meta Description Test
            "headings_score": {"max_points": 10, "weight": 1.2}, # Heading Tags Test (H1, H2)
            "image_alt_text_score": {"max_points": 7, "weight": 1}, # Image Alt Test
            "responsive_image_score": {"max_points": 5, "weight": 0.8}, # Responsive Image Test
            "content_length_score": {"max_points": 8, "weight": 1},
            "internal_links_score": {"max_points": 5, "weight": 0.7}, # Basic link presence
            "broken_links_penalty": {"max_points": 10, "weight": 1.5}, # Penalty, not direct score
            "open_graph_score": {"max_points": 3, "weight": 0.7}, # Social Media Meta Tags Test (OG)
            "twitter_card_score": {"max_points": 3, "weight": 0.7}, # Social Media Meta Tags Test (Twitter)
            "seo_friendly_url_score": {"max_points": 5, "weight": 1}, # SEO Friendly URL Test
            "inline_css_penalty": {"max_points": 3, "weight": 0.5}, # Inline CSS Test (penalty)
            "deprecated_html_penalty": {"max_points": 5, "weight": 0.8}, # Deprecated HTML Tags Test (penalty)
            "flash_content_penalty": {"max_points": 5, "weight": 1}, # Flash Test (penalty)
            "frameset_penalty": {"max_points": 5, "weight": 1}, # Frameset Test (penalty)
            "unsafe_cross_origin_links_penalty": {"max_points": 4, "weight": 0.8},

            # --- Technical SEO Factors ---
            "https_score": {"max_points": 10, "weight": 1.5}, # SSL Checker and HTTPS Test
            "robots_txt_score": {"max_points": 5, "weight": 1}, # Robots.txt Test (presence, basic disallow)
            "sitemap_score": {"max_points": 5, "weight": 1}, # Sitemap Test (presence)
            "canonical_tag_score": {"max_points": 7, "weight": 1.2}, # Canonical Tag Test / URL Canonicalization Test
            "mobile_responsive_score": {"max_points": 10, "weight": 1.5}, # Meta Viewport Test + Heuristics
            "structured_data_score": {"max_points": 8, "weight": 1}, # Structured Data Test
            "meta_robots_score": {"max_points": 5, "weight": 1}, # Noindex/Nofollow Tag Test
            "http_version_score": {"max_points": 3, "weight": 0.7}, # HTTP2 Test
            "hsts_score": {"max_points": 4, "weight": 0.8}, # HSTS Test
            "mixed_content_penalty": {"max_points": 8, "weight": 1.2}, # Mixed Content Test (penalty)
            "url_redirects_penalty": {"max_points": 5, "weight": 0.8}, # URL Redirects Test (penalty for long chains/bad types)
            "custom_404_page_score": {"max_points": 3, "weight": 0.5}, # Custom 404 Error Page Test
            "html_page_size_score": {"max_points": 5, "weight": 0.8}, # HTML Page Size Test
            "dom_size_score": {"max_points": 5, "weight": 0.8}, # DOM Size Test
            "html_compression_score": {"max_points": 4, "weight": 1}, # HTML Compression/GZIP Test
            "page_cache_score": {"max_points": 5, "weight": 0.7}, # Page Cache Test
            "favicon_score": {"max_points": 2, "weight": 0.5}, # Favicon Test
            "charset_score": {"max_points": 2, "weight": 0.8}, # Charset Declaration Test
            "doctype_score": {"max_points": 2, "weight": 1}, # Doctype Test

            # --- Content Analysis Factors ---
            "readability_score": {"max_points": 10, "weight": 1},
            "keyword_usage_score": {"max_points": 10, "weight": 1.2}, # Keywords Usage Test
            "most_common_keywords_score": {"max_points": 5, "weight": 0.8}, # Most Common Keywords Test (informational, less direct score impact)
            "text_html_ratio_score": {"max_points": 5, "weight": 0.7},
            "spell_check_penalty": {"max_points": 5, "weight": 0.8}, # Spell Check Test (penalty)
            
            "category_weights": { "OnPage": 0.40, "Technical": 0.35, "Content": 0.25 }
        }
        # Override defaults with config from file
        for key, value in self.scoring_config.get("weights", {}).items():
            if key in self.default_weights:
                if isinstance(self.default_weights[key], dict) and isinstance(value, dict):
                    self.default_weights[key].update(value)
                else: self.default_weights[key] = value
        if "category_weights" in self.scoring_config:
            self.default_weights["category_weights"].update(self.scoring_config["category_weights"])

    def analyze(self, url: str, full_report_data: dict = None) -> dict:
        if not full_report_data:
            return {self.module_name: {"scoring_status": "error", "error_message": "No report data."}}

        on_page_data = full_report_data.get("OnPageAnalyzer", {})
        tech_data = full_report_data.get("TechnicalSEOAnalyzer", {})
        content_data = full_report_data.get("ContentAnalyzer", {})

        scores = {
            "on_page": {"earned_points": 0, "max_points": 0, "issues": [], "successes": []},
            "technical": {"earned_points": 0, "max_points": 0, "issues": [], "successes": []},
            "content": {"earned_points": 0, "max_points": 0, "issues": [], "successes": []},
        }

        self._score_on_page(on_page_data, scores["on_page"])
        self._score_technical(tech_data, scores["technical"])
        self._score_content(content_data, scores["content"])
        
        final_scores = {}
        for category, data in scores.items():
            cat_score = (data["earned_points"] / data["max_points"] * 100) if data["max_points"] > 0 else 0
            final_scores[f"{category}_score_percent"] = round(max(0, min(cat_score, 100)), 1) # Clamp between 0-100
            final_scores[f"{category}_issues"] = data["issues"]
            final_scores[f"{category}_successes"] = data["successes"]

        overall_score = 0; total_weight = 0
        cat_weights = self.default_weights["category_weights"]
        for cat_name, weight in cat_weights.items():
            score_key = f"{cat_name.lower()}_score_percent"
            if score_key in final_scores and final_scores[score_key] is not None:
                 overall_score += final_scores[score_key] * weight
                 total_weight += weight
        
        final_scores["overall_seo_score_percent"] = round(overall_score / total_weight, 1) if total_weight > 0 else 0
        final_scores["scoring_status"] = "completed"
        return {self.module_name: final_scores}

    def _add_score(self, category_data, check_name, earned, max_points_override=None, issue_msg=None, success_msg=None, is_penalty=False):
        rule = self.default_weights.get(check_name, {"max_points": 0, "weight": 1})
        max_p = max_points_override if max_points_override is not None else rule["max_points"]
        
        # For penalties, 'earned' is the amount to deduct from max_p.
        # The actual points added to 'earned_points' will be (max_p - earned_penalty)
        actual_earned = (max_p - earned) if is_penalty else earned
        
        category_data["earned_points"] += actual_earned * rule["weight"]
        category_data["max_points"] += max_p * rule["weight"]
        
        title_cased_check_name = check_name.replace('_score','').replace('_penalty','').replace('_',' ').title()

        if is_penalty:
            if earned > 0 and issue_msg: # If there's a penalty amount
                category_data["issues"].append(f"{title_cased_check_name}: {issue_msg} (Penalty: {earned:.1f}/{max_p:.1f})")
            elif success_msg : # No penalty applied
                 category_data["successes"].append(f"{title_cased_check_name}: {success_msg} (Score: {max_p:.1f}/{max_p:.1f})")
        else: # Regular score
            if earned < max_p * 0.8 and issue_msg: # If less than 80% and has issue message
                category_data["issues"].append(f"{title_cased_check_name}: {issue_msg} (Score: {earned:.1f}/{max_p:.1f})")
            elif earned >= max_p * 0.8 and success_msg:
                 category_data["successes"].append(f"{title_cased_check_name}: {success_msg} (Score: {earned:.1f}/{max_p:.1f})")


    def _score_on_page(self, data, score_data):
        if not data or not data.get("isLoaded"): return

        # Title
        max_p = self.default_weights["title_score"]["max_points"]
        if data.get("isTitle"):
            self._add_score(score_data, "title_score", max_p if data.get("isTitleEnoughLong") else max_p * 0.3, issue_msg="Title length suboptimal.", success_msg="Title present and well-sized.")
        else: self._add_score(score_data, "title_score", 0, issue_msg="Title missing.")

        # Meta Description
        max_p = self.default_weights["meta_description_score"]["max_points"]
        if data.get("isMetaDescription"):
            self._add_score(score_data, "meta_description_score", max_p if data.get("isMetaDescriptionEnoughLong") else max_p * 0.3, issue_msg="Meta description length suboptimal.", success_msg="Meta description present and well-sized.")
        else: self._add_score(score_data, "meta_description_score", 0, issue_msg="Meta description missing.")

        # Headings
        max_p_h = self.default_weights["headings_score"]["max_points"]; h_earned = 0
        if data.get("isH1"): h_earned += max_p_h * (0.6 if data.get("isH1OnlyOne") else 0.3)
        else: score_data["issues"].append("Headings: H1 tag missing.")
        if data.get("isH2"): h_earned += max_p_h * 0.4
        self._add_score(score_data, "headings_score", h_earned, issue_msg="Heading structure (H1/H2) needs improvement.", success_msg="Good H1/H2 usage.")

        # Image Alt Text
        max_p = self.default_weights["image_alt_text_score"]["max_points"]
        missing_alt = data.get("notOptimizedImagesCount", 0); total_img = data.get("total_images_on_page", 0)
        if total_img > 0: self._add_score(score_data, "image_alt_text_score", max_p * ((total_img - missing_alt) / total_img), issue_msg=f"{missing_alt} images missing alt text.", success_msg="Most images have alt text.")
        else: self._add_score(score_data, "image_alt_text_score", max_p, success_msg="No images to check for alt text.")
        
        # Responsive Images
        max_p = self.default_weights["responsive_image_score"]["max_points"]
        resp_issues = data.get("responsiveImageIssuesCount", 0)
        if total_img > 0: self._add_score(score_data, "responsive_image_score", max_p * ((total_img - resp_issues) / total_img), issue_msg=f"{resp_issues} images may not be responsive.", success_msg="Images appear responsive.")
        else: self._add_score(score_data, "responsive_image_score", max_p, success_msg="No images to check for responsiveness.")

        # Content Length
        self._add_score(score_data, "content_length_score", self.default_weights["content_length_score"]["max_points"] if data.get("isContentEnoughLong") else 0, issue_msg=f"Content may be too short (Words: {data.get('wordsCount',0)}).", success_msg="Content length is adequate.")

        # Broken Links Penalty
        max_p_bl = self.default_weights["broken_links_penalty"]["max_points"]
        broken_count = data.get("brokenLinksCount", 0); checked_count = data.get("linksCheckedForBrokenStatus", 0)
        penalty = 0
        if checked_count > 0 and broken_count > 0: penalty = min(max_p_bl, max_p_bl * (broken_count / (checked_count * 0.1))) # Max penalty if 10% are broken
        self._add_score(score_data, "broken_links_penalty", penalty, is_penalty=True, issue_msg=f"{broken_count} broken links found.", success_msg="No broken links found among checked links.")

        # Social Meta Tags
        self._add_score(score_data, "open_graph_score", self.default_weights["open_graph_score"]["max_points"] if data.get("hasOpenGraph") else 0, issue_msg="Open Graph tags missing.", success_msg="Open Graph tags present.")
        self._add_score(score_data, "twitter_card_score", self.default_weights["twitter_card_score"]["max_points"] if data.get("hasTwitterCards") else 0, issue_msg="Twitter Card tags missing.", success_msg="Twitter Card tags present.")

        # SEO Friendly URL
        self._add_score(score_data, "seo_friendly_url_score", self.default_weights["seo_friendly_url_score"]["max_points"] if data.get("isSeoFriendlyUrl", True) else 0, issue_msg=f"URL issues: {'; '.join(data.get('seoFriendlyUrlIssues',[]))}", success_msg="URL appears SEO-friendly.")

        # Penalties
        self._add_score(score_data, "inline_css_penalty", self.default_weights["inline_css_penalty"]["max_points"] * 0.1 * data.get("inlineCssCount",0) if data.get("hasInlineCss") else 0, is_penalty=True, issue_msg=f"{data.get('inlineCssCount',0)} inline style attributes found.", success_msg="No inline CSS found.")
        self._add_score(score_data, "deprecated_html_penalty", self.default_weights["deprecated_html_penalty"]["max_points"] if data.get("hasDeprecatedHtmlTags") else 0, is_penalty=True, issue_msg=f"Deprecated HTML tags found: {list(data.get('deprecatedHtmlTagsFound',{}).keys())}", success_msg="No deprecated HTML tags found.")
        self._add_score(score_data, "flash_content_penalty", self.default_weights["flash_content_penalty"]["max_points"] if data.get("hasFlashContent") else 0, is_penalty=True, issue_msg="Flash content detected.", success_msg="No Flash content detected.")
        self._add_score(score_data, "frameset_penalty", self.default_weights["frameset_penalty"]["max_points"] if data.get("hasFrameset") else 0, is_penalty=True, issue_msg="Frameset tag detected.", success_msg="No Frameset tag detected.")
        self._add_score(score_data, "unsafe_cross_origin_links_penalty", self.default_weights["unsafe_cross_origin_links_penalty"]["max_points"] * (data.get("unsafeCrossOriginLinksCount",0) * 0.2), is_penalty=True, issue_msg=f"{data.get('unsafeCrossOriginLinksCount',0)} unsafe cross-origin links.", success_msg="No unsafe cross-origin links found.")


    def _score_technical(self, data, score_data):
        if not data: return

        self._add_score(score_data, "https_score", self.default_weights["https_score"]["max_points"] if data.get("hasHttps") else 0, issue_msg="Site not using HTTPS.", success_msg="HTTPS enabled.")
        self._add_score(score_data, "robots_txt_score", self.default_weights["robots_txt_score"]["max_points"] if data.get("robotsTxtStatus") == "found" and not data.get("robotsTxtDisallowsAll") else 0, issue_msg="Robots.txt missing, inaccessible, or disallows all.", success_msg="Robots.txt found and accessible.")
        self._add_score(score_data, "sitemap_score", self.default_weights["sitemap_score"]["max_points"] if data.get("hasSitemap") else 0, issue_msg="Sitemap not found.", success_msg="Sitemap accessible.")
        self._add_score(score_data, "canonical_tag_score", self.default_weights["canonical_tag_score"]["max_points"] if data.get("hasCanonicalTag") else 0, issue_msg="Canonical tag missing.", success_msg="Canonical tag present.")
        self._add_score(score_data, "mobile_responsive_score", self.default_weights["mobile_responsive_score"]["max_points"] if data.get("mobileResponsive") else 0, issue_msg=f"Mobile responsiveness issues: {data.get('mobileFriendlinessNotes',[])}", success_msg="Page appears mobile-friendly.")
        self._add_score(score_data, "structured_data_score", self.default_weights["structured_data_score"]["max_points"] if data.get("hasSchema") else 0, issue_msg="No significant structured data found.", success_msg="Structured data present.")
        
        # Meta Robots
        max_p = self.default_weights["meta_robots_score"]["max_points"]
        if data.get("hasMetaNoindex"): self._add_score(score_data, "meta_robots_score", 0, issue_msg="Page is set to 'noindex'.")
        elif data.get("metaRobots"): self._add_score(score_data, "meta_robots_score", max_p, success_msg=f"Meta robots: {data.get('metaRobots')}")
        else: self._add_score(score_data, "meta_robots_score", max_p * 0.7, issue_msg="Meta robots tag missing.")

        self._add_score(score_data, "http_version_score", self.default_weights["http_version_score"]["max_points"] if data.get("httpVersion","").startswith("HTTP/2") or data.get("httpVersion","").startswith("HTTP/3") else 0, issue_msg="Not using HTTP/2 or HTTP/3.", success_msg=f"Using {data.get('httpVersion')}.")
        self._add_score(score_data, "hsts_score", self.default_weights["hsts_score"]["max_points"] if data.get("hstsHeader") else 0, issue_msg="HSTS header missing.", success_msg="HSTS header present.")
        self._add_score(score_data, "mixed_content_penalty", self.default_weights["mixed_content_penalty"]["max_points"] if data.get("hasMixedContent") else 0, is_penalty=True, issue_msg=f"{len(data.get('mixedContentItems',[]))} mixed content items found.", success_msg="No mixed content found.")
        
        # URL Redirects Penalty (simple: penalize if any redirects happened for the main URL)
        if data.get("hasRedirects"):
            redirect_count = max(len(data.get("redirectHistory", [])) - 1, 0)
            penalty = self.default_weights["url_redirects_penalty"]["max_points"] * 0.5 * redirect_count
            penalty = min(self.default_weights["url_redirects_penalty"]["max_points"], penalty)
            self._add_score(
                score_data,
                "url_redirects_penalty",
                penalty,
                is_penalty=True,
                issue_msg=f"{redirect_count} redirects for main URL.",
                success_msg="No redirects for main URL."
            )
        else:
            self._add_score(score_data, "url_redirects_penalty", 0, is_penalty=True, success_msg="No redirects for main URL.")


        self._add_score(score_data, "custom_404_page_score", self.default_weights["custom_404_page_score"]["max_points"] if data.get("hasCustom404PageHeuristic") else 0, issue_msg="Custom 404 page might be missing or generic.", success_msg="Custom 404 page detected.")
        
        # Page Size & DOM Size (penalize if too large - simplistic thresholds)
        page_size_kb = data.get("htmlPageSize", 0) / 1024
        if page_size_kb > 500: self._add_score(score_data, "html_page_size_score", 0, issue_msg=f"HTML page size is large ({page_size_kb:.0f}KB).")
        elif page_size_kb > 200: self._add_score(score_data, "html_page_size_score", self.default_weights["html_page_size_score"]["max_points"] * 0.5, issue_msg=f"HTML page size is moderate ({page_size_kb:.0f}KB).")
        else: self._add_score(score_data, "html_page_size_score", self.default_weights["html_page_size_score"]["max_points"], success_msg=f"HTML page size is good ({page_size_kb:.0f}KB).")

        dom_elements = data.get("domSize", 0)
        if dom_elements > 1500: self._add_score(score_data, "dom_size_score", 0, issue_msg=f"DOM size is very large ({dom_elements} elements).")
        elif dom_elements > 800: self._add_score(score_data, "dom_size_score", self.default_weights["dom_size_score"]["max_points"] * 0.5, issue_msg=f"DOM size is large ({dom_elements} elements).")
        else: self._add_score(score_data, "dom_size_score", self.default_weights["dom_size_score"]["max_points"], success_msg=f"DOM size is good ({dom_elements} elements).")

        self._add_score(score_data, "html_compression_score", self.default_weights["html_compression_score"]["max_points"] if "gzip" in data.get("htmlCompressionGzipTest","") or "br" in data.get("htmlCompressionGzipTest","") else 0, issue_msg="HTML compression (Gzip/Brotli) not detected.", success_msg="HTML compression enabled.")
        
        # Page Cache (basic: check if any cache control header is present)
        cache_headers = data.get("pageCacheHeaders", {})
        has_cache_directive = any(cache_headers.get(h) for h in ["Cache-Control", "Expires", "ETag"])
        self._add_score(score_data, "page_cache_score", self.default_weights["page_cache_score"]["max_points"] if has_cache_directive else 0, issue_msg="No significant client-side caching headers found.", success_msg="Caching headers detected.")
        
        self._add_score(score_data, "favicon_score", self.default_weights["favicon_score"]["max_points"] if data.get("favicon") else 0, issue_msg="Favicon missing.", success_msg="Favicon present.")
        self._add_score(score_data, "charset_score", self.default_weights["charset_score"]["max_points"] if data.get("isCharacterEncode") else 0, issue_msg="Charset declaration missing.", success_msg="Charset declared.")
        self._add_score(score_data, "doctype_score", self.default_weights["doctype_score"]["max_points"] if data.get("isDoctype") else 0, issue_msg="Doctype missing.", success_msg="Doctype declared.")


    def _score_content(self, data, score_data):
        if not data or data.get("content_analysis_status") != "completed":
            score_data["issues"].append("Content: Analysis module did not run or found no content.")
            return

        # Readability
        max_p = self.default_weights["readability_score"]["max_points"]
        f_score = data.get("flesch_reading_ease_score")
        if f_score is not None:
            if f_score >= 60: self._add_score(score_data, "readability_score", max_p, success_msg=f"Good readability (Flesch: {f_score}).")
            elif f_score >= 30: self._add_score(score_data, "readability_score", max_p * 0.5, issue_msg=f"Readability could be improved (Flesch: {f_score}).")
            else: self._add_score(score_data, "readability_score", max_p * 0.1, issue_msg=f"Content very difficult to read (Flesch: {f_score}).")
        else: self._add_score(score_data, "readability_score", 0, issue_msg="Readability score N/A.")

        # Keyword Usage
        max_p_kw = self.default_weights["keyword_usage_score"]["max_points"]
        kw_usage = data.get("keywordUsage", {})
        if data.get("target_keywords_analyzed"): # Only if keywords were targeted
            found_kws = sum(1 for dets in kw_usage.values() if dets.get("phrase_count",0) > 0)
            total_targeted = len(data.get("target_keywords_analyzed",[]))
            if total_targeted > 0:
                self._add_score(score_data, "keyword_usage_score", max_p_kw * (found_kws / total_targeted), issue_msg=f"{total_targeted - found_kws} target keywords not found or low presence.", success_msg="Target keywords effectively used.")
            else: # Should not happen if target_keywords_analyzed is populated
                 self._add_score(score_data, "keyword_usage_score", max_p_kw, success_msg="No specific keywords targeted for usage analysis.")
        else:
            self._add_score(score_data, "keyword_usage_score", max_p_kw, success_msg="No specific keywords targeted for usage analysis.") # Neutral if no keywords provided

        # Most Common Keywords (informational, small score for having diverse content)
        if data.get("mostCommonKeywords"): self._add_score(score_data, "most_common_keywords_score", self.default_weights["most_common_keywords_score"]["max_points"], success_msg="Common keywords identified.")
        else: self._add_score(score_data, "most_common_keywords_score", 0, issue_msg="Could not identify common keywords.")


        # Text-HTML Ratio
        max_p = self.default_weights["text_html_ratio_score"]["max_points"]
        ratio_stat = data.get("textToHtmlRatioStatus")
        ratio_val = data.get("textToHtmlRatioPercent")
        if ratio_stat == "low_ratio": self._add_score(score_data, "text_html_ratio_score", max_p * 0.2, issue_msg=f"Text-to-HTML ratio low ({ratio_val}%).")
        elif ratio_stat == "calculated" or ratio_stat == "high_ratio": self._add_score(score_data, "text_html_ratio_score", max_p, success_msg=f"Text-to-HTML ratio is {ratio_val}%.")
        else: self._add_score(score_data, "text_html_ratio_score", 0, issue_msg="Text-to-HTML ratio N/A.")

        # Spell Check Penalty
        spell_check_data = data.get("spellCheck", {})
        if spell_check_data.get("status") == "completed":
            misspelled_count = spell_check_data.get("misspelled_words_count", 0)
            # Penalize more for higher percentage of misspelled words, up to a cap
            penalty = min(self.default_weights["spell_check_penalty"]["max_points"], misspelled_count * 0.5) 
            self._add_score(score_data, "spell_check_penalty", penalty, is_penalty=True, issue_msg=f"{misspelled_count} potential spelling errors found.", success_msg="No significant spelling errors found.")
        elif spell_check_data.get("status") == "skipped_pyspellchecker_not_installed":
             self._add_score(score_data, "spell_check_penalty", 0, is_penalty=True, issue_msg="Spell check skipped (pyspellchecker not installed).")
