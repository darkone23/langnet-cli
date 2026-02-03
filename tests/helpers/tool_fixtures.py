"""
Test helper functions for working with tool output fixtures.

This module provides utilities for loading fixtures, validating schemas,
and comparing adapter outputs with real backend data.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest
import structlog

from langnet.logging import setup_logging

logger = structlog.get_logger(__name__)


class ToolFixtureMixin:
    """Mixin class for tests that use tool output fixtures."""
    
    @pytest.fixture
    def fixture_dir(self) -> Path:
        """Return the fixture directory path."""
        return Path("tests/fixtures/raw_tool_outputs")
    
    def load_tool_fixture(
        self, 
        tool: str, 
        action: str, 
        lang: Optional[str] = None, 
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load a tool fixture file.
        
        Args:
            tool: Backend tool name
            action: Action performed
            lang: Language code (optional)
            query: Query word (optional)
            
        Returns:
            Loaded fixture data
            
        Raises:
            FileNotFoundError: If fixture doesn't exist
        """
        fixture_dir = Path("tests/fixtures/raw_tool_outputs")
        tool_dir = fixture_dir / tool
        
        # Build filename pattern
        filename_parts = [f"{tool}_{action}"]
        if lang:
            filename_parts.append(lang)
        if query:
            safe_query = "".join(c for c in query if c.isalnum() or c in ('-', '_')).lower()
            filename_parts.append(safe_query)
        
        filename = "_".join(filename_parts) + ".json"
        fixture_path = tool_dir / filename
        
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def skip_if_no_fixture(self, tool: str, action: str, lang: Optional[str] = None, query: Optional[str] = None):
        """Skip test if fixture doesn't exist."""
        try:
            self.load_tool_fixture(tool, action, lang, query)
        except FileNotFoundError:
            pytest.skip(f"No fixture available for {tool}/{action}" + (f"/{lang}" if lang else ""))
    
    def assert_tool_schema(self, raw_output: Dict[str, Any], schema_path: Optional[Path] = None) -> bool:
        """Assert that raw output matches expected schema.
        
        Args:
            raw_output: Raw tool output to validate
            schema_path: Path to schema file (auto-detected if None)
            
        Returns:
            True if validation passes
            
        Raises:
            AssertionError: If validation fails
        """
        try:
            import jsonschema
        except ImportError:
            logger.warning("jsonschema not available, skipping schema validation")
            return True
        
        if schema_path is None:
            # Auto-detect schema path
            tool = raw_output.get("_tool", "unknown")
            schema_path = Path("tests/fixtures/raw_tool_outputs") / tool / f"schema_{tool}.json"
        
        if not schema_path.exists():
            logger.warning(f"Schema not found: {schema_path}")
            return True
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        try:
            jsonschema.validate(instance=raw_output, schema=schema)
            return True
        except jsonschema.ValidationError as e:
            raise AssertionError(f"Schema validation failed: {e.message}")
    
    def generate_fixture_from_live(
        self, 
        tool: str, 
        action: str, 
        lang: Optional[str] = None, 
        query: str, 
        dict_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a fixture from live backend data.
        
        Args:
            tool: Backend tool name
            action: Action to perform
            lang: Language code
            query: Word to query
            dict_name: Dictionary name (optional)
            
        Returns:
            Live backend data
        """
        try:
            import requests
        except ImportError:
            raise ImportError("requests library required for live fixture generation")
        
        # Build API URL
        base_url = os.getenv("LANGNET_API_URL", "http://localhost:8000")
        url = f"{base_url}/api/tool/{tool}/{action}"
        params = {}
        
        if lang:
            params["lang"] = lang
        if dict_name:
            params["dict"] = dict_name
        params["query"] = query
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Save fixture
        self.save_fixture(tool, action, lang, query, data)
        
        return data
    
    def save_fixture(
        self, 
        tool: str, 
        action: str, 
        lang: Optional[str], 
        query: str, 
        data: Dict[str, Any]
    ):
        """Save fixture data to file.
        
        Args:
            tool: Backend tool name
            action: Action performed
            lang: Language code
            query: Query word
            data: Data to save
        """
        fixture_dir = Path("tests/fixtures/raw_tool_outputs")
        tool_dir = fixture_dir / tool
        tool_dir.mkdir(parents=True, exist_ok=True)
        
        # Build filename
        safe_query = "".join(c for c in query if c.isalnum() or c in ('-', '_')).lower()
        filename_parts = [f"{tool}_{action}"]
        if lang:
            filename_parts.append(lang)
        filename_parts.append(safe_query)
        
        filename = "_".join(filename_parts) + ".json"
        fixture_path = tool_dir / filename
        
        # Add metadata
        data["_tool"] = tool
        data["_action"] = action
        data["_lang"] = lang
        data["_query"] = query
        data["_generated"] = True
        
        with open(fixture_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("fixture_saved", path=str(fixture_path))
    
    def compare_adapter_output(
        self, 
        raw_data: Dict[str, Any], 
        unified_data: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare raw tool output with adapter unified output.
        
        Args:
            raw_data: Raw tool output
            unified_data: Adapter-converted unified output
            
        Returns:
            Comparison results
        """
        comparison = {
            "raw_structure": self._analyze_structure(raw_data),
            "unified_structure": self._analyze_structure(unified_data),
            "key_differences": self._find_key_differences(raw_data, unified_data),
            "adapter_quality": self._assess_adapter_quality(raw_data, unified_data)
        }
        
        return comparison
    
    def _analyze_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Analyze JSON structure."""
        if isinstance(data, dict):
            return {
                "type": "object",
                "path": path,
                "keys": list(data.keys()),
                "nested": {k: self._analyze_structure(v, f"{path}.{k}" if path else k) for k, v in data.items()}
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "path": path,
                "length": len(data),
                "element_type": type(data[0]).__name__ if data else "unknown"
            }
        else:
            return {
                "type": type(data).__name__,
                "path": path,
                "value": str(data)[:100] if str(data) else "empty"
            }
    
    def _find_key_differences(self, raw: Any, unified: Any, path: str = "") -> List[Dict[str, Any]]:
        """Find key-level differences."""
        differences = []
        
        if isinstance(raw, dict) and isinstance(unified, dict):
            raw_keys = set(raw.keys())
            unified_keys = set(unified.keys())
            
            for key in raw_keys - unified_keys:
                differences.append({
                    "type": "missing_in_unified",
                    "path": f"{path}.{key}" if path else key,
                    "raw_value": raw[key]
                })
            
            for key in unified_keys - raw_keys:
                differences.append({
                    "type": "extra_in_unified",
                    "path": f"{path}.{key}" if path else key,
                    "unified_value": unified[key]
                })
        
        return differences
    
    def _assess_adapter_quality(self, raw: Any, unified: Any) -> Dict[str, Any]:
        """Assess the quality of adapter conversion."""
        quality = {
            "completeness": 0.0,
            "accuracy": 0.0,
            "preservation": 0.0,
            "issues": []
        }
        
        # Basic completeness check
        if isinstance(raw, dict) and isinstance(unified, dict):
            raw_keys = set(raw.keys())
            unified_keys = set(unified.keys())
            
            if raw_keys:
                quality["completeness"] = len(unified_keys & raw_keys) / len(raw_keys)
        
        # Check for critical data preservation
        critical_fields = ["word", "lemma", "pos", "definition"]
        preserved_critical = 0
        
        for field in critical_fields:
            if isinstance(raw, dict) and field in raw:
                if isinstance(unified, dict) and field in unified:
                    if str(raw[field]).lower() == str(unified[field]).lower():
                        preserved_critical += 1
        
        if critical_fields:
            quality["accuracy"] = preserved_critical / len(critical_fields)
        
        # Check for data loss
        if isinstance(raw, dict) and isinstance(unified, dict):
            raw_values = [str(v) for v in raw.values() if v and not str(v).startswith("_")]
            unified_values = [str(v) for v in unified.values() if v and not str(v).startswith("_")]
            
            if raw_values:
                preserved_values = len(set(unified_values) & set(raw_values))
                quality["preservation"] = preserved_values / len(raw_values)
        
        # Identify issues
        if quality["completeness"] < 0.8:
            quality["issues"].append("Low completeness - significant data loss")
        
        if quality["accuracy"] < 0.9:
            quality["issues"].append("Low accuracy - critical field mismatch")
        
        if quality["preservation"] < 0.8:
            quality["issues"].append("Low preservation - data values not preserved")
        
        return quality


# Test configuration
RAW_TEST_MODE = os.getenv("RAW_TEST_MODE", "false").lower() == "true"


@pytest.fixture
def tool_fixture_mixin():
    """Provide the ToolFixtureMixin for test classes."""
    return ToolFixtureMixin()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "raw_test: mark test as using raw backend data"
    )
    config.addinivalue_line(
        "markers", "integration_test: mark test as integration test"
    )


def pytest_runtest_setup(item):
    """Setup for each test item."""
    if "raw_test" in item.keywords and not RAW_TEST_MODE:
        pytest.skip("RAW_TEST_MODE not enabled - skipping raw backend test")


# Common test word lists
TEST_WORDS = {
    "latin": ["lupus", "arma", "vir", "rosa", "amicus"],
    "greek": ["logos", "anthropos", "polis", "theos", "bios"],
    "sanskrit": ["agni", "yoga", "karma", "dharma", "atman"]
}

# Test fixture templates
FIXTURE_TEMPLATES = {
    "diogenes": {
        "search": {
            "chunks": [
                {
                    "headword": "test_word",
                    "morphology": {
                        "morphs": [
                            {
                                "stem": ["test"],
                                "tags": ["noun"],
                                "defs": ["test definition"]
                            }
                        ]
                    }
                }
            ],
            "dg_parsed": True
        }
    },
    "whitakers": {
        "analyze": {
            "raw": "test analysis",
            "parsing": [
                {
                    "stem": "test",
                    "ending": "us",
                    "part_of_speech": "noun",
                    "translation": ["test"]
                }
            ]
        }
    }
}