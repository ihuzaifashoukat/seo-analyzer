# Advanced SEO Analyzer: Comprehensive Python SEO Audit Tool 🐍📊

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](CONTRIBUTING.md)

The **Advanced SEO Analyzer** is a powerful Python-based command-line tool and web service designed to perform a comprehensive SEO audit of any webpage. It's built with modularity in mind, allowing for easy expansion and customization of SEO checks to help you optimize your web presence effectively.

Unlock insights into your website's on-page, technical, and content SEO aspects to improve search engine rankings and user experience.

## ✨ Key Features

This SEO audit tool provides a detailed analysis across several key areas:

**1. On-Page Analysis (`OnPageAnalyzer`):**
   - **Meta Tags**: Title (content, length, duplication), Description (content, length).
   - **Heading Structure**: H1-H6 content, counts, H1 uniqueness.
   - **Image SEO**: Alt attributes, responsive image patterns (`srcset`, `picture`), aspect ratio hints.
   - **Link Audit**: Internal/external link counts, no-follow internal links, anchor text length, active broken link checking (limited), unsafe cross-origin links (`rel="noopener"`).
   - **Content Quality**: Word count, content length sufficiency, paragraph count, Lorem Ipsum detection.
   - **Technical Elements**: iFrames, Apple Touch Icon, external JS/CSS file counts, inline CSS, deprecated HTML tags, Flash detection, nested tables, framesets.
   - **Social Media**: Open Graph and Twitter Card meta tag detection.
   - **URL Structure**: SEO-friendly URL checks (length, depth, characters, file extensions).
   - **Favicon**: Presence and URL.

**2. Technical SEO Analysis (`TechnicalSEOAnalyzer`):**
   - **Core Web Vitals & Performance Hints**: HTML page size, DOM element count, HTML compression (GZIP), HTTP/2, HSTS, server signature, page caching headers (Cache-Control, Expires), CDN usage hints.
   - **Crawlability & Indexability**: Doctype, charset, `robots.txt` (sitemap declarations, disallows), sitemap presence, meta viewport, AMP detection, language declaration, `hreflang` tags, canonical tags, `noindex`/`nofollow` meta tags.
   - **Security**: SSL/HTTPS verification, mixed content detection, plaintext emails, meta refresh.
   - **Structured Data**: JSON-LD, Microdata, general Schema.org detection.
   - **Analytics**: Google Analytics (GA/Gtag) detection.
   - **Server Configuration**: URL redirects tracing, custom 404 page heuristics, directory browsing heuristics, SPF records (requires `dnspython`), `ads.txt` presence.

**3. Content Analysis (`ContentAnalyzer`):**
   - **Keyword Insights**: Top N keywords (keyword cloud data), target keyword usage analysis (presence, density).
   - **Readability**: Flesch Reading Ease score.
   - **Content Metrics**: Text-to-HTML ratio.
   - **Quality Checks**: Basic spell check (requires `pyspellchecker`).

**4. SEO Scoring (`ScoringModule`):**
   - **Categorized Scores**: On-Page, Technical, and Content SEO scores.
   - **Overall SEO Score**: A comprehensive percentage reflecting the page's SEO health.
   - **Actionable Feedback**: Lists of identified issues and successes for each category.
   - **Configurable Weights**: Customize scoring criteria via a JSON configuration file.

## 📂 Project Structure

```
seo-analyzer/
├── app.py                  # Main script to run the analyzer (CLI & API)
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── LICENSE                 # Project's MIT License
├── modules/
│   ├── __init__.py         # Makes 'modules' a Python package
│   ├── base_module.py      # Abstract base class for SEO modules
│   ├── on_page_analyzer.py
│   ├── technical_seo_analyzer.py
│   ├── content_analyzer.py
│   └── scoring_module.py     # Calculates SEO scores
└── reports/                  # Directory for saved JSON reports (created automatically)
```

## 🚀 Getting Started

Follow these steps to set up and run the Advanced SEO Analyzer:

