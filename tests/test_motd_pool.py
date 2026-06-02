from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from langnet.cli import main
from langnet.motd_pool import (
    MotdPoolCard,
    build_motd_pool,
    cards_from_word_of_day_payload,
    export_motd_pool_snapshot,
    load_motd_candidate_json,
    motd_candidate_set_from_items,
    restore_motd_pool_snapshot,
    sample_motd_pool,
    validate_motd_pool,
)
from langnet.reduction.models import ReductionResult, SenseBucket, WitnessSenseUnit

EXPECTED_ALL_LANGUAGE_MOTD_COUNT = 3


def _card(language: str, query: str, *, rank: int = 1) -> MotdPoolCard:
    return MotdPoolCard(
        language=language,
        query=query,
        level="beginner",
        didactic_score=90 - rank,
        didactic_rationale=f"{query} is useful for early reading.",
        item={
            "language": language,
            "query": query,
            "display": query,
            "canonical_name": query,
            "summary": "source-backed learner gloss",
            "learner_note": "Notice how this word behaves in context.",
            "recommended_request": {
                "language": language,
                "q": query,
                "dictionary": "all",
                "translation": "cache",
                "backend": "cli",
            },
            "ui": {
                "badge": language.upper(),
                "href_query": f"language={language}&q={query}",
                "short_gloss": "source-backed learner gloss",
            },
        },
        source="fixture",
        source_ref=f"fixture:{language}:{query}",
    )


def _reduction(language: str, query: str) -> ReductionResult:
    glosses = {
        "san": "fire; sacrificial fire",
        "grc": "word; speech; account; reason",
        "lat": "love; like",
    }
    gloss = glosses.get(language, "learner gloss")
    witness = WitnessSenseUnit(
        wsu_id=f"wsu:{language}:{query}",
        lexeme_anchor=f"lex:{query}",
        sense_anchor=f"sense:lex:{query}#1",
        gloss=gloss,
        normalized_gloss=gloss,
        source_tool="fixture",
        claim_id="claim-fixture",
        source_triple_subject=f"lex:{query}",
        evidence={
            "source_tool": "fixture",
            "source_ref": f"fixture:{language}:{query}",
            "source_entry": {
                "source_ref": f"fixture:{language}:{query}",
                "term": query,
                "source_text": gloss,
            },
        },
    )
    return ReductionResult(
        query=query,
        language=language,
        lexeme_anchors=[f"lex:{query}"],
        buckets=[
            SenseBucket(
                bucket_id=f"bucket:{language}:{query}",
                normalized_gloss=gloss,
                display_gloss=gloss,
                witnesses=[witness],
                confidence_label="single-witness",
            )
        ],
    )


