from __future__ import annotations

from typing import Dict, List, Any, Tuple
from collections import defaultdict
import re


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower()) if s else ""


def group_duplicates_by_field(pages: List[Dict[str, Any]], field_path: List[str]) -> Dict[str, List[str]]:
    """
    Groups pages by a normalized string field and returns mapping: normalized_value -> [urls]
    field_path: e.g., ["OnPageAnalyzer", "title"]
    """
    groups: Dict[str, List[str]] = defaultdict(list)
    for p in pages:
        attrs = p.get('seo_attributes', {})
        f = attrs
        for key in field_path:
            f = f.get(key, {}) if isinstance(f, dict) else None
            if f is None:
                break
        if isinstance(f, str) and f:
            val = _norm_text(f)
            if val:
                groups[val].append(p.get('url'))
    return {k: v for k, v in groups.items() if len(v) > 1}


def duplicate_text_by_hash(pages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Uses OnPageAnalyzer.visibleTextHash to flag duplicate/same text samples across pages.
    """
    groups: Dict[str, List[str]] = defaultdict(list)
    for p in pages:
        attrs = p.get('seo_attributes', {})
        ona = attrs.get('OnPageAnalyzer', {})
        h = ona.get('visibleTextHash')
        if h:
            groups[h].append(p.get('url'))
    return {k: v for k, v in groups.items() if len(v) > 1}

