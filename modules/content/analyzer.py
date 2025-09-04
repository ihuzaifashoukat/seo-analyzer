from bs4 import BeautifulSoup, Comment
from ..base_module import SEOModule
from .keywords import analyze_keywords
from .readability import calculate_flesch_reading_ease
from .ratio import calculate_text_to_html_ratio
from .spellcheck import perform_spell_check
from .intent import classify_search_intent
from .structure import analyze_content_structure


class ContentAnalyzer(SEOModule):
    """Analyzes content-related SEO aspects of a given URL."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.content_config = self.config
        self.top_n_keywords = self.content_config.get("top_n_keywords_count", 10)
        self.spellcheck_lang = self.content_config.get("spellcheck_language", "en")

    def analyze(self, url: str) -> dict:
        results = {"content_analysis_status": "pending"}
        soup = self.fetch_html(url)
        if not soup:
            results["content_analysis_status"] = "failed_to_fetch_html"
            results["error_message"] = f"Could not retrieve or parse HTML from {url}"
            return {self.module_name: results}

        text_soup = BeautifulSoup(str(soup), 'html.parser')
        for element in text_soup(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
            element.decompose()
        for comment in text_soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        raw_html_content = soup.prettify()
        text_content = text_soup.get_text(separator=" ", strip=True)
        # First paragraph sample and location-based keyword check
        first_para_tag = text_soup.find('p')
        first_para_text = first_para_tag.get_text(strip=True) if first_para_tag else None

        if not text_content.strip():
            results["content_analysis_status"] = "no_text_content_found"
            results["error_message"] = "No significant text content found on the page after stripping common elements."
            for key in ["keywordUsage", "mostCommonKeywords", "keywordCloudData", "flesch_reading_ease_score", "flesch_reading_interpretation", "textToHtmlRatioPercent", "spellCheck"]:
                results[key] = {} if "keyword" in key.lower() or "spell" in key.lower() else None
            return {self.module_name: results}

        target_keywords = self.content_config.get("target_keywords", [])
        results.update(analyze_keywords(text_content, target_keywords, self.top_n_keywords))
        if target_keywords:
            pk = target_keywords[0].lower()
            words_100 = ' '.join(text_content.split()[:100]).lower()
            results["primaryKeywordInFirst100Words"] = pk in words_100
            results["firstParagraphContainsPrimaryKeyword"] = bool(first_para_text and pk in first_para_text.lower())
            results["firstParagraphSample"] = first_para_text[:240] if first_para_text else None
        results.update(calculate_flesch_reading_ease(text_content))
        results.update(calculate_text_to_html_ratio(text_content, raw_html_content))
        results.update(perform_spell_check(text_content, self.spellcheck_lang))
        results.update(classify_search_intent(text_content, url))
        results.update(analyze_content_structure(text_soup, text_content))

        results["content_analysis_status"] = "completed"
        return {self.module_name: results}
