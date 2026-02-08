#!/usr/bin/env python3
"""
Guardrails to keep deprecated tools out of the codebase.
"""

from pathlib import Path


def test_no_sktlemmatizer_in_code():
    """Ensure the deprecated sktlemmatizer tool name does not creep back into code."""
    repo_root = Path(__file__).resolve().parents[1]
    forbidden = "sktlemmatizer"
    offending_files: list[str] = []

    for path in (repo_root / "src").rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if forbidden in content:
            offending_files.append(str(path))

    assert not offending_files, f"Forbidden term '{forbidden}' found in: {offending_files}"
