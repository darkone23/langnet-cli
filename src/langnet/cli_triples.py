from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass

import click

from langnet.execution.handlers import dico as dico_handlers


def triple_matches_filters(
    triple: dict,
    predicate_filter: str | None,
    subject_filter: str | None,
) -> bool:
    """Return whether a triple matches optional display filters."""
    if predicate_filter and triple.get("predicate") != predicate_filter:
        return False
    if subject_filter:
        subject = triple.get("subject")
        if not isinstance(subject, str) or not subject.startswith(subject_filter):
            return False
    return True


def display_dico_resolutions(
    result,
    predicate_filter: str | None = None,
    subject_filter: str | None = None,
    max_triples: int = 10,
) -> None:
    """Display local DICO entries referenced by Heritage morphology URLs."""
    if any(claim.tool == "claim.dico.entries" for claim in result.claims):
        return
    refs = dico_handlers.extract_dico_refs_from_claims(result.claims)
    entries = dico_handlers.lookup_dico_entries(refs)
    if not entries:
        return
    for entry in entries:
        subject = f"lex:{entry.get('headword_norm') or entry.get('entry_id')}"
        triples = [
            triple
            for triple in dico_handlers.dico_entry_triples(entry)
            if triple_matches_filters(triple, predicate_filter, subject_filter)
        ]
        if not triples:
            continue
        click.echo(f"TOOL=local.dico.entry PRED=has_sense SUBJECT={subject}")
        for triple in triples[:max_triples]:
            click.echo(f"  triple {triple}")


