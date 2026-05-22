from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from click.testing import CliRunner

from langnet.cli import main
from langnet.foster_ossa.taxonomy import (
    audit_foster_taxonomy,
    render_taxonomy_audit_markdown,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _toc_row(source_ref: str, generated: dict[str, object]) -> dict[str, object]:
    return {
        "source_ref": source_ref,
        "scope": "toc-entry",
        "validation_status": "generated_valid",
        "generated_json": json.dumps(generated, ensure_ascii=False),
    }


def test_audit_foster_taxonomy_classifies_registered_and_candidate_terms() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        toc = base / "toc.jsonl"
        _write_jsonl(
            toc,
            [
                _toc_row(
                    "toc:1.6",
                    {
                        "source_ref": "toc:1.6",
                        "encounter_id": "1.6",
                        "title": "Functions",
                        "foster_terms": ["by-with-from-in", "of-possession"],
                        "traditional_terms": ["genitive", "ablative"],
                        "method_claims": ["Functions matter."],
                        "learner_actions": ["Use function names."],
                        "examples_present": [],
                        "not_supported_or_unclear": [],
                        "source_refs": ["page:69", "page:70"],
                    },
                )
            ],
        )

        audit = audit_foster_taxonomy(toc_summary_path=toc)

        by_term = {candidate["term"]: candidate for candidate in audit["candidates"]}
        assert by_term["genitive"]["classification"] == "existing_concept"
        assert by_term["genitive"]["matched_concept_ids"] == ["case.genitive"]
        assert by_term["by-with-from-in"]["classification"] == "direct_source_candidate"
        assert by_term["by-with-from-in"]["source_refs"] == ["page:69", "page:70"]


def test_audit_foster_taxonomy_matches_clear_foster_function_aliases() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        toc = base / "toc.jsonl"
        _write_jsonl(
            toc,
            [
                _toc_row(
                    "toc:1.6",
                    {
                        "source_ref": "toc:1.6",
                        "encounter_id": "1.6",
                        "title": "Functions",
                        "foster_terms": [
                            "function of-possession",
                            "function to-for-from",
                            "object forms",
                            "function of address",
                            "location function",
                            "function by-with-from-in",
                        ],
                        "traditional_terms": [],
                        "method_claims": [],
                        "learner_actions": [],
                        "examples_present": [],
                        "not_supported_or_unclear": [],
                        "source_refs": ["page:69"],
                    },
                )
            ],
        )

        audit = audit_foster_taxonomy(toc_summary_path=toc)

        by_term = {candidate["term"]: candidate for candidate in audit["candidates"]}
        assert by_term["function of-possession"]["classification"] == "existing_concept"
        assert by_term["function of-possession"]["matched_concept_ids"] == ["case.genitive"]
        assert by_term["function to-for-from"]["matched_concept_ids"] == ["case.dative"]
        assert by_term["object forms"]["matched_concept_ids"] == ["case.accusative"]
        assert by_term["function of address"]["matched_concept_ids"] == ["case.vocative"]
        assert by_term["location function"]["matched_concept_ids"] == ["case.locative"]
        assert by_term["function by-with-from-in"]["classification"] == "direct_source_candidate"
        assert by_term["function by-with-from-in"]["matched_concept_ids"] == []


def test_audit_foster_taxonomy_includes_platform_overlay_implications() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        toc = base / "toc.jsonl"
        experience = base / "experience.jsonl"
        _write_jsonl(toc, [])
        _write_jsonl(
            experience,
            [
                {
                    "source_ref": "experience:1",
                    "scope": "experience",
                    "validation_status": "generated_valid",
                    "generated_json": json.dumps(
                        {
                            "source_ref": "experience:1",
                            "experience": 1,
                            "toc_entry_count": 1,
                            "method_throughline": [],
                            "core_foster_terms": ["relative box"],
                            "traditional_bridge_terms": [],
                            "learner_sequence": [],
                            "platform_taxonomy_implications": [
                                "The platform should support clause boxes."
                            ],
                            "source_refs": ["toc:1.10", "page:86"],
                            "not_supported_or_unclear": [],
                        }
                    ),
                }
            ],
        )

        audit = audit_foster_taxonomy(toc_summary_path=toc, experience_summary_path=experience)

        classifications = {
            candidate["term"]: candidate["classification"] for candidate in audit["candidates"]
        }
        assert classifications["relative box"] == "method_supported_candidate"
        assert (
            classifications["The platform should support clause boxes."]
            == "platform_overlay_candidate"
        )


def test_render_taxonomy_audit_markdown_lists_candidates_and_refs() -> None:
    audit = {
        "summary": {"total_candidates": 1},
        "candidates": [
            {
                "term": "genitive",
                "classification": "existing_concept",
                "matched_concept_ids": ["case.genitive"],
                "source_refs": ["page:69"],
                "source_kinds": ["traditional_terms"],
                "occurrences": 1,
            }
        ],
    }

    markdown = render_taxonomy_audit_markdown(audit)

    assert "# Foster Ossa Taxonomy Audit" in markdown
    assert "genitive" in markdown
    assert "`case.genitive`" in markdown
    assert "`page:69`" in markdown


def test_foster_ossa_taxonomy_audit_cli_writes_markdown() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        toc = base / "toc.jsonl"
        output = base / "audit.md"
        _write_jsonl(
            toc,
            [
                _toc_row(
                    "toc:1.6",
                    {
                        "source_ref": "toc:1.6",
                        "encounter_id": "1.6",
                        "title": "Functions",
                        "foster_terms": ["of-possession"],
                        "traditional_terms": ["genitive"],
                        "method_claims": [],
                        "learner_actions": [],
                        "examples_present": [],
                        "not_supported_or_unclear": [],
                        "source_refs": ["page:69"],
                    },
                )
            ],
        )

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-taxonomy-audit",
                "--toc-summaries",
                str(toc),
                "--output",
                str(output),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "wrote:" in result.output
        assert "case.genitive" in output.read_text(encoding="utf-8")
