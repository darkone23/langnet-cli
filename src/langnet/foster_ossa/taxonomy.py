from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from langnet.learning.grammar_concepts import GrammarConcept, load_grammar_concepts

DIRECT_TOC_FIELDS = ("foster_terms", "traditional_terms")
EXPERIENCE_METHOD_FIELDS = ("core_foster_terms", "traditional_bridge_terms")
EXPERIENCE_OVERLAY_FIELDS = ("platform_taxonomy_implications",)

FOSTER_CONCEPT_ALIASES = {
    "function of-possession": ("case.genitive",),
    "form-of-possession": ("case.genitive",),
    "form of-possession": ("case.genitive",),
    "gen. of-possession": ("case.genitive",),
    "genitive form of-possession": ("case.genitive",),
    "of-possession": ("case.genitive",),
    "of-possession function": ("case.genitive",),
    "the double function of-possession": ("case.genitive",),
    "the form of-possession": ("case.genitive",),
    "the function of-possession": ("case.genitive",),
    "function to-for-from": ("case.dative",),
    "form to-for-from": ("case.dative",),
    "to-for-from": ("case.dative",),
    "to-for-from function": ("case.dative",),
    "object form": ("case.accusative",),
    "object forms": ("case.accusative",),
    "subject form": ("case.nominative",),
    "subject forms": ("case.nominative",),
    "function of address": ("case.vocative",),
    "location function": ("case.locative",),
}


def audit_foster_taxonomy(
    *,
    toc_summary_path: Path,
    experience_summary_path: Path | None = None,
) -> dict[str, Any]:
    concept_index = _concept_match_index(load_grammar_concepts())
    candidates: dict[str, dict[str, Any]] = {}
    for summary in _valid_generated_summaries(toc_summary_path):
        for field in DIRECT_TOC_FIELDS:
            for term in _string_items(summary.get(field)):
                _record_candidate(
                    candidates,
                    term=term,
                    source_kind=field,
                    source_refs=_string_items(summary.get("source_refs")),
                    default_classification="direct_source_candidate",
                    concept_index=concept_index,
                )
    if experience_summary_path is not None and experience_summary_path.exists():
        for summary in _valid_generated_summaries(experience_summary_path):
            for field in EXPERIENCE_METHOD_FIELDS:
                for term in _string_items(summary.get(field)):
                    _record_candidate(
                        candidates,
                        term=term,
                        source_kind=field,
                        source_refs=_string_items(summary.get("source_refs")),
                        default_classification="method_supported_candidate",
                        concept_index=concept_index,
                    )
            for field in EXPERIENCE_OVERLAY_FIELDS:
                for term in _string_items(summary.get(field)):
                    _record_candidate(
                        candidates,
                        term=term,
                        source_kind=field,
                        source_refs=_string_items(summary.get("source_refs")),
                        default_classification="platform_overlay_candidate",
                        concept_index=concept_index,
                    )
    rows = sorted(
        candidates.values(),
        key=lambda row: (
            _classification_rank(str(row["classification"])),
            -int(row["occurrences"]),
            str(row["term"]).casefold(),
        ),
    )
    counts = Counter(str(row["classification"]) for row in rows)
    return {
        "schema_version": "langnet.foster_ossa_taxonomy_audit.v1",
        "summary": {
            "total_candidates": len(rows),
            "classification_counts": dict(sorted(counts.items())),
        },
        "candidates": rows,
    }


