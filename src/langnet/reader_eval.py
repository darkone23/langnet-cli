from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from langnet.execution.handlers import cdsl as cdsl_handlers
from langnet.normalizer.utils import normalize_greekish_token

TOP_BUCKET_LIMIT = 3
LATIN_UM_SUFFIX_LEN = 2


def load_reader_eval_fixture(path: Path) -> dict[str, Any]:
    """Load a reader-eval fixture file."""
    return json.loads(path.read_text())


def iter_reader_eval_tokens(
    fixture: Mapping[str, Any],
    *,
    languages: set[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for passage in fixture.get("passages", []):
        if not isinstance(passage, Mapping):
            continue
        language = str(passage.get("language") or "")
        if languages is not None and language not in languages:
            continue
        for token in passage.get("tokens", []):
            if not isinstance(token, Mapping):
                continue
            tokens.append(
                {
                    "passage_id": str(passage.get("id") or ""),
                    "work": str(passage.get("work") or ""),
                    "citation": str(passage.get("citation") or ""),
                    "language": language,
                    **dict(token),
                }
            )
            if limit is not None and len(tokens) >= limit:
                return tokens
    return tokens


def summarize_reader_eval(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.get("passed") is True)
    meaning_passed = sum(1 for result in results if result.get("meaning_passed") is True)
    top_passed = sum(1 for result in results if result.get("top_passed") is True)
    failed = total - passed
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "hit_rate": passed / total if total else 0.0,
        "meaning_passed": meaning_passed,
        "meaning_failed": total - meaning_passed,
        "meaning_hit_rate": meaning_passed / total if total else 0.0,
        "top_passed": top_passed,
        "top_failed": total - top_passed,
        "top_hit_rate": top_passed / total if total else 0.0,
    }


def evaluate_reader_token(
    token: Mapping[str, Any],
    reduction: Mapping[str, Any],
    *,
    morphology_rows: Sequence[Mapping[str, Any]] | None = None,
    top_bucket_limit: int = TOP_BUCKET_LIMIT,
    error: str | None = None,
) -> dict[str, Any]:
    if error is not None:
        return {
            "passage_id": token.get("passage_id", ""),
            "language": token.get("language", ""),
            "surface": token.get("surface", ""),
            "passed": False,
            "error": error,
            "checks": {},
            "actual": {},
        }

    actual_lemmas = _actual_lemmas(reduction)
    top_lemmas = _top_lemmas(reduction, top_bucket_limit=top_bucket_limit) or actual_lemmas
    first_bucket_lemmas = _top_lemmas(reduction, top_bucket_limit=1) or top_lemmas[:1]
    text_blob = _normalized_text_blob(_flatten_strings(reduction))
    top_text_blob = _normalized_text_blob(_bucket_strings(_buckets(reduction)[:1]))
    morphology = list(morphology_rows or [])

    expected_lemmas = _strings(token.get("expected_lemmas"))
    expected_gloss_terms = _strings(token.get("expected_gloss_terms"))
    expected_components = _strings(token.get("expected_components"))
    known_bad_lemmas = _strings(token.get("known_bad_lemmas"))
    known_bad_gloss_terms = _strings(token.get("known_bad_gloss_terms"))

    lemma_hit = _any_lemma_member(expected_lemmas, actual_lemmas)
    top_lemma_hit = not expected_lemmas or _any_lemma_member(expected_lemmas, first_bucket_lemmas)
    gloss_hit = _any_normalized_substring(expected_gloss_terms, text_blob)
    top_gloss_hit = not expected_gloss_terms or _any_normalized_substring(
        expected_gloss_terms,
        top_text_blob,
    )
    top_answer_hit = top_gloss_hit and (top_lemma_hit or lemma_hit)
    component_hit = not expected_components or _all_normalized_substrings(
        expected_components,
        text_blob,
    )
    morphology_hit = not bool(token.get("expect_morphology")) or bool(morphology)
    known_bad_lemma_top = _any_normalized_member(known_bad_lemmas, first_bucket_lemmas)
    known_bad_gloss_top = _any_normalized_substring(known_bad_gloss_terms, top_text_blob)

    checks = {
        "lemma_hit": lemma_hit,
        "top_lemma_hit": top_lemma_hit,
        "gloss_hit": gloss_hit,
        "top_gloss_hit": top_gloss_hit,
        "top_answer_hit": top_answer_hit,
        "component_hit": component_hit,
        "morphology_hit": morphology_hit,
        "known_bad_lemma_not_top": not known_bad_lemma_top,
        "known_bad_gloss_not_top": not known_bad_gloss_top,
    }
    meaning_checks = {
        "lemma_hit": lemma_hit,
        "gloss_hit": gloss_hit,
        "component_hit": component_hit,
        "known_bad_lemma_not_top": not known_bad_lemma_top,
        "known_bad_gloss_not_top": not known_bad_gloss_top,
    }
    top_checks = {
        "top_answer_hit": top_answer_hit,
        "known_bad_lemma_not_top": not known_bad_lemma_top,
        "known_bad_gloss_not_top": not known_bad_gloss_top,
    }
    return {
        "passage_id": token.get("passage_id", ""),
        "language": token.get("language", ""),
        "surface": token.get("surface", ""),
        "passed": all(checks.values()),
        "meaning_passed": all(meaning_checks.values()),
        "top_passed": all(top_checks.values()),
        "checks": checks,
        "expected": {
            "lemmas": expected_lemmas,
            "gloss_terms": expected_gloss_terms,
            "components": expected_components,
        },
        "actual": {
            "lemmas": actual_lemmas,
            "top_lemmas": top_lemmas,
            "top_glosses": _display_glosses(_buckets(reduction)[:top_bucket_limit]),
            "morphology_rows": morphology,
        },
    }


def _strings(value: object) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return []
    return [str(item) for item in value if str(item)]


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.removeprefix("lex:").split())


