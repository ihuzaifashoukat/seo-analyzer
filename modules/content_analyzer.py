# modules/content_analyzer.py
import re
from bs4 import BeautifulSoup, Comment
from collections import Counter
# pip install pyspellchecker
try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None


from .base_module import SEOModule

# Basic list of English stopwords (can be expanded or made configurable)
STOPWORDS = set([
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in", 
    "into", "is", "it", "no", "not", "of", "on", "or", "such", "that", "the", 
    "their", "then", "there", "these", "they", "this", "to", "was", "will", "with",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", 
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", 
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", 
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", 
    "at", "by", "for", "with", "about", "against", "between", "into", "through", 
    "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", 
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", 
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", 
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", 
    "don", "should", "now"
])

class ContentAnalyzer(SEOModule):
    """
    Analyzes content-related SEO aspects of a given URL.
    """

    def __init__(self, config=None):
        super().__init__(config=config)
        self.content_config = self.config # Specific config for this module
        self.top_n_keywords = self.content_config.get("top_n_keywords_count", 10)
        self.spellcheck_lang = self.content_config.get("spellcheck_language", "en")


    def analyze(self, url: str) -> dict:
        results = {
            "content_analysis_status": "pending"
        }
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
        
        if not text_content.strip():
            results["content_analysis_status"] = "no_text_content_found"
            results["error_message"] = "No significant text content found on the page after stripping common elements."
            # Set defaults for content-dependent checks
            keys_needing_content = [
                "keywordUsage", "mostCommonKeywords", "keywordCloudData", 
                "flesch_reading_ease_score", "flesch_reading_interpretation",
                "textToHtmlRatioPercent", "spellCheck"
            ]
            for key in keys_needing_content:
                results[key] = {} if "keyword" in key.lower() or "spell" in key.lower() else None
            return {self.module_name: results}

        target_keywords = self.content_config.get("target_keywords", [])
        
        # Existing and enhanced keyword checks
        keyword_analysis_results = self._analyze_keywords(text_content, target_keywords)
        results.update(keyword_analysis_results) # Includes "keywordUsage", "mostCommonKeywords", "keywordCloudData"

        results.update(self._calculate_flesch_reading_ease(text_content))
        results.update(self._calculate_text_to_html_ratio(text_content, raw_html_content))
        results.update(self._perform_spell_check(text_content)) # Spell Check Test
        
        # Removed relatedKeywordsTest and competitorDomainsTest as they require external APIs.

        results["content_analysis_status"] = "completed"
        return {self.module_name: results}

    def _get_words_from_text(self, text: str, remove_stopwords=True, min_word_length=3) -> list:
        """Helper to get clean words from text."""
        text = text.lower()
        words = re.findall(r'\b[a-z0-9]+\b', text) # Alphanumeric words
        if remove_stopwords:
            words = [word for word in words if word not in STOPWORDS and len(word) >= min_word_length]
        else:
            words = [word for word in words if len(word) >= min_word_length]
        return words

    def _analyze_keywords(self, text_content: str, target_keywords: list) -> dict:
        # "Most Common Keywords Test", "Keywords Usage Test", "Keywords Cloud Test" (data for)
        
        # For most common keywords (general analysis)
        all_words_for_common = self._get_words_from_text(text_content, remove_stopwords=True, min_word_length=4) # Longer words for common
        common_word_counts = Counter(all_words_for_common)
        most_common_kws = [{"keyword": kw, "count": count} for kw, count in common_word_counts.most_common(self.top_n_keywords)]

        # For target keyword usage (specific analysis)
        # Use a version of text_content that is tokenized but might retain stopwords if they are part of a phrase
        # For simplicity, we'll use the same tokenization as for common words for density calculation base.
        # A more advanced approach would handle phrases better.
        
        base_words_for_density = self._get_words_from_text(text_content, remove_stopwords=False, min_word_length=1) # All words for density base
        total_words_for_density = len(base_words_for_density) if base_words_for_density else 1 # Avoid division by zero

        target_keyword_usage = {}
        if target_keywords:
            for kw_phrase in target_keywords:
                kw_phrase_lower = kw_phrase.lower()
                # Simple phrase count
                phrase_count = text_content.lower().count(kw_phrase_lower)
                density = (phrase_count / total_words_for_density * 100) if total_words_for_density > 0 else 0
                
                target_keyword_usage[kw_phrase] = {
                    "phrase_count": phrase_count,
                    "density_percent": round(density, 2)
                }
        
        return {
            "keywordUsage": target_keyword_usage, # Specific target keywords
            "mostCommonKeywords": most_common_kws, # General top keywords
            "keywordCloudData": most_common_kws # Same data can be used for a cloud
        }


    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        if not word: return 0
        word = re.sub(r'[^a-z]', '', word)
        if len(word) <= 3: return 1
        if word.endswith("e") and not word.endswith("le") and len(word) > 1:
            word = word[:-1]
        vowels = "aeiouy"
        syllable_count = 0
        prev_char_was_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_char_was_vowel:
                syllable_count += 1
            prev_char_was_vowel = is_vowel
        return max(1, syllable_count)

    def _calculate_flesch_reading_ease(self, text_content: str) -> dict:
        words = re.findall(r'\b[\w\'-]+\b', text_content)
        sentences = re.split(r'[.!?]+', text_content)
        words = [word for word in words if word]
        sentences = [sentence for sentence in sentences if sentence.strip()]
        num_words = len(words)
        num_sentences = len(sentences)
        
        if num_words < 100 or num_sentences < 3: # Need sufficient content
            return {
                "flesch_reading_ease_score": None,
                "flesch_reading_interpretation": "Not enough content (at least 100 words and 3 sentences recommended).",
            }
        num_syllables = sum(self._count_syllables(word) for word in words)
        try:
            score = round(206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words), 2)
        except ZeroDivisionError:
             return {"flesch_reading_ease_score": None, "flesch_reading_interpretation": "Calculation error."}

        interpretation = "N/A"
        if score >= 90: interpretation = "Very easy to read."
        elif score >= 70: interpretation = "Easy to read."
        elif score >= 60: interpretation = "Plain English."
        elif score >= 50: interpretation = "Fairly difficult to read."
        elif score >= 30: interpretation = "Difficult to read."
        else: interpretation = "Very difficult to read."
        return {"flesch_reading_ease_score": score, "flesch_reading_interpretation": interpretation}

    def _calculate_text_to_html_ratio(self, text_content: str, html_content: str) -> dict:
        len_text = len(text_content)
        len_html = len(html_content)
        if len_html == 0: ratio = 0
        else: ratio = round((len_text / len_html) * 100, 2)
        status = "calculated"
        if ratio < 15: status = "low_ratio" # Common threshold for "thin"
        elif ratio > 70: status = "high_ratio" 
        return {"textToHtmlRatioPercent": ratio, "textToHtmlRatioStatus": status}

    def _perform_spell_check(self, text_content: str) -> dict:
        # "Spell Check Test"
        if SpellChecker is None:
            return {"spellCheck": {"status": "skipped_pyspellchecker_not_installed", "misspelled_words_sample": []}}
        
        try:
            spell = SpellChecker(language=self.spellcheck_lang)
            # Get words, but don't remove stopwords for spell checking, and keep original case for context
            words_for_spellcheck = re.findall(r'\b[a-zA-Z]+\b', text_content) # Only alphabetic words
            
            # Reduce number of words to check for performance if text is very long
            if len(words_for_spellcheck) > 1000: # Arbitrary limit
                words_for_spellcheck = words_for_spellcheck[:1000]

            misspelled = list(spell.unknown(words_for_spellcheck)) # Find unknown words
            
            # Further filter: common names, acronyms, or very short words might be flagged.
            # This is a basic filter. More advanced would use a custom dictionary.
            misspelled_filtered = [word for word in misspelled if len(word) > 3 and not word.isupper()]


            return {"spellCheck": {
                "status": "completed",
                "language": self.spellcheck_lang,
                "misspelled_words_sample": misspelled_filtered[:20], # Sample of misspelled words
                "misspelled_words_count": len(misspelled_filtered)
                }
            }
        except Exception as e:
            return {"spellCheck": {"status": "error", "error_message": str(e), "misspelled_words_sample": []}}


if __name__ == '__main__':
    pass
