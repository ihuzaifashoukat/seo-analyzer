# app.py
import argparse
import json
import os
from datetime import datetime
from urllib.parse import urlparse

# Import Flask for API (conditionally or always, then check run mode)
try:
    from flask import Flask, request, jsonify
except ImportError:
    Flask = None # Will prevent API mode if Flask not installed

# Import modules
from modules.on_page import OnPageAnalyzer
from modules.technical import TechnicalSEOAnalyzer
from modules.content import ContentAnalyzer
from modules.scoring import ScoringModule
from modules.site_audit import FullSiteAudit

DEFAULT_CONFIG = {
    "OnPageAnalyzer": {
        "title_min_length": 20, "title_max_length": 70,
        "desc_min_length": 70, "desc_max_length": 160,
        "content_min_words": 300, "links_min_count": 5,
        "active_check_limit": 10, "url_max_length": 100, "url_max_depth": 4
    },
    "TechnicalSEOAnalyzer": {},
    "ContentAnalyzer": {"top_n_keywords_count": 10, "spellcheck_language": "en"},
    "ScoringModule": {
        "weights": {}, # Users can override specific scoring weights here
        "category_weights": {"OnPage": 0.40, "Technical": 0.35, "Content": 0.25}
    },
    "FullSiteAudit": {
        "max_pages": 100,
        "max_depth": 3,
        "respect_robots": True,
        "same_domain_only": True,
        "include_subdomains": False,
        "rate_limit_rps": 0.0
    },
    "Global": {"request_timeout": 10}
}

# --- Flask App Setup (if Flask is available) ---
if Flask:
    app = Flask(__name__)
    # Global variable to hold the loaded configuration for the Flask app
    # This will be set when the app starts, similar to how CLI loads config
    flask_app_config = DEFAULT_CONFIG.copy() 
else:
    app = None

class SEOAnalyzer:
    def __init__(self, url, output_format="json", config=None):
        self.config = config if config else DEFAULT_CONFIG.copy()
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL provided: {url}")
        self.url = self.normalize_url(url)
        self.domain = urlparse(self.url).netloc
        self.report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "target_url": self.url,
            "domain": self.domain,
            "seo_attributes": {}
        }
        self.output_format = output_format # Less relevant for API, but kept for core class
        self.modules = []

    def normalize_url(self, url):
        if not url.startswith(('http://', 'https://')):
            return 'http://' + url
        return url

    def is_valid_url(self, url):
        try:
            result = urlparse(self.normalize_url(url))
            return all([result.scheme, result.netloc])
        except ValueError: return False

    def register_module(self, module_instance):
        self.modules.append(module_instance)
        # Suppress print for API mode, or make it configurable
        # print(f"Registered module: {module_instance.__class__.__name__}")


    def run_analysis(self, target_url, cli_keywords=None, custom_module_config=None):
        """
        Core analysis logic, callable by both CLI and API.
        cli_keywords: keywords from CLI.
        custom_module_config: specific config for modules, potentially from API request.
        """
        # Reset report for new analysis if this instance is reused (though typically not for API)
        self.url = self.normalize_url(target_url)
        self.domain = urlparse(self.url).netloc
        self.report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "target_url": self.url,
            "domain": self.domain,
            "seo_attributes": {}
        }
        self.modules = [] # Clear previously registered modules

        # Instantiate and register modules using the instance's config
        # The instance's self.config should be the fully merged config (default + file + API overrides)

        # Prepare module configs first so we can share target keywords with OnPage as well
        content_cfg = self.config.get("ContentAnalyzer", {}).copy()
        if custom_module_config and "ContentAnalyzer" in custom_module_config:
            content_cfg.update(custom_module_config["ContentAnalyzer"])
        if cli_keywords:  # CLI keywords override any other keyword source for ContentAnalyzer
            content_cfg["target_keywords"] = cli_keywords
        elif "target_keywords" not in content_cfg:  # Ensure key exists if not from CLI or custom_module_config
            content_cfg["target_keywords"] = []

        on_page_cfg = self.config.get("OnPageAnalyzer", {}).copy()
        if custom_module_config and "OnPageAnalyzer" in custom_module_config:
            on_page_cfg.update(custom_module_config["OnPageAnalyzer"])
        # Share target keywords with OnPage analyzer for placement checks
        if "target_keywords" not in on_page_cfg:
            on_page_cfg["target_keywords"] = content_cfg.get("target_keywords", [])

        tech_cfg = self.config.get("TechnicalSEOAnalyzer", {}).copy()
        if custom_module_config and "TechnicalSEOAnalyzer" in custom_module_config:
            tech_cfg.update(custom_module_config["TechnicalSEOAnalyzer"])

        # Register modules (OnPage -> Technical -> Content -> Scoring)
        self.register_module(OnPageAnalyzer(config=on_page_cfg))
        self.register_module(TechnicalSEOAnalyzer(config=tech_cfg))
        self.register_module(ContentAnalyzer(config=content_cfg))
        
        # Scoring module
        scoring_cfg = self.config.get("ScoringModule", {})
        if custom_module_config and "ScoringModule" in custom_module_config:
            scoring_cfg.update(custom_module_config["ScoringModule"])
        scoring_module_instance = ScoringModule(config=scoring_cfg)


        # Run analysis modules
        print(f"Starting SEO analysis for: {self.url}") # Keep for console feedback
        for module in self.modules:
            try:
                # print(f"Running module: {module.__class__.__name__}...") # Verbose
                module_results = module.analyze(self.url)
                self.report["seo_attributes"].update(module_results)
                # print(f"Module {module.__class__.__name__} completed.") # Verbose
            except Exception as e:
                print(f"Error running module {module.__class__.__name__}: {e}")
                self.report["seo_attributes"][module.__class__.__name__ + "_error"] = str(e)
        
        # Run scoring module
        try:
            # print(f"Running module: {scoring_module_instance.__class__.__name__}...") # Verbose
            scoring_data = scoring_module_instance.analyze(url=self.url, full_report_data=self.report["seo_attributes"])
            self.report["seo_attributes"].update(scoring_data)
            # print(f"Module {scoring_module_instance.__class__.__name__} completed.") # Verbose
        except Exception as e:
            print(f"Error running module {scoring_module_instance.__class__.__name__}: {e}")
            self.report["seo_attributes"][scoring_module_instance.__class__.__name__ + "_error"] = str(e)

        print("SEO analysis complete.")
        return self.report


    def save_report_to_file(self, filename_prefix="seo_report"): # Renamed for clarity
        if not os.path.exists("reports"):
            os.makedirs("reports")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_domain_name = self.domain.replace(".", "_")
        filename = f"reports/{filename_prefix}_{safe_domain_name}_{timestamp}.{self.output_format}"
        try:
            with open(filename, "w") as f:
                if self.output_format == "json": json.dump(self.report, f, indent=4)
                else: f.write(str(self.report))
            print(f"Report saved to {filename}")
            return filename
        except IOError as e:
            print(f"Error saving report: {e}")
            return None

