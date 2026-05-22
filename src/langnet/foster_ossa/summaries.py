from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from langnet.foster_ossa.models import FosterOssaSummaryPlan

PROMPT_VERSION = "foster-ossa-summary-v1"
TOC_SUMMARY_PROMPT_VERSION = "foster-ossa-toc-summary-v2"
EXPERIENCE_SUMMARY_PROMPT_VERSION = "foster-ossa-experience-summary-v2"
SECOND_EXPERIENCE = 2
TOC_SUMMARY_REQUIRED_KEYS = (
    "source_ref",
    "encounter_id",
    "title",
    "page_span",
    "foster_terms",
    "traditional_terms",
    "method_claims",
    "learner_actions",
    "examples_present",
    "not_supported_or_unclear",
    "source_refs",
)
EXPERIENCE_SUMMARY_REQUIRED_KEYS = (
    "source_ref",
    "experience",
    "toc_entry_count",
    "method_throughline",
    "core_foster_terms",
    "traditional_bridge_terms",
    "learner_sequence",
    "platform_taxonomy_implications",
    "source_refs",
    "not_supported_or_unclear",
)

SYSTEM_PROMPT = (
    "You summarize Reginald Foster's Ossa Latinitatis Sola for classical-language "
    "learners.\n"
    "Use only the supplied excerpt. Do not invent facts, examples, page claims, or "
    "grammar explanations not supported by the excerpt.\n"
    "Prefer concise, source-backed English. If the excerpt is too fragmentary to "
    "summarize, say so explicitly in the requested output schema.\n"
    "When the user requests JSON, return only one valid JSON object."
)

STRUCTURED_JSON_RULES = (
    "Return raw JSON only. Do not wrap the JSON in markdown fences. Do not include "
    "introductory or trailing prose. Use double quotes for every JSON key and "
    "string. Do not use typographic quote characters as JSON delimiters. Use arrays "
    "of strings for list fields, including examples_present and "
    "not_supported_or_unclear. source_ref must exactly equal Source. source_refs "
    "must include at least one page:* reference copied from Source pages."
)
ARRAY_KEYS_BY_SCOPE = {
    "toc-entry": (
        "foster_terms",
        "traditional_terms",
        "method_claims",
        "learner_actions",
        "examples_present",
        "not_supported_or_unclear",
        "source_refs",
    ),
    "experience": (
        "method_throughline",
        "core_foster_terms",
        "traditional_bridge_terms",
        "learner_sequence",
        "platform_taxonomy_implications",
        "source_refs",
        "not_supported_or_unclear",
    ),
}
STRING_KEYS_BY_SCOPE = {
    "toc-entry": ("source_ref", "encounter_id", "title", "page_span"),
    "experience": ("source_ref",),
}


def plan_summary_chunks(
    rows: Iterable[Mapping[str, Any]],
    *,
    scope: str,
    model: str,
) -> list[FosterOssaSummaryPlan]:
    if scope not in {"page", "toc-entry", "experience"}:
        raise ValueError(f"Unsupported Foster Ossa summary scope: {scope}")
    plans: list[FosterOssaSummaryPlan] = []
    for row in rows:
        if scope == "toc-entry":
            source_ref = str(row["source_ref"])
            prompt_version = TOC_SUMMARY_PROMPT_VERSION
            input_text = _toc_entry_input_text(row)
        elif scope == "experience":
            source_ref = str(row["source_ref"])
            prompt_version = EXPERIENCE_SUMMARY_PROMPT_VERSION
            input_text = _experience_input_text(row)
        else:
            page_number = int(row["page_number"])
            section = str(row.get("section") or "unknown")
            text = str(row.get("text") or "").strip()
            source_ref = f"page:{page_number}"
            prompt_version = PROMPT_VERSION
            input_text = f"Foster Ossa page {page_number} [{section}]\n\n{text}"
        plans.append(
            FosterOssaSummaryPlan(
                source_ref=source_ref,
                scope=scope,
                model=model,
                prompt_version=prompt_version,
                input_hash=sha256(input_text.encode("utf-8")).hexdigest(),
                input_text=input_text,
            )
        )
    return plans


