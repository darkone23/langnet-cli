from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from langnet.reader.models import ReaderAlias

_REQUIRED_ALIAS_KEYS = {"alias", "language", "kind", "target", "display"}
_OPTIONAL_ALIAS_KEYS = {"sources"}
_SUPPORTED_ALIAS_KEYS = _REQUIRED_ALIAS_KEYS | _OPTIONAL_ALIAS_KEYS


@dataclass(frozen=True)
class AliasConflict:
    alias: str
    language: str
    targets: tuple[str, ...]


def load_aliases(root: Path) -> list[ReaderAlias]:
    if not root.exists():
        return []

    aliases: list[ReaderAlias] = []
    for path in sorted(root.rglob("*.yaml")):
        aliases.extend(_load_alias_file(path))
    return aliases


def validate_aliases(aliases: list[ReaderAlias]) -> list[AliasConflict]:
    targets_by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    for alias in aliases:
        key = (alias.language, alias.alias)
        if alias.target not in targets_by_key[key]:
            targets_by_key[key].append(alias.target)

    conflicts: list[AliasConflict] = []
    for (language, alias), targets in sorted(targets_by_key.items()):
        if len(targets) > 1:
            conflicts.append(AliasConflict(alias=alias, language=language, targets=tuple(targets)))
    return conflicts


def _load_alias_file(path: Path) -> list[ReaderAlias]:
    current: dict[str, object] | None = None
    aliases: list[ReaderAlias] = []
    saw_header = False

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.rstrip()
        if not line:
            continue
        if line == "aliases:" and not saw_header:
            saw_header = True
            continue
        if not saw_header:
            _raise_unsupported(path, line_number)
        if line.startswith("  - alias: "):
            if current is not None:
                aliases.append(_alias_from_record(path, current))
            alias_value = _parse_quoted_scalar(
                path,
                line_number,
                line.removeprefix("  - alias: "),
            )
            current = {"alias": alias_value}
            continue
        if line.startswith("    "):
            if current is None:
                _raise_unsupported(path, line_number)
                continue
            key, value = _parse_key_value(path, line_number, line.removeprefix("    "))
            current[key] = value
            continue
        _raise_unsupported(path, line_number)

    if current is not None:
        aliases.append(_alias_from_record(path, current))
    return aliases


def _parse_key_value(path: Path, line_number: int, body: str) -> tuple[str, object]:
    if ": " not in body:
        _raise_unsupported(path, line_number)
    key, value_text = body.split(": ", 1)
    if key not in _SUPPORTED_ALIAS_KEYS:
        _raise_unsupported(path, line_number)
    if key == "sources":
        return key, _parse_inline_string_list(path, line_number, value_text)
    return key, _parse_quoted_scalar(path, line_number, value_text)


def _parse_quoted_scalar(path: Path, line_number: int, value_text: str) -> str:
    if not (value_text.startswith('"') and value_text.endswith('"')):
        _raise_unsupported(path, line_number)
    try:
        value = ast.literal_eval(value_text)
    except (SyntaxError, ValueError) as exc:
        msg = f"{path}:{line_number}: invalid quoted string"
        raise ValueError(msg) from exc
    if not isinstance(value, str):
        _raise_unsupported(path, line_number)
    return value


def _parse_inline_string_list(path: Path, line_number: int, value_text: str) -> tuple[str, ...]:
    if not (value_text.startswith("[") and value_text.endswith("]")):
        _raise_unsupported(path, line_number)
    try:
        value = ast.literal_eval(value_text)
    except (SyntaxError, ValueError) as exc:
        msg = f"{path}:{line_number}: invalid inline string list"
        raise ValueError(msg) from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _raise_unsupported(path, line_number)
    return tuple(value)


def _alias_from_record(path: Path, record: dict[str, object]) -> ReaderAlias:
    missing = sorted(_REQUIRED_ALIAS_KEYS - record.keys())
    if missing:
        msg = f"{path}: alias record missing required keys: {', '.join(missing)}"
        raise ValueError(msg)

    sources = record.get("sources", ())
    if not isinstance(sources, tuple) or not all(isinstance(item, str) for item in sources):
        msg = f"{path}: alias record has invalid sources"
        raise ValueError(msg)
    typed_sources = cast(tuple[str, ...], sources)

    return ReaderAlias(
        alias=_record_str(path, record, "alias"),
        language=_record_str(path, record, "language"),
        kind=_record_str(path, record, "kind"),
        target=_record_str(path, record, "target"),
        display=_record_str(path, record, "display"),
        source_file=str(path),
        sources=typed_sources,
    )


def _record_str(path: Path, record: dict[str, object], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: alias record key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _raise_unsupported(path: Path, line_number: int) -> None:
    msg = f"{path}:{line_number}: unsupported alias YAML line"
    raise ValueError(msg)
