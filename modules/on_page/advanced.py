import re
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

try:
    # Reuse content utilities for tokenization/stopwords
    from ..content.text_utils import get_words_from_text, STOPWORDS
except Exception:  # Fallback minimal
    STOPWORDS = set()
    def get_words_from_text(text: str, remove_stopwords=True, min_word_length=3):
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        if remove_stopwords:
            words = [w for w in words if w not in STOPWORDS and len(w) >= min_word_length]
        else:
            words = [w for w in words if len(w) >= min_word_length]
        return words


def analyze_keyword_placement(soup: BeautifulSoup, visible_text: str, target_keywords: list[str] | None) -> dict:
    primary_kw = (target_keywords[0].strip() if target_keywords else None) or None
    sec_kws = target_keywords[1:] if target_keywords and len(target_keywords) > 1 else []

    first_paragraph = None
    first_p_tag = soup.find('p')
    if first_p_tag:
        first_paragraph = first_p_tag.get_text(strip=True)

    total_occurrences = 0
    in_first_para = False
    secondary_found = []
    if primary_kw and visible_text:
        total_occurrences = visible_text.lower().count(primary_kw.lower())
        in_first_para = bool(first_paragraph and primary_kw.lower() in first_paragraph.lower())
    if sec_kws and visible_text:
        low = visible_text.lower()
        for s in sec_kws:
            if s and s.lower() in low:
                secondary_found.append(s)

    # LSI/semantic candidates: top content words excluding the keyword terms
    tokens = get_words_from_text(visible_text or '', remove_stopwords=True, min_word_length=4)
    ignore_terms = set([t.lower() for t in (target_keywords or [])])
    from collections import Counter
    counts = Counter([t for t in tokens if t not in ignore_terms])
    lsi_candidates = [w for w, _ in counts.most_common(20)]

    return {
        "primaryKeyword": primary_kw,
        "primaryKeywordOccurrences": total_occurrences,
        "primaryKeywordInFirstParagraph": in_first_para,
        "secondaryKeywordsFound": secondary_found,
        "lsiCandidates": lsi_candidates,
        "firstParagraphSample": first_paragraph[:240] if first_paragraph else None,
    }


def _slugify_like(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'[^a-z0-9\-]+', '-', s)
    s = re.sub(r'-{2,}', '-', s)
    return s.strip('-')


def check_url_slug_quality(url: str, primary_keyword: str | None) -> dict:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    segments = [seg for seg in path.split('/') if seg]
    slug = segments[-1] if segments else ''
    has_hyphens = '-' in slug
    special_chars = bool(re.search(r'[^a-zA-Z0-9\-]', slug))
    contains_primary = bool(primary_keyword and primary_keyword.lower() in slug.lower())
    # Stopword heaviness
    slug_words = re.findall(r'[a-zA-Z0-9]+', slug.lower())
    stopwords_in_slug = sum(1 for w in slug_words if w in STOPWORDS)
    return {
        "urlSlug": slug,
        "urlSlugHasHyphens": has_hyphens,
        "urlSlugHasSpecialChars": special_chars,
        "urlContainsPrimaryKeyword": contains_primary,
        "urlSlugStopwordsCount": stopwords_in_slug,
        "urlSlugNormalized": _slugify_like(slug) if slug else '',
    }


def analyze_images_keywords(soup: BeautifulSoup, primary_keyword: str | None) -> dict:
    imgs = soup.find_all('img')
    kw_in_alt = 0
    descriptive_filenames_issues = []
    for img in imgs:
        alt = (img.get('alt') or '').strip().lower()
        src = (img.get('src') or '').strip()
        if primary_keyword and primary_keyword.lower() in alt:
            kw_in_alt += 1
        # Filename heuristics
        if src and not src.startswith(('data:', 'blob:')):
            name = src.split('/')[-1]
            name_no_ext = name.split('?')[0]
            base = re.sub(r'\.[a-zA-Z0-9]+$', '', name_no_ext)
            base_low = base.lower()
            if re.fullmatch(r'(img|image|photo|pic|dsc)[-_]?\d{2,}', base_low) or len(base_low) <= 3:
                descriptive_filenames_issues.append(src)
    return {
        "imagesWithPrimaryKeywordAlt": kw_in_alt,
        "imageDescriptiveFilenameIssues": descriptive_filenames_issues,
        "imageDescriptiveFilenameIssuesCount": len(descriptive_filenames_issues),
    }


def detect_breadcrumbs(soup: BeautifulSoup) -> dict:
    has_breadcrumb_schema = bool(soup.find(attrs={"itemtype": re.compile("schema.org/BreadcrumbList", re.I)}))
    breadcrumb_like = soup.find(class_=re.compile("breadcrumb", re.I)) or soup.find("nav", class_=re.compile("breadcrumb", re.I))
    return {
        "hasBreadcrumbs": bool(has_breadcrumb_schema or breadcrumb_like),
    }


def detect_share_buttons(soup: BeautifulSoup) -> dict:
    hrefs = [a.get('href', '') for a in soup.find_all('a', href=True)]
    share_domains = ['facebook.com/sharer', 'twitter.com/intent', 'linkedin.com/share', 'wa.me/', 'api.whatsapp.com', 't.me/share']
    has_share = any(any(dom in h for dom in share_domains) for h in hrefs)
    classes_text = ' '.join([c for tag in soup.find_all(True) for c in (tag.get('class') or [])])
    if 'share' in classes_text.lower():
        has_share = True
    return {"hasShareButtons": has_share}


def extract_content_dates(soup: BeautifulSoup, head_request_func, url: str, timeout: int) -> dict:
    # Meta tags commonly used for dates
    published = None; modified = None
    sel = [
        ("meta", {"property": "article:published_time"}, "content"),
        ("meta", {"name": re.compile(r"date|dc.date|dcterms\.created", re.I)}, "content"),
        ("time", {"itemprop": re.compile(r"datePublished|dateCreated", re.I)}, "datetime"),
        ("meta", {"property": "article:modified_time"}, "content"),
        ("time", {"itemprop": re.compile(r"dateModified", re.I)}, "datetime"),
    ]
    for tag, attrs, attr_name in sel:
        for el in soup.find_all(tag, attrs=attrs):
            val = el.get(attr_name) or el.get_text(strip=True)
            if not val:
                continue
            if 'publish' in str(attrs).lower() or 'datecreated' in str(attrs).lower():
                if not published:
                    published = val
            elif 'modified' in str(attrs).lower() or 'datemodified' in str(attrs).lower():
                if not modified:
                    modified = val
    last_mod_header = None
    try:
        resp, _ = head_request_func(url, timeout=timeout, allow_redirects=True)
        if resp is not None:
            last_mod_header = resp.headers.get('Last-Modified')
    except Exception:
        pass
    return {
        "publishedDate": published,
        "modifiedDate": modified,
        "lastModifiedHeader": last_mod_header,
    }


def analyze_forms(soup: BeautifulSoup) -> dict:
    forms = soup.find_all('form')
    inputs = sum(len(f.find_all(['input','select','textarea'])) for f in forms)
    return {
        'formCount': len(forms),
        'formFieldCount': inputs,
    }
