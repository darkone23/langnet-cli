from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from langnet.reader.opengreekandlatin import (
    OglSourceCandidate,
    discover_ogl_source_view_candidates,
    discover_ogl_sources,
    parse_ogl_tei,
    parsed_ogl_source_candidate,
)
from langnet.reader.storage import list_source_index

_CTS_URN_RE = re.compile(r"urn:cts:[A-Za-z0-9_.:-]+")

OGL_VIEW_COMPARISON_COLUMNS = [
    "alternate_view",
    "work_key",
    "selected_source_view",
    "selected_source_path",
    "selected_segment_count",
    "selected_token_count",
    "selected_title",
    "selected_author",
    "alternate_source_path",
    "alternate_segment_count",
    "alternate_token_count",
    "alternate_title",
    "alternate_author",
    "segment_delta",
    "token_delta",
    "title_changed",
    "author_changed",
]


def audit_ogl_imports(
    *,
    catalog_path: Path,
    roots: dict[str, Path | None],
    collections: set[str] | None = None,
    sample_limit: int = 8,
) -> dict[str, Any]:
    items = []
    for collection_id, root in roots.items():
        if collections and collection_id not in collections:
            continue
        if root is None or not root.exists():
            items.append(
                {
                    "collection_id": collection_id,
                    "root": str(root) if root else "",
                    "root_exists": False,
                    "candidate_count": 0,
                    "selected_count": 0,
                    "catalog_row_count": 0,
                    "catalog_missing_selected_count": 0,
                    "status_counts": {},
                    "view_counts": {},
                    "skip_reason_counts": {},
                    "view_comparison_sample_count": 0,
                    "view_comparison_samples": [],
                    "samples": [],
                }
            )
            continue

        candidates = discover_ogl_sources(root, collection_id)
        view_candidates = discover_ogl_source_view_candidates(root, collection_id)
        selected = [
            candidate for candidate in candidates if candidate.import_status == "text_imported"
        ]
        catalog_rows = list_source_index(
            catalog_path, collection_id=collection_id, limit=10_000_000
        )
        catalog_paths = {str(row.get("source_path") or "") for row in catalog_rows}
        selected_missing_catalog = [
            candidate for candidate in selected if str(candidate.source_path) not in catalog_paths
        ]
        skipped = [
            candidate for candidate in candidates if candidate.import_status != "text_imported"
        ]
        view_comparison_samples = _source_view_comparison_samples(
            selected,
            view_candidates,
            sample_limit,
        )

        items.append(
            {
                "collection_id": collection_id,
                "root": str(root),
                "root_exists": True,
                "candidate_count": len(candidates),
                "selected_count": len(selected),
                "catalog_row_count": len(catalog_rows),
                "catalog_missing_selected_count": len(selected_missing_catalog),
                "synthetic_identity_count": sum(
                    1 for candidate in candidates if candidate.synthetic_work_id
                ),
                "missing_cts_edition_count": sum(
                    1 for candidate in candidates if not candidate.cts_edition_urn
                ),
                "status_counts": dict(Counter(candidate.import_status for candidate in candidates)),
                "view_counts": dict(Counter(candidate.source_view for candidate in candidates)),
                "skip_reason_counts": dict(
                    Counter(candidate.skip_reason or "" for candidate in skipped)
                ),
                "view_comparison_sample_count": len(view_comparison_samples),
                "view_comparison_samples": view_comparison_samples,
                "samples": [
                    _candidate_sample(candidate)
                    for candidate in [
                        *selected_missing_catalog[:sample_limit],
                        *skipped[: max(sample_limit - len(selected_missing_catalog), 0)],
                    ][:sample_limit]
                ],
            }
        )

    return {
        "schema_version": "langnet.reader.v1",
        "mode": "ogl-audit",
        "catalog_path": str(catalog_path),
        "items": items,
        "summary": {
            "collection_count": len(items),
            "candidate_count": sum(int(item["candidate_count"]) for item in items),
            "selected_count": sum(int(item["selected_count"]) for item in items),
            "catalog_row_count": sum(int(item["catalog_row_count"]) for item in items),
            "catalog_missing_selected_count": sum(
                int(item["catalog_missing_selected_count"]) for item in items
            ),
            "view_comparison_sample_count": sum(
                int(item["view_comparison_sample_count"]) for item in items
            ),
        },
    }


