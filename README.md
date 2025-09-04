# Advanced SEO Analyzer

A modern, modular SEO analysis toolkit for Python. Run focused page-level audits or full site crawls, capture technical/content issues with clear severities, and export structured data for reporting. Built with extensibility in mind and designed for practical, actionable insights.

## Highlights

- On-page, Technical, and Content analyzers with unified scoring
- Full Site Audit (Ahrefs-style) with concurrency, filtering, and exports
- LLM/AI directives checklist (llms.txt / ai.txt)
- Optional Lighthouse/CrUX metrics via PageSpeed Insights API
- Duplicate detection across titles, descriptions, and visible text
- Link graph, redirect chains/loops, status distribution, and internal link suggestions
- REST API (Flask) and rich CLI with mobile-first and JS rendering options

## Contents

- Overview
- Features
- Project Structure
- Quick Start
- CLI Usage
- API Usage
- Configuration
- Output & Exports
- Optional Dependencies
- Roadmap
- Contributing & License

---

## Overview

The analyzer is split into focused subpackages: `on_page`, `technical`, `content`, `scoring`, and `site_audit`. Each module exposes a small, well-defined surface and can be extended independently. The CLI supports both single-page analysis and site-wide crawling with concurrency and filters. Results are JSON-first with optional CSV exports for pages, issues, and link edges.

## Features

- On-Page Analysis
  - Title/meta description presence and lengths, duplication hints
  - Heading structure (H1–H6), multiple H1 detection
  - Image alt, responsive patterns, basic layout red flags
  - Link audit (internal/external, broken links, rel, unsafe cross-origin)
  - Content stats (word count, paragraphs, lorem ipsum)
  - URL structure (length, depth, case), deprecated tags, inline CSS
  - Social tags (Open Graph, Twitter Cards), favicon

- Technical SEO
  - Crawlability/Indexability: doctype, charset, viewport, AMP, language, hreflang, canonical, robots meta, structured data (JSON-LD/Microdata)
  - Network & Headers: HTTP version, HSTS, server signature, cache headers, CDN hints
  - Performance: DOM size, gzip, TTFB, optional PSI (Lighthouse/CrUX)
  - Security: HTTPS usage, mixed content, plaintext emails, meta refresh
  - Site-level: redirects chain trace, custom 404, directory browsing, SPF, ads.txt
  - Assets: caching headers for CSS/JS/images; minification heuristics for CSS/JS
  - LLMs: `llms.txt` / `ai.txt` detection and checklist with recommendations

- Content Analysis
  - Keyword extraction and target keyword usage
  - Readability (Flesch Reading Ease)
  - Text-to-HTML ratio
  - Spellcheck (optional dependency)

- Scoring
  - Category scores (On-Page, Technical, Content) and overall score
  - Configurable weights and category emphasis

- Full Site Audit
  - Crawler with robots.txt respect, include/exclude filters, subdomain toggle, depth/page caps, rate limiting, and optional JS rendering for discovery
  - Concurrency for per-page analysis
  - Issues with severity (error/warning/notice) across HTTP, redirects, sitemap, canonical, indexing, content/meta, links, international, performance, and security
  - Status distribution, redirect loops, duplicate titles/meta/visible text, internal link graph (in/out degree) and heuristic internal link suggestions
  - Optional exports: `pages.csv`, `issues.csv`, `edges.csv`

## Project Structure

```
seo-analyzer/
├── app.py                      # CLI & API entrypoint
├── requirements.txt
├── modules/
│   ├── __init__.py
│   ├── base_module.py          # Base with session, retries, headers
│   ├── on_page/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # On-page orchestrator
│   │   ├── text_utils.py
│   │   ├── title_meta.py
│   │   ├── headings_links_images.py
│   │   └── social_misc.py
│   ├── technical/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # Technical orchestrator
│   │   ├── network.py
│   │   ├── html_core.py
│   │   ├── metrics.py
│   │   ├── site_checks.py
│   │   ├── assets.py
│   │   ├── llms_txt.py         # LLMs/AI directives checklist
│   │   └── performance_api.py  # PageSpeed Insights (optional)
│   ├── content/
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── text_utils.py
│   │   ├── keywords.py
│   │   ├── readability.py
│   │   ├── ratio.py
│   │   └── spellcheck.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── weights.py
│   │   ├── util.py
│   │   ├── on_page.py
│   │   ├── technical.py
│   │   └── content.py
│   └── site_audit/
│       ├── __init__.py
│       ├── crawler.py          # Discovery crawler
│       ├── render.py           # Optional Playwright renderer
│       ├── audit.py            # Crawl + analyze + aggregate
│       ├── issues.py           # Issue model & derivation
│       ├── duplication.py      # Duplicate grouping helpers
│       ├── sitemap.py          # Sitemap parsing & bucketing
│       ├── export.py           # CSV exporters
│       └── compare.py          # Diff between audit reports
└── README.md
```

## Quick Start

1) Python env
- Python 3.8+
- Optional: `python -m venv venv && source venv/bin/activate`

2) Install
- `pip install -r requirements.txt`
- Optional dependencies:
  - Playwright (JS rendering): `pip install playwright && playwright install`
  - PSI (Lighthouse/CrUX): needs a Google API key (config below)

3) Single-Page Audit (CLI)
- `python app.py https://www.example.com`
- Saves report to `reports/seo_report_<domain>_<timestamp>.json`

