"""Shared validation helpers for languages, tools, and actions."""

from __future__ import annotations

from typing import Iterable

VALID_LANGUAGES = {"lat", "grc", "san"}
LANG_ALIASES = {"grk": "grc"}

VALID_TOOLS = {"diogenes", "whitakers", "heritage", "cdsl", "cltk"}
VALID_ACTIONS_BY_TOOL = {
    "diogenes": {"parse"},
    "whitakers": {"search"},
    "heritage": {"morphology", "canonical", "lemmatize"},
    "cdsl": {"lookup"},
    "cltk": {"morphology", "dictionary"},
}


def normalize_language(lang: str | None) -> str:
    if not lang:
        raise ValueError("Missing required parameter: language")
    lang = lang.strip().lower()
    if lang in LANG_ALIASES:
        lang = LANG_ALIASES[lang]
    if lang not in VALID_LANGUAGES:
        raise ValueError(
            f"Invalid language: {lang}. Must be one of: {', '.join(sorted(VALID_LANGUAGES | set(LANG_ALIASES)))}"
        )
    return lang


def validate_word(word: str | None) -> None:
    if word is None:
        raise ValueError("Missing required parameter: search term")
    if not str(word).strip():
        raise ValueError("Search term cannot be empty")


def validate_query(lang: str | None, word: str | None) -> tuple[str | None, str | None]:
    """Validate and normalize a query (language + word). Returns (error, normalized_lang)."""
    try:
        normalized_lang = normalize_language(lang)
    except ValueError as exc:
        return str(exc), None
    try:
        validate_word(word)
    except ValueError as exc:
        return str(exc), None
    return None, normalized_lang


def _invalid_set_message(name: str, value: str | None, allowed: Iterable[str]) -> str:
    return f"Invalid {name}: {value}. Must be one of: {', '.join(sorted(allowed))}"


def validate_tool_request(
    tool: str | None,
    action: str | None,
    lang: str | None = None,
    query: str | None = None,
    dict_name: str | None = None,
) -> str | None:
    """Validate tool/action and any tool-specific parameters. Returns error string or None."""
    if tool not in VALID_TOOLS:
        return _invalid_set_message("tool", tool, VALID_TOOLS)

    valid_actions = VALID_ACTIONS_BY_TOOL.get(tool, set())
    if action not in valid_actions:
        return _invalid_set_message("action", action, valid_actions or {"<none>"})

    validators = {
        "diogenes": lambda: _validate_lang_and_query(lang, query),
        "whitakers": lambda: _require_query(query, "whitakers"),
        "heritage": lambda: _require_query(query, "heritage"),
        "cdsl": lambda: _require_query(query, "cdsl"),
        "cltk": lambda: _validate_lang_and_query(lang, query),
    }

    return validators.get(tool, lambda: None)()


def _require_query(query: str | None, tool: str) -> str | None:
    return None if query else f"Missing required parameter: query for {tool} tool"


def _validate_lang_and_query(lang: str | None, query: str | None) -> str | None:
    if not lang:
        return "Missing required parameter: lang"
    if lang not in (VALID_LANGUAGES | set(LANG_ALIASES)):
        return _invalid_set_message("language", lang, VALID_LANGUAGES | set(LANG_ALIASES))
    if not query:
        return "Missing required parameter: query"
    return None
