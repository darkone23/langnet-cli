#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb
import orjson

from langnet.encounter_briefing import build_encounter_briefing_flow
from langnet.word_index.service import word_index_neighborhood_payload

ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
DEFAULT_MOTD_POOL = ROOT / "data/build/motd_pool.duckdb"
DEFAULT_OUTPUT = ROOT / "examples/debug/motd-reader-flow-audit.json"
_GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
MAX_NOISY_REF_CHARS = 8


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit MOTD pool cards against word-index, encounter hits, and briefing."
    )
    parser.add_argument("--motd-pool", type=Path, default=DEFAULT_MOTD_POOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--language", choices=("all", "grc", "lat", "san"), default="all")
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Limit to one or more MOTD query values. May be repeated.",
    )
    parser.add_argument("--encounter-limit", type=int, default=0)
    parser.add_argument("--encounter-timeout", type=int, default=75)
    parser.add_argument("--radius", type=int, default=6)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    rows = _load_pool_rows(args.motd_pool, language=args.language, queries=tuple(args.query))
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        item = row["item"]
        language = str(item.get("language") or row["language"])
        query = str(item.get("query") or row["query"])
        if args.progress:
            print(f"[{index + 1}/{len(rows)}] {language}:{query}", flush=True)
        record = {
            "card_key": row["card_key"],
            "language": language,
            "query": query,
            "display": str(item.get("display") or query),
            "stored_summary": str(item.get("summary") or ""),
            "stored_short_gloss": str(_mapping(item.get("ui")).get("short_gloss") or ""),
            "source_basis": (
                item.get("source_basis") if isinstance(item.get("source_basis"), list) else []
            ),
            "issues": [],
        }
        _audit_stored_card(record)
        _audit_word_index(record, language=language, query=query, radius=args.radius)
        if args.encounter_limit > 0 and index < args.encounter_limit:
            _audit_encounter_and_brief(
                record,
                language=language,
                query=query,
                timeout=args.encounter_timeout,
            )
        records.append(record)

    summary = _summary(records, args)
    output = {"summary": summary, "records": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(orjson.dumps(output, option=orjson.OPT_INDENT_2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _load_pool_rows(
    db_path: Path,
    *,
    language: str,
    queries: Sequence[str],
) -> list[dict[str, Any]]:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        where_clauses: list[str] = []
        params: list[Any] = []
        if language != "all":
            where_clauses.append("language = ?")
            params.append(language)
        clean_queries = [query for query in queries if query.strip()]
        if clean_queries:
            where_clauses.append(f"query IN ({', '.join('?' for _ in clean_queries)})")
            params.extend(clean_queries)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        rows = conn.execute(
            f"""
            SELECT card_key, language, query, item_json
            FROM motd_pool_cards
            {where_sql}
            ORDER BY language, didactic_score DESC, query
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "card_key": str(card_key),
            "language": str(language),
            "query": str(query),
            "item": orjson.loads(str(item_json)),
        }
        for card_key, language, query, item_json in rows
    ]


def _audit_stored_card(record: dict[str, Any]) -> None:
    source_basis = _sequence(record.get("source_basis"))
    empty_refs = [
        basis
        for basis in source_basis
        if isinstance(basis, Mapping) and not str(basis.get("source_ref") or "").strip()
    ]
    if empty_refs:
        record["issues"].append("stored_empty_source_ref")
    if _GREEK_RE.search(str(record.get("stored_summary") or "")):
        record["issues"].append("stored_summary_contains_greek")
    if _GREEK_RE.search(str(record.get("stored_short_gloss") or "")):
        record["issues"].append("stored_short_gloss_contains_greek")


def _audit_word_index(
    record: dict[str, Any],
    *,
    language: str,
    query: str,
    radius: int,
) -> None:
    try:
        payload = word_index_neighborhood_payload(
            language,
            query,
            source="all",
            radius=radius,
            merge="lexeme",
        )
    except Exception as exc:  # noqa: BLE001
        record["word_index_error"] = repr(exc)
        record["issues"].append("word_index_error")
        return

    neighborhood = _mapping(payload.get("neighborhood"))
    anchor = _mapping(neighborhood.get("anchor"))
    groups = _sequence(neighborhood.get("groups"))
    record["word_index"] = {
        "anchor_status": str(neighborhood.get("anchor_status") or ""),
        "anchor_query": str(anchor.get("query") or ""),
        "anchor_display": str(anchor.get("display") or ""),
        "anchor_source": str(anchor.get("source") or ""),
        "source_group_count": len(groups),
        "exact_source_group_count": sum(
            1 for group in groups if _mapping(group).get("anchor_status") == "exact"
        ),
    }
    if not anchor:
        record["issues"].append("no_word_index_anchor")
    elif record["word_index"]["anchor_status"] == "not_found":
        record["issues"].append("word_index_anchor_not_found")


def _audit_encounter_and_brief(
    record: dict[str, Any],
    *,
    language: str,
    query: str,
    timeout: int,
) -> None:
    payload, error = _encounter(language, query, timeout=timeout)
    if error:
        record["encounter_error"] = error
        record["issues"].append("encounter_error")
        return
    if not payload:
        record["issues"].append("encounter_empty_payload")
        return
    sources = _encounter_sources(payload)
    refs = _encounter_refs(payload)
    record["encounter"] = {
        "source_count": len(sources),
        "sources": sources,
        "source_ref_count": len(refs),
        "source_refs": refs[:12],
    }
    if not sources:
        record["issues"].append("no_encounter_sources")
    try:
        flow = build_encounter_briefing_flow(payload)
    except Exception as exc:  # noqa: BLE001
        record["briefing_error"] = repr(exc)
        record["issues"].append("briefing_error")
        return
    digest = _mapping(flow.get("digest"))
    draft = _mapping(flow.get("draft_output"))
    brief_refs = [str(ref) for ref in _sequence(digest.get("source_refs"))]
    record["briefing"] = {
        "meaning_count": len(_sequence(digest.get("meanings"))),
        "source_refs": brief_refs,
        "draft_short": str(draft.get("short") or ""),
    }
    noisy_refs = [ref for ref in brief_refs if _looks_like_noisy_ref(ref)]
    if noisy_refs:
        record["briefing_noisy_refs"] = noisy_refs
        record["issues"].append("briefing_noisy_refs")
    if not _sequence(digest.get("meanings")):
        record["issues"].append("briefing_no_meanings")


def _encounter(
    language: str,
    query: str,
    *,
    timeout: int,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        result = subprocess.run(
            [
                "just",
                "cli",
                "encounter",
                language,
                query,
                "all",
                "--translation-mode",
                "cache",
                "--output",
                "json",
            ],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return None, f"timeout:{exc}"
    if result.returncode != 0:
        return None, f"exit_{result.returncode}:{result.stderr.strip() or result.stdout.strip()}"
    start = result.stdout.find("{")
    if start < 0:
        return None, "json_missing"
    try:
        return json.loads(result.stdout[start:]), None
    except json.JSONDecodeError as exc:
        return None, f"json_invalid:{exc}"


def _encounter_sources(payload: Mapping[str, Any]) -> list[str]:
    sources: set[str] = set()
    for meaning in _display_meanings(payload):
        for source in _sequence(meaning.get("sources")):
            text = str(source).strip()
            if text:
                sources.add(text)
    for basis in _source_basis(payload):
        tool = str(_mapping(basis).get("tool") or "").strip()
        if tool:
            sources.add(tool)
    return sorted(sources)


def _encounter_refs(payload: Mapping[str, Any]) -> list[str]:
    refs: set[str] = set()
    for meaning in _display_meanings(payload):
        for ref in _sequence(meaning.get("source_refs")):
            text = str(ref).strip()
            if text:
                refs.add(text)
    for basis in _source_basis(payload):
        ref = str(_mapping(basis).get("source_ref") or "").strip()
        if ref:
            refs.add(ref)
    return sorted(refs)


def _display_meanings(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    display = _mapping(payload.get("display"))
    meanings = display.get("meanings")
    if isinstance(meanings, Sequence) and not isinstance(meanings, (str, bytes)):
        return [item for item in meanings if isinstance(item, Mapping)]
    return []


def _source_basis(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    basis = payload.get("source_basis")
    if isinstance(basis, Sequence) and not isinstance(basis, (str, bytes)):
        return [item for item in basis if isinstance(item, Mapping)]
    return []


def _looks_like_noisy_ref(ref: str) -> bool:
    if not ref:
        return False
    if ":" in ref or any(ch.isdigit() for ch in ref):
        return False
    return len(ref) <= MAX_NOISY_REF_CHARS


def _summary(records: Sequence[Mapping[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    issue_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    flagged_by_language: Counter[str] = Counter()
    for record in records:
        language = str(record.get("language") or "")
        language_counts[language] += 1
        issues = [str(issue) for issue in _sequence(record.get("issues"))]
        if issues:
            flagged_by_language[language] += 1
        issue_counts.update(issues)
    return {
        "schema_version": "langnet.debug.motd_reader_flow_audit.v1",
        "motd_pool": str(args.motd_pool),
        "output": str(args.output),
        "rows": len(records),
        "encounter_limit": args.encounter_limit,
        "language_counts": dict(sorted(language_counts.items())),
        "flagged_by_language": dict(sorted(flagged_by_language.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


if __name__ == "__main__":
    main()
