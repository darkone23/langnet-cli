from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from langnet.reader.opengreekandlatin import discover_ogl_sources
from langnet.reader.storage import list_source_index


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
                    "samples": [],
                }
            )
            continue

        candidates = discover_ogl_sources(root, collection_id)
        selected = [candidate for candidate in candidates if candidate.import_status == "text_imported"]
        catalog_rows = list_source_index(catalog_path, collection_id=collection_id, limit=10_000_000)
        catalog_paths = {str(row.get("source_path") or "") for row in catalog_rows}
        selected_missing_catalog = [
            candidate
            for candidate in selected
            if str(candidate.source_path) not in catalog_paths
        ]
        skipped = [candidate for candidate in candidates if candidate.import_status != "text_imported"]

        items.append(
            {
                "collection_id": collection_id,
                "root": str(root),
                "root_exists": True,
                "candidate_count": len(candidates),
                "selected_count": len(selected),
                "catalog_row_count": len(catalog_rows),
                "catalog_missing_selected_count": len(selected_missing_catalog),
                "synthetic_identity_count": sum(1 for candidate in candidates if candidate.synthetic_work_id),
                "missing_cts_edition_count": sum(
                    1 for candidate in candidates if not candidate.cts_edition_urn
                ),
                "status_counts": dict(Counter(candidate.import_status for candidate in candidates)),
                "view_counts": dict(Counter(candidate.source_view for candidate in candidates)),
                "skip_reason_counts": dict(
                    Counter(candidate.skip_reason or "" for candidate in skipped)
                ),
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
        },
    }


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
