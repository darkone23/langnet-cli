"""
Fuzz testing module for generating and validating tool output fixtures.

This module provides automated testing capabilities for individual backend tools,
including fixture generation, schema validation, and comparison with unified outputs.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema
import requests
import structlog
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

logger = structlog.get_logger(__name__)
console = Console()


class ToolFuzzer:
    """Automated fuzz testing for backend tools."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.fixture_dir = Path("tests/fixtures/raw_tool_outputs")
        self.fixture_dir.mkdir(parents=True, exist_ok=True)

    def generate_fixtures(
        self,
        tool: str,
        action: str,
        word_list: list[str],
        lang: str | None = None,
        dict_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate fixtures for a tool with given word list.

        Args:
            tool: Backend tool name (diogenes, whitakers, etc.)
            action: Action to perform (search, parse, etc.)
            word_list: List of words to query
            lang: Language code (required for some tools)
            dict_name: Dictionary name (for heritage/cdsl)

        Returns:
            Dictionary with results and statistics
        """
        results: dict[str, Any] = {
            "tool": tool,
            "action": action,
            "total_words": len(word_list),
            "successful": 0,
            "failed": 0,
            "results": {},
            "errors": [],
        }

        console.print(f"[bold]Generating fixtures for {tool}/{action}[/]")
        console.print(f"Words: {', '.join(word_list)}")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Generating fixtures", total=len(word_list))

            for word in word_list:
                try:
                    # Generate fixture
                    fixture_data = self._generate_single_fixture(
                        tool, action, word, lang, dict_name
                    )

                    if fixture_data and "error" not in fixture_data:
                        results["successful"] += 1
                        results["results"][word] = fixture_data
                        console.print(f"[green]✓ {word}[/]")
                    else:
                        results["failed"] += 1
                        error_msg = (
                            fixture_data.get("error", "Unknown error")
                            if fixture_data
                            else "Unknown error"
                        )
                        results["errors"].append({"word": word, "error": error_msg})
                        console.print(f"[red]✗ {word}: {error_msg}[/]")

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"word": word, "error": str(e)})
                    console.print(f"[red]✗ {word}: {str(e)}[/]")

                progress.update(task, advance=1)

        # Save results summary
        summary_path = self.fixture_dir / f"{tool}_{action}_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        console.print("\n[bold]Results:[/]")
        console.print(f"  Total: {results['total_words']}")
        console.print(f"  Successful: {results['successful']}")
        console.print(f"  Failed: {results['failed']}")
        console.print(f"  Summary saved to: {summary_path}")

        return results

    def _generate_single_fixture(
        self,
        tool: str,
        action: str,
        word: str,
        lang: str | None = None,
        dict_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Generate a single fixture for a word."""
        try:
            # Build API URL
            url = f"{self.base_url}/api/tool/{tool}/{action}"
            params = {}

            if lang:
                params["lang"] = lang
            if dict_name:
                params["dict"] = dict_name
            params["query"] = word

            # Make API request
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Save fixture
            self._save_fixture(tool, action, lang, word, data)

            return data

        except requests.RequestException as e:
            logger.error(
                "fixture_generation_failed", tool=tool, action=action, word=word, error=str(e)
            )
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            logger.error(
                "fixture_generation_error", tool=tool, action=action, word=word, error=str(e)
            )
            return {"error": f"Generation failed: {str(e)}"}

    def _save_fixture(
        self, tool: str, action: str, lang: str | None, word: str, data: dict[str, Any]
    ):
        """Save fixture data to file."""
        # Create filename
        safe_word = "".join(c for c in word if c.isalnum() or c in ("-", "_")).lower()
        filename = f"{tool}_{action}"
        if lang:
            filename += f"_{lang}"
        filename += f"_{safe_word}.json"

        fixture_path = self.fixture_dir / tool / filename

        # Save data
        with open(fixture_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug("fixture_saved", path=str(fixture_path))

    def validate_fixtures(self, tool: str, action: str) -> dict[str, Any]:
        """Validate all fixtures for a tool against its schema.

        Args:
            tool: Backend tool name
            action: Action performed

        Returns:
            Validation results
        """
        schema_path = self.fixture_dir / tool / f"schema_{tool}.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        # Load schema
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

        # Find all fixtures for this tool/action
        tool_dir = self.fixture_dir / tool
        fixture_files = list(tool_dir.glob(f"*_{action}*.json"))

        results: dict[str, Any] = {
            "tool": tool,
            "action": action,
            "total_fixtures": len(fixture_files),
            "valid": 0,
            "invalid": 0,
            "validation_errors": [],
        }

        console.print(f"[bold]Validating {len(fixture_files)} fixtures for {tool}/{action}[/]")

        for fixture_path in fixture_files:
            try:
                # Load fixture
                with open(fixture_path, encoding="utf-8") as f:
                    fixture_data = json.load(f)

                # Validate against schema
                jsonschema.validate(instance=fixture_data, schema=schema)

                results["valid"] += 1
                console.print(f"[green]✓ {fixture_path.name}[/]")

            except jsonschema.ValidationError as e:
                results["invalid"] += 1
                error_info = {
                    "file": fixture_path.name,
                    "error": str(e.message),
                    "path": list(e.absolute_path) if e.absolute_path else [],
                }
                results["validation_errors"].append(error_info)
                console.print(f"[red]✗ {fixture_path.name}: {e.message}[/]")

            except Exception as e:
                results["invalid"] += 1
                error_info = {"file": fixture_path.name, "error": f"Validation failed: {str(e)}"}
                results["validation_errors"].append(error_info)
                console.print(f"[red]✗ {fixture_path.name}: {str(e)}[/]")

        # Save validation results
        validation_path = self.fixture_dir / f"{tool}_{action}_validation.json"
        with open(validation_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        console.print("\n[bold]Validation Results:[/]")
        console.print(f"  Total fixtures: {results['total_fixtures']}")
        console.print(f"  Valid: {results['valid']}")
        console.print(f"  Invalid: {results['invalid']}")
        if results["validation_errors"]:
            console.print(f"  Errors saved to: {validation_path}")

        return results

    def compare_with_schema(self, tool: str, action: str) -> dict[str, Any]:
        """Compare raw tool outputs with unified schema outputs.

        Args:
            tool: Backend tool name
            action: Action performed

        Returns:
            Comparison results
        """
        console.print(f"[bold]Comparing {tool}/{action} raw vs unified outputs[/]")

        # Get sample word (first valid fixture)
        tool_dir = self.fixture_dir / tool
        fixture_files = list(tool_dir.glob(f"*_{action}*.json"))

        if not fixture_files:
            return {"error": "No fixtures found"}

        # Use first fixture for comparison
        sample_fixture = fixture_files[0]
        with open(sample_fixture, encoding="utf-8") as f:
            raw_data = json.load(f)

        # Extract query from filename
        word = sample_fixture.stem.split(f"_{action}")[-1].split("_")[-1]

        # Get unified output via API
        try:
            unified_url = f"{self.base_url}/api/q"
            unified_params = {"l": "lat", "s": word}  # Default to Latin
            if tool == "diogenes" and "grc" in sample_fixture.name:
                unified_params["l"] = "grc"
            elif tool in {"heritage", "cdsl"}:
                unified_params["l"] = "san"

            response = requests.get(unified_url, params=unified_params, timeout=30)
            response.raise_for_status()
            unified_data = response.json()

        except Exception as e:
            return {"error": f"Failed to get unified output: {str(e)}"}

        # Compare structures
        comparison = {
            "tool": tool,
            "action": action,
            "word": word,
            "raw_structure": self._analyze_structure(raw_data),
            "unified_structure": self._analyze_structure(unified_data),
            "differences": self._find_differences(raw_data, unified_data),
        }

        # Save comparison
        comparison_path = self.fixture_dir / f"{tool}_{action}_comparison.json"
        with open(comparison_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)

        console.print(f"Comparison saved to: {comparison_path}")

        return comparison

    def _analyze_structure(self, data: Any) -> dict[str, Any]:
        """Analyze the structure of JSON data."""
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys()),
                "nested": {k: self._analyze_structure(v) for k, v in data.items()},
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "element_type": type(data[0]).__name__ if data else None,
            }
        else:
            return {"type": type(data).__name__, "value": str(data)[:100]}

    def _find_differences(
        self, raw_data: Any, unified_data: Any, path: str = ""
    ) -> list[dict[str, Any]]:
        """Find differences between raw and unified data structures."""
        differences = []

        if type(raw_data) is not type(unified_data):
            differences.append(
                {
                    "path": path,
                    "raw_type": type(raw_data).__name__,
                    "unified_type": type(unified_data).__name__,
                    "description": "Type mismatch",
                }
            )
            return differences

        if isinstance(raw_data, dict):
            raw_keys = set(raw_data.keys())
            unified_keys = set(unified_data.keys())

            # Keys only in raw data
            for key in raw_keys - unified_keys:
                differences.append(
                    {
                        "path": f"{path}.{key}" if path else key,
                        "raw_key": key,
                        "unified_key": None,
                        "description": "Key missing in unified output",
                    }
                )

            # Keys only in unified data
            for key in unified_keys - raw_keys:
                differences.append(
                    {
                        "path": f"{path}.{key}" if path else key,
                        "raw_key": None,
                        "unified_key": key,
                        "description": "Key missing in raw output",
                    }
                )

            # Recursively check common keys
            for key in raw_keys & unified_keys:
                differences.extend(
                    self._find_differences(
                        raw_data[key], unified_data[key], f"{path}.{key}" if path else key
                    )
                )

        elif isinstance(raw_data, list):
            if len(raw_data) != len(unified_data):
                differences.append(
                    {
                        "path": path,
                        "raw_length": len(raw_data),
                        "unified_length": len(unified_data),
                        "description": "Length mismatch",
                    }
                )
            else:
                for i, (raw_item, unified_item) in enumerate(zip(raw_data, unified_data)):
                    differences.extend(
                        self._find_differences(raw_item, unified_item, f"{path}[{i}]")
                    )

        return differences


def get_test_word_lists() -> dict[str, list[str]]:
    """Get predefined test word lists for each language."""
    return {
        "latin": ["lupus", "arma", "vir", "rosa", "amicus"],
        "greek": ["logos", "anthropos", "polis", "theos", "bios"],
        "sanskrit": ["agni", "yoga", "karma", "dharma", "atman"],
    }


def run_fuzz_testing(  # noqa: PLR0913
    tool: str | None = None,
    action: str | None = None,
    words: list[str] | None = None,
    validate: bool = False,
    compare: bool = False,
    base_url: str = "http://localhost:8000",
):
    """Run fuzz testing with specified parameters.

    Args:
        tool: Specific tool to test (None for all)
        action: Specific action to test (None for all)
        words: Specific words to test (None for defaults)
        validate: Whether to validate fixtures
        compare: Whether to compare with unified schema
        base_url: Base URL for API calls
    """
    fuzzer = ToolFuzzer(base_url)
    word_lists = get_test_word_lists()

    test_words = {None: words} if words else word_lists

    # Test each tool/action combination
    test_matrix = [
        ("diogenes", "search", "latin"),
        ("diogenes", "search", "greek"),
        ("whitakers", "analyze", None),
        ("heritage", "morphology", "sanskrit"),
        ("cdsl", "lookup", "sanskrit"),
        ("cltk", "morphology", "latin"),
        ("cltk", "morphology", "greek"),
        ("cltk", "morphology", "sanskrit"),
    ]

    if tool:
        test_matrix = [(t, a, lang) for t, a, lang in test_matrix if t == tool]
    if action:
        test_matrix = [(t, a, lang) for t, a, lang in test_matrix if a == action]

    for tool_name, action_name, lang in test_matrix:
        if tool_name in test_words:
            words_to_test = test_words[tool_name]
        else:
            words_to_test = []

            # Generate fixtures
            fuzzer.generate_fixtures(
                tool=tool_name,
                action=action_name,
                word_list=words_to_test,
                lang=lang,
                dict_name="mw" if tool_name in {"heritage", "cdsl"} else None,
            )

            # Validate fixtures
            if validate:
                fuzzer.validate_fixtures(tool_name, action_name)

            # Compare with unified schema
            if compare:
                fuzzer.compare_with_schema(tool_name, action_name)


if __name__ == "__main__":
    # Example usage
    run_fuzz_testing(
        tool="diogenes", action="search", words=["lupus", "vir"], validate=True, compare=True
    )
