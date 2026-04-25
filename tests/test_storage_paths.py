"""Tests for storage path management."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from langnet.storage.paths import all_db_paths, main_db_path, tool_db_path


class TestStoragePaths(unittest.TestCase):
    """Tests for storage path functions."""

    def test_main_db_path_returns_langnet_duckdb(self):
        """Main DB path should end with langnet.duckdb."""
        path = main_db_path()
        self.assertEqual(path.name, "langnet.duckdb")
        self.assertIn("cache", str(path))

    def test_tool_db_path_creates_tool_specific_path(self):
        """Tool DB paths should be in tools/ subdirectory."""
        diogenes_path = tool_db_path("diogenes")
        self.assertEqual(diogenes_path.name, "diogenes.duckdb")
        self.assertIn("tools", str(diogenes_path))

        whitakers_path = tool_db_path("whitakers")
        self.assertEqual(whitakers_path.name, "whitakers.duckdb")
        self.assertEqual(whitakers_path.parent, diogenes_path.parent)

    def test_tool_db_path_creates_directory(self):
        """Tool DB path should ensure tools/ directory exists."""
        path = tool_db_path("test_tool")
        self.assertTrue(path.parent.exists())
        self.assertEqual(path.parent.name, "tools")

    def test_all_db_paths_includes_main_and_tools(self):
        """all_db_paths should return main and all tool paths."""
        paths = all_db_paths()

        # Should have main database
        self.assertIn("main", paths)
        self.assertEqual(paths["main"].name, "langnet.duckdb")

        # Should have tool databases
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
            self.assertIn(key, paths, f"Missing tool path for {tool}")
            self.assertEqual(paths[key].name, f"{tool}.duckdb")

    def test_all_db_paths_returns_dict_with_path_values(self):
        """all_db_paths should return dict[str, Path]."""
        paths = all_db_paths()
        self.assertIsInstance(paths, dict)
        for name, path in paths.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(path, Path)

    @mock.patch.dict(os.environ, {"LANGNET_DATA_DIR": "/tmp/test_custom"})
    def test_langnet_data_dir_env_override(self):
        """LANGNET_DATA_DIR environment variable should override default path."""
        # Need to reload the module to pick up env var
        import importlib  # noqa: PLC0415

        from langnet.databuild import paths as databuild_paths  # noqa: PLC0415
        from langnet.storage import paths as storage_paths  # noqa: PLC0415

        importlib.reload(databuild_paths)
        importlib.reload(storage_paths)

        path = storage_paths.main_db_path()
        self.assertIn("/tmp/test_custom", str(path))
        self.assertEqual(path.name, "langnet.duckdb")

        # Reload again to restore original behavior
        importlib.reload(databuild_paths)
        importlib.reload(storage_paths)

    def test_paths_are_consistent_across_calls(self):
        """Paths should be deterministic and consistent."""
        path1 = main_db_path()
        path2 = main_db_path()
        self.assertEqual(path1, path2)

        tool1 = tool_db_path("diogenes")
        tool2 = tool_db_path("diogenes")
        self.assertEqual(tool1, tool2)

    def test_main_db_and_tool_db_in_same_cache_dir(self):
        """Main DB and tool DBs should be in related directories under cache/."""
        main = main_db_path()
        tool = tool_db_path("diogenes")

        # Both should be under cache/
        self.assertIn("cache", str(main))
        self.assertIn("cache", str(tool))

        # Tool should be in tools/ subdirectory of same cache
        self.assertEqual(tool.parent.parent, main.parent)
