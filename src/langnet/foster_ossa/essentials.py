from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

FOSTER_ESSENTIALS_SCHEMA_VERSION = "langnet.foster_ossa_essentials.v1"
MIN_AGGREGATE_CONCEPT_LINKS = 2


@dataclass(frozen=True, slots=True)
class FosterEssential:
    id: str
    label: str
    status: str
    foster_terms: tuple[str, ...]
    concept_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    summary_refs: tuple[str, ...]
    learner_action: str
    product_use: str
    morphology_predicates: tuple[str, ...]
    reader_example_queries: tuple[str, ...]
    caveats: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def default_foster_essentials() -> list[FosterEssential]:
    return [
        FosterEssential(
            id="of-possession",
            label="of-possession",
            status="codified",
            foster_terms=(
                "function of-possession",
                "of-possession",
                "form-of-possession",
                "genitive form of-possession",
            ),
            concept_ids=("case.genitive",),
            source_refs=("page:69", "page:125", "page:140", "page:522", "page:618"),
            summary_refs=("toc:1.6", "toc:1.22", "toc:1.25", "toc:4.30"),
            learner_action=(
                "Ask what relation, possession, belonging, source, or description "
                "the form marks."
            ),
            product_use="Show a possession/relation gateway beside genitive evidence.",
            morphology_predicates=("case=genitive",),
            reader_example_queries=("genitive possession", "of-possession", "case.genitive"),
        ),
        FosterEssential(
            id="to-for-from",
            label="to-for-from",
            status="codified",
            foster_terms=("function to-for-from", "form to-for-from", "to-for-from function"),
            concept_ids=("case.dative",),
            source_refs=("page:69", "page:133", "page:179", "page:505"),
            summary_refs=("toc:1.6", "toc:1.33", "toc:4.21", "toc:4.27"),
            learner_action="Ask who receives, benefits, is approached, or is the reference point.",
            product_use="Show a recipient/benefit/reference gateway beside dative evidence.",
            morphology_predicates=("case=dative",),
            reader_example_queries=("dative recipient", "to-for-from", "case.dative"),
        ),
        FosterEssential(
            id="object-form",
            label="object form",
            status="codified",
            foster_terms=("object form", "object forms"),
            concept_ids=("case.accusative",),
            source_refs=("page:56", "page:69", "page:86", "page:448", "page:522"),
            summary_refs=("toc:1.2", "toc:1.6", "toc:1.11", "toc:4.3"),
            learner_action=(
                "Ask what receives the action or functions as the object or motion goal."
            ),
            product_use="Show the receiving/object function beside accusative evidence.",
            morphology_predicates=("case=accusative",),
            reader_example_queries=("accusative object", "object form", "case.accusative"),
        ),
        FosterEssential(
            id="function-of-address",
            label="function of address",
            status="codified",
            foster_terms=("function of address", "direct address"),
            concept_ids=("case.vocative",),
            source_refs=("page:69", "page:311"),
            summary_refs=("toc:1.6", "toc:3.11"),
            learner_action=(
                "Ask whether the word names the person or thing being directly addressed."
            ),
            product_use="Show direct address separately from subject/object roles.",
            morphology_predicates=("case=vocative",),
            reader_example_queries=(
                "vocative direct address",
                "function of address",
                "case.vocative",
            ),
        ),
        FosterEssential(
            id="location-function",
            label="location function",
            status="codified",
            foster_terms=("location function", "place where"),
            concept_ids=("case.locative",),
            source_refs=("page:69", "page:301", "page:311"),
            summary_refs=("toc:1.6", "toc:3.1", "toc:3.11"),
            learner_action="Ask where, when, or in what setting the form locates the expression.",
            product_use="Show location/setting function where the platform has locative evidence.",
            morphology_predicates=("case=locative",),
            reader_example_queries=("locative place", "location function", "case.locative"),
        ),
        FosterEssential(
            id="subject-form",
            label="subject form",
            status="codified",
            foster_terms=("subject form", "subject forms"),
            concept_ids=("case.nominative",),
            source_refs=("page:56", "page:86", "page:149"),
            summary_refs=("toc:1.2", "toc:1.11", "toc:1.27"),
            learner_action="Ask what names the subject or topic whose function is being asserted.",
            product_use="Show naming/subject function where the platform has nominative evidence.",
            morphology_predicates=("case=nominative",),
            reader_example_queries=("nominative subject", "subject form", "case.nominative"),
            caveats=("Bare 'subject' remains reviewable; only 'subject form' is codified here.",),
        ),
        FosterEssential(
            id="by-with-from-in",
            label="by-with-from-in",
            status="aggregate_candidate",
            foster_terms=(
                "function by-with-from-in",
                "form by-with-from-in",
                "by-with-from-in function",
            ),
            concept_ids=("case.ablative", "case.instrumental", "case.locative"),
            source_refs=("page:69", "page:103", "page:108", "page:149", "page:611"),
            summary_refs=("toc:1.6", "toc:1.27", "toc:1.28", "toc:4.26", "toc:4.27"),
            learner_action=(
                "Ask whether the expression marks source, means, accompaniment, "
                "cause, place, or setting."
            ),
            product_use=(
                "Keep as a Foster aggregate candidate that can fan out into "
                "ablative, instrumental, and locative evidence."
            ),
            morphology_predicates=("case=ablative", "case=instrumental", "case=locative"),
            reader_example_queries=(
                "ablative means",
                "instrumental means",
                "locative place",
                "by-with-from-in",
            ),
            caveats=(
                "Do not collapse this bundle into only case.ablative",
                "Needs a product aggregate concept before it becomes a stable learner-facing node.",
            ),
        ),
    ]