def _actual_lemmas(reduction: Mapping[str, Any]) -> list[str]:
    values = [
        str(value).removeprefix("lex:") for value in _strings(reduction.get("lexeme_anchors"))
    ]
    for bucket in _buckets(reduction):
        for witness in _witnesses(bucket):
            values.extend(_witness_lemma_forms(witness))
    return _dedupe(values)


def _top_lemmas(reduction: Mapping[str, Any], *, top_bucket_limit: int) -> list[str]:
    values: list[str] = []
    for bucket in _buckets(reduction)[:top_bucket_limit]:
        for witness in _witnesses(bucket):
            values.extend(_witness_lemma_forms(witness))
    return _dedupe(values)


def _witness_lemma_forms(witness: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    anchor = witness.get("lexeme_anchor")
    if isinstance(anchor, str):
        lemma = anchor.removeprefix("lex:")
        values.append(lemma)
        values.append(_sanskrit_display_form(lemma))
    evidence = witness.get("evidence")
    if isinstance(evidence, Mapping):
        display_iast = evidence.get("display_iast")
        display_slp1 = evidence.get("display_slp1")
        if isinstance(display_iast, str):
            values.append(display_iast)
        if isinstance(display_slp1, str):
            values.append(_sanskrit_display_form(display_slp1))
        source_entry = evidence.get("source_entry")
        if isinstance(source_entry, Mapping):
            for key in ("headword_roma", "headword_norm", "key_iast", "key2_iast"):
                value = source_entry.get(key)
                if isinstance(value, str):
                    values.append(value)
    return values


def _sanskrit_display_form(value: str) -> str:
    if not value:
        return ""
    return cdsl_handlers._slp1_to_iast(value)  # type: ignore[attr-defined]


def _buckets(reduction: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    buckets = reduction.get("buckets")
    if not isinstance(buckets, Sequence) or isinstance(buckets, (str, bytes)):
        return []
    return [bucket for bucket in buckets if isinstance(bucket, Mapping)]


def _witnesses(bucket: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    witnesses = bucket.get("witnesses")
    if not isinstance(witnesses, Sequence) or isinstance(witnesses, (str, bytes)):
        return []
    return [witness for witness in witnesses if isinstance(witness, Mapping)]


def _display_glosses(buckets: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(bucket.get("display_gloss"))
        for bucket in buckets
        if isinstance(bucket.get("display_gloss"), str) and bucket.get("display_gloss")
    ]


def _bucket_strings(buckets: Sequence[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for bucket in buckets:
        values.extend(_flatten_strings(bucket))
    return values


def _flatten_strings(value: object) -> list[str]:
    values: list[str] = []
    if isinstance(value, str):
        values.append(value)
    elif isinstance(value, Mapping):
        for child in value.values():
            values.extend(_flatten_strings(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            values.extend(_flatten_strings(child))
    return values


def _normalized_text_blob(values: Sequence[str]) -> str:
    return "\n".join(_normalize(value) for value in values)


def _any_normalized_member(expected: Sequence[str], actual: Sequence[str]) -> bool:
    actual_values = {_normalize(value) for value in actual}
    return any(_normalize(value) in actual_values for value in expected)


def _any_lemma_member(expected: Sequence[str], actual: Sequence[str]) -> bool:
    actual_values = {key for value in actual for key in _lemma_match_keys(value)}
    return any(
        expected_key in actual_values
        for expected_value in expected
        for expected_key in _lemma_match_keys(expected_value)
    )


def _lemma_match_keys(value: str) -> set[str]:
    normalized = _normalize(value)
    base = normalized.split("#", 1)[0]
    keys = {normalized, base}
    keys.update({key[:-1] for key in list(keys) if key.endswith(("h", "ḥ")) and len(key) > 1})
    keys.update(_latin_inflectional_match_keys(base))
    greekish = normalize_greekish_token(value)
    if greekish:
        keys.add(greekish)
    return keys


def _latin_inflectional_match_keys(value: str) -> set[str]:
    if not value.isascii() or not value.isalpha():
        return set()
    if len(value) <= LATIN_UM_SUFFIX_LEN or not value.endswith("um"):
        return set()
    stem = value[:-LATIN_UM_SUFFIX_LEN]
    if not stem:
        return set()
    return {f"{stem}a", f"{stem}us"}


def _any_normalized_substring(needles: Sequence[str], haystack: str) -> bool:
    return any(_normalize(needle) in haystack for needle in needles)


def _all_normalized_substrings(needles: Sequence[str], haystack: str) -> bool:
    return all(_normalize(needle) in haystack for needle in needles)


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = _normalize(value)
        if not value or normalized in seen:
            continue
        seen.add(normalized)
        out.append(value)
    return out
