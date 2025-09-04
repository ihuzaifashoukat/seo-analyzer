from __future__ import annotations

from typing import Dict, Any, List


def _page_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    pages = report.get('site_audit', {}).get('pages', [])
    return {p.get('url'): p for p in pages if p.get('url')}


def diff_site_audits(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    old_map = _page_map(old)
    new_map = _page_map(new)

    old_urls = set(old_map.keys())
    new_urls = set(new_map.keys())

    added = sorted(list(new_urls - old_urls))
    removed = sorted(list(old_urls - new_urls))
    common = new_urls & old_urls

    status_changes = []
    title_changes = []
    desc_changes = []
    text_hash_changes = []
    for u in common:
        o = old_map[u]
        n = new_map[u]
        otech = (o.get('seo_attributes') or {}).get('TechnicalSEOAnalyzer', {})
        ntech = (n.get('seo_attributes') or {}).get('TechnicalSEOAnalyzer', {})
        if otech.get('httpStatusCode') != ntech.get('httpStatusCode'):
            status_changes.append({'url': u, 'old': otech.get('httpStatusCode'), 'new': ntech.get('httpStatusCode')})
        oon = (o.get('seo_attributes') or {}).get('OnPageAnalyzer', {})
        non = (n.get('seo_attributes') or {}).get('OnPageAnalyzer', {})
        if oon.get('title') != non.get('title'):
            title_changes.append({'url': u, 'old': oon.get('title'), 'new': non.get('title')})
        if oon.get('metaDescription') != non.get('metaDescription'):
            desc_changes.append({'url': u, 'old': oon.get('metaDescription'), 'new': non.get('metaDescription')})
        if oon.get('visibleTextHash') and non.get('visibleTextHash') and oon.get('visibleTextHash') != non.get('visibleTextHash'):
            text_hash_changes.append({'url': u, 'old_hash': oon.get('visibleTextHash'), 'new_hash': non.get('visibleTextHash')})

    return {
        'added_pages': added,
        'removed_pages': removed,
        'status_code_changes': status_changes,
        'title_changes': title_changes,
        'meta_description_changes': desc_changes,
        'text_hash_changes': text_hash_changes,
    }