def foster_essentials_payload(
    essentials: list[FosterEssential] | None = None,
) -> dict[str, object]:
    rows = essentials or default_foster_essentials()
    return {
        "schema_version": FOSTER_ESSENTIALS_SCHEMA_VERSION,
        "validation": validate_foster_essentials(rows),
        "essentials": [row.as_dict() for row in rows],
    }


def get_foster_essential(term: str) -> FosterEssential | None:
    key = _normalize(term)
    for essential in default_foster_essentials():
        aliases = (essential.id, essential.label, *essential.foster_terms)
        if key in {_normalize(alias) for alias in aliases}:
            return essential
    return None


def validate_foster_essentials(essentials: list[FosterEssential]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    ids = [essential.id for essential in essentials]
    for duplicate in sorted(_duplicates(ids)):
        issues.append(
            {
                "code": "duplicate_id",
                "message": f"Duplicate Foster essential id: {duplicate}",
            }
        )
    for essential in essentials:
        if essential.status not in {"codified", "aggregate_candidate", "needs_review"}:
            issues.append(
                {
                    "code": "invalid_status",
                    "message": f"{essential.id} has unsupported status {essential.status!r}.",
                }
            )
        if not essential.source_refs or not all(
            ref.startswith("page:") for ref in essential.source_refs
        ):
            issues.append(
                {
                    "code": "missing_page_refs",
                    "message": f"{essential.id} must carry page:* source refs.",
                }
            )
        if not essential.summary_refs or not all(
            ref.startswith(("toc:", "experience:")) for ref in essential.summary_refs
        ):
            issues.append(
                {
                    "code": "missing_summary_refs",
                    "message": f"{essential.id} must carry toc:* or experience:* summary refs.",
                }
            )
        if essential.status == "codified" and not essential.concept_ids:
            issues.append(
                {
                    "code": "missing_concept_bridge",
                    "message": f"{essential.id} is codified but has no concept bridge.",
                }
            )
        if (
            essential.status == "aggregate_candidate"
            and len(essential.concept_ids) < MIN_AGGREGATE_CONCEPT_LINKS
        ):
            issues.append(
                {
                    "code": "weak_aggregate",
                    "message": (
                        f"{essential.id} is an aggregate candidate but has fewer "
                        f"than {MIN_AGGREGATE_CONCEPT_LINKS} concept links."
                    ),
                }
            )
    status_counts = Counter(essential.status for essential in essentials)
    return {
        "valid": not issues,
        "summary": {
            "total": len(essentials),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "issues": issues,
    }


def render_foster_essentials_markdown(
    essentials: list[FosterEssential] | None = None,
) -> str:
    rows = essentials or default_foster_essentials()
    validation = validate_foster_essentials(rows)
    lines = [
        "# Foster Essentials Pack",
        "",
        "This is a structured, source-backed starter pack for codifying Foster/Ossa "
        "method items in LangNet. It is not a complete curriculum.",
        "",
        "## Summary",
        "",
        f"- Schema: `{FOSTER_ESSENTIALS_SCHEMA_VERSION}`",
        f"- Valid: `{validation['valid']}`",
        f"- Total essentials: {validation['summary']['total']}",
    ]
    status_counts = validation["summary"]["status_counts"]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status.replace('_', ' ')}: {count}")
    lines.extend(["", "## Essentials", ""])
    for essential in rows:
        lines.extend(
            [
                f"### `{essential.id}`",
                "",
                f"- Label: `{essential.label}`",
                f"- Status: {essential.status.replace('_', ' ')}",
                f"- Concept bridge: {_markdown_refs(essential.concept_ids)}",
                f"- Foster terms: {_markdown_refs(essential.foster_terms)}",
                f"- Source refs: {_markdown_refs(essential.source_refs)}",
                f"- Summary refs: {_markdown_refs(essential.summary_refs)}",
                f"- Morphology predicates: {_markdown_refs(essential.morphology_predicates)}",
                f"- Learner action: {essential.learner_action}",
                f"- Product use: {essential.product_use}",
            ]
        )
        if essential.caveats:
            lines.append(f"- Caveats: {'; '.join(essential.caveats)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_foster_essentials_artifacts(
    *,
    json_output: Path,
    markdown_output: Path,
    essentials: list[FosterEssential] | None = None,
) -> list[Path]:
    rows = essentials or default_foster_essentials()
    json_output = json_output.expanduser()
    markdown_output = markdown_output.expanduser()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(foster_essentials_payload(rows), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_output.write_text(render_foster_essentials_markdown(rows), encoding="utf-8")
    return [json_output, markdown_output]


def _duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if count > 1}


def _normalize(term: str) -> str:
    return " ".join(term.casefold().replace("-", " ").split())


def _markdown_refs(refs: tuple[str, ...]) -> str:
    if not refs:
        return "`-`"
    return ", ".join(f"`{ref}`" for ref in refs)