def write_ogl_view_comparison_artifact(
    *,
    root: Path,
    collection_id: str,
    output_dir: Path,
    limit_per_view: int = 10,
    alternate_views: tuple[str, ...] = ("alternate_view_corrected", "alternate_view_split"),
) -> dict[str, Any]:
    view_candidates = discover_ogl_source_view_candidates(root, collection_id)
    selected = [candidate for candidate in view_candidates if candidate.source_view == "data"]
    comparisons = _bounded_source_view_comparison_samples_by_view(
        selected,
        view_candidates,
        alternate_views=alternate_views,
        limit_per_view=limit_per_view,
    )
    rows = [_comparison_tsv_row(comparison) for comparison in comparisons]
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{collection_id}_source_view_comparison"
    json_path = output_dir / f"{stem}.json"
    tsv_path = output_dir / f"{stem}.tsv"
    payload = {
        "schema_version": "langnet.reader.v1",
        "mode": "ogl-view-comparison",
        "collection_id": collection_id,
        "root": str(root),
        "summary": {
            "selected_count": len(selected),
            "candidate_count": len(view_candidates),
            "comparison_count": len(comparisons),
            "alternate_views": list(alternate_views),
            "limit_per_view": limit_per_view,
        },
        "comparisons": comparisons,
        "outputs": {
            "json_path": str(json_path),
            "tsv_path": str(tsv_path),
        },
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with tsv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OGL_VIEW_COMPARISON_COLUMNS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return payload


def _candidate_sample(candidate) -> dict[str, Any]:
    return {
        "source_id": candidate.source_id,
        "source_path": str(candidate.source_path),
        "source_view": candidate.source_view,
        "import_status": candidate.import_status,
        "skip_reason": candidate.skip_reason,
        "segment_count": candidate.segment_count,
        "cts_work_urn": candidate.cts_work_urn,
        "cts_edition_urn": candidate.cts_edition_urn,
        "synthetic_work_id": candidate.synthetic_work_id,
        "cts_groupname": candidate.cts_groupname,
        "cts_title": candidate.cts_title,
    }


def _source_view_comparison_samples(
    selected: list[OglSourceCandidate],
    candidates: list[OglSourceCandidate],
    sample_limit: int,
) -> list[dict[str, Any]]:
    if sample_limit <= 0:
        return []
    selected_by_key = {
        work_key: candidate
        for candidate in selected
        if (work_key := _candidate_work_key(candidate))
    }
    selected_paths = {candidate.source_path for candidate in selected}
    samples: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for raw_candidate in sorted(
        candidates, key=lambda item: (item.source_priority, item.source_view, str(item.source_path))
    ):
        if raw_candidate.source_path in selected_paths:
            continue
        candidate = parsed_ogl_source_candidate(raw_candidate)
        work_key = _candidate_work_key(candidate)
        if not work_key or work_key not in selected_by_key:
            continue
        selected_candidate = selected_by_key[work_key]
        pair_key = (work_key, str(candidate.source_path))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        selected_metrics = _candidate_view_metrics(selected_candidate)
        alternate_metrics = _candidate_view_metrics(candidate)
        samples.append(
            {
                "work_key": work_key,
                "selected": selected_metrics,
                "alternate": alternate_metrics,
                "differences": {
                    "segment_delta": int(alternate_metrics["segment_count"])
                    - int(selected_metrics["segment_count"]),
                    "token_delta": int(alternate_metrics["token_count"])
                    - int(selected_metrics["token_count"]),
                    "title_changed": alternate_metrics["title"] != selected_metrics["title"],
                    "author_changed": alternate_metrics["author"] != selected_metrics["author"],
                },
            }
        )
        if len(samples) >= sample_limit:
            break
    return samples


def _source_view_comparison_samples_by_view(
    selected: list[OglSourceCandidate],
    candidates: list[OglSourceCandidate],
    *,
    alternate_views: tuple[str, ...],
    limit_per_view: int,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for alternate_view in alternate_views:
        view_candidates = [
            candidate for candidate in candidates if candidate.source_view == alternate_view
        ]
        view_samples = _source_view_comparison_samples(
            selected,
            view_candidates,
            limit_per_view,
        )
        for sample in view_samples:
            sample["alternate_view"] = alternate_view
        samples.extend(view_samples)
    return samples


def _bounded_source_view_comparison_samples_by_view(
    selected: list[OglSourceCandidate],
    candidates: list[OglSourceCandidate],
    *,
    alternate_views: tuple[str, ...],
    limit_per_view: int,
) -> list[dict[str, Any]]:
    selected_lookup = _SelectedCandidateLookup(selected)
    samples: list[dict[str, Any]] = []
    for alternate_view in alternate_views:
        samples.extend(
            _bounded_source_view_comparisons_for_view(
                candidates,
                alternate_view=alternate_view,
                limit=limit_per_view,
                selected_lookup=selected_lookup,
            )
        )
    return samples


class _SelectedCandidateLookup:
    def __init__(self, selected: list[OglSourceCandidate]) -> None:
        self._by_work_key = {
            work_key: candidate
            for candidate in selected
            if (work_key := _cheap_candidate_work_key(candidate))
        }

    def for_work_key(self, work_key: str) -> OglSourceCandidate | None:
        return self._by_work_key.get(work_key)


def _bounded_source_view_comparisons_for_view(
    candidates: list[OglSourceCandidate],
    *,
    alternate_view: str,
    limit: int,
    selected_lookup: _SelectedCandidateLookup,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    view_candidates = [
        candidate for candidate in candidates if candidate.source_view == alternate_view
    ]
    for raw_alternate in sorted(view_candidates, key=lambda item: str(item.source_path)):
        comparison = _comparison_for_raw_alternate(
            raw_alternate,
            alternate_view=alternate_view,
            selected_lookup=selected_lookup,
        )
        if comparison is None:
            continue
        samples.append(comparison)
        if len(samples) >= limit:
            break
    return samples


def _comparison_for_raw_alternate(
    raw_alternate: OglSourceCandidate,
    *,
    alternate_view: str,
    selected_lookup: _SelectedCandidateLookup,
) -> dict[str, Any] | None:
    work_key = _cheap_candidate_work_key(raw_alternate)
    if not work_key:
        return None
    selected_candidate = selected_lookup.for_work_key(work_key)
    if selected_candidate is None:
        return None
    alternate = parsed_ogl_source_candidate(raw_alternate)
    selected_candidate = parsed_ogl_source_candidate(selected_candidate)
    comparison = _source_view_comparison(
        selected_candidate,
        alternate,
        work_key=work_key,
    )
    comparison["alternate_view"] = alternate_view
    return comparison


def _comparison_tsv_row(comparison: dict[str, Any]) -> dict[str, Any]:
    selected = comparison["selected"]
    alternate = comparison["alternate"]
    differences = comparison["differences"]
    return {
        "alternate_view": comparison.get("alternate_view") or alternate["source_view"],
        "work_key": comparison["work_key"],
        "selected_source_view": selected["source_view"],
        "selected_source_path": selected["source_path"],
        "selected_segment_count": selected["segment_count"],
        "selected_token_count": selected["token_count"],
        "selected_title": selected["title"],
        "selected_author": selected["author"],
        "alternate_source_path": alternate["source_path"],
        "alternate_segment_count": alternate["segment_count"],
        "alternate_token_count": alternate["token_count"],
        "alternate_title": alternate["title"],
        "alternate_author": alternate["author"],
        "segment_delta": differences["segment_delta"],
        "token_delta": differences["token_delta"],
        "title_changed": differences["title_changed"],
        "author_changed": differences["author_changed"],
    }


def _source_view_comparison(
    selected_candidate: OglSourceCandidate,
    alternate_candidate: OglSourceCandidate,
    *,
    work_key: str,
) -> dict[str, Any]:
    selected_metrics = _candidate_view_metrics(selected_candidate)
    alternate_metrics = _candidate_view_metrics(alternate_candidate)
    return {
        "work_key": work_key,
        "selected": selected_metrics,
        "alternate": alternate_metrics,
        "differences": {
            "segment_delta": int(alternate_metrics["segment_count"])
            - int(selected_metrics["segment_count"]),
            "token_delta": int(alternate_metrics["token_count"])
            - int(selected_metrics["token_count"]),
            "title_changed": alternate_metrics["title"] != selected_metrics["title"],
            "author_changed": alternate_metrics["author"] != selected_metrics["author"],
        },
    }


def _candidate_work_key(candidate: OglSourceCandidate) -> str:
    return candidate.cts_work_urn or candidate.synthetic_work_id or candidate.edition_key


def _relative_view_key(candidate: OglSourceCandidate) -> str:
    source_id = candidate.source_id
    head, sep, tail = source_id.partition("/")
    if sep and head in {"data", "corrected", "split", "volumes", "Volumes"}:
        return tail
    return source_id


def _cheap_candidate_work_key(candidate: OglSourceCandidate) -> str:
    if candidate.cts_work_urn or candidate.synthetic_work_id:
        return _candidate_work_key(candidate)
    try:
        prefix = candidate.source_path.read_text(encoding="utf-8", errors="ignore")[:65536]
    except OSError:
        return ""
    urns = _CTS_URN_RE.findall(prefix)
    if not urns:
        return ""
    return _work_urn_from_edition_urn(max(urns, key=_urn_specificity_key))


def _work_urn_from_edition_urn(urn: str) -> str:
    prefix, dot, _edition = urn.rpartition(".")
    return prefix if dot else urn


def _urn_specificity_key(urn: str) -> tuple[int, int]:
    object_part = urn.rsplit(":", 1)[-1]
    return (object_part.count("."), len(urn))


def _candidate_view_metrics(candidate: OglSourceCandidate) -> dict[str, Any]:
    try:
        parsed = parse_ogl_tei(candidate)
    except Exception as exc:  # noqa: BLE001
        return {
            "source_path": str(candidate.source_path),
            "source_view": candidate.source_view,
            "import_status": candidate.import_status,
            "segment_count": candidate.segment_count,
            "token_count": 0,
            "title": candidate.cts_title or "",
            "author": candidate.cts_groupname or "",
            "parse_error": str(exc),
        }
    return {
        "source_path": str(candidate.source_path),
        "source_view": candidate.source_view,
        "import_status": candidate.import_status,
        "segment_count": len(parsed.segments),
        "token_count": sum(len(segment.normalized_text.split()) for segment in parsed.segments),
        "title": parsed.work.title,
        "author": parsed.work.author,
        "parse_error": "",
    }
