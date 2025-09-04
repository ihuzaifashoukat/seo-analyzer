from urllib.parse import urljoin
from bs4 import BeautifulSoup, Doctype
import re
import json

def check_doctype(soup: BeautifulSoup) -> dict:
    doctype_item = None
    for item in soup.contents:
        if isinstance(item, Doctype):
            doctype_item = item
            break
    return {"isDoctype": bool(doctype_item)}

def check_character_encoding(soup: BeautifulSoup) -> dict:
    meta_charset = soup.find("meta", attrs={"charset": True})
    if meta_charset:
        return {"isCharacterEncode": True, "charsetValue": meta_charset.get("charset")}
    http_equiv = soup.find("meta", attrs={"http-equiv": re.compile("Content-Type", re.I)})
    if http_equiv and "charset=" in http_equiv.get("content", "").lower():
        return {"isCharacterEncode": True, "charsetValue": http_equiv.get("content").split("charset=")[-1].strip()}
    return {"isCharacterEncode": False, "charsetValue": None}

def check_viewport_meta(soup: BeautifulSoup) -> dict:
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})
    return {"viewport": bool(viewport_tag), "viewportContent": viewport_tag.get("content") if viewport_tag else None}

def check_amp(soup: BeautifulSoup, base_url: str) -> dict:
    amp_link_tag = soup.find("link", rel="amphtml", href=True)
    if amp_link_tag:
        return {"isAmp": True, "ampUrl": urljoin(base_url, amp_link_tag["href"])}
    html_tag = soup.find("html")
    if html_tag and (html_tag.has_attr("amp") or html_tag.has_attr("\u26A1")):
        return {"isAmp": True, "ampUrl": None}
    return {"isAmp": False, "ampUrl": None}

def check_language_and_hreflang(soup: BeautifulSoup, base_url: str) -> dict:
    html_tag = soup.find("html"); lang_attr = html_tag.get("lang") if html_tag else None
    hreflang_links_data = []; has_hreflang_tag = False
    for tag in soup.find_all("link", rel="alternate", hreflang=True, href=True):
        has_hreflang_tag = True; hreflang_links_data.append({"lang_code": tag["hreflang"], "url": urljoin(base_url, tag["href"])})
    return {"language": lang_attr.lower() if lang_attr else None, "hasHreflang": has_hreflang_tag, "hreflangLinks": hreflang_links_data}

def check_canonical_tag(soup: BeautifulSoup, current_url: str) -> dict:
    tag = soup.find("link", attrs={"rel": "canonical"}, href=True)
    return {"canonicalUrl": urljoin(current_url, tag["href"]) if tag else None, "hasCanonicalTag": bool(tag)}

def check_meta_robots(soup: BeautifulSoup) -> dict:
    tag = soup.find("meta", attrs={"name": re.compile(r"robots", re.I)})
    content = tag.get("content", "").lower() if tag else None
    return {"metaRobots": content, "hasMetaNoindex": "noindex" in (content or ""), "hasMetaNofollowDirective": "nofollow" in (content or "")}

def check_structured_data(soup: BeautifulSoup) -> dict:
    json_ld_list = []; microdata_list = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            json_ld_list.append(json.loads(script.string))
        except Exception:
            pass
    for item_scope in soup.find_all(attrs={"itemscope": True}):
        is_nested = False; parent = item_scope.parent
        while parent:
            if parent.has_attr("itemscope") and parent != item_scope:
                is_nested = True; break
            parent = parent.parent
        if is_nested:
            continue
        details = {"type": item_scope.get("itemtype", "UnknownType"), "properties": {}}
        for prop_tag in item_scope.find_all(attrs={"itemprop": True}):
            is_direct = True; p_parent = prop_tag.parent
            while p_parent and p_parent != item_scope:
                if p_parent.has_attr("itemscope"):
                    is_direct = False; break
                p_parent = p_parent.parent
            if not is_direct:
                continue
            name = prop_tag.get("itemprop"); value = None
            if prop_tag.has_attr("itemscope"):
                value = {"@type": "NestedItemscope", "itemtype": prop_tag.get("itemtype", "UnknownNestedType")}
            elif prop_tag.name == 'meta':
                value = prop_tag.get("content")
            elif prop_tag.name in ['a', 'link']:
                value = prop_tag.get("href")
            elif prop_tag.name in ['img', 'audio', 'video', 'embed', 'iframe', 'source', 'track']:
                value = prop_tag.get("src")
            elif prop_tag.name == 'time':
                value = prop_tag.get("datetime") or prop_tag.get_text(strip=True)
            elif prop_tag.name == 'data':
                value = prop_tag.get("value") or prop_tag.get_text(strip=True)
            elif prop_tag.name == 'object':
                value = prop_tag.get("data")
            else:
                value = prop_tag.get_text(strip=True)
            if name and value is not None:
                if name in details["properties"]:
                    if not isinstance(details["properties"][name], list):
                        details["properties"][name] = [details["properties"][name]]
                    details["properties"][name].append(value)
                else:
                    details["properties"][name] = value
        if details["properties"]:
            microdata_list.append(details)
    has_schema = any("schema.org" in str(t).lower() for t in soup.find_all(True, itemtype=True)) or bool(json_ld_list) or any("schema.org" in i.get("type","").lower() for i in microdata_list)
    return {"hasJsonLd": bool(json_ld_list), "jsonLdData": json_ld_list, "hasMicrodata": bool(microdata_list), "microdataItems": microdata_list, "hasSchema": has_schema}

