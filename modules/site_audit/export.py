from __future__ import annotations

import csv
from typing import List, Dict, Any


def export_pages_csv(path: str, pages: List[Dict[str, Any]]):
    if not pages:
        return
    # Flatten core fields for a quick overview
    fieldnames = [
        'url',
        'overall_score', 'technical_score', 'on_page_score', 'content_score',
        'http_status', 'ttfb_seconds', 'has_canonical', 'has_sitemap', 'viewport', 'has_schema',
        'word_count', 'h1_count', 'internal_links', 'external_links',
        'title', 'meta_description'
    ]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in pages:
            attrs = p.get('seo_attributes', {})
            s = attrs.get('ScoringModule', {})
            tech = attrs.get('TechnicalSEOAnalyzer', {})
            onp = attrs.get('OnPageAnalyzer', {})
            w.writerow({
                'url': p.get('url'),
                'overall_score': s.get('overall_seo_score_percent'),
                'technical_score': s.get('technical_score_percent'),
                'on_page_score': s.get('on_page_score_percent'),
                'content_score': s.get('content_score_percent'),
                'http_status': tech.get('httpStatusCode'),
                'ttfb_seconds': (tech.get('siteLoadingSpeedTest') or {}).get('ttfb_seconds'),
                'has_canonical': tech.get('hasCanonicalTag'),
                'has_sitemap': tech.get('hasSitemap'),
                'viewport': tech.get('viewport'),
                'has_schema': tech.get('hasSchema'),
                'word_count': onp.get('wordsCount'),
                'h1_count': onp.get('h1Count'),
                'internal_links': onp.get('internalLinkCount'),
                'external_links': onp.get('externalLinkCount'),
                'title': onp.get('title'),
                'meta_description': onp.get('metaDescription'),
            })


def export_issues_csv(path: str, issues: List[Dict[str, Any]]):
    if not issues:
        # still create file with headers
        fieldnames = ['url', 'code', 'title', 'severity', 'category', 'details']
        with open(path, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return
    fieldnames = ['url', 'code', 'title', 'severity', 'category', 'details']
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i in issues:
            w.writerow({
                'url': i.get('url'),
                'code': i.get('code'),
                'title': i.get('title'),
                'severity': i.get('severity'),
                'category': i.get('category'),
                'details': i.get('details'),
            })


def export_edges_csv(path: str, edges: List[Dict[str, Any]]):
    fieldnames = ['source', 'target', 'rel']
    import csv
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for e in edges:
            w.writerow({'source': e.get('source'), 'target': e.get('target'), 'rel': ",".join(e.get('rel') or [])})
