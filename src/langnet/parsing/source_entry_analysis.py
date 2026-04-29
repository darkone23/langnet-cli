"""Grammar-backed source entry analyzers for dictionary diagnostics."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict, cast

from lark import Lark, Token, Tree

_GRAMMAR_DIR = Path(__file__).parent / "grammars"


class ParsedSourceEntry(TypedDict, total=False):
    """Diagnostic parse result for one dictionary entry."""

    source_tool: str
    parser: str
    parsed: bool
    format: str
    headword: str
    principal_parts: list[str]
    pos: str
    gender: str
    bracketed_form: str
    grammar_markers: list[str]
    preamble: str
    sense_number: str
    definition_text: str
    continuation_text: str
    example_text: str
    senses: list[dict[str, object]]
    raw_text: str
    error: str


ParserKind = Literal["dico", "gaffiot"]


def parse_source_entry(source_tool: str, raw_text: str) -> ParsedSourceEntry | None:
    """Parse a source entry with the grammar associated with its dictionary format."""
    normalized_tool = source_tool.strip().lower()
    if normalized_tool in {"diogenes", "cltk", "lewis", "lewis_short"}:
        return _parse_diogenes_like(source_tool, raw_text)
    if normalized_tool not in {"dico", "gaffiot"}:
        return None
    parser_kind = "dico" if normalized_tool == "dico" else "gaffiot"
    parser = _parser(parser_kind)
    try:
        tree = parser.parse(raw_text)
    except Exception as exc:
        return {
            "source_tool": source_tool,
            "parser": f"lark:{parser_kind}_entry",
            "parsed": False,
            "format": parser_kind,
            "raw_text": raw_text,
            "error": exc.__class__.__name__,
        }
    if parser_kind == "dico":
        return _dico_parse_result(source_tool, raw_text, tree)
    return _gaffiot_parse_result(source_tool, raw_text, tree)


def _parse_diogenes_like(source_tool: str, raw_text: str) -> ParsedSourceEntry:
    from langnet.parsing.diogenes_parser import DiogenesEntryParser  # noqa: PLC0415

    parser = DiogenesEntryParser()
    parsed = parser.parse_safe(raw_text)
    if parsed is None:
        return {
            "source_tool": source_tool,
            "parser": "lark:diogenes_entry",
            "parsed": False,
            "format": "diogenes",
            "raw_text": raw_text,
            "error": "LarkError",
        }
    header = parsed.get("header", {})
    senses = parsed.get("senses", [])
    first_gloss = ""
    if senses:
        first_sense = senses[0]
        first_gloss = str(first_sense.get("gloss") or "")
    return _trim_empty(
        {
            "source_tool": source_tool,
            "parser": "lark:diogenes_entry",
            "parsed": True,
            "format": "diogenes",
            "headword": str(header.get("lemma") or ""),
            "principal_parts": list(header.get("principal_parts") or []),
            "pos": str(header.get("pos") or ""),
            "gender": str(header.get("gender") or ""),
            "definition_text": first_gloss,
            "senses": [dict(sense) for sense in senses],
            "raw_text": raw_text,
        }
    )


@lru_cache(maxsize=2)
def _parser(kind: ParserKind) -> Lark:
    grammar_path = _GRAMMAR_DIR / f"{kind}_entry.lark"
    grammar_text = grammar_path.read_text(encoding="utf-8")
    return Lark(
        grammar_text,
        start="start",
        parser="earley",
        lexer="dynamic_complete",
        ambiguity="resolve",
        propagate_positions=True,
    )


def _dico_parse_result(source_tool: str, raw_text: str, tree: Tree) -> ParsedSourceEntry:
    words = _tokens(tree, "WORD")
    bracketed_forms = _tokens(tree, "BRACKET_TEXT")
    grammar_markers = [token.value for token in _tokens(tree, "POS_MARKER")]
    text_tokens = _tokens(tree, "TEXT")
    definition_text = text_tokens[0].value.strip() if text_tokens else raw_text.strip()
    continuation_text = text_tokens[1].value.strip() if len(text_tokens) > 1 else ""
    return _trim_empty(
        {
            "source_tool": source_tool,
            "parser": "lark:dico_entry",
            "parsed": True,
            "format": "dico",
            "headword": words[0].value if words else "",
            "bracketed_form": bracketed_forms[0].value.strip() if bracketed_forms else "",
            "grammar_markers": grammar_markers,
            "definition_text": definition_text,
            "continuation_text": continuation_text,
            "raw_text": raw_text,
        }
    )


def _gaffiot_parse_result(source_tool: str, raw_text: str, tree: Tree) -> ParsedSourceEntry:
    preamble = _first_token_value(tree, "PREAMBLE")
    sense_number = _first_token_value(tree, "NUMBER")
    definition_text = _first_token_value(tree, "DEFINITION_TEXT")
    text_tokens = _tokens(tree, "TEXT")
    example_text = text_tokens[-1].value.strip() if sense_number and text_tokens else ""
    if not definition_text and text_tokens:
        definition_text = text_tokens[0].value.strip()
    return _trim_empty(
        {
            "source_tool": source_tool,
            "parser": "lark:gaffiot_entry",
            "parsed": True,
            "format": "gaffiot",
            "preamble": preamble.strip() if preamble else "",
            "sense_number": sense_number,
            "definition_text": definition_text.strip() if definition_text else "",
            "example_text": example_text,
            "raw_text": raw_text,
        }
    )


def _tokens(tree: Tree, token_type: str) -> list[Token]:
    return [token for token in tree.scan_values(lambda value: _is_token(value, token_type))]


def _first_token_value(tree: Tree, token_type: str) -> str:
    tokens = _tokens(tree, token_type)
    return tokens[0].value if tokens else ""


def _is_token(value: object, token_type: str) -> bool:
    return isinstance(value, Token) and value.type == token_type


def _trim_empty(mapping: dict[str, object]) -> ParsedSourceEntry:
    return cast(
        ParsedSourceEntry,
        {key: value for key, value in mapping.items() if value not in (None, "", [], {})},
    )
