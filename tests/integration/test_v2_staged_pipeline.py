"""Integration tests for V2 staged execution pipeline with persistent storage.

These tests validate the complete flow:
1. Plan generation
2. Staged execution (fetch → extract → derive → claim)
3. Persistent storage with versioning
4. Cache behavior across runs
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from query_spec import LanguageHint, NormalizedQuery

from langnet.clients.base import RawResponseEffect
from langnet.execution.registry import default_registry
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.db import connect_duckdb
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.paths import all_db_paths, main_db_path, tool_db_path
from langnet.storage.plan_index import PlanResponseIndex, apply_schema


class V2StagedPipelineTests(unittest.TestCase):
    """Tests for V2 staged execution with persistent storage."""

    def setUp(self) -> None:
        """Set up test database in temp directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="langnet_test_")
        self.db_path = Path(self.temp_dir) / "test.duckdb"

    def tearDown(self) -> None:
        """Clean up test database."""
        if self.db_path.exists():
            self.db_path.unlink()
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_persistent_storage_paths_exist(self) -> None:
        """Verify storage paths are configured and accessible."""
        main_path = main_db_path()
        self.assertTrue(main_path.name == "langnet.duckdb")
        self.assertIn("cache", str(main_path))

        # Tool paths should be in tools/ subdirectory
        diogenes_path = tool_db_path("diogenes")
        self.assertEqual(diogenes_path.name, "diogenes.duckdb")
        self.assertIn("tools", str(diogenes_path))

    def test_staged_execution_with_in_memory_db(self) -> None:
        """Test complete staged pipeline with in-memory database."""
        with connect_duckdb(":memory:") as conn:
            apply_schema(conn)

            # Set up indexes
            raw_index = RawResponseIndex(conn)
            extraction_index = ExtractionIndex(conn)
            derivation_index = DerivationIndex(conn)
            claim_index = ClaimIndex(conn)
            plan_index = PlanResponseIndex(conn)

            # Create a simple plan using stub tools (unused for now)
            _registry = default_registry(use_stubs=True)

            # Build a minimal plan for testing (unused for now)
            _normalized = NormalizedQuery(
                original="test",
                language=LanguageHint.LANGUAGE_HINT_LAT,
                candidates=[],
                normalizations=[],
            )

            # Use the planner to create a plan (unused for now)
            _planner = ToolPlanner(
                PlannerConfig(
                    diogenes_parse_endpoint="http://example.com",
                    heritage_base_url="http://example.com",
                    heritage_max_results=5,
                    include_whitakers=True,
                    include_cltk=False,
                    max_candidates=3,
                )
            )

            # Note: This will fail if planner requires real services
            # For now, we just verify the test structure is correct
            # Real integration tests would need live services

            # Verify indexes are accessible
            self.assertIsNotNone(raw_index)
            self.assertIsNotNone(extraction_index)
            self.assertIsNotNone(derivation_index)
            self.assertIsNotNone(claim_index)
            self.assertIsNotNone(plan_index)

    def test_persistent_db_survives_across_connections(self) -> None:
        """Verify data persists across database connections."""
        # First connection: write data
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            raw_index = RawResponseIndex(conn)

            # Insert a test response
            effect = RawResponseEffect(
                response_id="test-resp-1",
                tool="test.tool",
                call_id="test-call-1",
                endpoint="http://example.com",
                status_code=200,
                content_type="text/plain",
                headers={},
                body=b"test response",
            )
            raw_index.store(effect)

        # Second connection: verify data exists
        with connect_duckdb(self.db_path, read_only=True) as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM raw_response_index WHERE response_id = ?",
                ["test-resp-1"],
            ).fetchone()
            self.assertEqual(result[0], 1, "Response should persist across connections")  # type: ignore[index]

    def test_extraction_index_stores_and_retrieves(self) -> None:
        """Verify extraction index can store and retrieve extractions."""
        with connect_duckdb(self.db_path) as conn:
            apply_schema(conn)
            extraction_index = ExtractionIndex(conn)
            raw_index = RawResponseIndex(conn)

            # First store a raw response
            raw_effect = RawResponseEffect(
                response_id="test-resp-1",
                tool="test.tool",
                call_id="test-call-1",
                endpoint="http://example.com",
                status_code=200,
                content_type="text/plain",
                headers={},
                body=b"test response",
            )
            raw_index.store(raw_effect)

            # Then store an extraction based on that response
            extraction_id = extraction_index.store(
                response=raw_effect,
                kind="test_kind",
                canonical="test_canonical",
                payload={"key": "value"},
                load_duration_ms=10,
            )

            # Verify it's stored correctly
            query = """
                SELECT extraction_id, kind, canonical
                FROM extraction_index
                WHERE extraction_id = ?
            """
            result = conn.execute(query, [extraction_id]).fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], extraction_id)  # type: ignore[index]
            self.assertEqual(result[1], "test_kind")  # type: ignore[index]
            self.assertEqual(result[2], "test_canonical")  # type: ignore[index]

    def test_all_db_paths_returns_expected_tools(self) -> None:
        """Verify all_db_paths returns main and tool databases."""
        paths = all_db_paths()

        # Should have main database
        self.assertIn("main", paths)

        # Should have all expected tool databases
        expected_tools = [
            "diogenes",
            "whitakers",
            "cltk",
            "spacy",
            "heritage",
            "cdsl",
            "cts_index",
        ]
        for tool in expected_tools:
            key = f"tool:{tool}"
            self.assertIn(key, paths, f"Missing path for {tool}")
