from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import dotenv

from langnet.reader.metadata_overlay import load_metadata_overlays
from langnet.reader.models import ReaderMetadataOverlay

_RECOMMENDATIONS = {"accept", "reject", "needs_review"}
_CONFIDENCE = {"high", "medium", "low"}
_AMBIGUITY_MARKERS = ("ambiguous", "composite", "traditional", "needs source", "needs review")


@dataclass(frozen=True)
class ReaderMetadataOverlayDecision:
    recommendation: str
    confidence: str
    rationale: str
    flags: tuple[str, ...] = ()
    reviewer: str = "rule"
    model: str | None = None


@dataclass(frozen=True)
class ReaderMetadataOverlayReview:
    overlay: ReaderMetadataOverlay
    decision: ReaderMetadataOverlayDecision
    approved: bool
    applied: bool


OverlayReviewer = Callable[[ReaderMetadataOverlay], ReaderMetadataOverlayDecision]
OverlayApprover = Callable[[ReaderMetadataOverlayReview], bool]


def rule_overlay_reviewer(overlay: ReaderMetadataOverlay) -> ReaderMetadataOverlayDecision:
    note = overlay.note.casefold()
    evidence_types = {item.source_type for item in overlay.evidence}
    has_local = "local_source" in evidence_types
    has_external = bool(evidence_types - {"local_source"})
    if any(marker in note for marker in _AMBIGUITY_MARKERS):
        recommendation = "needs_review"
        confidence = "medium" if has_local and has_external else "low"
        rationale = "The candidate has evidence, but its note flags ambiguity or review needs."
        flags = ("ambiguous_or_review_needed",)
    elif has_local and has_external:
        recommendation = "accept"
        confidence = "high"
        rationale = "The candidate has both local-source and external evidence."
        flags = ("local_source", "external_evidence")
    elif has_external:
        recommendation = "needs_review"
        confidence = "medium"
        rationale = "The candidate has external evidence but no local source confirmation."
        flags = ("external_evidence_only",)
    else:
        recommendation = "needs_review"
        confidence = "low"
        rationale = "The candidate does not yet have enough evidence for automatic acceptance."
        flags = ("weak_evidence",)
    return ReaderMetadataOverlayDecision(
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        flags=flags,
        reviewer="rule",
        model="local-rule",
    )


def llm_overlay_reviewer(
    overlay: ReaderMetadataOverlay,
    *,
    model: str,
) -> ReaderMetadataOverlayDecision:
    dotenv.load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise click.ClickException("Set OPENAI_API_KEY before using --reviewer llm.")
    api_base = os.getenv(
        "OPENAI_API_BASE",
        os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    os.environ["OPENAI_BASE_URL"] = api_base
    try:
        import aisuite as ai  # noqa: PLC0415
    except ImportError as exc:
        raise click.ClickException("aisuite is required for LLM overlay review.") from exc

    client = ai.Client({"api_key": api_key})
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You review classical-text metadata overlay candidates. "
                    "Return strict JSON only with keys recommendation, confidence, "
                    "rationale, and flags. recommendation must be one of accept, "
                    "reject, needs_review. confidence must be high, medium, or low. "
                    "Prefer needs_review when authorship is traditional, composite, "
                    "or the local source is not clearly identified."
                ),
            },
            {"role": "user", "content": _overlay_review_prompt(overlay)},
        ],
    )
    content = response.choices[0].message.content or ""
    return _decision_from_llm_json(content, model=model)


def review_metadata_overlay_candidates(  # noqa: PLR0913
    root: Path,
    *,
    reviewer: OverlayReviewer,
    collection_id: str | None = None,
    field: str | None = None,
    match_value: str | None = None,
    limit: int = 500,
    apply: bool = False,
    approve: OverlayApprover | None = None,
    retrieved_at: str | None = None,
) -> list[ReaderMetadataOverlayReview]:
    reviews: list[ReaderMetadataOverlayReview] = []
    for overlay in _candidate_overlays(
        root,
        collection_id=collection_id,
        field=field,
        match_value=match_value,
        limit=limit,
    ):
        decision = reviewer(overlay)
        pending_review = ReaderMetadataOverlayReview(
            overlay=overlay,
            decision=decision,
            approved=False,
            applied=False,
        )
        approved = bool(
            apply
            and decision.recommendation != "reject"
            and approve is not None
            and approve(pending_review)
        )
        applied = False
        if approved:
            _promote_overlay_in_file(
                overlay,
                decision,
                retrieved_at=retrieved_at or _today_utc(),
            )
            applied = True
        reviews.append(
            ReaderMetadataOverlayReview(
                overlay=overlay,
                decision=decision,
                approved=approved,
                applied=applied,
            )
        )
    return reviews


def review_to_payload(review: ReaderMetadataOverlayReview) -> dict[str, object]:
    overlay = review.overlay
    decision = review.decision
    return {
        "collection_id": overlay.collection_id,
        "match_field": overlay.match_field,
        "match_value": overlay.match_value,
        "field": overlay.field,
        "value": overlay.value,
        "source_file": overlay.source_file,
        "current_status": overlay.status,
        "current_confidence": overlay.confidence,
        "recommendation": decision.recommendation,
        "review_confidence": decision.confidence,
        "reviewer": decision.reviewer,
        "model": decision.model,
        "rationale": decision.rationale,
        "flags": list(decision.flags),
        "approved": review.approved,
        "applied": review.applied,
    }