# --- Flask Route (if Flask is available) ---
if app:
    @app.route('/analyze', methods=['POST', 'GET'])
    def analyze_endpoint():
        if request.method == 'GET':
            # Get params from query string for GET requests
            url_to_analyze = request.args.get('url')
            keywords_str = request.args.get('keywords') # comma-separated string
            # Config can also be passed as a JSON string in a query param, or use server's default/loaded config
            # For simplicity, API calls might rely more on a server-side loaded config file for detailed weights.
        elif request.method == 'POST':
            # Get params from JSON body for POST requests
            data = request.get_json()
            if not data: return jsonify({"error": "Invalid JSON payload"}), 400
            url_to_analyze = data.get('url')
            keywords_str = data.get('keywords') # Can be a list or comma-separated string
            # Potentially allow passing a partial config override in the POST body
            # api_custom_config = data.get('config_override', {}) 
        
        if not url_to_analyze:
            return jsonify({"error": "URL parameter is required"}), 400

        cli_keywords_list = []
        if keywords_str:
            if isinstance(keywords_str, list):
                cli_keywords_list = keywords_str
            else: # Assume comma-separated string
                cli_keywords_list = [kw.strip() for kw in keywords_str.split(',')]
        
        # Use the global flask_app_config which should be pre-loaded (e.g. from a file at app startup)
        # For now, it uses DEFAULT_CONFIG. A more robust app would load from file via --config CLI arg.
        analyzer_instance = SEOAnalyzer(url=url_to_analyze, config=flask_app_config.copy()) # Use a copy
        
        try:
            # The run_analysis method needs to be adapted or a new one created for API
            # that doesn't rely on argparse `args`
            analysis_report = analyzer_instance.run_analysis(target_url=url_to_analyze, cli_keywords=cli_keywords_list)
            return jsonify(analysis_report)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    @app.route('/full-audit', methods=['POST', 'GET'])
    def full_audit_endpoint():
        if request.method == 'GET':
            data = request.args
        else: # POST
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400

        url_to_audit = data.get('url')
        if not url_to_audit:
            return jsonify({"error": "URL parameter is required"}), 400

        # Use the global flask_app_config and override with API params
        current_config = flask_app_config.copy()
        
        # Apply API overrides for FullSiteAudit
        fa_cfg = current_config.setdefault("FullSiteAudit", {}).copy()
        if 'max_pages' in data: fa_cfg["max_pages"] = int(data['max_pages'])
        if 'max_depth' in data: fa_cfg["max_depth"] = int(data['max_depth'])
        if 'rate_limit' in data: fa_cfg["rate_limit_rps"] = float(data['rate_limit'])
        if 'include_subdomains' in data: fa_cfg["include_subdomains"] = bool(data['include_subdomains'])
        if 'respect_robots' in data: fa_cfg["respect_robots"] = bool(data['respect_robots'])
        current_config["FullSiteAudit"] = fa_cfg
        
        keywords_str = data.get('keywords')
        cli_keywords_list = []
        if keywords_str:
            if isinstance(keywords_str, list):
                cli_keywords_list = keywords_str
            else:
                cli_keywords_list = [kw.strip() for kw in keywords_str.split(',')]

        try:
            auditor = FullSiteAudit(root_url=url_to_audit, app_config=current_config)
            report = auditor.run(target_keywords=cli_keywords_list)
            return jsonify(report)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

