"""
Tool output comparison and analysis utilities.

This module provides tools for comparing raw tool outputs with unified schema outputs,
detecting schema changes, and generating adapter fixes.
"""

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
import structlog
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from langnet.logging import setup_logging

logger = structlog.get_logger(__name__)
console = Console()


class ToolOutputComparator:
    """Compare raw tool outputs with unified schema outputs."""

    def __init__(self, fixture_dir: str = "tests/fixtures/raw_tool_outputs"):
        self.fixture_dir = Path(fixture_dir)

    def compare_raw_to_unified(self, tool: str, action: str, word: str) -> Dict[str, Any]:
        """Compare raw tool output with unified schema output for a specific word.

        Args:
            tool: Backend tool name
            action: Action performed
            word: Word that was queried

        Returns:
            Comparison results with differences and suggestions
        """
        # Load raw fixture
        raw_fixture = self._find_fixture(tool, action, word)
        if not raw_fixture:
            return {"error": f"No fixture found for {tool}/{action}/{word}"}

        with open(raw_fixture, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Get unified output (this would normally come from API)
        unified_data = self._get_unified_output(tool, word)
        if not unified_data:
            return {"error": f"Could not get unified output for {word}"}

        # Compare structures
        comparison = {
            "tool": tool,
            "action": action,
            "word": word,
            "raw_structure": self._analyze_structure(raw_data),
            "unified_structure": self._analyze_structure(unified_data),
            "key_differences": self._find_key_differences(raw_data, unified_data),
            "missing_fields": self._find_missing_fields(raw_data, unified_data),
            "extra_fields": self._find_extra_fields(raw_data, unified_data),
            "adapter_suggestions": self._generate_adapter_suggestions(raw_data, unified_data),
        }

        return comparison

    def detect_schema_drift(self, tool: str, action: str) -> Dict[str, Any]:
        """Detect schema changes between old and new fixture versions.

        Args:
            tool: Backend tool name
            action: Action performed

        Returns:
            Schema drift detection results
        """
        fixture_dir = self.fixture_dir / tool
        fixture_files = list(fixture_dir.glob(f"*_{action}*.json"))

        if len(fixture_files) < 2:
            return {"error": "Need at least 2 fixture versions to detect drift"}

        # Sort by modification time to get old and new versions
        fixture_files.sort(key=lambda x: x.stat().st_mtime)
        old_fixture = fixture_files[0]
        new_fixture = fixture_files[-1]

        with open(old_fixture, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        with open(new_fixture, "r", encoding="utf-8") as f:
            new_data = json.load(f)

        drift = {
            "tool": tool,
            "action": action,
            "old_fixture": old_fixture.name,
            "new_fixture": new_fixture.name,
            "timestamp_old": old_fixture.stat().st_mtime,
            "timestamp_new": new_fixture.stat().st_mtime,
            "structural_changes": self._find_structural_changes(old_data, new_data),
            "field_changes": self._find_field_changes(old_data, new_data),
            "breaking_changes": self._detect_breaking_changes(old_data, new_data),
            "adapter_impact": self._assess_adapter_impact(old_data, new_data),
        }

        return drift

    def generate_adapter_fixes(self, tool: str, schema_changes: Dict[str, Any]) -> List[str]:
        """Generate code suggestions for adapter fixes based on schema changes.

        Args:
            tool: Backend tool name
            schema_changes: Schema change detection results

        Returns:
            List of code suggestions
        """
        fixes = []

        if schema_changes.get("breaking_changes"):
            fixes.append("# BREAKING DETECTED - Adapter needs major update")
            fixes.append("# Consider implementing a new adapter version")

            for change in schema_changes["breaking_changes"]:
                fixes.append(f"# Breaking change: {change}")

        if schema_changes.get("structural_changes"):
            fixes.append("# STRUCTURAL CHANGES DETECTED")
            fixes.append("# Update adapter mapping logic:")

            for change in schema_changes["structural_changes"]:
                if change["type"] == "field_renamed":
                    fixes.append(
                        f"#  - Field '{change['old_path']}' renamed to '{change['new_path']}'"
                    )
                elif change["type"] == "field_added":
                    fixes.append(f"#  - New field '{change['path']}' added")
                elif change["type"] == "field_removed":
                    fixes.append(f"#  - Field '{change['path']}' removed")

        if schema_changes.get("field_changes"):
            fixes.append("# FIELD CHANGES DETECTED")
            fixes.append("# Update field extraction logic:")

            for change in schema_changes["field_changes"]:
                if change["type"] == "type_changed":
                    fixes.append(
                        f"#  - Field '{change['path']}' type changed from {change['old_type']} to {change['new_type']}"
                    )
                elif change["type"] == "value_changed":
                    fixes.append(f"#  - Field '{change['path']}' value changed significantly")

        return fixes

    def _find_fixture(self, tool: str, action: str, word: str) -> Optional[Path]:
        """Find fixture file for tool/action/word combination."""
        tool_dir = self.fixture_dir / tool
        safe_word = "".join(c for c in word if c.isalnum() or c in ("-", "_")).lower()

        # Look for matching fixture files
        for pattern in [f"*_{action}_{safe_word}.json", f"*_{safe_word}.json"]:
            matches = list(tool_dir.glob(pattern))
            if matches:
                return matches[0]

        return None

    def _get_unified_output(self, tool: str, word: str) -> Optional[Dict[str, Any]]:
        """Get unified schema output (mock implementation for now)."""
        # In real implementation, this would call the API
        # For now, return a mock structure
        return {
            "word": word,
            "language": "lat"
            if tool in ["diogenes", "whitakers"]
            else "san"
            if tool in ["heritage", "cdsl"]
            else "grc",
            "senses": [
                {"pos": "noun", "definition": "mock definition", "examples": [], "citations": []}
            ],
            "source": tool,
        }

    def _analyze_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Analyze JSON structure recursively."""
        if isinstance(data, dict):
            return {
                "type": "object",
                "path": path,
                "keys": list(data.keys()),
                "nested": {
                    k: self._analyze_structure(v, f"{path}.{k}" if path else k)
                    for k, v in data.items()
                },
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "path": path,
                "length": len(data),
                "element_type": type(data[0]).__name__ if data else "unknown",
            }
        else:
            return {
                "type": type(data).__name__,
                "path": path,
                "value": str(data)[:100] if str(data) else "empty",
            }

    def _find_key_differences(self, raw: Any, unified: Any, path: str = "") -> List[Dict[str, Any]]:
        """Find key-level differences between raw and unified data."""
        differences = []

        if isinstance(raw, dict) and isinstance(unified, dict):
            raw_keys = set(raw.keys())
            unified_keys = set(unified.keys())

            for key in raw_keys - unified_keys:
                differences.append(
                    {
                        "type": "missing_in_unified",
                        "path": f"{path}.{key}" if path else key,
                        "raw_value": raw[key],
                    }
                )

            for key in unified_keys - raw_keys:
                differences.append(
                    {
                        "type": "extra_in_unified",
                        "path": f"{path}.{key}" if path else key,
                        "unified_value": unified[key],
                    }
                )

            for key in raw_keys & unified_keys:
                differences.extend(
                    self._find_key_differences(
                        raw[key], unified[key], f"{path}.{key}" if path else key
                    )
                )

        return differences

    def _find_missing_fields(self, raw: Any, unified: Any, path: str = "") -> List[str]:
        """Find fields present in unified but missing from raw."""
        missing = []

        if isinstance(raw, dict) and isinstance(unified, dict):
            for key, value in unified.items():
                current_path = f"{path}.{key}" if path else key

                if key not in raw:
                    missing.append(current_path)
                elif isinstance(value, dict):
                    missing.extend(self._find_missing_fields(raw[key], value, current_path))
                elif isinstance(value, list):
                    missing.extend(self._find_missing_fields(raw[key], value, current_path))

        return missing

    def _find_extra_fields(self, raw: Any, unified: Any, path: str = "") -> List[str]:
        """Find fields present in raw but missing from unified."""
        extra = []

        if isinstance(raw, dict) and isinstance(unified, dict):
            for key, value in raw.items():
                current_path = f"{path}.{key}" if path else key

                if key not in unified:
                    extra.append(current_path)
                elif isinstance(value, dict):
                    extra.extend(self._find_extra_fields(value, unified[key], current_path))
                elif isinstance(value, list):
                    extra.extend(self._find_extra_fields(value, unified[key], current_path))

        return extra

    def _generate_adapter_suggestions(self, raw: Any, unified: Any) -> List[str]:
        """Generate adapter improvement suggestions."""
        suggestions = []

        # Check for common patterns that need adapter handling
        if isinstance(raw, dict) and "error" in raw:
            suggestions.append("Raw output contains error - adapter should handle gracefully")

        if isinstance(raw, dict) and "chunks" in raw:
            suggestions.append(
                "Raw output uses 'chunks' structure - adapter should flatten to senses"
            )

        if isinstance(raw, dict) and "parsing" in raw:
            suggestions.append(
                "Raw output uses 'parsing' array - adapter should extract definitions"
            )

        return suggestions

    def _find_structural_changes(self, old: Any, new: Any, path: str = "") -> List[Dict[str, Any]]:
        """Find structural changes between old and new data."""
        changes = []

        if isinstance(old, dict) and isinstance(new, dict):
            old_keys = set(old.keys())
            new_keys = set(new.keys())

            # Added fields
            for key in new_keys - old_keys:
                changes.append(
                    {
                        "type": "field_added",
                        "path": f"{path}.{key}" if path else key,
                        "new_value": new[key],
                    }
                )

            # Removed fields
            for key in old_keys - new_keys:
                changes.append(
                    {
                        "type": "field_removed",
                        "path": f"{path}.{key}" if path else key,
                        "old_value": old[key],
                    }
                )

            # Recursively check common keys
            for key in old_keys & new_keys:
                changes.extend(
                    self._find_structural_changes(
                        old[key], new[key], f"{path}.{key}" if path else key
                    )
                )

        return changes

    def _find_field_changes(self, old: Any, new: Any, path: str = "") -> List[Dict[str, Any]]:
        """Find field-level changes between old and new data."""
        changes = []

        if isinstance(old, dict) and isinstance(new, dict):
            for key in old.keys() & new.keys():
                current_path = f"{path}.{key}" if path else key

                old_type = type(old[key]).__name__
                new_type = type(new[key]).__name__

                if old_type != new_type:
                    changes.append(
                        {
                            "type": "type_changed",
                            "path": current_path,
                            "old_type": old_type,
                            "new_type": new_type,
                        }
                    )
                elif isinstance(old[key], (str, int, float)) and old[key] != new[key]:
                    changes.append(
                        {
                            "type": "value_changed",
                            "path": current_path,
                            "old_value": old[key],
                            "new_value": new[key],
                        }
                    )

                # Recursively check nested structures
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    changes.extend(self._find_field_changes(old[key], new[key], current_path))

        return changes

    def _detect_breaking_changes(self, old: Any, new: Any) -> List[str]:
        """Detect breaking changes that would break adapter compatibility."""
        breaking = []

        # Check for major structural changes
        if isinstance(old, dict) and isinstance(new, dict):
            if set(old.keys()) != set(new.keys()):
                breaking.append("Major structural change - field names have changed")

        # Check for type changes in critical fields
        critical_fields = ["chunks", "solutions", "entries", "parsing"]
        for field in critical_fields:
            if isinstance(old, dict) and isinstance(new, dict):
                if field in old and field in new:
                    old_type = type(old[field]).__name__
                    new_type = type(new[field]).__name__
                    if old_type != new_type:
                        breaking.append(
                            f"Critical field '{field}' type changed from {old_type} to {new_type}"
                        )

        return breaking

    def _assess_adapter_impact(self, old: Any, new: Any) -> Dict[str, Any]:
        """Assess the impact of changes on existing adapters."""
        impact = {
            "high_impact": False,
            "medium_impact": False,
            "low_impact": False,
            "required_changes": [],
        }

        # Check for breaking changes
        breaking_changes = self._detect_breaking_changes(old, new)
        if breaking_changes:
            impact["high_impact"] = True
            impact["required_changes"].extend(breaking_changes)

        # Check for structural changes
        structural_changes = self._find_structural_changes(old, new)
        if structural_changes:
            impact["medium_impact"] = True
            impact["required_changes"].extend(
                [
                    change["path"]
                    for change in structural_changes
                    if change["type"] in ["field_added", "field_removed"]
                ]
            )

        # Check for field changes
        field_changes = self._find_field_changes(old, new)
        if field_changes:
            impact["low_impact"] = True
            impact["required_changes"].extend(
                [change["path"] for change in field_changes if change["type"] == "value_changed"]
            )

        return impact


@click.command()
@click.option("--tool", required=True, help="Backend tool name")
@click.option("--action", required=True, help="Action performed")
@click.option("--word", help="Specific word to compare")
@click.option("--generate-fixes", is_flag=True, help="Generate adapter fix suggestions")
@click.option("--output", type=click.Path(), help="Save comparison results to file")
def compare_tool_outputs(tool: str, action: str, word: str, generate_fixes: bool, output: str):
    """Compare raw tool outputs with unified schema outputs."""
    comparator = ToolOutputComparator()

    if word:
        # Compare specific word
        result = comparator.compare_raw_to_unified(tool, action, word)

        if "error" in result:
            click.echo(f"[red]Error: {result['error']}[/]")
            return

        # Display comparison
        _display_comparison(result, console)

        if generate_fixes:
            suggestions = comparator.generate_adapter_fixes(tool, result)
            click.echo("\n[yellow]Adapter Fix Suggestions:[/]")
            for suggestion in suggestions:
                click.echo(f"  {suggestion}")

        # Save results to file if requested
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"[green]Results saved to: {output}[/]")

    else:
        # Detect schema drift for tool/action
        drift = comparator.detect_schema_drift(tool, action)

        if "error" in drift:
            click.echo(f"[red]Error: {drift['error']}[/]")
            return

        # Display drift analysis
        _display_drift(drift, console)

        if generate_fixes:
            fixes = comparator.generate_adapter_fixes(tool, drift)
            click.echo("\n[yellow]Adapter Fix Suggestions:[/]")
            for fix in fixes:
                click.echo(f"  {fix}")

        # Save results to file if requested
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(drift, f, indent=2, ensure_ascii=False)
            click.echo(f"[green]Results saved to: {output}[/]")


def _display_comparison(result: Dict[str, Any], console: Console):
    """Display comparison results in a formatted way."""
    console.print(f"[bold]Comparison: {result['tool']}/{result['action']} - {result['word']}[/]")

    # Display key differences
    if result.get("key_differences"):
        console.print("\n[yellow]Key Differences:[/]")
        for diff in result["key_differences"]:
            console.print(f"  • {diff['type']}: {diff['path']}")

    # Display missing fields
    if result.get("missing_fields"):
        console.print("\n[red]Missing Fields in Raw Output:[/]")
        for field in result["missing_fields"]:
            console.print(f"  • {field}")

    # Display extra fields
    if result.get("extra_fields"):
        console.print("\n[blue]Extra Fields in Raw Output:[/]")
        for field in result["extra_fields"]:
            console.print(f"  • {field}")

    # Display adapter suggestions
    if result.get("adapter_suggestions"):
        console.print("\n[green]Adapter Suggestions:[/]")
        for suggestion in result["adapter_suggestions"]:
            console.print(f"  • {suggestion}")


def _display_drift(drift: Dict[str, Any], console: Console):
    """Display schema drift analysis."""
    console.print(f"[bold]Schema Drift Analysis: {drift['tool']}/{drift['action']}[/]")

    # Display file information
    console.print(f"\n[yellow]File Comparison:[/]")
    console.print(f"  Old: {drift['old_fixture']} ({drift['timestamp_old']})")
    console.print(f"  New: {drift['new_fixture']} ({drift['timestamp_new']})")

    # Display breaking changes
    if drift.get("breaking_changes"):
        console.print(f"\n[red]Breaking Changes:[/]")
        for change in drift["breaking_changes"]:
            console.print(f"  • {change}")

    # Display adapter impact
    impact = drift.get("adapter_impact", {})
    if impact:
        console.print(f"\n[yellow]Adapter Impact:[/]")
        if impact["high_impact"]:
            console.print("  🚨 High impact - immediate action required")
        if impact["medium_impact"]:
            console.print("  ⚠️  Medium impact - adapter updates needed")
        if impact["low_impact"]:
            console.print("  📝 Low impact - minor adjustments required")


if __name__ == "__main__":
    compare_tool_outputs()
