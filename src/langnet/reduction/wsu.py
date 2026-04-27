from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from langnet.execution import predicates
from langnet.reduction.models import WitnessSenseUnit


def normalize_gloss(gloss: str) -> str:
    """Conservative gloss normalization for deterministic fixture extraction."""
    return re.sub(r"\s+", " ", gloss.strip().lower())


def _stable_wsu_id(
    lexeme_anchor: str,
    sense_anchor: str,
    normalized_gloss: str,
    claim_id: str,
) -> str:
    material = "\x1f".join([lexeme_anchor, sense_anchor, normalized_gloss, claim_id])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"wsu:{digest}"


def _claim_triples(claim: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = claim.get("value")
    if not isinstance(value, Mapping):
        return []
    triples = value.get("triples")
    if not isinstance(triples, Sequence) or isinstance(triples, (str, bytes)):
        return []
    return [cast(Mapping[str, Any], triple) for triple in triples if isinstance(triple, Mapping)]


def _evidence_from(triple: Mapping[str, Any]) -> dict[str, Any]:
    metadata = triple.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    evidence = metadata.get("evidence")
    payload = dict(evidence) if isinstance(evidence, Mapping) else {}
    for key in (
        "source_lang",
        "source_ref",
        "translation_id",
        "display_iast",
        "display_slp1",
        "display_gloss",
        "source_entry",
        "source_segments",
        "source_notes",
        "parsed_glosses",
        "translated_segments",
        "source_encoding",
    ):
        value = metadata.get(key)
        if value and key not in payload:
            payload[key] = value
    return payload


def extract_witness_sense_units(claims: Sequence[Mapping[str, Any]]) -> list[WitnessSenseUnit]:
    """Extract WSUs by pairing ``has_sense`` triples with matching ``gloss`` triples."""
    witnesses: list[WitnessSenseUnit] = []
    seen: set[tuple[str, str, str]] = set()

    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        triples = _claim_triples(claim)
        sense_links: dict[str, tuple[str, dict[str, Any]]] = {}

        for triple in triples:
            if triple.get("predicate") != predicates.HAS_SENSE:
                continue
            subject = triple.get("subject")
            obj = triple.get("object")
            if isinstance(subject, str) and isinstance(obj, str):
                sense_links[obj] = (subject, _evidence_from(triple))

        for triple in triples:
            if triple.get("predicate") != predicates.GLOSS:
                continue
            sense_anchor = triple.get("subject")
            gloss = triple.get("object")
            if not isinstance(sense_anchor, str) or not isinstance(gloss, str):
                continue
            link = sense_links.get(sense_anchor)
            if link is None:
                continue
            lexeme_anchor, link_evidence = link
            normalized_gloss = normalize_gloss(gloss)
            dedupe_key = (sense_anchor, normalized_gloss, claim_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            evidence = _evidence_from(triple) or link_evidence
            source_tool = str(evidence.get("source_tool") or claim.get("tool") or "")
            witnesses.append(
                WitnessSenseUnit(
                    wsu_id=_stable_wsu_id(
                        lexeme_anchor,
                        sense_anchor,
                        normalized_gloss,
                        claim_id,
                    ),
                    lexeme_anchor=lexeme_anchor,
                    sense_anchor=sense_anchor,
                    gloss=gloss,
                    normalized_gloss=normalized_gloss,
                    source_tool=source_tool,
                    claim_id=claim_id,
                    source_triple_subject=lexeme_anchor,
                    evidence=evidence,
                )
            )

    return witnesses