def experience_rows_from_toc_summary_jsonl(
    path: Path,
    *,
    experience: int | None = None,
) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for line in path.expanduser().read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("scope") != "toc-entry":
            continue
        if row.get("validation_status") != "generated_valid":
            continue
        summary_json = row.get("generated_json") or generated_summary_json(
            scope="toc-entry",
            generated_text=str(row.get("generated_text") or ""),
        )
        summary = json.loads(summary_json)
        encounter_id = str(summary.get("encounter_id") or row.get("source_ref", "")).split(":")[-1]
        if "." not in encounter_id:
            continue
        summary_experience = int(encounter_id.split(".", maxsplit=1)[0])
        if experience is not None and summary_experience != experience:
            continue
        groups.setdefault(summary_experience, []).append(summary)
    rows: list[dict[str, Any]] = []
    for summary_experience, summaries in sorted(groups.items()):
        summaries.sort(key=lambda item: _encounter_sort_key(str(item.get("encounter_id") or "")))
        source_refs = [str(item["source_ref"]) for item in summaries]
        text = json.dumps(summaries, ensure_ascii=False, sort_keys=True)
        rows.append(
            {
                "source_ref": f"experience:{summary_experience}",
                "experience": summary_experience,
                "toc_entry_count": len(summaries),
                "source_refs": source_refs,
                "text": text,
                "text_hash": sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    return rows


def write_summary_markdown_docs(*, input_path: Path, output_dir: Path) -> list[Path]:
    summaries = _valid_toc_summaries_from_jsonl(input_path)
    grouped: dict[int, list[dict[str, Any]]] = {}
    for summary in summaries:
        encounter_id = str(summary["encounter_id"])
        experience = int(encounter_id.split(".", maxsplit=1)[0])
        grouped.setdefault(experience, []).append(summary)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index_path = output_dir / "README.md"
    index_path.write_text(_summary_docs_index(grouped), encoding="utf-8")
    written.append(index_path)
    for experience, rows in sorted(grouped.items()):
        rows.sort(key=lambda item: _encounter_sort_key(str(item["encounter_id"])))
        path = output_dir / f"experience-{experience}.md"
        body = [f"# Foster Ossa Experience {experience}", ""]
        body.append(
            "Generated from validated TOC-entry summary JSON. Treat this as a "
            "secondary study aid; source page references remain authoritative."
        )
        body.append("")
        body.extend(render_toc_summary_markdown(row) for row in rows)
        path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
        written.append(path)
    return written


def render_toc_summary_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        f"## {summary['source_ref']} - {summary.get('title') or summary.get('encounter_id')}",
        "",
        f"Source refs: {_markdown_refs(summary.get('source_refs', []))}",
        "",
        "### Method Claims",
        *_markdown_list(summary.get("method_claims", [])),
        "",
        "### Learner Actions",
        *_markdown_list(summary.get("learner_actions", [])),
    ]
    unclear = summary.get("not_supported_or_unclear") or []
    if unclear:
        lines.extend(["", "### Unclear Or Unsupported", *_markdown_list(unclear)])
    return "\n".join(lines).rstrip() + "\n"


def summarize_plan(plan: FosterOssaSummaryPlan) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to generate Foster Ossa summaries")
    base_url = (
        os.environ.get("OPENAI_API_BASE")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://openrouter.ai/api/v1"
    )
    os.environ["OPENAI_BASE_URL"] = base_url

    import aisuite as ai  # noqa: PLC0415

    client = ai.Client({"api_key": api_key})
    response = client.chat.completions.create(
        model=plan.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Prompt version: {plan.prompt_version}\n"
                    f"Source: {plan.source_ref}\n"
                    f"Scope: {plan.scope}\n\n"
                    f"{plan.input_text}"
                ),
            },
        ],
        **completion_options_for_summary(plan),
    )
    return _response_text(response).strip()


def completion_options_for_summary(plan: FosterOssaSummaryPlan) -> dict[str, object]:
    options: dict[str, object] = {"temperature": 0}
    if plan.scope in {"toc-entry", "experience"}:
        options["response_format"] = {"type": "json_object"}
    return options


def validate_generated_summary(
    *,
    scope: str,
    generated_text: str,
    expected_source_ref: str | None = None,
) -> list[str]:
    if scope not in {"toc-entry", "experience"}:
        return []
    text = generated_text.strip()
    if text.startswith("```"):
        text = _strip_json_fence(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc.msg}"]
    if not isinstance(payload, dict):
        return ["summary JSON must be an object"]
    required_keys = (
        TOC_SUMMARY_REQUIRED_KEYS if scope == "toc-entry" else EXPERIENCE_SUMMARY_REQUIRED_KEYS
    )
    issues = [f"missing required key: {key}" for key in required_keys if key not in payload]
    if expected_source_ref is not None and payload.get("source_ref") != expected_source_ref:
        issues.append(f"source_ref must equal {expected_source_ref}")
    issues.extend(_field_type_issues(scope, payload))
    issues.extend(_source_ref_issues(payload))
    return issues


