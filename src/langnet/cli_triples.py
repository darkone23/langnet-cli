from __future__ import annotations

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
