def score_on_page(data, score_data, weights, add_score):
    if not data or not data.get("isLoaded"):
        return
    # Title
    max_p = weights["title_score"]["max_points"]
    if data.get("isTitle"):
        add_score(score_data, weights, "title_score", max_p if data.get("isTitleEnoughLong") else max_p * 0.3, issue_msg="Title length suboptimal.", success_msg="Title present and well-sized.")
    else:
        add_score(score_data, weights, "title_score", 0, issue_msg="Title missing.")
    # Meta Description
    max_p = weights["meta_description_score"]["max_points"]
    if data.get("isMetaDescription"):
        add_score(score_data, weights, "meta_description_score", max_p if data.get("isMetaDescriptionEnoughLong") else max_p * 0.3, issue_msg="Meta description length suboptimal.", success_msg="Meta description present and well-sized.")
    else:
        add_score(score_data, weights, "meta_description_score", 0, issue_msg="Meta description missing.")
    # Headings
    max_p_h = weights["headings_score"]["max_points"]
    h_earned = 0
    if data.get("isH1"):
        h_earned += max_p_h * (0.6 if data.get("isH1OnlyOne") else 0.3)
    else:
        score_data["issues"].append("Headings: H1 tag missing.")
    if data.get("isH2"):
        h_earned += max_p_h * 0.4
    add_score(score_data, weights, "headings_score", h_earned, issue_msg="Heading structure (H1/H2) needs improvement.", success_msg="Good H1/H2 usage.")
    # Image Alt Text
    max_p = weights["image_alt_text_score"]["max_points"]
    missing_alt = data.get("notOptimizedImagesCount", 0)
    total_img = data.get("total_images_on_page", 0)
    if total_img > 0:
        add_score(score_data, weights, "image_alt_text_score", max_p * ((total_img - missing_alt) / total_img), issue_msg=f"{missing_alt} images missing alt text.", success_msg="Good alt text coverage.")
    else:
        add_score(score_data, weights, "image_alt_text_score", max_p * 0.5, issue_msg="No images detected.")
    # Responsive Images
    max_p = weights["responsive_image_score"]["max_points"]
    responsive_issues = data.get("responsiveImageIssuesCount", 0)
    add_score(score_data, weights, "responsive_image_score", max(0, max_p - responsive_issues), issue_msg=f"{responsive_issues} images may be non-responsive.", success_msg="Responsive images in use.")
    # Content length
    add_score(score_data, weights, "content_length_score", weights["content_length_score"]["max_points"] if data.get("isContentEnoughLong") else 0, issue_msg="Content length appears thin.", success_msg="Content length is sufficient.")
    # Internal links
    add_score(score_data, weights, "internal_links_score", weights["internal_links_score"]["max_points"] if data.get("isTooEnoughlinks") else 0, issue_msg="Too few links.", success_msg="Healthy link count.")
    # Broken links penalty
    add_score(score_data, weights, "broken_links_penalty", min(weights["broken_links_penalty"]["max_points"], data.get("brokenLinksCount", 0)), is_penalty=True, issue_msg=f"{data.get('brokenLinksCount',0)} broken links detected.", success_msg="No broken links.")
    # Social tags
    add_score(score_data, weights, "open_graph_score", weights["open_graph_score"]["max_points"] if data.get("hasOpenGraph") else 0, issue_msg="Open Graph tags missing.", success_msg="Open Graph tags present.")
    add_score(score_data, weights, "twitter_card_score", weights["twitter_card_score"]["max_points"] if data.get("hasTwitterCards") else 0, issue_msg="Twitter card tags missing.", success_msg="Twitter card tags present.")
    # URL
    add_score(score_data, weights, "seo_friendly_url_score", weights["seo_friendly_url_score"]["max_points"] if data.get("isSeoFriendlyUrl") else 0, issue_msg="URL may not be SEO friendly.", success_msg="SEO friendly URL.")
    # Inline CSS penalty
    add_score(score_data, weights, "inline_css_penalty", min(weights["inline_css_penalty"]["max_points"], data.get("inlineCssCount", 0) * 0.1), is_penalty=True, issue_msg="Inline CSS detected.", success_msg="No inline CSS issues.")
    # Deprecated/Flash/Frameset
    add_score(score_data, weights, "deprecated_html_penalty", weights["deprecated_html_penalty"]["max_points"] if data.get("hasDeprecatedHtmlTags") else 0, is_penalty=True, issue_msg="Deprecated HTML tags found.", success_msg="No deprecated HTML tags.")
    add_score(score_data, weights, "flash_content_penalty", weights["flash_content_penalty"]["max_points"] if data.get("hasFlashContent") else 0, is_penalty=True, issue_msg="Flash content found.", success_msg="No Flash content.")
    add_score(score_data, weights, "frameset_penalty", weights["frameset_penalty"]["max_points"] if data.get("hasFrameset") else 0, is_penalty=True, issue_msg="Framesets detected.", success_msg="No framesets.")
    # Unsafe cross-origin links
    add_score(score_data, weights, "unsafe_cross_origin_links_penalty", min(weights["unsafe_cross_origin_links_penalty"]["max_points"], data.get("unsafeCrossOriginLinksCount", 0) * 0.5), is_penalty=True, issue_msg="Unsafe rel on target=_blank links.", success_msg="Cross-origin links use rel noopener.")