def generated_summary_json(*, scope: str, generated_text: str) -> str:
    if scope not in {"toc-entry", "experience"}:
        return ""
    text = generated_text.strip()
    if text.startswith("```"):
        text = _strip_json_fence(text)
    payload = json.loads(text)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _field_type_issues(scope: str, payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in STRING_KEYS_BY_SCOPE[scope]:
        if key in payload and not isinstance(payload[key], str):
            issues.append(f"{key} must be a string")
    for key in ARRAY_KEYS_BY_SCOPE[scope]:
        if key in payload and not isinstance(payload[key], list):
            issues.append(f"{key} must be an array")
    return issues


def _source_ref_issues(payload: Mapping[str, Any]) -> list[str]:
    source_refs = payload.get("source_refs")
    if isinstance(source_refs, list) and not any(
        str(ref).startswith("page:") for ref in source_refs
    ):
        return ["source_refs must include at least one page:* reference"]
    return []


def _response_text(response: Any) -> str:
    choices = _get_value(response, "choices")
    if not choices:
        return ""
    first = choices[0]
    message = _get_value(first, "message")
    content = _get_value(message, "content") if message is not None else None
    return str(content or "")


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _strip_json_fence(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _toc_entry_input_text(row: Mapping[str, Any]) -> str:
    text = str(row.get("text") or "").strip()
    return (
        "Summarize this Foster Ossa table-of-contents encounter as structured JSON.\n"
        "Use only the supplied excerpt. Keep direct quotations short and rare.\n"
        f"{STRUCTURED_JSON_RULES}\n"
        "Expected JSON keys: source_ref, encounter_id, title, page_span, "
        "foster_terms, traditional_terms, method_claims, learner_actions, "
        "examples_present, not_supported_or_unclear, source_refs.\n\n"
        "Field contract: title is a single string; page_span is a string; "
        "foster_terms, traditional_terms, method_claims, learner_actions, "
        "examples_present, not_supported_or_unclear, and source_refs are arrays "
        "of strings.\n\n"
        f"Source: {row['source_ref']}\n"
        f"Encounter: {row.get('encounter_id') or ''}\n"
        f"Latin title: {row.get('latin_title') or ''}\n"
        f"English title: {row.get('english_title') or ''}\n"
        f"Page span: {row.get('page_start')}--{row.get('page_end')}\n"
        f"Source pages: {_source_pages_ref(row)}\n\n"
        f"{text}"
    )


def _experience_input_text(row: Mapping[str, Any]) -> str:
    return (
        "Summarize these validated Foster Ossa TOC-entry summaries into one "
        "experience-level structured study summary.\n"
        "Use only the supplied TOC-entry summary JSON. Preserve uncertainty and "
        "source references. Do not add grammar claims that are absent from the "
        "input summaries.\n"
        f"{STRUCTURED_JSON_RULES}\n"
        "Expected JSON keys: source_ref, experience, toc_entry_count, "
        "method_throughline, core_foster_terms, traditional_bridge_terms, "
        "learner_sequence, platform_taxonomy_implications, source_refs, "
        "not_supported_or_unclear.\n\n"
        "Field contract: source_ref is a string; experience and toc_entry_count "
        "are numbers; method_throughline, core_foster_terms, "
        "traditional_bridge_terms, learner_sequence, "
        "platform_taxonomy_implications, source_refs, and "
        "not_supported_or_unclear are arrays of strings.\n\n"
        f"Source: {row['source_ref']}\n"
        f"Experience: {row.get('experience')}\n"
        f"TOC summaries included: {row.get('toc_entry_count')}\n"
        f"TOC source refs: {', '.join(str(ref) for ref in row.get('source_refs', []))}\n\n"
        f"{row.get('text') or ''}"
    )


def _encounter_sort_key(encounter_id: str) -> tuple[int, int]:
    experience, encounter = encounter_id.split(".", maxsplit=1)
    return int(experience), int(encounter)


def _valid_toc_summaries_from_jsonl(path: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for line in path.expanduser().read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("scope") != "toc-entry" or row.get("validation_status") != "generated_valid":
            continue
        summary_json = row.get("generated_json") or generated_summary_json(
            scope="toc-entry",
            generated_text=str(row.get("generated_text") or ""),
        )
        summaries.append(json.loads(summary_json))
    return summaries


def _summary_docs_index(grouped: Mapping[int, list[dict[str, Any]]]) -> str:
    lines = [
        "# Foster Ossa Generated Summary Documents",
        "",
        "These documents are generated from validated TOC-entry summary JSON. "
        "They are review aids, not replacement source text.",
        "",
    ]
    if SECOND_EXPERIENCE not in grouped:
        lines.extend(
            [
                "Experience 2 is present in the source extraction, but it is not "
                "represented here because the TOC-entry summary scope follows "
                "numbered systematic grammar encounters. The Second Experience "
                "is the spoken/application experience with reading sheets rather "
                "than a numbered grammar-encounter sequence.",
                "",
            ]
        )
    for experience, rows in sorted(grouped.items()):
        lines.append(
            f"- [Experience {experience}](experience-{experience}.md): {len(rows)} entries"
        )
    return "\n".join(lines).rstrip() + "\n"


def _markdown_refs(refs: object) -> str:
    if not isinstance(refs, list):
        return ""
    return ", ".join(f"`{ref}`" for ref in refs)


def _markdown_list(items: object) -> list[str]:
    if not isinstance(items, list) or not items:
        return ["- None recorded."]
    return [f"- {item}" for item in items]


def _source_pages_ref(row: Mapping[str, Any]) -> str:
    pages = row.get("pages")
    if isinstance(pages, list) and pages:
        refs = [f"page:{item['page_number']}" for item in pages if isinstance(item, Mapping)]
        if refs:
            return ", ".join(refs)
    return f"page:{row.get('page_start')}-page:{row.get('page_end')}"
