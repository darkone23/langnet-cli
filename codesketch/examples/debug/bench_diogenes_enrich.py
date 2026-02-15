"""
Ad-hoc benchmark for Diogenes citation enrichment.

Loads an already-adapted query result (e.g., /tmp/langnet_query.json) and
measures how long citation enrichment takes without restarting the server.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean

from langnet.adapters.diogenes import DiogenesBackendAdapter


def collect_citation_maps(data: list[dict]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    for entry in data:
        if entry.get("source") != "diogenes":
            continue
        for block in entry.get("dictionary_blocks", []):
            cits = block.get("citations")
            if isinstance(cits, dict):
                citations.append({str(k): str(v) for k, v in cits.items()})
    return citations


def bench_enrich(adapter: DiogenesBackendAdapter, citations: list[dict[str, str]], language: str) -> float:
    start = time.perf_counter()
    for cits in citations:
        adapter._enrich_citations(cits, language)  # noqa: SLF001
    return (time.perf_counter() - start) * 1000


def bench_bulk(adapter: DiogenesBackendAdapter, citations: list[dict[str, str]]) -> float:
    urns: dict[str, str | None] = {}
    for cits in citations:
        for urn, text in cits.items():
            if urn.startswith("urn:cts"):
                urns[urn] = text

    start = time.perf_counter()
    adapter._cts_mapper.get_urn_metadata_bulk(urns)  # noqa: SLF001
    return (time.perf_counter() - start) * 1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Path to langnet query JSON output")
    parser.add_argument("--language", default="grc")
    args = parser.parse_args()

    data = json.loads(args.path.read_text())
    citations = collect_citation_maps(data)
    adapter = DiogenesBackendAdapter()

    total_ms = bench_enrich(adapter, citations, args.language)
    per_block = total_ms / len(citations) if citations else 0
    bulk_ms = bench_bulk(adapter, citations)

    print(f"blocks={len(citations)} total_ms={total_ms:.2f} avg_per_block_ms={per_block:.2f}")
    print(f"bulk_only_cts_lookup_ms={bulk_ms:.2f}")
    print(f"unique_cts_urns={len({u for c in citations for u in c if u.startswith('urn:cts')})}")


if __name__ == "__main__":
    main()
