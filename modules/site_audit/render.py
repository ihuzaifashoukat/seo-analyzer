from __future__ import annotations

from typing import Optional


def render_html(url: str, user_agent: Optional[str] = None, timeout: int = 20) -> Optional[str]:
    """
    Best-effort HTML rendering using Playwright if available.
    Returns the rendered HTML as a string, or None if rendering fails or Playwright is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=user_agent or None)
            page = context.new_page()
            page.set_default_timeout(timeout * 1000)
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None

