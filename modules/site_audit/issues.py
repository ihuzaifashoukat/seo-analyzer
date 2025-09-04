from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class Issue:
    url: str
    code: str
    title: str
    severity: str  # error | warning | notice
    category: str  # technical | on_page | content | performance | international | security | links | ai
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sev(cond: bool, when_true: str, when_false: str = "") -> str:
    return when_true if cond else when_false


def _status_bucket(sc: Optional[int]) -> Optional[str]:
    if sc is None:
        return None
    if sc == 403:
        return '403'
    if 400 <= sc < 500:
        return '4xx'
    if 500 <= sc < 600:
        return '5xx'
    if 300 <= sc < 400:
        return '3xx'
    if sc == 200:
        return '200'
    return str(sc)


def derive_issues(url: str, page_attrs: Dict[str, Any]) -> List[Issue]:
    issues: List[Issue] = []

    onpage = page_attrs.get('OnPageAnalyzer', {})
    tech = page_attrs.get('TechnicalSEOAnalyzer', {})
    content = page_attrs.get('ContentAnalyzer', {})

    # HTTP status buckets
    sc = tech.get('httpStatusCode')
    bucket = _status_bucket(sc)
    if bucket == '404':
        issues.append(Issue(url, 'HTTP_404', 'Page not found (404)', 'error', 'technical', 'Return 200 or redirect to relevant page'))
    if bucket == '403':
        issues.append(Issue(url, 'HTTP_403', 'Forbidden (403)', 'error', 'technical', 'Check auth rules and access control'))
    if bucket == '5xx':
        issues.append(Issue(url, 'HTTP_5XX', f'Server error ({sc})', 'error', 'technical', 'Investigate server reliability'))
    if bucket == '4xx' and sc != 404 and sc != 403:
        issues.append(Issue(url, 'HTTP_4XX', f'Client error ({sc})', 'error', 'technical', 'Fix broken URL or routing'))
    if bucket == '3xx':
        # Redirect checks
        rh = tech.get('redirectHistory') or []
        if len([h for h in rh if (h.get('status_code') or 0) // 100 == 3]) > 1:
            issues.append(Issue(url, 'REDIRECT_CHAIN', 'Redirect chain detected', 'warning', 'technical', 'Reduce to single redirect'))
        # Loop check handled at site-level; page-level notice here if any repetition
        seen = set()
        for hop in rh:
            u2 = hop.get('url')
            if not u2:
                continue
            if u2 in seen:
                issues.append(Issue(url, 'REDIRECT_LOOP', 'Redirect loop detected', 'error', 'technical', 'Fix loop in redirects'))
                break
        # 302 temporary redirect
        if any(h.get('status_code') == 302 for h in rh) or sc == 302:
            issues.append(Issue(url, 'TEMP_REDIRECT_302', 'Temporary redirect (302)', 'notice', 'technical', 'Use 301 if permanent'))

    # Timeout pages are marked elsewhere (not available per-page unless fetch failed)

    # Meta refresh redirect
    if tech.get('hasMetaRefresh'):
        issues.append(Issue(url, 'META_REFRESH', 'Meta refresh redirect', 'warning', 'technical', 'Avoid meta refresh redirects'))

    # HTTPS to HTTP redirects
    rh = tech.get('redirectHistory') or []
    if rh:
        try:
            first = rh[0].get('url')
            last = rh[-1].get('url')
            if first and last and first.startswith('https://') and last.startswith('http://'):
                issues.append(Issue(url, 'HTTPS_TO_HTTP', 'HTTPS redirects to HTTP', 'error', 'security', 'Avoid downgrading scheme'))
        except Exception:
            pass

    # Technical: robots.txt disallow all
    if tech.get('robotsTxtDisallowsAllGeneral'):
        issues.append(Issue(url, 'ROBOTS_DISALLOW_ALL', 'Robots.txt disallows all', 'error', 'technical', 'User-agent * disallows /'))

    # Technical: no sitemap
    if not tech.get('hasSitemap'):
        issues.append(Issue(url, 'NO_SITEMAP', 'No sitemap detected', 'warning', 'technical', 'Sitemap not declared in robots.txt nor found at common paths'))

    # Canonical issues
    if not tech.get('hasCanonicalTag'):
        issues.append(Issue(url, 'NO_CANONICAL', 'Missing canonical tag', 'warning', 'technical', 'Add a rel=canonical to prevent duplicate content issues'))
    # Cross-scheme canonicals
    can_url = tech.get('canonicalUrl')
    if can_url and isinstance(can_url, str):
        try:
            from urllib.parse import urlparse
            cu = urlparse(can_url)
            pu = urlparse(url)
            if pu.scheme == 'http' and cu.scheme == 'https':
                issues.append(Issue(url, 'CANONICAL_HTTP_TO_HTTPS', 'Canonical from HTTP to HTTPS', 'notice', 'technical', 'Prefer canonical on final protocol'))
            if pu.scheme == 'https' and cu.scheme == 'http':
                issues.append(Issue(url, 'CANONICAL_HTTPS_TO_HTTP', 'Canonical from HTTPS to HTTP', 'warning', 'technical', 'Avoid HTTP canonical from HTTPS page'))
        except Exception:
            pass

    # Indexing: meta and header
    if tech.get('hasMetaNoindex'):
        issues.append(Issue(url, 'NOINDEX', 'Page set to noindex', 'warning', 'technical', 'Remove noindex to allow indexing if this page should rank'))
    xrt = (tech.get('xRobotsTag') or '')
    if isinstance(xrt, str) and xrt:
        if 'noindex' in xrt.lower():
            issues.append(Issue(url, 'NOINDEX_HEADER', 'X-Robots-Tag noindex', 'warning', 'technical', 'Remove header noindex if page should be indexed'))
        if 'nofollow' in xrt.lower():
            issues.append(Issue(url, 'NOFOLLOW_HEADER', 'X-Robots-Tag nofollow', 'notice', 'technical', 'Header nofollow present'))
    # Nofollow page via meta
    if tech.get('hasMetaNofollowDirective'):
        issues.append(Issue(url, 'NOFOLLOW_PAGE', 'Page set to nofollow', 'notice', 'technical', 'Remove nofollow unless intentionally blocking link equity'))

    # Technical: missing viewport (mobile-unfriendly)
    if not tech.get('viewport'):
        issues.append(Issue(url, 'NO_VIEWPORT', 'Missing viewport meta', 'warning', 'performance', 'Add <meta name="viewport" ...> for mobile devices'))

    # Technical: mixed content
    if tech.get('hasMixedContent'):
        issues.append(Issue(url, 'MIXED_CONTENT', 'Mixed content detected', 'error', 'security', 'Serve all assets over HTTPS'))

    # Technical: slow TTFB heuristic
    ttfb = (tech.get('siteLoadingSpeedTest') or {}).get('ttfb_seconds')
    if isinstance(ttfb, (int, float)) and ttfb is not None:
        if ttfb >= 1.0:
            issues.append(Issue(url, 'SLOW_TTFB', f'High TTFB: {ttfb}s', 'notice' if ttfb < 1.5 else 'warning', 'performance', 'Optimize server response time'))

    # Content & Meta: title/description
    if not onpage.get('isTitle'):
        issues.append(Issue(url, 'MISSING_TITLE', 'Missing title tag', 'error', 'on_page', 'Every page should have a unique, descriptive title'))
    if not onpage.get('isMetaDescription'):
        issues.append(Issue(url, 'MISSING_META_DESC', 'Missing meta description', 'warning', 'on_page', 'Add a compelling meta description'))
    if onpage.get('hasMultipleTitleTags'):
        issues.append(Issue(url, 'MULTIPLE_TITLE_TAGS', 'Multiple title tags', 'warning', 'on_page', 'Keep a single <title> tag per page'))
    if onpage.get('hasMultipleMetaDescriptionTags'):
        issues.append(Issue(url, 'MULTIPLE_META_DESC_TAGS', 'Multiple meta description tags', 'notice', 'on_page', 'Keep a single meta description per page'))

    # H1 issues
    if onpage.get('h1Count', 0) == 0:
        issues.append(Issue(url, 'MISSING_H1', 'Missing H1 heading', 'warning', 'on_page', 'Add a primary H1 heading'))
    elif onpage.get('h1Count', 0) > 1:
        issues.append(Issue(url, 'MULTIPLE_H1', 'Multiple H1 headings', 'notice', 'on_page', 'Use a single H1 to clarify page topic'))

    # Content: low word count
    if isinstance(onpage.get('wordsCount'), int) and onpage['wordsCount'] < 300:
        issues.append(Issue(url, 'LOW_WORD_COUNT', f'Low content ({onpage["wordsCount"]} words)', 'notice', 'content', 'Consider adding more useful content'))

    # Link issues
    if (onpage.get('brokenLinksCount') or 0) > 0:
        issues.append(Issue(url, 'BROKEN_OUTGOING_LINKS', 'Page has links to broken pages', 'warning', 'links', 'Fix or remove broken outbound links'))
    if (onpage.get('internalLinksCount') or 0) == 0 and (onpage.get('externalLinksCount') or 0) == 0:
        issues.append(Issue(url, 'NO_OUTGOING_LINKS', 'Page has no outgoing links', 'notice', 'links', 'Consider adding contextual links'))

    # HTTPS pages linking to HTTP
    try:
        from urllib.parse import urlparse
        if urlparse(url).scheme == 'https':
            http_links = [l for l in (onpage.get('internalLinks') or []) if l.startswith('http://')]
            if http_links:
                issues.append(Issue(url, 'HTTPS_LINKS_TO_HTTP', 'HTTPS page links to HTTP', 'warning', 'security', 'Update internal links to HTTPS'))
    except Exception:
        pass

    # Resource & Performance: broken JS/CSS and large files (heuristic based on caching/minification checks)
    js_cache = (tech.get('javascriptCachingTest') or {}).get('details') or []
    css_cache = (tech.get('cssCachingTest') or {}).get('details') or []
    if any((d.get('status_code') or 200) >= 400 for d in js_cache):
        issues.append(Issue(url, 'JS_BROKEN', 'Page has broken JavaScript resources', 'error', 'performance', 'Fix failing JS requests'))
    if any((d.get('status_code') or 200) >= 400 for d in css_cache):
        issues.append(Issue(url, 'CSS_BROKEN', 'Page has broken CSS resources', 'error', 'performance', 'Fix failing CSS requests'))
    js_min = (tech.get('javascriptMinificationTest') or {}).get('details') or []
    css_min = (tech.get('cssMinificationTest') or {}).get('details') or []
    if any(d.get('status') == 'skipped_too_large' for d in css_min):
        issues.append(Issue(url, 'CSS_TOO_LARGE', 'CSS file size too large (heuristic)', 'warning', 'performance', 'Split or optimize large CSS files'))
    if any(d.get('status') == 'skipped_too_large' for d in js_min):
        issues.append(Issue(url, 'JS_TOO_LARGE', 'JavaScript file size too large (heuristic)', 'warning', 'performance', 'Split or optimize large JS files'))

    # Canonical target probe (precise)
    cprobe = tech.get('canonicalTargetProbe') or {}
    csc = cprobe.get('status_code')
    if isinstance(csc, int):
        if 300 <= csc < 400:
            issues.append(Issue(url, 'CANONICAL_TO_REDIRECT', 'Canonical points to redirect', 'warning', 'technical', 'Point canonical directly to final URL'))
        elif 400 <= csc < 500:
            issues.append(Issue(url, 'CANONICAL_TO_4XX', f'Canonical points to 4xx ({csc})', 'error', 'technical', 'Fix canonical target'))
        elif 500 <= csc < 600:
            issues.append(Issue(url, 'CANONICAL_TO_5XX', f'Canonical points to 5xx ({csc})', 'error', 'technical', 'Fix canonical target server error'))

    # URL Structure
    try:
        from urllib.parse import urlparse
        pu = urlparse(url)
        path = pu.path or '/'
        if '//' in path:
            issues.append(Issue(url, 'DOUBLE_SLASH_URL', 'Double slash in URL path', 'notice', 'technical', 'Normalize URL path'))
        if '%' in path:
            issues.append(Issue(url, 'URL_ENCODING', 'URL encoding present in path', 'notice', 'technical', 'Avoid unnecessary encodings in URLs'))
    except Exception:
        pass

    # SSL/HTTPS
    if tech.get('hasHttps') is False:
        issues.append(Issue(url, 'NO_HTTPS', 'Page not served over HTTPS', 'warning', 'security', 'Enable HTTPS'))

    # Schema presence
    if not tech.get('hasSchema'):
        issues.append(Issue(url, 'NO_SCHEMA', 'No structured data detected', 'notice', 'technical', 'Add Schema.org markup where relevant'))

    # Image optimization (missing alts)
    if (onpage.get('notOptimizedImagesCount') or 0) > 0:
        issues.append(Issue(url, 'IMAGES_MISSING_ALT', 'Images without alt text', 'notice', 'content', 'Add descriptive alt attributes'))

    # Timeouts / request failed
    site_speed = tech.get('siteLoadingSpeedTest') or {}
    if tech.get('initial_request_failed') or (site_speed.get('ttfb_seconds') is None and tech.get('httpStatusCode') is None):
        issues.append(Issue(url, 'REQUEST_TIMEOUT', 'Page timed out or failed to load', 'error', 'technical', 'Investigate server/network issues'))

    # AI/LLM directives
    if tech.get('llmsTxtStatus') != 'found':
        issues.append(Issue(url, 'NO_LLM_TXT', 'No llms.txt/ai.txt found', 'notice', 'ai', 'Add llms.txt to guide AI crawlers'))

    return issues


def derive_site_issues(pages: List[Dict[str, Any]], nodes: Dict[str, Dict[str, int]], edges: List[Dict[str, Any]], sitemap_report: Optional[Dict[str, Any]] = None) -> List[Issue]:
    issues: List[Issue] = []
    url_set = {p.get('url') for p in pages}
    # Orphan pages: no inbound internal links
    for u, deg in nodes.items():
        if deg.get('in', 0) == 0:
            issues.append(Issue(u, 'ORPHAN_PAGE', 'Orphan page (no internal links)', 'warning', 'links', 'Add internal links to this page'))
    # Redirected pages with no inbound
    sc_map = {p.get('url'): (p.get('seo_attributes') or {}).get('TechnicalSEOAnalyzer', {}).get('httpStatusCode') for p in pages}
    for u, sc in sc_map.items():
        if sc and 300 <= sc < 400 and nodes.get(u, {}).get('in', 0) == 0:
            issues.append(Issue(u, 'REDIRECT_NO_INBOUND', 'Redirected page with no incoming links', 'notice', 'links', 'Remove or update references'))

    # Nofollow-only inbound / mixed
    inbound_map: Dict[str, List[List[str]]] = {u: [] for u in url_set}
    for e in edges:
        tgt = e.get('target')
        rel = e.get('rel') or []
        if tgt in inbound_map:
            inbound_map[tgt].append(rel)
    for u, rel_lists in inbound_map.items():
        if not rel_lists:
            continue
        any_dofollow = any(('nofollow' not in (rl or [])) for rl in rel_lists)
        any_nofollow = any(('nofollow' in (rl or [])) for rl in rel_lists)
        if not any_dofollow and any_nofollow:
            issues.append(Issue(u, 'NOFOLLOW_ONLY_INBOUND', 'Nofollow-only incoming internal links', 'notice', 'links', 'Add at least one dofollow internal link'))
        elif any_dofollow and any_nofollow:
            issues.append(Issue(u, 'MIXED_INBOUND_FOLLOWS', 'Nofollow and dofollow incoming links', 'notice', 'links', 'Consider link policy consistency'))

    # Pages linking to redirects
    status_map = sc_map
    for e in edges:
        src = e.get('source')
        tgt = e.get('target')
        if tgt in status_map and status_map[tgt] and 300 <= status_map[tgt] < 400:
            issues.append(Issue(src, 'LINKS_TO_REDIRECTS', 'Page has links to redirects', 'notice', 'links', 'Update links to final URLs'))
    # Sitemap issues summary
    if sitemap_report and sitemap_report.get('sitemapUrls'):
        buckets = sitemap_report.get('statusBuckets', {})
        for key, lst in buckets.items():
            sev = 'error' if any(x in key for x in ['4xx', '5xx', 'forbidden', 'timeout']) else 'warning'
            title = f"Sitemap URLs: {key.replace('_', ' ')}"
            for u in lst[:50]:  # cap individual entries to avoid giant lists
                issues.append(Issue(u, f'SITEMAP_{key.upper()}', title, sev, 'technical', 'Investigate sitemap URL status'))
        if not sitemap_report.get('parsedAnySitemap'):
            issues.append(Issue(list(url_set)[0] if url_set else '', 'SITEMAP_INVALID', 'Invalid sitemap format or fetch error', 'warning', 'technical', 'Fix sitemap availability and XML format'))
    # International SEO: hreflang checks (basic)
    # Build maps for hreflang and canonical
    hreflang_map: Dict[str, List[Dict[str, str]]] = {}
    canonical_map: Dict[str, Optional[str]] = {}
    html_lang: Dict[str, Optional[str]] = {}
    for p in pages:
        u = p.get('url')
        tech = p.get('seo_attributes', {}).get('TechnicalSEOAnalyzer', {})
        hreflang_map[u] = tech.get('hreflangLinks') or []
        canonical_map[u] = tech.get('canonicalUrl')
        html_lang[u] = tech.get('language')
    # Missing reciprocal hreflang
    for u, links in hreflang_map.items():
        for l in links:
            target = l.get('url')
            if target and target in hreflang_map:
                if not any(ll.get('url') == u for ll in hreflang_map[target]):
                    issues.append(Issue(u, 'HREFLANG_NO_RETURN', 'Missing reciprocal hreflang', 'warning', 'international', f'Return-tag missing from {target}'))
            else:
                issues.append(Issue(u, 'HREFLANG_TO_UNKNOWN', 'Hreflang points to unknown page', 'notice', 'international', 'Target not in crawl set'))
    # Hreflang vs HTML lang mismatch (heuristic)
    for u, lang in html_lang.items():
        if not lang:
            continue
        links = hreflang_map.get(u, [])
        if links and not any((l.get('lang_code') or '').lower().startswith(lang.lower()) for l in links):
            issues.append(Issue(u, 'LANG_MISMATCH', 'HTML lang and hreflang mismatch', 'notice', 'international', 'Ensure hreflang includes page language'))
    # Duplicate pages without canonical (titles/text)
    # Simple approach: if multiple pages share same visibleTextHash but no canonical, flag
    text_hash_to_urls: Dict[str, List[str]] = {}
    for p in pages:
        u = p.get('url')
        ona = p.get('seo_attributes', {}).get('OnPageAnalyzer', {})
        h = ona.get('visibleTextHash')
        if h:
            text_hash_to_urls.setdefault(h, []).append(u)
    for h, group in text_hash_to_urls.items():
        if len(group) > 1:
            for u in group:
                can = canonical_map.get(u)
                if not can:
                    issues.append(Issue(u, 'DUPLICATE_NO_CANONICAL', 'Duplicate content without canonical', 'warning', 'technical', 'Add canonical to preferred page'))

    # Canonical target has no inbound internal links (if target within crawl set)
    for u in url_set:
        can = canonical_map.get(u)
        if can and can in nodes and nodes.get(can, {}).get('in', 0) == 0:
            issues.append(Issue(can, 'CANONICAL_TARGET_NO_INBOUND', 'Canonical URL has no incoming internal links', 'notice', 'links', 'Add internal links to canonical target'))
    return issues
