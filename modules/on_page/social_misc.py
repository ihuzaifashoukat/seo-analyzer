import re
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup

def check_content_stats(page_text_content: str, soup: BeautifulSoup, content_min_words: int) -> dict:
    import re as _re
    words = _re.findall(r'\b\w+\b', page_text_content.lower())
    word_count = len(words)
    paragraphs_count = len(soup.find_all("p"))
    has_lorem_ipsum = "lorem ipsum" in page_text_content.lower()
    return {
        "wordsCount": word_count,
        "isContentEnoughLong": word_count >= content_min_words,
        "paragraphs": paragraphs_count,
        "loremIpsum": has_lorem_ipsum,
    }

def check_iframes(soup: BeautifulSoup) -> dict:
    iframes = soup.find_all("iframe")
    return {"isNotIframe": len(iframes) == 0, "iframes": len(iframes)}

def check_apple_touch_icon(soup: BeautifulSoup, base_url: str) -> dict:
    import re as _re
    icon_tag = soup.find("link", rel=_re.compile(r"apple-touch-icon", _re.I))
    icon_url = urljoin(base_url, icon_tag["href"]) if icon_tag and icon_tag.get("href") else None
    return {"appleTouchIcon": bool(icon_url), "appleTouchIconUrl": icon_url}

def check_script_and_css_files(soup: BeautifulSoup) -> dict:
    js_files = len(soup.find_all("script", src=True))
    css_files = len(soup.find_all("link", rel="stylesheet", href=True))
    return {"javascriptFiles": js_files, "cssFiles": css_files}

def check_strong_tags(soup: BeautifulSoup) -> dict:
    strong_tags = len(soup.find_all("strong"))
    b_tags = len(soup.find_all("b"))
    return {"strongTags": strong_tags + b_tags}

def check_open_graph(soup: BeautifulSoup) -> dict:
    import re as _re
    og_tags = {}
    for tag in soup.find_all("meta", attrs={"property": _re.compile(r"^og:", _re.I)}):
        prop = tag.get("property")
        content = tag.get("content")
        if prop and content:
            og_tags[prop] = content
    return {"hasOpenGraph": bool(og_tags), "openGraphTags": og_tags}

def check_twitter_cards(soup: BeautifulSoup) -> dict:
    import re as _re
    twitter_tags = {}
    for tag in soup.find_all("meta", attrs={"name": _re.compile(r"^twitter:", _re.I)}):
        name = tag.get("name")
        content = tag.get("content")
        if name and content:
            twitter_tags[name] = content
    return {"hasTwitterCards": bool(twitter_tags), "twitterCardTags": twitter_tags}

def check_seo_friendly_url(url: str, url_max_length: int, url_max_depth: int) -> dict:
    import re as _re
    parsed_url = urlparse(url)
    path = unquote(parsed_url.path)
    is_seo_friendly = True
    issues = []
    if len(url) > url_max_length:
        is_seo_friendly = False
        issues.append(f"URL is too long (>{url_max_length} chars).")
    path_segments = [seg for seg in path.split('/') if seg]
    if len(path_segments) > url_max_depth:
        is_seo_friendly = False
        issues.append(f"URL path is too deep (>{url_max_depth} segments).")
    if any(char.isupper() for char in path):
        issues.append("URL path contains uppercase characters. Prefer lowercase.")
    if _re.search(r"\.(php|asp|aspx|jsp|html|htm)$", path.lower()) and path != "/" and path_segments:
        issues.append("URL contains file extensions. Consider using clean URLs.")
    return {"isSeoFriendlyUrl": is_seo_friendly, "seoFriendlyUrlIssues": issues}

def check_inline_css(soup: BeautifulSoup) -> dict:
    inline_css_count = 0
    for tag in soup.find_all(style=True):
        inline_css_count += 1
    return {"inlineCssCount": inline_css_count, "hasInlineCss": inline_css_count > 0}

def check_deprecated_html_tags(soup: BeautifulSoup, deprecated_tags: list[str]) -> dict:
    found_deprecated = {}
    for dep_tag_name in deprecated_tags:
        tags = soup.find_all(dep_tag_name)
        if tags:
            found_deprecated[dep_tag_name] = len(tags)
    return {"deprecatedHtmlTagsFound": found_deprecated, "hasDeprecatedHtmlTags": bool(found_deprecated)}

def check_flash_content(soup: BeautifulSoup) -> dict:
    import re as _re
    flash_objects = soup.find_all(['object', 'embed'], attrs={'type': _re.compile(r'application/x-shockwave-flash', _re.I)})
    flash_objects_classid = soup.find_all('object', attrs={'classid': _re.compile(r'clsid:D27CDB6E-AE6D-11cf-96B8-444553540000', _re.I)})
    has_flash = bool(flash_objects or flash_objects_classid)
    return {"hasFlashContent": has_flash}

def check_nested_tables(soup: BeautifulSoup) -> dict:
    nested = False
    for table in soup.find_all('table'):
        if table.find('table'):
            nested = True
            break
    return {"hasNestedTables": nested}

def check_frameset(soup: BeautifulSoup) -> dict:
    frameset = bool(soup.find('frameset') or soup.find('frame'))
    return {"hasFrameset": frameset}

