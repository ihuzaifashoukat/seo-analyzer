def score_technical(data, score_data, weights, add_score):
    if not data:
        return
    # HTTPS
    add_score(score_data, weights, "https_score", weights["https_score"]["max_points"] if data.get("hasHttps") else 0, issue_msg="HTTPS not detected.", success_msg="HTTPS detected.")
    # Robots
    add_score(score_data, weights, "robots_txt_score", weights["robots_txt_score"]["max_points"] if data.get("robotsTxtStatus") in ("found",) else 0, issue_msg="robots.txt not found.", success_msg="robots.txt found.")
    # Sitemap
    add_score(score_data, weights, "sitemap_score", weights["sitemap_score"]["max_points"] if data.get("hasSitemap") else 0, issue_msg="Sitemap not found.", success_msg="Sitemap found.")
    # Canonical
    add_score(score_data, weights, "canonical_tag_score", weights["canonical_tag_score"]["max_points"] if data.get("hasCanonicalTag") else 0, issue_msg="Canonical tag missing.", success_msg="Canonical tag present.")
    # Mobile
    add_score(score_data, weights, "mobile_responsive_score", weights["mobile_responsive_score"]["max_points"] if data.get("mobileResponsive") else 0, issue_msg="Mobile-friendliness issues detected.", success_msg="Mobile responsive layout.")
    # Structured Data
    structured = data.get("hasSchema") or data.get("hasJsonLd") or data.get("hasMicrodata")
    add_score(score_data, weights, "structured_data_score", weights["structured_data_score"]["max_points"] if structured else 0, issue_msg="No structured data detected.", success_msg="Structured data detected.")
    # Meta robots
    add_score(score_data, weights, "meta_robots_score", weights["meta_robots_score"]["max_points"] if data.get("metaRobots") is not None else 0, issue_msg="Meta robots missing.", success_msg="Meta robots tag present.")
    # HTTP version
    http2 = 1 if str(data.get("httpVersion","")) in ("HTTP/2.0","HTTP/3") else 0
    add_score(score_data, weights, "http_version_score", weights["http_version_score"]["max_points"] * http2, issue_msg="Not using HTTP/2.", success_msg="Uses HTTP/2.")
    # HSTS
    add_score(score_data, weights, "hsts_score", weights["hsts_score"]["max_points"] if data.get("hstsHeader") else 0, issue_msg="HSTS header missing.", success_msg="HSTS header present.")
    # Mixed content penalty
    add_score(score_data, weights, "mixed_content_penalty", weights["mixed_content_penalty"]["max_points"] if data.get("hasMixedContent") else 0, is_penalty=True, issue_msg="Mixed content found.", success_msg="No mixed content.")
    # Redirects penalty
    has_redirects = data.get("hasRedirects")
    add_score(score_data, weights, "url_redirects_penalty", weights["url_redirects_penalty"]["max_points"] if has_redirects else 0, is_penalty=True, issue_msg="Redirects present.", success_msg="No redirects.")
    # Custom 404
    add_score(score_data, weights, "custom_404_page_score", weights["custom_404_page_score"]["max_points"] if data.get("hasCustom404PageHeuristic") else 0, issue_msg="Custom 404 might be missing.", success_msg="Custom 404 page detected.")
    # Page size
    page_size_kb = (data.get("htmlPageSize", 0) or 0) / 1024
    if page_size_kb > 500:
        add_score(score_data, weights, "html_page_size_score", 0, issue_msg=f"HTML page size is large ({page_size_kb:.0f}KB).")
    elif page_size_kb > 200:
        add_score(score_data, weights, "html_page_size_score", weights["html_page_size_score"]["max_points"] * 0.5, issue_msg=f"HTML page size is moderate ({page_size_kb:.0f}KB).")
    else:
        add_score(score_data, weights, "html_page_size_score", weights["html_page_size_score"]["max_points"], success_msg=f"HTML page size is good ({page_size_kb:.0f}KB).")
    # DOM size
    dom_elements = data.get("domSize", 0)
    if dom_elements > 1500:
        add_score(score_data, weights, "dom_size_score", 0, issue_msg=f"DOM size is very large ({dom_elements} elements).")
    elif dom_elements > 800:
        add_score(score_data, weights, "dom_size_score", weights["dom_size_score"]["max_points"] * 0.5, issue_msg=f"DOM size is large ({dom_elements} elements).")
    else:
        add_score(score_data, weights, "dom_size_score", weights["dom_size_score"]["max_points"], success_msg=f"DOM size is good ({dom_elements} elements).")
    # Compression
    enc = (data.get("htmlCompressionGzipTest") or "").lower()
    add_score(score_data, weights, "html_compression_score", weights["html_compression_score"]["max_points"] if ("gzip" in enc or "br" in enc) else 0, issue_msg="HTML compression not detected.", success_msg="HTML compression enabled.")
    # Page Cache
    cache_headers = data.get("pageCacheHeaders", {})
    has_cache_directive = any(cache_headers.get(h) for h in ["Cache-Control", "Expires", "ETag"])
    add_score(score_data, weights, "page_cache_score", weights["page_cache_score"]["max_points"] if has_cache_directive else 0, issue_msg="No caching headers found.", success_msg="Caching headers detected.")
    # Favicon/Charset/Doctype
    add_score(score_data, weights, "favicon_score", weights["favicon_score"]["max_points"] if data.get("favicon_status") == "detected" or data.get("favicon") else 0, issue_msg="Favicon missing.", success_msg="Favicon present.")
    add_score(score_data, weights, "charset_score", weights["charset_score"]["max_points"] if data.get("isCharacterEncode") else 0, issue_msg="Charset declaration missing.", success_msg="Charset declared.")
    add_score(score_data, weights, "doctype_score", weights["doctype_score"]["max_points"] if data.get("isDoctype") else 0, issue_msg="Doctype missing.", success_msg="Doctype declared.")

