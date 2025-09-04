from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re

def extract_image_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls = []
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if not src.startswith(('data:', 'blob:')):
            urls.append(urljoin(base_url, src))
    for source in soup.find_all("source", srcset=True):
        srcset = source["srcset"]
        for candidate in srcset.split(','):
            url = candidate.strip().split(' ')[0]
            if url and not url.startswith(('data:', 'blob:')):
                urls.append(urljoin(base_url, url))
    return list(dict.fromkeys(urls))  # dedupe preserve order

def extract_css_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls = []
    for link in soup.find_all("link", rel="stylesheet", href=True):
        urls.append(urljoin(base_url, link["href"]))
    return list(dict.fromkeys(urls))

def extract_js_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls = []
    for script in soup.find_all("script", src=True):
        urls.append(urljoin(base_url, script["src"]))
    return list(dict.fromkeys(urls))

def extract_inline_css_content(soup: BeautifulSoup, limit: int = 3) -> list[dict[str, str]]:
    inline_css = []
    for i, style_tag in enumerate(soup.find_all("style")):
        content = style_tag.string
        if content and content.strip():
            inline_css.append({"source": f"inline_style_tag_{i+1}", "content": content.strip()})
    return inline_css[:limit]

def extract_inline_js_content(soup: BeautifulSoup, limit: int = 3) -> list[dict[str, str]]:
    inline_js = []
    for i, script_tag in enumerate(soup.find_all("script")):
        if not script_tag.has_attr("src"):
            content = script_tag.string
            if content and content.strip():
                inline_js.append({"source": f"inline_script_tag_{i+1}", "content": content.strip()})
    return inline_js[:limit]

def check_content_minification(content: str, asset_type: str = "unknown", whitespace_ratio_threshold: float = 0.15, avg_line_length_threshold: int = 200, single_long_line_threshold: int = 500) -> dict:
    if not content:
        return {"is_minified_heuristic": False, "reason": "No content", "whitespace_ratio": 0, "avg_line_length": 0, "line_count": 0, "char_count": 0}
    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)
    whitespace_chars = len(re.findall(r"\s", content))
    whitespace_ratio = whitespace_chars / char_count if char_count > 0 else 0
    avg_line_length = char_count / line_count if line_count > 0 else 0
    is_minified = False
    reason = []
    if line_count == 1 and char_count > single_long_line_threshold:
        is_minified = True; reason.append(f"Single line with {char_count} chars (>{single_long_line_threshold}).")
    elif line_count > 1:
        if whitespace_ratio < whitespace_ratio_threshold:
            is_minified = True; reason.append(f"Whitespace ratio {whitespace_ratio:.2f} < {whitespace_ratio_threshold:.2f}.")
        if avg_line_length > avg_line_length_threshold:
            if is_minified:
                reason.append(f"Avg line length {avg_line_length:.0f} > {avg_line_length_threshold:.0f}.")
            else:
                is_minified = True; reason.append(f"Avg line length {avg_line_length:.0f} > {avg_line_length_threshold:.0f} (whitespace ratio was {whitespace_ratio:.2f}).")
        elif not is_minified:
            reason.append(f"Whitespace ratio {whitespace_ratio:.2f} >= {whitespace_ratio_threshold:.2f} and Avg line length {avg_line_length:.0f} <= {avg_line_length_threshold:.0f}.")
    else:
        reason.append(f"Single line with {char_count} chars (<= {single_long_line_threshold}). Whitespace ratio {whitespace_ratio:.2f}.")
    return {
        "is_minified_heuristic": is_minified,
        "reason": " ".join(reason) if reason else "Not enough indicators for minification.",
        "whitespace_ratio": round(whitespace_ratio, 3),
        "avg_line_length": round(avg_line_length, 1),
        "line_count": line_count,
        "char_count": char_count,
    }

def analyze_asset_caching(soup: BeautifulSoup, base_url: str, asset_type: str, make_request_fn, headers: dict, timeout: int, limits: dict) -> dict:
    # asset_type can be 'image', 'javascript', 'css'
    test_name = f"{asset_type}CachingTest"
    if asset_type == 'image':
        asset_urls = extract_image_urls(soup, base_url)[:limits.get('max_images_to_check_cache', 10)]
    elif asset_type == 'javascript':
        asset_urls = extract_js_urls(soup, base_url)[:limits.get('max_js_to_check_cache', 10)]
    elif asset_type == 'css':
        asset_urls = extract_css_urls(soup, base_url)[:limits.get('max_css_to_check_cache', 10)]
    else:
        return {test_name: {"status": "error_internal", "details": "Invalid asset type specified."}}
    if not asset_urls:
        return {test_name: {"status": f"no_{asset_type}_found"}}
    results_list = []
    for url in asset_urls:
        resp, _ = make_request_fn(url, headers=headers, timeout=timeout, method="head")
        if not resp:
            results_list.append({"url": url, "status": "error_fetching"})
            continue
        headers_ci = resp.headers
        cache_control = headers_ci.get("Cache-Control", "")
        expires = headers_ci.get("Expires", "")
        etag = headers_ci.get("ETag")
        results_list.append({
            "url": url,
            "status_code": resp.status_code,
            "has_cache_control": bool(cache_control),
            "has_expires": bool(expires),
            "has_etag": bool(etag),
            "cache_control": cache_control,
            "expires": expires,
            "etag": etag,
        })
    return {test_name: {"status": "completed", "assets_checked": len(results_list), "details": results_list}}

