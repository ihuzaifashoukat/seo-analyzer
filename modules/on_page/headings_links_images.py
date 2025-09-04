import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests

GENERIC_ANCHORS = set([
    'click here','read more','learn more','more','here','this link','link','see more','details','view more','check this','visit'
])

def check_headings(soup: BeautifulSoup, primary_keyword: str | None = None) -> dict:
    headings_data = {"h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}
    for i in range(1, 7):
        for h_tag in soup.find_all(f"h{i}"):
            headings_data[f"h{i}"].append(h_tag.get_text(strip=True))
    h1_content_list = headings_data["h1"]
    h1_count = len(h1_content_list)
    h1_contains_kw = False
    subheads_kw_matches = 0
    if primary_keyword:
        lowkw = primary_keyword.lower()
        h1_contains_kw = any(lowkw in (h or '').lower() for h in h1_content_list)
        for level in ["h2","h3","h4","h5","h6"]:
            subheads_kw_matches += sum(1 for h in headings_data[level] if lowkw in (h or '').lower())
    # Simple heading hierarchy validation: avoid skipping levels drastically
    levels_present = [i for i in range(1,7) if headings_data.get(f"h{i}")]
    hierarchy_valid = True
    if levels_present:
        last = levels_present[0]
        for lv in levels_present[1:]:
            if lv - last > 1:
                hierarchy_valid = False
                break
            last = lv
    return {
        "isH1": h1_count > 0,
        "h1": h1_content_list,
        "h1Count": h1_count,
        "isH1OnlyOne": h1_count == 1,
        "isH2": len(headings_data["h2"]) > 0,
        "h2": headings_data["h2"], "h3": headings_data["h3"], "h4": headings_data["h4"],
        "h5": headings_data["h5"], "h6": headings_data["h6"],
        "h2Count": len(headings_data["h2"]), "h3Count": len(headings_data["h3"]),
        "h4Count": len(headings_data["h4"]), "h5Count": len(headings_data["h5"]),
        "h6Count": len(headings_data["h6"]),
        "h1ContainsPrimaryKeyword": h1_contains_kw,
        "subheadingsPrimaryKeywordMatches": subheads_kw_matches,
        "headingHierarchyValid": hierarchy_valid,
    }

def check_images(soup: BeautifulSoup, base_url: str, headers: dict, request_timeout: int, active_check_limit: int) -> dict:
    images = soup.find_all("img")
    not_optimized_imgs_src = []
    broken_images_details = []
    responsive_image_issues = []
    aspect_ratio_issues = []  # Placeholder

    images_to_actively_check = images[:active_check_limit]

    if images_to_actively_check:
        print(f"Actively checking up to {len(images_to_actively_check)} images for broken status (total on page: {len(images)})...")
        for img_tag in images_to_actively_check:
            src = img_tag.get("src")
            if src and not src.startswith(('data:', 'blob:')):
                full_img_url = urljoin(base_url, src)
                try:
                    response = requests.head(full_img_url, timeout=request_timeout / 2, allow_redirects=True, headers=headers)
                    if response.status_code >= 400:
                        broken_images_details.append({"url": full_img_url, "status_code": response.status_code})
                except requests.exceptions.Timeout:
                    broken_images_details.append({"url": full_img_url, "status_code": "timeout"})
                except requests.exceptions.RequestException:
                    broken_images_details.append({"url": full_img_url, "status_code": "request_error"})

    for img in images:
        alt_text = img.get("alt", "").strip()
        if not alt_text:
            img_src_for_alt = img.get("src", "N/A")
            if not img_src_for_alt.startswith(('data:', 'blob:')):
                not_optimized_imgs_src.append(img_src_for_alt)

        has_srcset = img.has_attr("srcset")
        in_picture = bool(img.find_parent("picture"))
        if not (has_srcset or in_picture):
            style = (img.get("style", "") or "").lower()
            if "max-width" not in style and "width: 100%" not in style and "height: auto" not in style:
                responsive_image_issues.append(img.get("src", "N/A"))

    return {
        "total_images_on_page": len(images),
        "notOptimizedImgs": not_optimized_imgs_src,
        "notOptimizedImagesCount": len(not_optimized_imgs_src),
        "brokenImages": broken_images_details,
        "brokenImagesCount": len(broken_images_details),
        "imagesCheckedForBrokenStatus": len(images_to_actively_check),
        "responsiveImageIssues": responsive_image_issues,
        "responsiveImageIssuesCount": len(responsive_image_issues),
        "imageAspectRatioIssues": aspect_ratio_issues,
        "imageAspectRatioIssuesCount": len(aspect_ratio_issues),
    }

def check_links(soup: BeautifulSoup, base_url: str, headers: dict, request_timeout: int, active_check_limit: int, links_min_count: int) -> dict:
    internal_links_list = []
    external_links_list = []
    internal_nofollow_links_list = []
    broken_links_details = []
    unsafe_cross_origin_links = []
    internal_links_detailed = []

    total_anchor_text_length = 0
    valid_links_for_anchor_avg = 0
    generic_anchor_count = 0
    base_domain = urlparse(base_url).netloc

    all_a_tags = soup.find_all("a", href=True)

    for a_tag in all_a_tags:
        href = a_tag["href"]
        anchor_text = a_tag.get_text(strip=True)
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full_url = urljoin(base_url, href)
        link_domain = urlparse(full_url).netloc
        rel_vals = a_tag.get("rel", []) or []
        is_nofollow = "nofollow" in rel_vals
        if anchor_text:
            total_anchor_text_length += len(anchor_text)
            valid_links_for_anchor_avg += 1
            if anchor_text.lower().strip() in GENERIC_ANCHORS:
                generic_anchor_count += 1
        if link_domain == base_domain:
            internal_links_list.append(full_url)
            if is_nofollow:
                internal_nofollow_links_list.append(full_url)
            internal_links_detailed.append({
                "url": full_url,
                "rel": rel_vals,
                "target": a_tag.get("target"),
            })
        else:
            external_links_list.append(full_url)
            if a_tag.get("target") == "_blank" and not ("noopener" in a_tag.get("rel", []) or "noreferrer" in a_tag.get("rel", [])):
                unsafe_cross_origin_links.append(full_url)

    all_discovered_links = internal_links_list + external_links_list
    links_to_actively_check = all_discovered_links[:active_check_limit]

    if links_to_actively_check:
        print(f"Actively checking up to {len(links_to_actively_check)} links for broken status (total on page: {len(all_discovered_links)})...")
        for link_url_to_check in links_to_actively_check:
            try:
                response = requests.head(link_url_to_check, timeout=request_timeout / 2, allow_redirects=True, headers=headers)
                if response.status_code >= 400:
                    broken_links_details.append({"url": link_url_to_check, "status_code": response.status_code})
            except requests.exceptions.Timeout:
                broken_links_details.append({"url": link_url_to_check, "status_code": "timeout"})
            except requests.exceptions.RequestException:
                broken_links_details.append({"url": link_url_to_check, "status_code": "request_error"})

    links_count_total = len(all_discovered_links)
    avg_anchor_len = (total_anchor_text_length / valid_links_for_anchor_avg) if valid_links_for_anchor_avg > 0 else 0
    generic_ratio = (generic_anchor_count / valid_links_for_anchor_avg) if valid_links_for_anchor_avg > 0 else 0

    return {
        "linksCount": links_count_total,
        "isTooEnoughlinks": links_count_total >= links_min_count,
        "internalLinks": internal_links_list,
        "internalLinksCount": len(internal_links_list),
        "externalLinks": external_links_list,
        "externalLinksCount": len(external_links_list),
        "internalNoFollowLinks": internal_nofollow_links_list,
        "internalNoFollowLinksCount": len(internal_nofollow_links_list),
        "averageAnchorTextLength": round(avg_anchor_len, 2),
        "brokenLinks": broken_links_details,
        "brokenLinksCount": len(broken_links_details),
        "linksCheckedForBrokenStatus": len(links_to_actively_check),
        "unsafeCrossOriginLinks": unsafe_cross_origin_links,
        "unsafeCrossOriginLinksCount": len(unsafe_cross_origin_links),
        "internalLinksDetailed": internal_links_detailed,
        "genericAnchorTextCount": generic_anchor_count,
        "genericAnchorTextRatio": round(generic_ratio, 3),
        "descriptiveAnchorTextRatio": round(1 - generic_ratio, 3) if valid_links_for_anchor_avg > 0 else 0,
    }
