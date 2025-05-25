# main.py
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
from modules.on_page_analyzer import OnPageAnalyzer
from modules.technical_seo_analyzer import TechnicalSEOAnalyzer
from modules.content_analyzer import ContentAnalyzer
from modules.scoring_module import ScoringModule

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
        
        on_page_cfg = self.config.get("OnPageAnalyzer", {})
        if custom_module_config and "OnPageAnalyzer" in custom_module_config:
            on_page_cfg.update(custom_module_config["OnPageAnalyzer"])
        self.register_module(OnPageAnalyzer(config=on_page_cfg))

        tech_cfg = self.config.get("TechnicalSEOAnalyzer", {})
        if custom_module_config and "TechnicalSEOAnalyzer" in custom_module_config:
            tech_cfg.update(custom_module_config["TechnicalSEOAnalyzer"])
        self.register_module(TechnicalSEOAnalyzer(config=tech_cfg))

        content_cfg = self.config.get("ContentAnalyzer", {})
        if custom_module_config and "ContentAnalyzer" in custom_module_config:
            content_cfg.update(custom_module_config["ContentAnalyzer"])
        if cli_keywords: # CLI keywords override any other keyword source for ContentAnalyzer
            content_cfg["target_keywords"] = cli_keywords
        elif "target_keywords" not in content_cfg: # Ensure key exists if not from CLI or custom_module_config
             content_cfg["target_keywords"] = []
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

def run_cli():
    parser = argparse.ArgumentParser(description="Advanced SEO Analyzer")
    parser.add_argument("url", nargs='?', default=None, help="The URL of the website to analyze (omit to run in API/server mode).")
    parser.add_argument("--output", choices=["json", "txt"], default="json", help="Output format for the report.")
    parser.add_argument("--keywords", nargs="+", default=[], help="Target keywords for content analysis.")
    parser.add_argument("--config", type=str, default=None, help="Path to a JSON config file.")
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
    elif args.url: # If URL is provided, run in CLI mode
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