class MotdPoolTest(unittest.TestCase):
    def test_motd_pool_group_without_subcommand_samples_default_pool(self) -> None:
        result = CliRunner().invoke(main, ["motd-pool"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("Usage:", result.output)
        self.assertNotIn("Traceback", result.output)

    def test_databuild_motd_pool_defaults_to_prod_llm_profile(self) -> None:
        result = CliRunner().invoke(main, ["databuild", "motd-pool", "--help"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("[default: prod]", result.output)
        self.assertIn("prod => llm", result.output)
        self.assertIn("smoke => curated", result.output)
        self.assertIn("candidate-json", result.output)
        self.assertIn("uses a reviewed", result.output)
        self.assertIn("LLM-curated JSON file", result.output)

    def test_databuild_motd_pool_auto_falls_back_to_curated_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "motd_pool.duckdb"
            with (
                patch("langnet.cli._word_of_day_candidate_pools", return_value=None),
                patch(
                    "langnet.cli._word_of_day_probe_reduction",
                    side_effect=lambda **kwargs: _reduction(kwargs["language"], kwargs["text"]),
                ),
            ):
                result = CliRunner().invoke(
                    main,
                    [
                        "databuild",
                        "motd-pool",
                        "--candidate-source",
                        "auto",
                        "--output",
                        str(db_path),
                        "--per-language",
                        "1",
                        "--timeout-ms",
                        "1000",
                        "--output-json",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["inserted"], EXPECTED_ALL_LANGUAGE_MOTD_COUNT)
        self.assertEqual(payload["language_counts"], {"grc": 1, "lat": 1, "san": 1})

    def test_builds_validates_and_samples_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "motd_pool.duckdb"
            build_motd_pool(
                db_path,
                [
                    _card("san", "agni", rank=1),
                    _card("lat", "amo", rank=1),
                    _card("lat", "rex", rank=2),
                    _card("grc", "logos", rank=1),
                ],
                replace=True,
            )

            validation = validate_motd_pool(db_path, per_language=1)
            self.assertIs(validation["ok"], True)
            self.assertEqual(validation["language_counts"], {"grc": 1, "lat": 2, "san": 1})

            first = sample_motd_pool(db_path, language="lat", count=1, seed="daily")
            second = sample_motd_pool(db_path, language="lat", count=1, seed="daily")
            self.assertEqual(first["schema_version"], "langnet.word_of_day.v1")
            self.assertEqual(
                [item["query"] for item in first["items"]],
                [item["query"] for item in second["items"]],
            )
            self.assertEqual(first["generator"]["mode"], "precomputed-pool")

    def test_sample_cli_returns_word_of_day_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "motd_pool.duckdb"
            build_motd_pool(
                db_path,
                [_card("san", "agni"), _card("grc", "logos"), _card("lat", "amo")],
                replace=True,
            )

            result = CliRunner().invoke(
                main,
                [
                    "motd-pool",
                    "sample",
                    "--db",
                    str(db_path),
                    "--language",
                    "all",
                    "--count",
                    "3",
                    "--seed",
                    "daily",
                    "--output",
                    "json",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            payload = json.loads(result.output)
            self.assertEqual(payload["schema_version"], "langnet.word_of_day.v1")
            self.assertEqual(len(payload["items"]), EXPECTED_ALL_LANGUAGE_MOTD_COUNT)
            self.assertEqual({item["language"] for item in payload["items"]}, {"grc", "lat", "san"})

    def test_exports_and_restores_reviewed_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "motd_pool.duckdb"
            snapshot_path = temp_path / "motd_pool_snapshot.json"
            restored_path = temp_path / "restored.duckdb"
            build_motd_pool(
                db_path,
                [_card("san", "agni"), _card("grc", "logos"), _card("lat", "amo")],
                replace=True,
            )

            export_payload = export_motd_pool_snapshot(db_path, snapshot_path)
            restore_payload = restore_motd_pool_snapshot(snapshot_path, restored_path)
            sample = sample_motd_pool(restored_path, language="all", count=3, seed="daily")

            self.assertEqual(export_payload["card_count"], EXPECTED_ALL_LANGUAGE_MOTD_COUNT)
            self.assertEqual(restore_payload["restored"], EXPECTED_ALL_LANGUAGE_MOTD_COUNT)
            self.assertEqual({item["query"] for item in sample["items"]}, {"agni", "logos", "amo"})

    def test_restore_snapshot_rejects_mismatched_card_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            snapshot_path = temp_path / "motd_pool_snapshot.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "schema_version": "langnet.motd_pool.snapshot.v1",
                        "card_count": 1,
                        "cards": [
                            {
                                "card_key": "lat:amo",
                                "language": "lat",
                                "query": "rex",
                                "level": "beginner",
                                "didactic_score": 80,
                                "didactic_rationale": "fixture",
                                "item": {"language": "lat", "query": "rex"},
                                "source": "fixture",
                                "source_ref": "fixture",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "card_key"):
                restore_motd_pool_snapshot(snapshot_path, temp_path / "restored.duckdb")

    def test_snapshot_cli_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "motd_pool.duckdb"
            snapshot_path = temp_path / "motd_pool_snapshot.json"
            restored_path = temp_path / "restored.duckdb"
            build_motd_pool(
                db_path,
                [_card("san", "agni"), _card("grc", "logos"), _card("lat", "amo")],
                replace=True,
            )

            export_result = CliRunner().invoke(
                main,
                [
                    "motd-pool",
                    "export",
                    "--db",
                    str(db_path),
                    "--path",
                    str(snapshot_path),
                    "--output",
                    "json",
                ],
            )
            restore_result = CliRunner().invoke(
                main,
                [
                    "motd-pool",
                    "restore",
                    "--path",
                    str(snapshot_path),
                    "--db",
                    str(restored_path),
                    "--output",
                    "json",
                ],
            )

            self.assertEqual(export_result.exit_code, 0, export_result.output)
            self.assertEqual(restore_result.exit_code, 0, restore_result.output)
            self.assertEqual(json.loads(export_result.output)["card_count"], 3)
            self.assertEqual(json.loads(restore_result.output)["restored"], 3)
            self.assertTrue(validate_motd_pool(restored_path, per_language=1)["ok"])

    def test_sample_missing_pool_returns_empty_contract_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "missing.duckdb"

            payload = sample_motd_pool(db_path, language="all", count=3, seed="daily")

            self.assertEqual(payload["schema_version"], "langnet.word_of_day.v1")
            self.assertEqual(payload["items"], [])
            self.assertIn("does not exist", payload["warnings"][0]["message"])

    def test_sample_cli_missing_pool_returns_json_contract_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "missing.duckdb"

            result = CliRunner().invoke(
                main,
                [
                    "motd-pool",
                    "sample",
                    "--db",
                    str(db_path),
                    "--language",
                    "all",
                    "--count",
                    "3",
                    "--seed",
                    "daily",
                    "--output",
                    "json",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertNotIn("Traceback", result.output)
            payload = json.loads(result.output)
            self.assertEqual(payload["items"], [])
            self.assertIn("does not exist", payload["warnings"][0]["message"])

    def test_load_candidate_json_preserves_llm_didactic_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_path = Path(temp_dir) / "llm-candidates.json"
            candidate_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "language": "lat",
                                "query": "amo",
                                "difficulty": "beginner",
                                "summary": "love; like",
                                "didactic_score": 97,
                                "didactic_rationale": "High-frequency verb with clear paradigms.",
                            },
                            {
                                "language": "grc",
                                "query": "logos",
                                "difficulty": "beginner",
                                "summary_hint": "word; account; reason",
                                "didactic_score": 95,
                                "didactic_rationale": "Culturally central semantic range.",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            candidate_set = load_motd_candidate_json(candidate_path)

            self.assertEqual([candidate.query for candidate in candidate_set.pools["lat"]], ["amo"])
            self.assertEqual(candidate_set.pools["lat"][0].summary_hint, "love; like")
            self.assertEqual(candidate_set.pools["lat"][0].didactic_score, 97)
            self.assertEqual(
                candidate_set.pools["lat"][0].didactic_rationale,
                "High-frequency verb with clear paradigms.",
            )
            self.assertEqual(candidate_set.metadata["lat:amo"].didactic_score, 97)
            self.assertIn("High-frequency", candidate_set.metadata["lat:amo"].didactic_rationale)

    def test_cards_from_word_of_day_payload_uses_didactic_metadata(self) -> None:
        candidate_set = motd_candidate_set_from_items(
            [
                {
                    "language": "lat",
                    "query": "amo",
                    "difficulty": "beginner",
                    "summary": "love",
                    "didactic_score": 99,
                    "didactic_rationale": "Core first-conjugation verb.",
                }
            ],
            source_ref="fixture-candidates.json",
        )
        payload = {
            "items": [
                {
                    "language": "lat",
                    "query": "amo",
                    "display": "amo",
                    "canonical_name": "amo",
                    "summary": "love",
                    "learner_note": "Watch the first person singular ending.",
                }
            ]
        }

        cards = cards_from_word_of_day_payload(
            payload,
            candidate_metadata=candidate_set.metadata,
            source="llm-curated-json",
            source_ref="fixture-candidates.json",
        )

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].didactic_score, 99)
        self.assertEqual(cards[0].didactic_rationale, "Core first-conjugation verb.")
