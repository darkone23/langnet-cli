"""
Tool output comparison and analysis utilities.

This module provides tools for comparing raw tool outputs with unified schema outputs,
detecting schema changes, and generating adapter fixes.
"""

import difflib
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TypedDict, cast

import click
import structlog
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from langnet.types import JSONMapping, JSONValue

logger = structlog.get_logger(__name__)
console = Console()


class AdapterImpact(TypedDict):
    high_impact: bool
    medium_impact: bool
    low_impact: bool
    required_changes: list[str]


class SchemaDriftError(TypedDict):
    error: str


class SchemaDrift(TypedDict):
    tool: str
    action: str
    old_fixture: str
    new_fixture: str
    timestamp_old: float
    timestamp_new: float
    structural_changes: list[Mapping[str, Any]]
    field_changes: list[Mapping[str, Any]]
    breaking_changes: list[str]
    adapter_impact: AdapterImpact


class ToolOutputComparator:
    """Compare raw tool outputs with unified schema outputs."""

    def __init__(self, fixture_dir: str = "tests/fixtures/raw_tool_outputs"):
        self.fixture_dir = Path(fixture_dir)

    def compare_raw_to_unified(self, tool: str, action: str, word: str) -> JSONMapping:
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

    def detect_schema_drift(self, tool: str, action: str) -> SchemaDrift | SchemaDriftError:
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
            error_result: SchemaDriftError = {"error": "Need at least 2 fixture versions to detect drift"}
            return error_result

        # Sort by modification time to get old and new versions
        fixture_files.sort(key=lambda x: x.stat().st_mtime)
        old_fixture = fixture_files[0]
        new_fixture = fixture_files[-1]

        with open(old_fixture, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        with open(new_fixture, "r", encoding="utf-8") as f:
            new_data = json.load(f)

        drift: SchemaDrift = {
            "tool": tool,
            "action": action,
            "old_fixture": old_fixture.name,
            "new_fixture": new_fixture.name,
            "timestamp_old": old_fixture.stat().st_mtime,
            "timestamp_new": new_fixture.stat().st_mtime,
            "structural_changes": _as_list_of_mappings(self._find_structural_changes(old_data, new_data)),
            "field_changes": _as_list_of_mappings(self._find_field_changes(old_data, new_data)),
            "breaking_changes": self._detect_breaking_changes(old_data, new_data),
            "adapter_impact": self._assess_adapter_impact(old_data, new_data),
        }

        return drift

    def generate_adapter_fixes(
        self, tool: str, schema_changes: JSONMapping | SchemaDrift
    ) -> list[str]:
        """Generate code suggestions for adapter fixes based on schema changes.

        Args:
            tool: Backend tool name
            schema_changes: Schema change detection results

        Returns:
            List of code suggestions
        """
        fixes = []

        breaking_changes = _as_list_of_str(schema_changes.get("breaking_changes"))  # type: ignore[arg-type]

        if breaking_changes:
            fixes.append("# BREAKING DETECTED - Adapter needs major update")
            fixes.append("# Consider implementing a new adapter version")

            for change in breaking_changes:
                fixes.append(f"# Breaking change: {change}")

        structural_changes = _as_list_of_mappings(schema_changes.get("structural_changes"))  # type: ignore[arg-type]

        if structural_changes:
            fixes.append("# STRUCTURAL CHANGES DETECTED")
            fixes.append("# Update adapter mapping logic:")

            for change in structural_changes:
                change_type = change.get("type")
                if change_type == "field_renamed":
                    fixes.append(
                        f"#  - Field '{change.get('old_path')}' renamed to '{change.get('new_path')}'"
                    )
                elif change_type == "field_added":
                    fixes.append(f"#  - New field '{change.get('path')}' added")
                elif change_type == "field_removed":
                    fixes.append(f"#  - Field '{change.get('path')}' removed")

        field_changes = _as_list_of_mappings(schema_changes.get("field_changes"))  # type: ignore[arg-type]

        if field_changes:
            fixes.append("# FIELD CHANGES DETECTED")
            fixes.append("# Update field extraction logic:")

            for change in field_changes:
                change_type = change.get("type")
                if change_type == "type_changed":
                    fixes.append(
                        f"#  - Field '{change.get('path')}' type changed from {change.get('old_type')} to {change.get('new_type')}"
                    )
                elif change_type == "value_changed":
                    fixes.append(
                        f"#  - Field '{change.get('path')}' value changed significantly"
                    )

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

    def _get_unified_output(self, tool: str, word: str) -> Optional[JSONMapping]:
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

    def _analyze_structure(self, data: JSONValue, path: str = "") -> JSONMapping:
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

    def _find_key_differences(
        self, raw: JSONValue, unified: JSONValue, path: str = ""
    ) -> list[JSONMapping]:
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

    def _find_missing_fields(self, raw: JSONValue, unified: JSONValue, path: str = "") -> list[str]:
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

    def _find_extra_fields(self, raw: JSONValue, unified: JSONValue, path: str = "") -> list[str]:
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

    def _generate_adapter_suggestions(self, raw: JSONValue, unified: JSONValue) -> list[str]:
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

    def _find_structural_changes(
        self, old: JSONValue, new: JSONValue, path: str = ""
    ) -> list[JSONMapping]:
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

    def _find_field_changes(
        self, old: JSONValue, new: JSONValue, path: str = ""
    ) -> list[JSONMapping]:
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

    def _detect_breaking_changes(self, old: JSONValue, new: JSONValue) -> list[str]:
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

    def _assess_adapter_impact(self, old: JSONValue, new: JSONValue) -> AdapterImpact:
        """Assess the impact of changes on existing adapters."""
        impact: AdapterImpact = {
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
                    str(change.get("path", ""))
                    for change in structural_changes
                    if change["type"] in ["field_added", "field_removed"]
                ]
            )

        # Check for field changes
        field_changes = self._find_field_changes(old, new)
        if field_changes:
            impact["low_impact"] = True
            impact["required_changes"].extend(
                [
                    str(change.get("path", ""))
                    for change in field_changes
                    if change["type"] == "value_changed"
                ]
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

        if isinstance(drift, dict) and "error" in drift:
            click.echo(f"[red]Error: {drift['error']}[/]")
            return

        if not isinstance(drift, dict):
            click.echo("[red]Unexpected drift result[/]")
            return

        if "breaking_changes" not in drift or "structural_changes" not in drift or "field_changes" not in drift:
            click.echo("[red]Schema drift payload missing expected keys[/]")
            return

        drift_payload: SchemaDrift = cast(SchemaDrift, drift)

        # Display drift analysis
        _display_drift(drift_payload, console)

        if generate_fixes:
            fixes = comparator.generate_adapter_fixes(tool, drift_payload)
            click.echo("\n[yellow]Adapter Fix Suggestions:[/]")
            for fix in fixes:
                click.echo(f"  {fix}")

        # Save results to file if requested
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(drift_payload, f, indent=2, ensure_ascii=False)
            click.echo(f"[green]Results saved to: {output}[/]")


def _display_comparison(result: JSONMapping, console: Console):
    """Display comparison results in a formatted way."""
    tool = str(result.get("tool", ""))
    action = str(result.get("action", ""))
    word = str(result.get("word", ""))
    console.print(f"[bold]Comparison: {tool}/{action} - {word}[/]")

    # Display key differences
    key_differences = _as_list_of_mappings(result.get("key_differences"))
    if key_differences:
        console.print("\n[yellow]Key Differences:[/]")
        for diff in key_differences:
            diff_type = diff.get("type", "unknown")
            path = diff.get("path", "")
            console.print(f"  • {diff_type}: {path}")

    # Display missing fields
    missing_fields = _as_list_of_str(result.get("missing_fields"))
    if missing_fields:
        console.print("\n[red]Missing Fields in Raw Output:[/]")
        for field in missing_fields:
            console.print(f"  • {field}")

    # Display extra fields
    extra_fields = _as_list_of_str(result.get("extra_fields"))
    if extra_fields:
        console.print("\n[blue]Extra Fields in Raw Output:[/]")
        for field in extra_fields:
            console.print(f"  • {field}")

    # Display adapter suggestions
    adapter_suggestions = _as_list_of_str(result.get("adapter_suggestions"))
    if adapter_suggestions:
        console.print("\n[green]Adapter Suggestions:[/]")
        for suggestion in adapter_suggestions:
            console.print(f"  • {suggestion}")


def _display_drift(drift: SchemaDrift | SchemaDriftError, console: Console):
    """Display schema drift analysis."""
    if isinstance(drift, dict) and "error" in drift:
        console.print(f"[red]Error: {drift['error']}[/]")
        return

    tool = str(drift.get("tool", ""))
    action = str(drift.get("action", ""))
    console.print(f"[bold]Schema Drift Analysis: {tool}/{action}[/]")

    # Display file information
    console.print(f"\n[yellow]File Comparison:[/]")
    console.print(f"  Old: {drift.get('old_fixture')} ({drift.get('timestamp_old')})")
    console.print(f"  New: {drift.get('new_fixture')} ({drift.get('timestamp_new')})")

    # Display breaking changes
    breaking_changes = _as_list_of_str(drift.get("breaking_changes"))
    if breaking_changes:
        console.print(f"\n[red]Breaking Changes:[/]")
        for change in breaking_changes:
            console.print(f"  • {change}")

    # Display adapter impact
    impact = drift.get("adapter_impact", {})
    if isinstance(impact, dict):
        console.print(f"\n[yellow]Adapter Impact:[/]")
        if bool(impact.get("high_impact")):
            console.print("  🚨 High impact - immediate action required")
        if bool(impact.get("medium_impact")):
            console.print("  ⚠️  Medium impact - adapter updates needed")
        if bool(impact.get("low_impact")):
            console.print("  📝 Low impact - minor adjustments required")


def _as_list_of_str(value: JSONValue | object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, (str, int, float, bool))]
    return []


def _as_list_of_mappings(value: JSONValue | object) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        return [cast(Mapping[str, Any], item) for item in value if isinstance(item, Mapping)]
    return []


if __name__ == "__main__":
    compare_tool_outputs()
