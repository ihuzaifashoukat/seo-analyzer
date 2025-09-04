def score_content(data, score_data, weights, add_score):
    if not data or data.get("content_analysis_status") != "completed":
        score_data["issues"].append("Content: Analysis module did not run or found no content.")
        return
    # Readability
    max_p = weights["readability_score"]["max_points"]
    f_score = data.get("flesch_reading_ease_score")
    if f_score is not None:
        if f_score >= 60:
            add_score(score_data, weights, "readability_score", max_p, success_msg=f"Good readability (Flesch: {f_score}).")
        elif f_score >= 30:
            add_score(score_data, weights, "readability_score", max_p * 0.5, issue_msg=f"Readability could be improved (Flesch: {f_score}).")
        else:
            add_score(score_data, weights, "readability_score", max_p * 0.1, issue_msg=f"Very difficult to read (Flesch: {f_score}).")
    else:
        add_score(score_data, weights, "readability_score", 0, issue_msg="Readability score N/A.")
    # Keyword Usage
    max_p_kw = weights["keyword_usage_score"]["max_points"]
    kw_usage = data.get("keywordUsage", {})
    if data.get("target_keywords_analyzed"):
        found_kws = sum(1 for dets in kw_usage.values() if dets.get("phrase_count", 0) > 0)
        total_targeted = len(data.get("target_keywords_analyzed", []))
        if total_targeted > 0:
            add_score(score_data, weights, "keyword_usage_score", max_p_kw * (found_kws / total_targeted), issue_msg=f"{total_targeted - found_kws} target keywords missing or low presence.", success_msg="Target keywords effectively used.")
        else:
            add_score(score_data, weights, "keyword_usage_score", max_p_kw, success_msg="No specific keywords targeted for usage analysis.")
    else:
        add_score(score_data, weights, "keyword_usage_score", max_p_kw, success_msg="No specific keywords targeted for usage analysis.")
    # Most Common Keywords
    if data.get("mostCommonKeywords"):
        add_score(score_data, weights, "most_common_keywords_score", weights["most_common_keywords_score"]["max_points"], success_msg="Common keywords identified.")
    else:
        add_score(score_data, weights, "most_common_keywords_score", 0, issue_msg="Could not identify common keywords.")
    # Text-HTML Ratio
    max_p = weights["text_html_ratio_score"]["max_points"]
    ratio_stat = data.get("textToHtmlRatioStatus")
    ratio_val = data.get("textToHtmlRatioPercent")
    if ratio_stat == "low_ratio":
        add_score(score_data, weights, "text_html_ratio_score", max_p * 0.2, issue_msg=f"Text-to-HTML ratio low ({ratio_val}%).")
    elif ratio_stat in ("calculated", "high_ratio"):
        add_score(score_data, weights, "text_html_ratio_score", max_p, success_msg=f"Text-to-HTML ratio is {ratio_val}%.")
    else:
        add_score(score_data, weights, "text_html_ratio_score", 0, issue_msg="Text-to-HTML ratio N/A.")
    # Spell Check Penalty
    spell_check_data = data.get("spellCheck", {})
    if spell_check_data.get("status") == "completed":
        misspelled_count = spell_check_data.get("misspelled_words_count", 0)
        penalty = min(weights["spell_check_penalty"]["max_points"], misspelled_count * 0.5)
        add_score(score_data, weights, "spell_check_penalty", penalty, is_penalty=True, issue_msg=f"{misspelled_count} potential spelling errors found.", success_msg="No significant spelling errors.")
    elif spell_check_data.get("status") == "skipped_pyspellchecker_not_installed":
        add_score(score_data, weights, "spell_check_penalty", 0, is_penalty=True, issue_msg="Spell check skipped (pyspellchecker not installed).")