def render_taxonomy_audit_markdown(audit: dict[str, Any]) -> str:
    raw_summary = audit.get("summary")
    summary = cast(Mapping[str, object], raw_summary) if isinstance(raw_summary, Mapping) else {}
    lines = [
        "# Foster Ossa Taxonomy Audit",
        "",
        "Generated from validated Foster Ossa summary JSON. Use this as a review "
        "surface before changing the stable grammar concept registry.",
        "",
        f"- Total candidates: {summary.get('total_candidates', 0)}",
    ]
    counts = summary.get("classification_counts")
    if isinstance(counts, Mapping):
        for name, count in sorted(counts.items()):
            lines.append(f"- {name}: {count}")
    by_class: dict[str, list[dict[str, Any]]] = {}
    candidates = audit.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict):
                by_class.setdefault(str(candidate["classification"]), []).append(candidate)
    sorted_classes = sorted(
        by_class.items(),
        key=lambda item: _classification_rank(item[0]),
    )
    for classification, rows in sorted_classes:
        lines.extend(["", f"## {classification.replace('_', ' ').title()}", ""])
        for row in rows:
            matched = _markdown_refs(row.get("matched_concept_ids"))
            refs = _markdown_refs(row.get("source_refs"))
            kinds = ", ".join(str(item) for item in row.get("source_kinds", []))
            line = f"- **{row['term']}**"
            if matched:
                line += f" -> {matched}"
            line += f" ({row['occurrences']} occurrence(s); {kinds})"
            if refs:
                line += f" — {refs}"
            lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


def write_taxonomy_audit_markdown(*, audit: dict[str, Any], output_path: Path) -> Path:
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_taxonomy_audit_markdown(audit), encoding="utf-8")
    return output_path


def _record_candidate(  # noqa: PLR0913
    candidates: dict[str, dict[str, Any]],
    *,
    term: str,
    source_kind: str,
    source_refs: list[str],
    default_classification: str,
    concept_index: dict[str, set[str]],
) -> None:
    key = _normalize_term(term)
    if not key:
        return
    matched_ids = sorted(concept_index.get(key, set()))
    row = candidates.setdefault(
        key,
        {
            "term": term,
            "normalized_term": key,
            "classification": "existing_concept" if matched_ids else default_classification,
            "matched_concept_ids": matched_ids,
            "source_kinds": [],
            "source_refs": [],
            "occurrences": 0,
        },
    )
    if matched_ids:
        row["classification"] = "existing_concept"
        row["matched_concept_ids"] = sorted(set(row["matched_concept_ids"]) | set(matched_ids))
    elif row["classification"] != "existing_concept":
        row["classification"] = _stronger_classification(
            str(row["classification"]),
            default_classification,
        )
    row["occurrences"] = int(row["occurrences"]) + 1
    row["source_kinds"] = sorted(set(row["source_kinds"]) | {source_kind})
    row["source_refs"] = sorted(
        set(row["source_refs"]) | set(source_refs),
        key=_source_ref_sort_key,
    )


def _valid_generated_summaries(path: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for line in path.expanduser().read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("validation_status") != "generated_valid":
            continue
        summary_json = row.get("generated_json")
        if not isinstance(summary_json, str):
            continue
        summary = json.loads(summary_json)
        if isinstance(summary, dict):
            summaries.append(summary)
    return summaries


def _concept_match_index(concepts: dict[str, GrammarConcept]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for concept in concepts.values():
        terms = [
            concept.id,
            concept.id.split(".")[-1],
            concept.kind,
            concept.foster_gateway,
            concept.plain_english,
            *concept.traditional.values(),
        ]
        for term in terms:
            key = _normalize_term(term)
            if key:
                index.setdefault(key, set()).add(concept.id)
    for term, concept_ids in FOSTER_CONCEPT_ALIASES.items():
        key = _normalize_term(term)
        if key:
            index.setdefault(key, set()).update(
                concept_id for concept_id in concept_ids if concept_id in concepts
            )
    return index


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_term(term: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", " ", term.casefold())
    return " ".join(cleaned.split())


def _classification_rank(classification: str) -> int:
    order = {
        "existing_concept": 0,
        "direct_source_candidate": 1,
        "method_supported_candidate": 2,
        "platform_overlay_candidate": 3,
    }
    return order.get(classification, 99)


def _stronger_classification(current: str, incoming: str) -> str:
    return current if _classification_rank(current) <= _classification_rank(incoming) else incoming


def _source_ref_sort_key(ref: str) -> tuple[str, int, str]:
    prefix, _, rest = ref.partition(":")
    numeric = rest.split(".", maxsplit=1)[0]
    return prefix, int(numeric) if numeric.isdigit() else 999999, ref


def _markdown_refs(value: object) -> str:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ""
    visible = value[:12]
    text = ", ".join(f"`{item}`" for item in visible)
    if len(value) > len(visible):
        text += f", ... ({len(value)} refs)"
    return text
