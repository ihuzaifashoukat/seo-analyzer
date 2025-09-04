import re
from bs4 import BeautifulSoup

def check_google_analytics(html_str: str) -> dict:
    patterns = {
        "isGoogleAnalyticsObject": r"window\.ga\s*=\s*window\.ga\s*\|\|\s*function\(\)",
        "isGoogleAnalyticsFunc": r"ga\s*\(\s*['\"]create['\"]\s*,",
        "hasGtagConfig": r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"](G|UA|AW)-",
        "hasGtagJs": r"https://www.googletagmanager.com/gtag/js\?id=(G|UA|AW)-"
    }
    results = {k: bool(re.search(v, html_str)) for k,v in patterns.items()}
    results["hasGoogleAnalytics"] = any(results.values())
    return results

def check_mobile_friendliness_heuristics(soup: BeautifulSoup, viewport_present: bool) -> dict:
    notes = []; responsive = viewport_present
    if not viewport_present:
        notes.append("Viewport meta tag missing.")
    fixed_widths = []
    for tag in ["body", "div", "main", "article", "section", "table"]:
        for el in soup.find_all(tag, style=True):
            if "width" in el['style']:
                m = re.search(r"width\s*:\s*(\d{3,})px", el['style'])
                if m and int(m.group(1)) > 380:
                    fixed_widths.append(f"<{el.name}> fixed width {m.group(1)}px"); responsive = False; break
        if fixed_widths and not responsive:
            break
    if fixed_widths:
        notes.append(f"Large fixed-width elements found: {', '.join(fixed_widths[:2])}.")
    if viewport_present and not fixed_widths:
        notes.append("Viewport present, no large inline fixed-widths. Good.")
    media_queries = any("@media" in s.string for s in soup.find_all("style") if s.string)
    if media_queries:
        notes.append("Internal CSS media queries found.")
    else:
        notes.append("No internal CSS media queries (may be external).")
    return {"mobileResponsive": responsive, "mobileFriendlinessNotes": notes, "hasInternalMediaQueries": media_queries}

def check_mixed_content(soup: BeautifulSoup, scheme: str) -> dict:
    items = []
    if scheme == "https":
        for tag, attr in [("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src"), ("video", "src"), ("audio", "src"), ("source", "src")]:
            for t in soup.find_all(tag, **{attr: re.compile(r"^http://", re.I)}):
                items.append({"tag": tag, "url": t[attr]})
    return {"mixedContentItems": items, "hasMixedContent": bool(items)}

def check_plaintext_emails(html_str: str) -> dict:
    emails = list(set(e for e in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html_str) if not any(ext in e.lower() for ext in ['.png','.jpg','.gif','.svg','.css','.js'])))
    return {"plaintextEmailsFound": emails, "hasPlaintextEmails": bool(emails)}

def check_meta_refresh(soup: BeautifulSoup) -> dict:
    tag = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
    return {"hasMetaRefresh": bool(tag), "metaRefreshContent": tag.get("content") if tag else None}

def check_modern_image_formats_html(soup: BeautifulSoup) -> dict:
    webp = False; avif = False
    for pic in soup.find_all("picture"):
        if pic.find("source", attrs={"type": "image/webp"}):
            webp = True
        if pic.find("source", attrs={"type": "image/avif"}):
            avif = True
    for img in soup.find_all("img", src=True):
        src = img["src"].lower()
        if ".webp" in src:
            webp = True
        if ".avif" in src:
            avif = True
        if webp and avif:
            break
    return {"usesWebPInHtml": webp, "usesAvifInHtml": avif, "modernImageFormatNotes": "HTML check only."}