def _candidate_overlays(
    root: Path,
    *,
    collection_id: str | None,
    field: str | None,
    match_value: str | None,
    limit: int,
) -> list[ReaderMetadataOverlay]:
    overlays = [
        overlay
        for overlay in load_metadata_overlays(root)
        if overlay.status == "candidate"
        and (collection_id is None or overlay.collection_id == collection_id)
        and (field is None or overlay.field == field)
        and (match_value is None or overlay.match_value == match_value)
    ]
    return overlays[:limit]


def _promote_overlay_in_file(
    overlay: ReaderMetadataOverlay,
    decision: ReaderMetadataOverlayDecision,
    *,
    retrieved_at: str,
) -> None:
    path = Path(overlay.source_file)
    lines = path.read_text(encoding="utf-8").splitlines()
    start, end = _find_overlay_block(lines, overlay)
    block = lines[start:end]
    updated = _rewrite_overlay_block(block, decision, retrieved_at=retrieved_at)
    path.write_text("\n".join([*lines[:start], *updated, *lines[end:]]) + "\n", encoding="utf-8")


def _find_overlay_block(lines: list[str], overlay: ReaderMetadataOverlay) -> tuple[int, int]:
    starts = [
        index
        for index, line in enumerate(lines)
        if line.startswith("  - collection_id: ")
        and _quoted_value(line.removeprefix("  - collection_id: ")) == overlay.collection_id
    ]
    for start in starts:
        end = next(
            (
                index
                for index in range(start + 1, len(lines))
                if lines[index].startswith("  - collection_id: ")
            ),
            len(lines),
        )
        block = lines[start:end]
        if _block_matches_overlay(block, overlay):
            return start, end
    msg = f"{overlay.source_file}: could not find overlay record for {overlay.match_value}"
    raise ValueError(msg)


def _block_matches_overlay(block: list[str], overlay: ReaderMetadataOverlay) -> bool:
    expected = {
        "collection_id": overlay.collection_id,
        "match_field": overlay.match_field,
        "match_value": overlay.match_value,
        "field": overlay.field,
        "value": overlay.value,
    }
    found: dict[str, str] = {}
    for line in block:
        if line.startswith("  - collection_id: "):
            found["collection_id"] = _quoted_value(line.removeprefix("  - collection_id: "))
            continue
        if line.startswith("    ") and ": " in line:
            key, value = line.removeprefix("    ").split(": ", 1)
            if key in expected:
                found[key] = _quoted_value(value)
    return found == expected


def _rewrite_overlay_block(
    block: list[str],
    decision: ReaderMetadataOverlayDecision,
    *,
    retrieved_at: str,
) -> list[str]:
    updated: list[str] = []
    inserted_evidence = False
    for line in block:
        if line.startswith("    status: "):
            updated.append('    status: "accepted"')
            continue
        if line.startswith("    confidence: "):
            updated.append(f"    confidence: {_yaml_string(decision.confidence)}")
            continue
        if line.startswith("    note: "):
            label = "LLM review" if decision.reviewer == "llm" else "Metadata review"
            updated.append("    note: " + _yaml_string(f"{label} accepted: {decision.rationale}"))
            continue
        updated.append(line)
        if line == "    evidence:":
            inserted_evidence = True
    if not inserted_evidence:
        updated.append("    evidence:")
    updated.extend(_review_evidence_lines(decision, retrieved_at=retrieved_at))
    return updated


def _review_evidence_lines(
    decision: ReaderMetadataOverlayDecision,
    *,
    retrieved_at: str,
) -> list[str]:
    source_type = f"{decision.reviewer}_review"
    citation = decision.model or decision.reviewer
    flag_text = ", ".join(decision.flags) if decision.flags else "none"
    label = (
        f"Recommendation {decision.recommendation} with {decision.confidence} confidence. "
        f"Flags: {flag_text}. Rationale: {decision.rationale}"
    )
    return [
        f"      - source_type: {_yaml_string(source_type)}",
        f"        citation: {_yaml_string(citation)}",
        f"        label: {_yaml_string(label)}",
        f"        retrieved_at: {_yaml_string(retrieved_at)}",
    ]


def _overlay_review_prompt(overlay: ReaderMetadataOverlay) -> str:
    payload = {
        "candidate": {
            "collection_id": overlay.collection_id,
            "match_field": overlay.match_field,
            "match_value": overlay.match_value,
            "field": overlay.field,
            "value": overlay.value,
            "note": overlay.note,
            "confidence": overlay.confidence,
            "evidence": [
                {
                    "source_type": item.source_type,
                    "citation": item.citation,
                    "label": item.label,
                    "retrieved_at": item.retrieved_at,
                }
                for item in overlay.evidence
            ],
        }
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _decision_from_llm_json(content: str, *, model: str) -> ReaderMetadataOverlayDecision:
    payload = _parse_json_object(content)
    recommendation = str(payload.get("recommendation") or "needs_review")
    confidence = str(payload.get("confidence") or "low")
    if recommendation not in _RECOMMENDATIONS:
        recommendation = "needs_review"
    if confidence not in _CONFIDENCE:
        confidence = "low"
    raw_flags = payload.get("flags") or []
    flags = tuple(str(item) for item in raw_flags) if isinstance(raw_flags, list) else ()
    rationale = str(payload.get("rationale") or "LLM response did not include a rationale.")
    return ReaderMetadataOverlayDecision(
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        flags=flags,
        reviewer="llm",
        model=model,
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end < start:
            return {}
        try:
            payload = json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def _quoted_value(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return ""
    return parsed if isinstance(parsed, str) else ""


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _today_utc() -> str:
    return datetime.now(UTC).date().isoformat()