1.  **Clone the Repository (Optional):**
    If you haven't already, clone this repository or ensure all project files are in a local directory.
    ```bash
    # git clone <repository_url> # If applicable
    # cd seo-analyzer
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    Activate it:
    -   Windows: `venv\Scripts\activate`
    -   macOS/Linux: `source venv/bin/activate`

3.  **Install Dependencies:**
    Navigate to the project directory in your terminal and run:
    ```bash
    pip install -r requirements.txt
    ```
    This installs `requests`, `beautifulsoup4`, `dnspython`, `pyspellchecker`, and `Flask`.

4.  **Run the Analyzer:**
    The tool operates in two modes: Command-Line Interface (CLI) or as a Flask Web Service (API).

    **A. Command-Line Interface (CLI) Mode:**
    To analyze a specific URL, execute the `app.py` script from the project's root directory:
    ```bash
    python app.py <YOUR_WEBSITE_URL>
    ```
    Example:
    ```bash
    python app.py https://www.example.com
    ```

    **CLI Optional Arguments:**
    -   `--output <format>`: Specify report format. Supports `json` (default) and `txt`.
        ```bash
        python app.py https://www.example.com --output json
        ```
    -   `--keywords <keyword1> ["<keyword phrase 2>"] ...`: Define target keywords for content analysis.
        ```bash
        python app.py https://www.example.com --keywords "seo audit tool" "python seo"
        ```
    -   `--config <path_to_config.json>`: Use a custom JSON configuration file to override default settings and scoring weights.
        ```bash
        python app.py https://www.example.com --config custom_config.json
        ```
        Example `custom_config.json`:
        ```json
        {
            "OnPageAnalyzer": {
                "title_min_length": 25,
                "desc_max_length": 155
            },
            "ScoringModule": {
                "weights": { "title_score": {"max_points": 15, "weight": 1.5} },
                "category_weights": { "OnPage": 0.50, "Technical": 0.30, "Content": 0.20 }
            },
            "Global": { "request_timeout": 15 }
        }
        ```

    **B. Flask Web Service (API) Mode:**
    To run the analyzer as a web service, execute `app.py` without specifying a URL:
    ```bash
    python app.py
    ```
    The server will start by default on `http://127.0.0.1:5000/`.
    -   You can use the `--config <path_to_config.json>` argument to load a custom configuration for the server. This config will apply to all API requests.

    **API Endpoint:**
    -   `POST /analyze` or `GET /analyze`
    -   **Parameters:**
        -   `url` (required): The URL to analyze.
        -   `keywords` (optional): Comma-separated string of keywords (for GET) or a JSON list (for POST).
    -   **Example GET Request:**
        ```
        http://127.0.0.1:5000/analyze?url=https://www.example.com&keywords=seo%20tools,python
        ```
    -   **Example POST Request (with JSON body):**
        ```json
        {
            "url": "https://www.example.com",
            "keywords": ["seo tools", "python for seo"]
        }
        ```
    -   **Response:** The API returns a JSON object identical to the report generated in CLI mode.

5.  **View Reports:**
    -   **CLI Mode**: Analysis reports are saved in the `reports/` directory. Filenames include a timestamp and the domain.
    -   **API Mode**: Responses are returned directly as JSON.

## 📄 Output JSON Structure

The output JSON provides a detailed breakdown of the SEO audit:

```json
{
  "analysis_timestamp": "YYYY-MM-DDTHH:MM:SS.ffffff",
  "target_url": "https://www.analyzed-url.com/",
  "domain": "www.analyzed-url.com",
  "seo_attributes": {
    "OnPageAnalyzer": {
      // ... on-page metrics ...
    },
    "TechnicalSEOAnalyzer": {
      // ... technical metrics ...
    },
    "ContentAnalyzer": {
      // ... content analysis metrics ...
    },
    "ScoringModule": {
        "on_page_score_percent": 85.0,
        "on_page_issues": ["Issue 1...", "Issue 2..."],
        "on_page_successes": ["Success 1...", "Success 2..."],
        // ... other category scores, issues, successes ...
        "overall_seo_score_percent": 82.5,
        "scoring_status": "completed"
    }
  }
}
```

## 💡 Future Enhancements

We're always looking to improve! Potential future features include:
-   **Advanced Rendering Analysis**: Integration with headless browsers (Selenium/Playwright) for JavaScript error testing, console logs, LCP/CLS metrics, and mobile snapshots.
-   **External API Integrations**: Checks for Safe Browsing, related keywords, and competitor domain analysis.
-   **Deeper Asset Analysis**: Modern image format usage (WebP, AVIF), image metadata, JS/CSS minification.
-   **Expanded Output Formats**: HTML reports, CSV exports.
-   **User Interface**: A dedicated web interface for easier interaction.

## 🤝 Contributing

Contributions are welcome! Whether it's bug fixes, feature additions, or documentation improvements, please feel free to fork the repository, make your changes, and submit a pull request.

Please read `CONTRIBUTING.md` (to be created) for details on our code of conduct and the process for submitting pull requests.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Optimize your web presence with data-driven SEO insights!*
