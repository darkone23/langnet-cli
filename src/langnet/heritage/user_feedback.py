from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from langnet.heritage.client import SktSearchMatch


def parse_user_feedback(html: str) -> list[SktSearchMatch]:
    """
    Parse Heritage sktuser feedback HTML for possible lemmatizations.

    The feedback page lists radio inputs named ``guess`` with values like
    ``{vi.s.nu},{n.}`` and nearby anchors pointing to dictionary entries.
    """
    soup = BeautifulSoup(html, "html.parser")
    matches: list[SktSearchMatch] = []
    seen: set[tuple[str, str]] = set()
    for input_el in soup.find_all("input", attrs={"name": "guess"}):
        value_raw = input_el.get("value", "")
        # BeautifulSoup's .get() can return str | list | None, ensure we have a string
        value = value_raw if isinstance(value_raw, str) else ""
        if not value:
            continue

        canonical = _extract_canonical(value)
        if not canonical:
            continue
        label_text, anchor = _extract_label_and_anchor(input_el)
        code = _extract_analysis(value)
        analysis = label_text or code
        display = canonical
        entry_url = ""
        if anchor and isinstance(anchor, Tag):
            href_raw = anchor.get("href")
            entry_url = href_raw if isinstance(href_raw, str) else ""
            display = _anchor_display(anchor) or display
        key = (analysis or "", display or canonical)
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            SktSearchMatch(
                canonical=canonical,
                display=display,
                entry_url=entry_url,
                analysis=analysis,
            )
        )
    return matches


def _extract_canonical(value: str) -> str:
    match = re.search(r"\{([^}]+)\}", value)
    if match:
        return match.group(1)
    return ""


def _extract_analysis(value: str) -> str:
    parts = re.findall(r"\{([^}]+)\}", value)
    if len(parts) >= 2:  # noqa: PLR2004
        return parts[1]
    return ""


def _extract_label_and_anchor(node) -> tuple[str, Tag | None]:
    container = getattr(node, "find_parent", lambda *_a, **_k: None)("th") or getattr(
        node, "parent", None
    )
    if not container:
        return "", None
    anchor = getattr(container, "find", lambda *_a, **_k: None)("a")
    label_text = ""
    if getattr(container, "get_text", None):
        text = container.get_text(" ", strip=True)
        if "[" in text:
            text = text.split("[", 1)[0]
        label_text = text.strip()
    return label_text, anchor


def _nearest_anchor(node):
    for sib in getattr(node, "next_siblings", []) or []:
        if getattr(sib, "name", None) == "a":
            return sib
        if getattr(sib, "find", None):
            anchor = sib.find("a")
            if anchor:
                return anchor
    parent = getattr(node, "parent", None)
    if parent is not None and getattr(parent, "find", None):
        return parent.find("a")
    return None


def _anchor_display(anchor) -> str:
    italic = getattr(anchor, "find", lambda *_a, **_kw: None)("i")
    if italic and italic.text:
        return italic.text.strip()
    text = getattr(anchor, "get_text", lambda **_kw: "")(strip=True)
    return text or ""