def analyze_asset_minification(soup: BeautifulSoup, base_url: str, asset_type: str, make_request_fn, headers: dict, timeout: int, config: dict) -> dict:
    # asset_type can be 'javascript', 'css'
    test_name = f"{asset_type}MinificationTest"
    external_asset_urls = []
    inline_assets_content = []
    if asset_type == 'javascript':
        external_asset_urls = extract_js_urls(soup, base_url)
        inline_assets_content = extract_inline_js_content(soup, limit=config.get("max_inline_js_to_check_minification", 3))
    elif asset_type == 'css':
        external_asset_urls = extract_css_urls(soup, base_url)
        inline_assets_content = extract_inline_css_content(soup, limit=config.get("max_inline_css_to_check_minification", 3))
    else:
        return {test_name: {"status": "error_internal", "details": "Invalid asset type specified."}}
    if not external_asset_urls and not inline_assets_content:
        return {test_name: {"status": f"no_{asset_type}_found_or_analyzed", "details": f"No suitable external or inline {asset_type} found on the page or limit reached."}}
    results_list = []
    processed_count = 0
    errors_count = 0
    minified_count = 0
    for asset_url in external_asset_urls[:config.get(f"max_{asset_type}_to_check_minification", 10)]:
        response = make_request_fn(asset_url, headers=headers, timeout=timeout, method="get")[0]
        if response:
            try:
                content_length = response.headers.get('Content-Length')
                max_size = config.get(f"max_{asset_type}_size_bytes_for_minification", 1 * 1024 * 1024)
                if content_length and int(content_length) > max_size:
                    results_list.append({"source_url": asset_url, "type": "external", "status": "skipped_too_large", "size_bytes": int(content_length)})
                    continue
                asset_content = response.text
                minification_info = check_content_minification(
                    asset_content,
                    asset_type,
                    whitespace_ratio_threshold=config.get(f"minification_whitespace_ratio_threshold_{asset_type}", 0.15),
                    avg_line_length_threshold=config.get(f"minification_avg_line_length_threshold_{asset_type}", 200),
                    single_long_line_threshold=config.get(f"minification_single_long_line_threshold_{asset_type}", 500),
                )
                results_list.append({"source_url": asset_url, "type": "external", "status": "analyzed", **minification_info})
                processed_count += 1
                if minification_info["is_minified_heuristic"]:
                    minified_count += 1
            except Exception as e:
                results_list.append({"source_url": asset_url, "type": "external", "status": "error_processing_content", "error": str(e)})
                errors_count += 1
        else:
            results_list.append({"source_url": asset_url, "type": "external", "status": "error_fetching"})
            errors_count += 1
    for inline_asset in inline_assets_content:
        try:
            content = inline_asset["content"]
            source_name = inline_asset["source"]
            if len(content) > config.get(f"max_inline_{asset_type}_size_bytes_for_minification", 100 * 1024):
                results_list.append({"source": source_name, "type": "inline", "status": "skipped_too_large", "size_bytes": len(content)})
                continue
            minification_info = check_content_minification(
                content,
                asset_type,
                whitespace_ratio_threshold=config.get(f"minification_whitespace_ratio_threshold_{asset_type}", 0.15),
                avg_line_length_threshold=config.get(f"minification_avg_line_length_threshold_{asset_type}", 200),
                single_long_line_threshold=config.get(f"minification_single_long_line_threshold_{asset_type}", 500),
            )
            results_list.append({"source": source_name, "type": "inline", "status": "analyzed", **minification_info})
            processed_count += 1
            if minification_info["is_minified_heuristic"]:
                minified_count += 1
        except Exception as e:
            results_list.append({"source": source_name, "type": "inline", "status": "error_processing_content", "error": str(e)})
            errors_count += 1
    overall_status = "completed"
    if errors_count > 0 and processed_count == 0:
        overall_status = "error_all_failed"
    elif errors_count > 0:
        overall_status = "completed_with_errors"
    summary = f"{processed_count} {asset_type} assets (external & inline) checked. {minified_count} appear minified. {errors_count} errors."
    return {test_name: {"status": overall_status, "summary": summary, "details": results_list}}