4) Full Site Audit (CLI)
- Example (mobile UA, filters, concurrency, exports):
```
python app.py https://www.example.com \
  --full-audit --max-pages 200 --max-depth 3 \
  --respect-robots --rate-limit 1.5 --workers 6 --mobile \
  --export-csv reports/example_audit \
  --include-path /blog --exclude-path re:^/admin --render-js
```
- Output:
  - JSON report at `reports/site_audit_<domain>_<timestamp>.json`
  - If `--export-csv` provided: `pages.csv`, `issues.csv`, `edges.csv`

## CLI Usage

- Single page:
  - `python app.py <URL> [--keywords ...] [--config path.json] [--output json|txt]`
- Full site audit:
  - `--full-audit`: enable crawl + multi-page analysis
  - `--max-pages`, `--max-depth`, `--rate-limit`
  - `--include-subdomains`, `--same-domain-only`, `--respect-robots`/`--ignore-robots`
  - `--include-path`, `--exclude-path` (prefix or `re:<pattern>`; repeatable)
  - `--workers` (concurrent analysis), `--mobile` (mobile UA), `--render-js` (Playwright)
  - `--auth-user`, `--auth-pass` for basic auth
  - `--export-csv <dir>` for CSVs
  - `--compare-report <file>` to diff two site audit JSONs

## API Usage (Flask)

Run without a URL to start the API:
- `python app.py`
- POST/GET `http://127.0.0.1:5000/analyze?url=https://www.example.com`
- Optional `keywords` (CSV or JSON array)
- Response mirrors the single-page JSON structure.

## Configuration

Config may be supplied via `--config path.json` or edited in `app.py`’s `DEFAULT_CONFIG`.

Example snippet:
```json
{
  "OnPageAnalyzer": {
    "title_min_length": 20,
    "title_max_length": 70,
    "desc_min_length": 70,
    "desc_max_length": 160
  },
  "TechnicalSEOAnalyzer": {
    "enable_pagespeed_insights": true,
    "psi_api_key": "YOUR_GOOGLE_API_KEY",
    "psi_strategy": "mobile",
    "max_inline_js_to_check_minification": 3,
    "max_js_to_check_minification": 10
  },
  "ContentAnalyzer": {
    "top_n_keywords_count": 10,
    "spellcheck_language": "en"
  },
  "ScoringModule": {
    "weights": {},
    "category_weights": { "OnPage": 0.40, "Technical": 0.35, "Content": 0.25 }
  },
  "FullSiteAudit": {
    "max_pages": 150,
    "max_depth": 3,
    "respect_robots": true,
    "same_domain_only": true,
    "include_subdomains": false,
    "rate_limit_rps": 1.5,
    "workers": 6,
    "include_paths": ["/blog"],
    "exclude_paths": ["re:^/admin"],
    "render_js": true
  },
  "Global": {
    "request_timeout": 12,
    "user_agent": "Mozilla/5.0 ...",
    "accept_language": "en-US,en;q=0.8",
    "http_retries_total": 2,
    "http_backoff_factor": 0.2,
    "http_status_forcelist": [429,500,502,503,504],
    "http_allowed_retry_methods": ["HEAD","GET","OPTIONS"]
  }
}
```

## Output & Exports

- Single-page JSON (top-level):
  - `seo_attributes.OnPageAnalyzer` (title/meta, headings, links, images, content stats, URL checks)
  - `seo_attributes.TechnicalSEOAnalyzer` (headers, protocol, indexability, structured data, assets, PSI if enabled, llms.txt, redirects, robots/sitemap, SPF, ads.txt)
  - `seo_attributes.ContentAnalyzer` (keywords, readability, ratio, spelling)
  - `seo_attributes.ScoringModule` (category and overall scores)

- Site audit JSON:
  - `site_audit.summary`: status distribution, redirect loops, health score, duplicate groups, link graph metrics, sitemap summary, aggregate scores
  - `site_audit.pages`: list of per-URL page results (same structure as single-page attributes)
  - `site_audit.issues`: flattened issues with `url`, `code`, `title`, `severity`, `category`, `details`
  - `site_audit.config_used`: crawl and worker config used; optional `exports` with CSV paths

- CSVs (if `--export-csv`):
  - `pages.csv`: URL, scores, HTTP status, TTFB, canonical/sitemap flags, schema, word count, H1 count, links, title, meta description
  - `issues.csv`: URL, code, title, severity, category, details
  - `edges.csv`: source, target, rel (internal link graph)

## Optional Dependencies

- `pyspellchecker`: content spell checks
- `dnspython`: SPF lookup
- `Pillow`: optional image-related utilities
- `flask`: API mode
- `playwright`: optional JS rendering for discovery (`--render-js`)
- PageSpeed Insights: requires Google API key (`enable_pagespeed_insights`)

## Roadmap

- Rendered HTML analysis (Playwright) for per-page analyzers and JS error capture
- Deeper structured data validation (rule-based, 190+ checks)
- Expanded issue catalog and weighting
- PSI/CrUX integration into health scoring/outlier detection
- GSC/GA integrations and IndexNow submissions
- Segmented crawling and richer URL detail panels

## Contributing & License

- Contributions welcome! Please open issues/PRs for features and fixes.
- MIT License. See `LICENSE`.

