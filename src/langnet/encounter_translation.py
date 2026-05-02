from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

from langnet.translation import (
    TranslationCache,
    populate_missing_translations,
    project_cached_translations,
    translation_cache_status_counts,
)


def resolve_translation_mode(use_translation_cache: bool, translation_mode: str) -> str:
    if translation_mode == "do-it-all":
        return "auto"
    if use_translation_cache and translation_mode == "off":
        return "cache"
    return translation_mode


def empty_translation_counts() -> dict[str, int]:
    return {"total": 0, "hits": 0, "missing": 0, "errors": 0, "empty": 0}


def merge_translation_counts(total: dict[str, int], counts: Mapping[str, int]) -> None:
    for key, value in counts.items():
        total[key] = total.get(key, 0) + int(value)


def add_translation_counts(
    total: dict[str, int],
    counts: Mapping[str, int],
    *,
    prefix: str = "",
) -> None:
    for key, value in counts.items():
        total[f"{prefix}{key}"] = total.get(f"{prefix}{key}", 0) + int(value)


def encounter_translation_diagnostics(
    *,
    mode: str,
    cache_path: Path,
    model: str,
    populate: bool,
) -> dict[str, object]:
    return {
        "mode": mode,
        "cache_db": str(cache_path),
        "model": model,
        "cache_available": False,
        "populate": populate,
        "written": 0,
        "before": empty_translation_counts(),
        "after": empty_translation_counts(),
        "batches": [],
    }


def apply_translation_cache(  # noqa: PLR0913
    *,
    claims: Sequence[Mapping[str, object]],
    language: str,
    model: str,
    cache: TranslationCache,
    populate: bool,
    translate: Callable[[object], str],
    diagnostics: dict[str, object],
    context: str,
) -> list[Mapping[str, object]]:
    before = translation_cache_status_counts(
        claims=claims,
        language=language,
        model=model,
        cache=cache,
    )
    written = 0
    if populate:
        written = populate_missing_translations(
            claims=claims,
            language=language,
            model=model,
            cache=cache,
            translate=translate,
        )
    after = translation_cache_status_counts(
        claims=claims,
        language=language,
        model=model,
        cache=cache,
    )
    merge_translation_counts(cast(dict[str, int], diagnostics["before"]), before)
    merge_translation_counts(cast(dict[str, int], diagnostics["after"]), after)
    diagnostics["written"] = cast(int, diagnostics["written"]) + written
    cast(list[dict[str, object]], diagnostics["batches"]).append(
        {
            "context": context,
            "before": before,
            "written": written,
            "after": after,
        }
    )
    return project_cached_translations(
        claims=claims,
        language=language,
        model=model,
        cache=cache,
    )