def run_cli():
    parser = argparse.ArgumentParser(description="Advanced SEO Analyzer")
    parser.add_argument("url", nargs='?', default=None, help="The URL to analyze or crawl (omit to run in API/server mode).")
    parser.add_argument("--output", choices=["json", "txt"], default="json", help="Output format for the report.")
    parser.add_argument("--keywords", nargs="+", default=[], help="Target keywords for content analysis.")
    parser.add_argument("--config", type=str, default=None, help="Path to a JSON config file.")
    # Full site audit options
    parser.add_argument("--full-audit", action="store_true", help="Enable full site audit (crawl + analyze multiple pages).")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages to crawl (overrides config).")
    parser.add_argument("--max-depth", type=int, default=None, help="Max crawl depth (overrides config).")
    parser.add_argument("--respect-robots", action="store_true", help="Respect robots.txt during crawl (default true via config).")
    parser.add_argument("--ignore-robots", action="store_true", help="Ignore robots.txt during crawl.")
    parser.add_argument("--include-subdomains", action="store_true", help="Include subdomains during crawl.")
    parser.add_argument("--same-domain-only", action="store_true", help="Restrict crawl to same domain only.")
    parser.add_argument("--rate-limit", type=float, default=None, help="Requests per second rate limit for crawling.")
    parser.add_argument("--workers", type=int, default=None, help="Concurrent workers for page analysis in full audit.")
    parser.add_argument("--mobile", action="store_true", help="Use a mobile user-agent for crawl and analysis.")
    parser.add_argument("--export-csv", type=str, default=None, help="Directory to export CSVs (pages.csv, issues.csv) during full audit.")
    parser.add_argument("--include-path", action='append', default=None, help="Include only URLs with these path prefixes or regex (prefix or re:<pattern>). Can be repeated.")
    parser.add_argument("--exclude-path", action='append', default=None, help="Exclude URLs with these path prefixes or regex (prefix or re:<pattern>). Can be repeated.")
    parser.add_argument("--auth-user", type=str, default=None, help="Basic auth username for staging/protected sites.")
    parser.add_argument("--auth-pass", type=str, default=None, help="Basic auth password for staging/protected sites.")
    parser.add_argument("--render-js", action="store_true", help="Enable JS rendering via Playwright if installed (for crawl discovery).")
    parser.add_argument("--compare-report", type=str, default=None, help="Path to previous site audit JSON to compare against.")
    # --serve, --host, --port arguments removed. 
    # Flask web service is started if 'url' argument is not provided.

    args = parser.parse_args()

    # Load and merge configurations for both CLI and potentially Flask default
    # This config will be used by flask_app_config if --serve is chosen
    global flask_app_config # Allow modifying the global for Flask app
    current_config = DEFAULT_CONFIG.copy()
    if args.config:
        try:
            with open(args.config, 'r') as f:
                custom_config = json.load(f)
                for key, value in custom_config.items(): # Simple merge
                    if key in current_config and isinstance(current_config[key], dict) and isinstance(value, dict):
                        current_config[key].update(value)
                    else: current_config[key] = value
            print(f"Loaded custom configuration from {args.config}")
            flask_app_config = current_config.copy() # Update Flask's default config
        except FileNotFoundError: print(f"Warning: Config file {args.config} not found. Using default settings.")
        except json.JSONDecodeError: print(f"Warning: Error decoding JSON from {args.config}. Using default settings.")
    else: # No --config arg, Flask uses the hardcoded DEFAULT_CONFIG
        flask_app_config = DEFAULT_CONFIG.copy()

    # If URL is not provided, run in API/server mode. Otherwise, run in CLI mode.
    if not args.url:
        if not Flask:
            print("Error: Flask is not installed. Cannot run in API/server mode.")
            print("Please install Flask ('pip install flask') to run as a server, or provide a URL to run in CLI mode.")
            parser.print_help()
            return
        
        # Use default host/port for the Flask app
        default_host = "127.0.0.1"
        default_port = 5000
        print(f"Starting Flask server on http://{default_host}:{default_port}/ (API mode)")
        app.run(host=default_host, port=default_port, debug=False)
    elif args.url and args.full_audit:
        try:
            # Merge config
            current_config = DEFAULT_CONFIG.copy()
            if args.config and os.path.exists(args.config):
                with open(args.config, 'r') as f:
                    file_cfg = json.load(f)
                    # Shallow merge
                    for k, v in file_cfg.items():
                        if isinstance(v, dict) and k in current_config:
                            current_config[k].update(v)
                        else:
                            current_config[k] = v

            # Apply CLI overrides for FullSiteAudit
            fa_cfg = current_config.setdefault("FullSiteAudit", {}).copy()
            if args.max_pages is not None:
                fa_cfg["max_pages"] = args.max_pages
            if args.max_depth is not None:
                fa_cfg["max_depth"] = args.max_depth
            if args.rate_limit is not None:
                fa_cfg["rate_limit_rps"] = args.rate_limit
            if args.include_subdomains:
                fa_cfg["include_subdomains"] = True
            if args.same_domain_only:
                fa_cfg["same_domain_only"] = True
            if args.ignore_robots:
                fa_cfg["respect_robots"] = False
            if args.respect_robots:
                fa_cfg["respect_robots"] = True
            if args.workers is not None:
                fa_cfg["workers"] = args.workers
            # Mobile UA override
            if args.mobile:
                ua_mobile = "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Mobile Safari/537.36"
                g = current_config.setdefault('Global', {})
                g['user_agent'] = ua_mobile
            if args.include_path:
                fa_cfg["include_paths"] = args.include_path
            if args.exclude_path:
                fa_cfg["exclude_paths"] = args.exclude_path
            if args.auth_user and args.auth_pass:
                fa_cfg["auth_username"] = args.auth_user
                fa_cfg["auth_password"] = args.auth_pass
            if args.render_js:
                fa_cfg["render_js"] = True
            current_config["FullSiteAudit"] = fa_cfg

            print(f"Starting Full Site Audit for: {args.url}")
            auditor = FullSiteAudit(root_url=args.url, app_config=current_config)
            report = auditor.run(target_keywords=args.keywords if args.keywords else None, export_dir=args.export_csv)

            # Save combined site audit report
            domain = urlparse(args.url).netloc.replace('.', '_')
            if not os.path.exists("reports"):
                os.makedirs("reports")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = f"reports/site_audit_{domain}_{timestamp}.json"
            with open(out_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Site audit saved to {out_path}")
            # Optional compare against previous report
            if args.compare_report and os.path.exists(args.compare_report):
                try:
                    from modules.site_audit.compare import diff_site_audits
                    with open(args.compare_report, 'r') as f:
                        old = json.load(f)
                    changes = diff_site_audits(old, report)
                    diff_path = f"reports/site_audit_diff_{domain}_{timestamp}.json"
                    with open(diff_path, 'w') as df:
                        json.dump(changes, df, indent=2)
                    print(f"Diff saved to {diff_path}")
                except Exception as e:
                    print(f"Failed to generate diff: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during full site audit: {e}")
    elif args.url: # If URL is provided, run in CLI mode (single page)
        try:
            analyzer = SEOAnalyzer(args.url, output_format=args.output, config=current_config)
            # Pass CLI keywords to the core analysis runner
            analysis_results = analyzer.run_analysis(target_url=args.url, cli_keywords=args.keywords)
            
            print("\n--- Analysis Summary ---")
            print(f"URL Analyzed: {analysis_results['target_url']}")
            print(f"Timestamp: {analysis_results['analysis_timestamp']}")
            overall_score_data = analysis_results.get("seo_attributes", {}).get("ScoringModule", {})
            if overall_score_data and "overall_seo_score_percent" in overall_score_data:
                print(f"Overall SEO Score: {overall_score_data['overall_seo_score_percent']}%")
                # ... (print other scores)
            
            analyzer.save_report_to_file() # Uses self.report which is set by run_analysis
        except ValueError as ve: print(f"Error: {ve}")
        except Exception as e: print(f"An unexpected error occurred: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    run_cli()
