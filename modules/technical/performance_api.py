from __future__ import annotations

from typing import Optional, Dict, Any
import requests


def fetch_pagespeed_insights(url: str, api_key: Optional[str] = None, strategy: str = "desktop", timeout: int = 20) -> Dict[str, Any]:
    """
    Fetches key Lighthouse/CrUX data from Google PageSpeed Insights v5 API.
    Returns a compact dict. If api_key is None or request fails, returns a skipped status.
    """
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": strategy}
    if api_key:
        params["key"] = api_key
    try:
        resp = requests.get(endpoint, params=params, timeout=timeout)
        if resp.status_code != 200:
            return {"psiStatus": f"http_{resp.status_code}"}
        data = resp.json()
        lighthouse = data.get('lighthouseResult', {})
        categories = lighthouse.get('categories', {})
        audits = lighthouse.get('audits', {})
        loading_exp = data.get('loadingExperience', {})
        origin_exp = data.get('originLoadingExperience', {})

        def score_of(cat):
            c = categories.get(cat, {})
            s = c.get('score')
            return round(s * 100) if isinstance(s, (int, float)) else None

        metrics = {
            'psiStatus': 'ok',
            'psiStrategy': strategy,
            'performanceScore': score_of('performance'),
            'accessibilityScore': score_of('accessibility'),
            'bestPracticesScore': score_of('best-practices'),
            'seoScore': score_of('seo'),
            'pwaScore': score_of('pwa'),
        }

        # Core metrics (where present)
        for key in ['first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time', 'cumulative-layout-shift', 'speed-index']:
            a = audits.get(key, {})
            val = a.get('displayValue') or a.get('numericValue')
            metrics[key.replace('-', '_')] = val

        # CrUX field data (loadingExperience)
        metrics['crux'] = {
            'overallCategory': loading_exp.get('overall_category'),
            'metrics': loading_exp.get('metrics'),
            'originOverallCategory': origin_exp.get('overall_category'),
        }
        return metrics
    except Exception as e:
        return {"psiStatus": "error", "psiError": str(e)}

