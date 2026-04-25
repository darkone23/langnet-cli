"""Performance benchmarks for langnet V2.

These benchmarks establish baseline performance metrics for:
- Database operations (storage layer)
- Handler execution (extract/derive/claim)
- Full pipeline execution
- Cache performance

Run with: python -m pytest tests/benchmarks/ -v --benchmark-only
Or for nose2: python -m unittest tests.benchmarks.test_performance
"""

from __future__ import annotations

import shutil
import tempfile
import time
import unittest
from pathlib import Path

from query_spec import ToolCallSpec, ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
)
from langnet.execution.handlers.diogenes import claim_morph, derive_morph, extract_html
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.db import connect_duckdb
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.plan_index import PlanResponseIndex, apply_schema


class PerformanceBenchmarks(unittest.TestCase):
    """Baseline performance benchmarks for V2 architecture."""

    def setUp(self) -> None:
        """Set up temp database for benchmarks."""
        self.temp_dir = tempfile.mkdtemp(prefix="langnet_bench_")
        self.db_path = Path(self.temp_dir) / "bench.duckdb"

    def tearDown(self) -> None:
        """Clean up temp database."""
        if self.db_path.exists():
            self.db_path.unlink()
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def _time_operation(self, operation, iterations=100):
        """Time an operation over multiple iterations."""
        start = time.perf_counter()
        for _ in range(iterations):
            operation()
        end = time.perf_counter()
        total_ms = (end - start) * 1000
        avg_ms = total_ms / iterations
        return {"total_ms": total_ms, "avg_ms": avg_ms, "iterations": iterations}

    def test_benchmark_database_insert_raw_response(self):
        """Benchmark: Insert raw response into database."""
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            raw_index = RawResponseIndex(conn)

            def insert_response():
                effect = RawResponseEffect(
                    response_id=f"resp-{time.perf_counter_ns()}",
                    tool="fetch.test",
                    call_id="call-1",
                    endpoint="http://example.com",
                    status_code=200,
                    content_type="text/html",
                    headers={},
                    body=b"<html>test response body</html>",
                )
                raw_index.store(effect)

            result = self._time_operation(insert_response, iterations=100)
            print(f"\n[DB INSERT] Raw response: {result['avg_ms']:.2f}ms avg")
            self.assertLess(result["avg_ms"], 50, "Raw response insert should be <50ms")

    def test_benchmark_database_query_raw_response(self):
        """Benchmark: Query raw response from database."""
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            raw_index = RawResponseIndex(conn)

            # Insert test data
            test_id = "resp-bench-query"
            effect = RawResponseEffect(
                response_id=test_id,
                tool="fetch.test",
                call_id="call-1",
                endpoint="http://example.com",
                status_code=200,
                content_type="text/html",
                headers={},
                body=b"<html>test</html>",
            )
            raw_index.store(effect)

            def query_response():
                conn.execute(
                    "SELECT body FROM raw_response_index WHERE response_id = ?",
                    [test_id],
                ).fetchone()

            result = self._time_operation(query_response, iterations=1000)
            print(f"\n[DB QUERY] Raw response: {result['avg_ms']:.3f}ms avg")
            self.assertLess(result["avg_ms"], 5, "Raw response query should be <5ms")

    def test_benchmark_extraction_index_insert(self):
        """Benchmark: Insert extraction into database."""
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            extraction_index = ExtractionIndex(conn)
            raw_index = RawResponseIndex(conn)

            # Create raw response first
            raw_effect = RawResponseEffect(
                response_id="resp-1",
                tool="fetch.test",
                call_id="call-1",
                endpoint="http://example.com",
                status_code=200,
                content_type="text/html",
                headers={},
                body=b"<html>test</html>",
            )
            raw_index.store(raw_effect)

            counter = [0]

            def insert_extraction():
                counter[0] += 1
                extraction_index.store(
                    response=raw_effect,
                    kind="test",
                    canonical=f"test_canonical_{counter[0]}",
                    payload={"lemma": "lupus", "pos": "noun"},
                    load_duration_ms=10,
                )

            result = self._time_operation(insert_extraction, iterations=100)
            print(f"\n[DB INSERT] Extraction: {result['avg_ms']:.2f}ms avg")
            self.assertLess(result["avg_ms"], 50, "Extraction insert should be <50ms")

    def test_benchmark_handler_extract_diogenes(self):
        """Benchmark: Diogenes HTML extraction handler."""
        # Sample Diogenes HTML response
        sample_html = b"""
        <html>
        <div class="diogenes">
            <span class="lemma">lupus</span>
            <span class="pos">noun</span>
            <div class="definition">wolf; a greedy person</div>
        </div>
        </html>
        """

        raw_effect = RawResponseEffect(
            response_id="resp-bench",
            tool="fetch.diogenes",
            call_id="call-bench",
            endpoint="http://example.com",
            status_code=200,
            content_type="text/html",
            headers={},
            body=sample_html,
        )

        call = ToolCallSpec(
            tool="extract.diogenes.html",
            call_id="call-extract",
            endpoint="internal://extract",
            params={},
            stage=ToolStage.TOOL_STAGE_EXTRACT,
        )

        def run_extract():
            extract_html(call, raw_effect)

        result = self._time_operation(run_extract, iterations=100)
        print(f"\n[HANDLER] Extract (Diogenes HTML): {result['avg_ms']:.2f}ms avg")
        self.assertLess(result["avg_ms"], 100, "Extraction should be <100ms")

    def test_benchmark_handler_derive_diogenes(self):
        """Benchmark: Diogenes morphology derivation handler."""
        extraction = ExtractionEffect(
            extraction_id="ext-bench",
            tool="extract.diogenes.html",
            call_id="call-extract",
            source_call_id="call-fetch",
            response_id="resp-bench",
            kind="html",
            canonical="lupus",
            payload={
                "chunks": [
                    {
                        "chunk_type": "morphology",
                        "morphology": {
                            "morphs": [{"lemma": "lupus", "pos": "noun", "case": "nominative"}]
                        },
                    }
                ]
            },
        )

        call = ToolCallSpec(
            tool="derive.diogenes.morph",
            call_id="call-derive",
            endpoint="internal://derive",
            params={"source_call_id": "call-extract"},
            stage=ToolStage.TOOL_STAGE_DERIVE,
        )

        def run_derive():
            derive_morph(call, extraction)

        result = self._time_operation(run_derive, iterations=100)
        print(f"\n[HANDLER] Derive (Diogenes morph): {result['avg_ms']:.2f}ms avg")
        self.assertLess(result["avg_ms"], 50, "Derivation should be <50ms")

    def test_benchmark_handler_claim_diogenes(self):
        """Benchmark: Diogenes claim handler."""
        derivation = DerivationEffect(
            derivation_id="drv-bench",
            tool="derive.diogenes.morph",
            call_id="call-derive",
            source_call_id="call-extract",
            extraction_id="ext-bench",
            kind="morph",
            canonical="lupus",
            payload={"lemmas": ["lupus"], "morphology": [{"pos": "noun"}]},
            provenance_chain=[
                ProvenanceLink(
                    stage="extract",
                    tool="extract.diogenes.html",
                    reference_id="ext-bench",
                )
            ],
        )

        call = ToolCallSpec(
            tool="claim.diogenes.morph",
            call_id="call-claim",
            endpoint="internal://claim",
            params={"source_call_id": "call-derive"},
            stage=ToolStage.TOOL_STAGE_CLAIM,
        )

        def run_claim():
            claim_morph(call, derivation)

        result = self._time_operation(run_claim, iterations=100)
        print(f"\n[HANDLER] Claim (Diogenes morph): {result['avg_ms']:.2f}ms avg")
        self.assertLess(result["avg_ms"], 50, "Claim should be <50ms")

    def test_benchmark_schema_application(self):
        """Benchmark: Schema application time."""

        def apply_schema_fresh():
            with connect_duckdb(":memory:") as conn:
                apply_schema(conn)

        result = self._time_operation(apply_schema_fresh, iterations=10)
        print(f"\n[DB SCHEMA] Apply schema: {result['avg_ms']:.2f}ms avg")
        self.assertLess(result["avg_ms"], 100, "Schema application should be <100ms")

    def test_benchmark_cache_hit_vs_miss(self):
        """Benchmark: Compare cache hit vs miss performance."""
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            raw_index = RawResponseIndex(conn)

            # Warm cache
            test_id = "resp-cache-bench"
            effect = RawResponseEffect(
                response_id=test_id,
                tool="fetch.test",
                call_id="call-1",
                endpoint="http://example.com",
                status_code=200,
                content_type="text/html",
                headers={},
                body=b"<html>cached response</html>",
            )
            raw_index.store(effect)

            # Benchmark cache hit
            def cache_hit():
                conn.execute(
                    "SELECT body FROM raw_response_index WHERE response_id = ?",
                    [test_id],
                ).fetchone()

            hit_result = self._time_operation(cache_hit, iterations=1000)

            # Benchmark cache miss (network simulation)
            def cache_miss_simulate():
                # Simulate 50ms network latency
                time.sleep(0.05)

            miss_result = self._time_operation(cache_miss_simulate, iterations=10)

            speedup = miss_result["avg_ms"] / hit_result["avg_ms"]
            print(f"\n[CACHE] Hit: {hit_result['avg_ms']:.3f}ms avg")
            print(f"[CACHE] Miss (simulated): {miss_result['avg_ms']:.2f}ms avg")
            print(f"[CACHE] Speedup: {speedup:.0f}x")

            self.assertGreater(speedup, 10, "Cache should be at least 10x faster than network")

    def test_benchmark_full_pipeline_memory(self):
        """Benchmark: Full pipeline with in-memory database."""
        # Note: This is a stub - full pipeline would require real services
        # For now, just benchmark the database setup overhead

        def setup_pipeline():
            with connect_duckdb(":memory:") as conn:
                apply_schema(conn)
                RawResponseIndex(conn)
                ExtractionIndex(conn)
                DerivationIndex(conn)
                ClaimIndex(conn)
                PlanResponseIndex(conn)

        result = self._time_operation(setup_pipeline, iterations=10)
        print(f"\n[PIPELINE] Setup (in-memory): {result['avg_ms']:.2f}ms avg")
        self.assertLess(result["avg_ms"], 200, "Pipeline setup should be <200ms")

    def test_benchmark_database_concurrent_reads(self):
        """Benchmark: Concurrent read performance."""
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            raw_index = RawResponseIndex(conn)

            # Insert 10 responses
            for i in range(10):
                effect = RawResponseEffect(
                    response_id=f"resp-{i}",
                    tool="fetch.test",
                    call_id=f"call-{i}",
                    endpoint="http://example.com",
                    status_code=200,
                    content_type="text/html",
                    headers={},
                    body=b"<html>test</html>",
                )
                raw_index.store(effect)

            # Benchmark sequential reads
            def read_all_sequential():
                for i in range(10):
                    conn.execute(
                        "SELECT body FROM raw_response_index WHERE response_id = ?",
                        [f"resp-{i}"],
                    ).fetchone()

            result = self._time_operation(read_all_sequential, iterations=100)
            print(f"\n[DB CONCURRENT] 10 sequential reads: {result['avg_ms']:.2f}ms avg")
            self.assertLess(result["avg_ms"], 50, "10 reads should be <50ms")


if __name__ == "__main__":
    # Run benchmarks
    unittest.main(verbosity=2)
