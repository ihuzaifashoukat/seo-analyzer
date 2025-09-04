from collections import Counter
from .text_utils import get_words_from_text

def _ngrams(tokens: list[str], n: int) -> Counter:
    if n <= 1:
        return Counter(tokens)
    grams = [' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    return Counter(grams)

def _simple_stem(word: str) -> str:
    # Very light stemming for English-like words
    w = word.lower()
    for suf in ['ing','edly','edly','ed','ly','s','es']:
        if w.endswith(suf) and len(w) > len(suf)+2:
            return w[:-len(suf)]
    return w

def analyze_keywords(text_content: str, target_keywords: list, top_n_keywords: int) -> dict:
    # Most Common Keywords Test, Keywords Usage Test, Keywords Cloud Data
    all_words_for_common = get_words_from_text(text_content, remove_stopwords=True, min_word_length=4)
    common_word_counts = Counter(all_words_for_common)
    most_common_kws = [{"keyword": kw, "count": count} for kw, count in common_word_counts.most_common(top_n_keywords)]

    base_words_for_density = get_words_from_text(text_content, remove_stopwords=False, min_word_length=1)
    total_words_for_density = len(base_words_for_density) if base_words_for_density else 1

    target_keyword_usage = {}
    if target_keywords:
        for kw_phrase in target_keywords:
            kw_phrase_lower = kw_phrase.lower()
            phrase_count = text_content.lower().count(kw_phrase_lower)
            density = (phrase_count / total_words_for_density * 100) if total_words_for_density > 0 else 0
            # Simple semantic variants via light stemming
            stem = _simple_stem(kw_phrase_lower.split()[0])
            variants_found = [w for w in all_words_for_common if _simple_stem(w) == stem and w != kw_phrase_lower]
            target_keyword_usage[kw_phrase] = {
                "phrase_count": phrase_count,
                "density_percent": round(density, 2),
                "semantic_variants_found": list(sorted(set(variants_found)))[:8],
            }

    # N-gram clouds for topic coverage
    tokens_no_stop = get_words_from_text(text_content, remove_stopwords=True, min_word_length=3)
    bigrams = _ngrams(tokens_no_stop, 2)
    trigrams = _ngrams(tokens_no_stop, 3)
    top_bigrams = [{"ngram": g, "count": c} for g, c in bigrams.most_common(10)]
    top_trigrams = [{"ngram": g, "count": c} for g, c in trigrams.most_common(10)]

    result = {
        "keywordUsage": target_keyword_usage,
        "mostCommonKeywords": most_common_kws,
        "keywordCloudData": most_common_kws,
        "topBigrams": top_bigrams,
        "topTrigrams": top_trigrams,
    }
    if target_keywords:
        result["target_keywords_analyzed"] = target_keywords
    return result
