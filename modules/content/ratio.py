def calculate_text_to_html_ratio(text_content: str, html_content: str) -> dict:
    len_text = len(text_content)
    len_html = len(html_content)
    ratio = 0 if len_html == 0 else round((len_text / len_html) * 100, 2)
    status = "calculated"
    if ratio < 15:
        status = "low_ratio"
    elif ratio > 70:
        status = "high_ratio"
    return {"textToHtmlRatioPercent": ratio, "textToHtmlRatioStatus": status}

