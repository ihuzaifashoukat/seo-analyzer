from urllib.parse import urljoin
from typing import Tuple, List, Dict, Optional


AI_BOT_RECOMMENDATIONS = [
    # Common AI/LLM-related user agents seen in practice
    "GPTBot",           # OpenAI
    "ChatGPT-User",     # OpenAI browser plugin UA
    "Google-Extended",  # Google data opt-out
    "CCBot",            # Common Crawl
    "ClaudeBot",        # Anthropic (various forms exist)
    "anthropic-ai",     # Alt string
    "PerplexityBot",    # Perplexity
    "Applebot-Extended",# Apple data opt-out
    "FacebookBot",      # Meta variants
    "Bytespider",       # ByteDance
]


def _fetch_first_available_llms_txt(base_domain_url: str, make_request_fn, headers: dict, timeout: int) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Tries to fetch llms.txt (or common alternates) from the site.
    Returns: (url_used, text_content, status_code)
    """
    candidates = [
        urljoin(base_domain_url, "/llms.txt"),
        urljoin(base_domain_url, "/ai.txt"),
        urljoin(base_domain_url, "/.well-known/ai.txt"),
    ]
    for url in candidates:
        resp, _ = make_request_fn(url, headers=headers, timeout=timeout)
        if resp and resp.status_code == 200 and resp.text:
            return url, resp.text, resp.status_code
        # If explicitly 200 required; skip others but remember last code
        last_status = resp.status_code if resp else None
    return None, None, None


def _parse_llms_txt(content: str) -> Dict:
    """
    Very lightweight parser for llms.txt-like files. Not a formal spec, but
    captures common patterns similar to robots.txt with extra AI-related directives.
    """
    groups: List[Dict] = []
    global_directives: List[Dict[str, str]] = []
    current_group: Optional[Dict] = None

    def start_group(user_agent: str):
        nonlocal current_group
        current_group = {
            "user_agent": user_agent,
            "allows": [],
            "disallows": [],
            "crawl_delay": None,
            "training": None,   # e.g., allow/deny training
            "extra": {},        # other key-value pairs seen in group scope
        }
        groups.append(current_group)

    for raw_line in content.splitlines():
        # Remove comments and trim
        line = raw_line.split('#', 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()

        kl = key.lower()
        if kl == "user-agent":
            start_group(val)
            continue

        # If we're within a UA group, classify common directives
        if current_group is not None:
            if kl == "allow":
                current_group["allows"].append(val)
                continue
            if kl == "disallow":
                current_group["disallows"].append(val)
                continue
            if kl in ("crawl-delay", "crawl_delay"):
                current_group["crawl_delay"] = val
                continue
            if kl in ("training", "allow-training", "data-usage", "data_use", "data-collection"):
                current_group["training"] = val
                continue
            # Anything else within a group, record in extra
            current_group["extra"][key] = val
        else:
            # Global scope directives (before any user-agent)
            global_directives.append({key: val})

    return {
        "user_agent_groups": groups,
        "global_directives": global_directives,
    }


def _recommendations_for_llms_txt(parsed: Dict) -> List[str]:
    recs: List[str] = []
    groups = parsed.get("user_agent_groups", [])
    if not groups:
        recs.append("Define at least one User-agent group (e.g., GPTBot, Google-Extended, *).")

    # See which recommended AI bots are covered
    present_uas = {g.get("user_agent", "").strip() for g in groups}
    missing = [ua for ua in AI_BOT_RECOMMENDATIONS if ua not in present_uas and ua.lower() not in present_uas]
    if missing:
        recs.append(f"Consider adding explicit directives for AI bots: {', '.join(missing[:8])}{'…' if len(missing)>8 else ''}.")

    # Encourage clarity on training/usage
    if any(g.get("training") for g in groups):
        pass
    else:
        recs.append("State training/usage policy per bot (e.g., Training: allow|deny).")

    # Suggest including sitemap/contact/policy in global directives
    gd_keys = {k.lower() for d in parsed.get("global_directives", []) for k in d.keys()}
    if "sitemap" not in gd_keys:
        recs.append("Include Sitemap: URL to help discovery.")
    if all(k not in gd_keys for k in ("contact", "owner", "email")):
        recs.append("Provide a Contact: email or URL for issues.")
    policy_keys = {k for k in gd_keys if "policy" in k or "license" in k}
    if not policy_keys:
        recs.append("Link a Policy/License for data usage (e.g., Policy: URL).")

    return recs


def check_llms_txt(base_domain_url: str, make_request_fn, headers: dict, timeout: int) -> dict:
    """
    Checks for presence of llms.txt (or common alternates), parses basic directives,
    and returns a checklist-style result with recommendations.
    """
    url_used, text_content, status_code = _fetch_first_available_llms_txt(base_domain_url, make_request_fn, headers, timeout)

    if not url_used or not text_content:
        return {
            "llmsTxtStatus": "not_found",
            "llmsTxtUrlDetected": None,
            "llmsTxtPreview": None,
            "llmsTxtParsed": False,
            "llmsTxtRecommendations": [
                "No llms.txt/ai.txt found. Consider adding one to guide AI/LLM crawlers.",
                "Document directives for common AI bots (GPTBot, Google-Extended, CCBot, Claude, Perplexity).",
            ],
        }

    parsed = _parse_llms_txt(text_content)
    groups = parsed.get("user_agent_groups", [])
    present_uas = [g.get("user_agent", "") for g in groups]
    missing_agents = [ua for ua in AI_BOT_RECOMMENDATIONS if ua not in present_uas and ua.lower() not in present_uas]
    recs = _recommendations_for_llms_txt(parsed)

    return {
        "llmsTxtStatus": "found",
        "llmsTxtUrlDetected": url_used,
        "llmsTxtPreview": text_content[:1000],
        "llmsTxtParsed": True,
        "llmsTxtUserAgentGroups": groups,
        "llmsTxtGlobalDirectives": parsed.get("global_directives", []),
        "llmsTxtHasAIUserAgents": any(ua in present_uas or ua.lower() in present_uas for ua in AI_BOT_RECOMMENDATIONS),
        "llmsTxtMissingRecommendedAgents": missing_agents,
        "llmsTxtRecommendations": recs,
    }

