from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from statistics import mean
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from .crawler import SiteCrawler
from .. import on_page, technical, content, scoring
from ..base_module import SEOModule
from .issues import derive_issues, Issue
from .export import export_pages_csv, export_issues_csv, export_edges_csv
from .duplication import group_duplicates_by_field, duplicate_text_by_hash
from .sitemap import parse_sitemap, probe_url_statuses


@dataclass
class FullAuditConfig:
    max_pages: int = 100
    max_depth: int = 3
    rate_limit_rps: float = 0.0
    respect_robots: bool = True
    same_domain_only: bool = True
    include_subdomains: bool = False


class FullSiteAudit:
    """
    Orchestrates a site-wide audit: crawl URLs, run per-page analyzers, aggregate results.
    """

    def __init__(self, root_url: str, app_config: Dict[str, Any]):
        self.root_url = root_url
        self.app_config = app_config or {}

        full_cfg = self.app_config.get('FullSiteAudit', {})
        self.crawl_config = {
            'max_pages': full_cfg.get('max_pages', 100),
            'max_depth': full_cfg.get('max_depth', 3),
            'rate_limit_rps': full_cfg.get('rate_limit_rps', 0.0),
            'respect_robots': full_cfg.get('respect_robots', True),
            'same_domain_only': full_cfg.get('same_domain_only', True),
            'include_subdomains': full_cfg.get('include_subdomains', False),
            'user_agent': self.app_config.get('Global', {}).get('user_agent', 'Mozilla/5.0 (compatible; SEOAnalyzer/1.0)')
        }
        self.workers = int(full_cfg.get('workers', 4))

    def _build_modules(self):
        on_page_cfg = self.app_config.get('OnPageAnalyzer', {})
        tech_cfg = self.app_config.get('TechnicalSEOAnalyzer', {})
        content_cfg = self.app_config.get('ContentAnalyzer', {})
        score_cfg = self.app_config.get('ScoringModule', {})
        return (
            on_page.OnPageAnalyzer(config={'Global': self.app_config.get('Global', {}), **on_page_cfg}),
            technical.TechnicalSEOAnalyzer(config={'Global': self.app_config.get('Global', {}), **tech_cfg}),
            content.ContentAnalyzer(config={'Global': self.app_config.get('Global', {}), **content_cfg}),
            scoring.ScoringModule(config={'Global': self.app_config.get('Global', {}), **score_cfg}),
        )

    def run(self, target_keywords: Optional[List[str]] = None, export_dir: Optional[str] = None) -> Dict[str, Any]:
        crawler = SiteCrawler(self.root_url, session=None, config=self.crawl_config)
        discovered_urls = crawler.crawl()

        pages: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        all_issues: List[Issue] = []

        on_page_analyzer, tech_analyzer, content_analyzer, scoring_module = self._build_modules()

        # Inject keywords if provided
        if target_keywords:
            c_cfg = content_analyzer.config
            c_cfg['target_keywords'] = target_keywords

        def analyze_one(url: str) -> Dict[str, Any]:
            page_result: Dict[str, Any] = {'url': url, 'seo_attributes': {}}
            # Run per-page analyzers
            page_result['seo_attributes'].update(on_page_analyzer.analyze(url))
            page_result['seo_attributes'].update(tech_analyzer.analyze(url))
            page_result['seo_attributes'].update(content_analyzer.analyze(url))
            # Score aggregation
            scoring_data = scoring_module.analyze(url=url, full_report_data=page_result['seo_attributes'])
            page_result['seo_attributes'].update(scoring_data)
            return page_result

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            future_map = {ex.submit(analyze_one, u): u for u in discovered_urls}
            for fut in as_completed(future_map):
                u = future_map[fut]
                try:
                    result = fut.result()
                    pages.append(result)
                    # Derive issues per page
                    pg_issues = derive_issues(u, result.get('seo_attributes', {}))
                    all_issues.extend(pg_issues)
                except Exception as e:
                    errors.append({'url': u, 'error': str(e)})

        # Aggregate domain-level summary
        overall_scores = []
        tech_scores = []
        onpage_scores = []
        content_scores = []
        for p in pages:
            sdata = p['seo_attributes'].get('ScoringModule', {})
            if not sdata:
                continue
            if 'overall_seo_score_percent' in sdata:
                overall_scores.append(sdata['overall_seo_score_percent'])
            if 'technical_score_percent' in sdata:
                tech_scores.append(sdata['technical_score_percent'])
            if 'on_page_score_percent' in sdata:
                onpage_scores.append(sdata['on_page_score_percent'])
            if 'content_score_percent' in sdata:
                content_scores.append(sdata['content_score_percent'])

        # Status code distribution and redirects/loop indicators from page data
        status_distribution: Dict[str, int] = {}
        redirect_loops: List[str] = []
        for p in pages:
            tech = p['seo_attributes'].get('TechnicalSEOAnalyzer', {})
            sc = tech.get('httpStatusCode')
            if sc is not None:
                status_distribution[str(sc)] = status_distribution.get(str(sc), 0) + 1
            # Detect loop if redirectHistory repeats a URL
            rh = tech.get('redirectHistory') or []
            seen_urls = set()
            for hop in rh:
                u = hop.get('url')
                if not u:
                    continue
                if u in seen_urls:
                    redirect_loops.append(p.get('url'))
                    break
                seen_urls.add(u)

        # Aggregate issues by severity
        sev_counts = {'error': 0, 'warning': 0, 'notice': 0}
        for i in all_issues:
            if i.severity in sev_counts:
                sev_counts[i.severity] += 1

        # Simple health score heuristic (can be configured later)
        health_score = None
        try:
            health = 100.0 - (sev_counts['error'] * 3.0 + sev_counts['warning'] * 1.5 + sev_counts['notice'] * 0.5)
            health_score = round(max(0.0, min(100.0, health)), 1)
        except Exception:
            pass

        # Build internal link graph from on-page data
        nodes = {}
        edges = []
        url_set = {p.get('url') for p in pages}
        for p in pages:
            u = p.get('url')
            ona = p['seo_attributes'].get('OnPageAnalyzer', {})
            outlinks = ona.get('internalLinks') or []
            nodes.setdefault(u, {'in': 0, 'out': 0})
            nodes[u]['out'] += len(outlinks)
            for v in outlinks:
                edges.append({'source': u, 'target': v})
                if v in url_set:
                    nodes.setdefault(v, {'in': 0, 'out': 0})
                    nodes[v]['in'] += 1

        # Duplicate detection across site
        dup_titles = group_duplicates_by_field(pages, ["OnPageAnalyzer", "title"])
        dup_meta = group_duplicates_by_field(pages, ["OnPageAnalyzer", "metaDescription"])
        dup_h1 = group_duplicates_by_field(pages, ["OnPageAnalyzer", "h1"])  # if string; h1 is list; skip
        dup_text_hash = duplicate_text_by_hash(pages)

        # Simple internal linking suggestions
        suggestions = []
        # Build a quick map of page -> text sample
        text_samples = {p.get('url'): (p['seo_attributes'].get('OnPageAnalyzer', {}).get('visibleTextSample') or '') for p in pages}
        titles = {p.get('url'): (p['seo_attributes'].get('OnPageAnalyzer', {}).get('title') or '') for p in pages}
        link_out = {p.get('url'): set(p['seo_attributes'].get('OnPageAnalyzer', {}).get('internalLinks') or []) for p in pages}
        for target, deg in nodes.items():
            if deg.get('in', 0) == 0:  # low inbound
                target_title = titles.get(target, '')
                if not target_title:
                    continue
                tokens = [t for t in re.split(r"\W+", target_title.lower()) if len(t) > 3]
                if not tokens:
                    continue
                for source in titles.keys():
                    if source == target:
                        continue
                    if target in link_out.get(source, set()):
                        continue
                    sample = text_samples.get(source, '').lower()
                    if any(tok in sample for tok in tokens[:3]):
                        suggestions.append({'from': source, 'to': target, 'anchor_hint': tokens[0]})
                        break

        # Parse sitemaps and bucket statuses (site-level)
        try:
            tech_any = next((p['seo_attributes'].get('TechnicalSEOAnalyzer', {}) for p in pages if p.get('seo_attributes')), {})
            base_url = self.root_url
            robots_txt_content = tech_any.get('robots_txt_content_full')
            sm = parse_sitemap(base_url, robots_txt_content=robots_txt_content, timeout=self.app_config.get('Global', {}).get('request_timeout', 10))
            status_buckets = probe_url_statuses(sm.get('sitemapUrls', [])[:500], timeout=self.app_config.get('Global', {}).get('request_timeout', 10))
        except Exception:
            sm = {'parsedAnySitemap': False, 'sitemapUrls': [], 'sitemapErrors': []}
            status_buckets = {}

        summary = {
            'root_url': self.root_url,
            'total_discovered': len(discovered_urls),
            'pages_analyzed': len(pages),
            'pages_failed': len(errors),
            'avg_overall_score': round(mean(overall_scores), 2) if overall_scores else None,
            'avg_technical_score': round(mean(tech_scores), 2) if tech_scores else None,
            'avg_on_page_score': round(mean(onpage_scores), 2) if onpage_scores else None,
            'avg_content_score': round(mean(content_scores), 2) if content_scores else None,
            'status_code_distribution': status_distribution,
            'redirect_loops_detected': redirect_loops,
            'issue_counts': sev_counts,
            'health_score': health_score,
            'link_nodes': nodes,
            'duplicate_titles': dup_titles,
            'duplicate_meta_descriptions': dup_meta,
            'duplicate_text_groups': dup_text_hash,
            'link_suggestions': suggestions,
            'sitemap_summary': {
                'parsed_any': sm.get('parsedAnySitemap'),
                'sitemaps_checked': sm.get('sitemapsChecked'),
                'sitemap_errors': sm.get('sitemapErrors'),
                'sitemap_url_count': len(sm.get('sitemapUrls', [])),
                'status_buckets': status_buckets,
            },
        }

        report = {
            'site_audit': {
                'summary': summary,
                'pages': pages,
                'errors': errors,
                'issues': [i.to_dict() for i in all_issues],
                'config_used': {
                    'crawl': self.crawl_config,
                    'workers': self.workers,
                }
            }
        }

        # Add site-level issues derived from link graph and sitemap
        try:
            from .issues import derive_site_issues
            site_issues = derive_site_issues(pages, nodes, edges, sitemap_report={'statusBuckets': status_buckets, **sm})
            report['site_audit']['issues'].extend([i.to_dict() for i in site_issues])
            for i in site_issues:
                if i.severity in sev_counts:
                    sev_counts[i.severity] += 1
            report['site_audit']['summary']['issue_counts'] = sev_counts
        except Exception:
            pass

        # Optional CSV export
        if export_dir:
            try:
                import os
                os.makedirs(export_dir, exist_ok=True)
                export_pages_csv(os.path.join(export_dir, 'pages.csv'), pages)
                export_issues_csv(os.path.join(export_dir, 'issues.csv'), [i.to_dict() for i in all_issues])
                export_edges_csv(os.path.join(export_dir, 'edges.csv'), edges)
                report['site_audit']['exports'] = {
                    'pages_csv': os.path.join(export_dir, 'pages.csv'),
                    'issues_csv': os.path.join(export_dir, 'issues.csv'),
                    'edges_csv': os.path.join(export_dir, 'edges.csv'),
                }
            except Exception:
                pass

        return report
