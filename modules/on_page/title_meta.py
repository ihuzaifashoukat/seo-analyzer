import re
from collections import Counter
from bs4 import BeautifulSoup

# Approximate pixel width using simple per-character weights (heuristic)
_CHAR_PX = {
    'i': 4, 'l': 4, 'j': 5, 't': 6, 'f': 6, 'r': 6, ' ': 3,
    'I': 6, 'J': 7, '1': 7, 's': 7, 'z': 7,
    'a': 7, 'c': 7, 'e': 7, 'o': 8, 'u': 8,
    'k': 8, 'v': 8, 'x': 8, 'y': 8,
    'A': 9, 'B': 10, 'C': 10, 'D': 10, 'E': 9, 'F': 9, 'G': 10, 'H': 10, 'K': 10, 'L': 9, 'M': 12, 'N': 10, 'O': 10, 'P': 10, 'Q': 10, 'R': 10, 'S': 9, 'T': 9, 'U': 10, 'V': 10, 'W': 12, 'X': 10, 'Y': 10, 'Z': 9,
}

def _estimate_pixels(text: str) -> int:
    if not text:
        return 0
    total = 0
    for ch in text:
        total += _CHAR_PX.get(ch, _CHAR_PX.get(ch.lower(), 9))
    return total

POWER_WORDS = set([
    'ultimate','proven','best','top','essential','secret','exclusive','easy','quick','simple','step-by-step','definitive','complete','powerful','effective','free','instant','guaranteed','new','now','today'
])

def _has_power_words(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(pw in low for pw in POWER_WORDS)

def _keyword_near_start(title: str, primary_kw: str, pos_threshold: int = 20) -> bool:
    if not title or not primary_kw:
        return False
    idx = title.lower().find(primary_kw.lower())
    return idx != -1 and idx <= pos_threshold

def check_title(soup: BeautifulSoup, title_min_len: int, title_max_len: int, target_keywords: list[str] | None = None) -> dict:
    title_tags = soup.find_all("title")
    title_tag = title_tags[0] if title_tags else None
    title_text = title_tag.string.strip() if title_tag and title_tag.string else None
    title_length = len(title_text) if title_text else 0
    title_pixels = _estimate_pixels(title_text) if title_text else 0

    status = "good"
    if not title_text:
        status = "missing"
    elif title_length < title_min_len:
        status = "too_short"
    elif title_length > title_max_len:
        status = "too_long"

    duplicate_words_count = 0
    if title_text:
        words = re.findall(r'\b\w+\b', title_text.lower())
        counts = Counter(words)
        duplicate_words_count = sum(1 for word, count in counts.items() if count > 1 and len(word) > 2)

    primary_kw = (target_keywords[0].strip() if target_keywords else None) or None
    has_primary_kw = bool(primary_kw and title_text and primary_kw.lower() in title_text.lower())
    near_start = _keyword_near_start(title_text or '', primary_kw or '') if has_primary_kw else False
    has_brand = False
    if title_text and ("|" in title_text or " - " in title_text):
        # Heuristic: text after last delimiter looks like brand
        has_brand = True

    return {
        "title": title_text,
        "isTitle": bool(title_text),
        "titleLength": title_length,
        "isTitleEnoughLong": status == "good" if title_text else False,
        "titlePixelWidth": title_pixels,
        "titleWithinPixelLimit": title_pixels <= 600 if title_text else False,
        "titleDuplicateWords": duplicate_words_count,
        "titleTagCount": len(title_tags),
        "hasMultipleTitleTags": len(title_tags) > 1,
        "titleHasBrandName": has_brand,
        "titleUsesPowerWords": _has_power_words(title_text or ''),
        "titlePrimaryKeywordPresent": has_primary_kw,
        "titleKeywordNearStart": near_start,
    }

CTA_PHRASES = set([
    'learn more','read more','buy now','shop now','get started','try now','sign up','contact us','book now','download','discover','find out','see how','start now','join now','request a quote','subscribe'
])

def _has_cta(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(phrase in low for phrase in CTA_PHRASES)

def check_meta_description(soup: BeautifulSoup, desc_min_len: int, desc_max_len: int, target_keywords: list[str] | None = None) -> dict:
    meta_desc_tags = soup.find_all("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_desc_tag = meta_desc_tags[0] if meta_desc_tags else None
    meta_desc_text = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None
    meta_desc_length = len(meta_desc_text) if meta_desc_text else 0
    meta_pixels = _estimate_pixels(meta_desc_text) if meta_desc_text else 0

    status = "good"
    if not meta_desc_text:
        status = "missing"
    elif meta_desc_length < desc_min_len:
        status = "too_short"
    elif meta_desc_length > desc_max_len:
        status = "too_long"

    primary_kw = (target_keywords[0].strip() if target_keywords else None) or None
    meta_has_primary_kw = bool(primary_kw and meta_desc_text and primary_kw.lower() in meta_desc_text.lower())

    return {
        "metaDescription": meta_desc_text,
        "isMetaDescription": bool(meta_desc_text),
        "descriptionLength": meta_desc_length,
        "isMetaDescriptionEnoughLong": status == "good" if meta_desc_text else False,
        "metaDescriptionPixelWidth": meta_pixels,
        "metaDescriptionWithinPixelLimit": meta_pixels <= 680 if meta_desc_text else False,
        "metaDescriptionTagCount": len(meta_desc_tags),
        "hasMultipleMetaDescriptionTags": len(meta_desc_tags) > 1,
        "metaHasCallToAction": _has_cta(meta_desc_text or ''),
        "metaContainsPrimaryKeyword": meta_has_primary_kw,
    }