def _jsonable_mapping(value: object) -> dict[str, object]:
    """Convert dataclass or mapping values into plain JSON-friendly dicts."""
    if is_dataclass(value) and not isinstance(value, type):
        return dict(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _provenance_to_json(provenance: object) -> list[dict[str, object]]:
    if not isinstance(provenance, Sequence) or isinstance(provenance, str):
        return []
    return [_jsonable_mapping(item) for item in provenance]


def _claim_triples(claim: object) -> list[dict[str, object]]:
    value = getattr(claim, "value", None)
    if not isinstance(value, Mapping):
        return []
    triples = value.get("triples")
    if not isinstance(triples, list):
        return []
    return [dict(triple) for triple in triples if isinstance(triple, Mapping)]


def _claim_summary(
    claim: object,
    *,
    triple_count: int,
    matching_triple_count: int,
    emitted_triple_count: int,
) -> dict[str, object]:
    return {
        "claim_id": getattr(claim, "claim_id", None),
        "tool": getattr(claim, "tool", None),
        "call_id": getattr(claim, "call_id", None),
        "source_call_id": getattr(claim, "source_call_id", None),
        "derivation_id": getattr(claim, "derivation_id", None),
        "subject": getattr(claim, "subject", None),
        "predicate": getattr(claim, "predicate", None),
        "handler_version": getattr(claim, "handler_version", None),
        "triple_count": triple_count,
        "matching_triple_count": matching_triple_count,
        "emitted_triple_count": emitted_triple_count,
        "provenance_chain": _provenance_to_json(getattr(claim, "provenance_chain", None)),
    }


def _triple_row(triple: Mapping[str, object], *, claim: object) -> dict[str, object]:
    row = dict(triple)
    row.setdefault("claim_id", getattr(claim, "claim_id", None))
    row.setdefault("claim_tool", getattr(claim, "tool", None))
    return row


def _dico_resolution_rows(
    result: object,
    predicate_filter: str | None,
    subject_filter: str | None,
    max_triples: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return synthetic JSON rows for local DICO entries discovered through Heritage."""
    claims = getattr(result, "claims", [])
    if any(getattr(claim, "tool", None) == "claim.dico.entries" for claim in claims):
        return [], []

    refs = dico_handlers.extract_dico_refs_from_claims(claims)
    entries = dico_handlers.lookup_dico_entries(refs)
    claim_rows: list[dict[str, object]] = []
    triple_rows: list[dict[str, object]] = []
    safe_max = max(0, max_triples)

    for entry in entries:
        subject = f"lex:{entry.get('headword_norm') or entry.get('entry_id')}"
        synthetic_claim_id = f"dico-entry:{entry.get('entry_id') or subject}"
        triples = [
            triple
            for triple in dico_handlers.dico_entry_triples(entry)
            if triple_matches_filters(triple, predicate_filter, subject_filter)
        ]
        if not triples:
            continue

        claim_rows.append(
            {
                "claim_id": synthetic_claim_id,
                "tool": "local.dico.entry",
                "call_id": None,
                "source_call_id": None,
                "derivation_id": None,
                "subject": subject,
                "predicate": "has_sense",
                "handler_version": None,
                "triple_count": len(triples),
                "matching_triple_count": len(triples),
                "emitted_triple_count": min(len(triples), safe_max),
                "provenance_chain": [],
            }
        )
        for triple in triples[:safe_max]:
            row = dict(triple)
            row.setdefault("claim_id", synthetic_claim_id)
            row.setdefault("claim_tool", "local.dico.entry")
            triple_rows.append(row)

    return claim_rows, triple_rows


def build_triples_dump_payload(  # noqa: PLR0913
    *,
    language: str,
    text: str,
    normalized_candidates: list[str],
    tool_filter: str,
    predicate_filter: str | None,
    subject_filter: str | None,
    max_triples: int,
    result: object,
    include_dico_resolutions: bool = False,
) -> dict[str, object]:
    """Build structured JSON for `triples-dump --output json`."""
    safe_max = max(0, max_triples)
    claim_rows: list[dict[str, object]] = []
    triple_rows: list[dict[str, object]] = []

    for claim in getattr(result, "claims", []):
        triples = _claim_triples(claim)
        matching = [
            triple
            for triple in triples
            if triple_matches_filters(triple, predicate_filter, subject_filter)
        ]
        emitted = matching[:safe_max]
        claim_rows.append(
            _claim_summary(
                claim,
                triple_count=len(triples),
                matching_triple_count=len(matching),
                emitted_triple_count=len(emitted),
            )
        )
        triple_rows.extend(_triple_row(triple, claim=claim) for triple in emitted)

    if include_dico_resolutions:
        dico_claims, dico_triples = _dico_resolution_rows(
            result, predicate_filter, subject_filter, safe_max
        )
        claim_rows.extend(dico_claims)
        triple_rows.extend(dico_triples)

    return {
        "query": {
            "language": language,
            "text": text,
            "normalized_candidates": normalized_candidates,
        },
        "tool_filter": tool_filter,
        "filters": {
            "predicate": predicate_filter,
            "subject_prefix": subject_filter,
            "max_triples": max_triples,
        },
        "claims": claim_rows,
        "triples": triple_rows,
        "warnings": [],
    }


def display_claim_triples(
    result,
    predicate_filter: str | None = None,
    subject_filter: str | None = None,
    max_triples: int = 10,
) -> None:
    """Display claim triples to stdout."""
    for claim in result.claims:
        val = claim.value if isinstance(claim.value, dict) else {}
        triples = val.get("triples") if isinstance(val, dict) else None
        if triples:
            filtered_triples = [
                t
                for t in triples
                if isinstance(t, dict)
                and triple_matches_filters(t, predicate_filter, subject_filter)
            ]
            if not filtered_triples:
                continue
            click.echo(f"TOOL={claim.tool} PRED={claim.predicate} SUBJECT={claim.subject}")
            sense_counts: dict[str, int] = {}
            for triple in filtered_triples:
                if triple.get("predicate") == "has_sense":
                    subj = triple.get("subject")
                    if isinstance(subj, str):
                        sense_counts[subj] = sense_counts.get(subj, 0) + 1
            if sense_counts:
                click.echo(f"  sense_counts {sense_counts}")
            for triple in filtered_triples[:max_triples]:
                click.echo(f"  triple {triple}")
        elif not predicate_filter and not subject_filter:
            click.echo(f"TOOL={claim.tool} PRED={claim.predicate} SUBJECT={claim.subject}")
