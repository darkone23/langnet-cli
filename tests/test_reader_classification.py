from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langnet.reader.classification import load_work_classifications

CANONICAL_POPULARITY_SCORE = 100
DISCOVERY_GLOBAL_POPULARITY_SCORE = 72
DISCOVERY_GROUP_POPULARITY_SCORE = 96


def test_load_work_classifications_reads_generated_csv_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "work_id,classification_category,classification_period,"
                    "classification_date_range,classification_authorship_status,"
                    "classification_popularity_score,classification_popularity_tier,"
                    "classification_scope,classification_scope_popularity_score,"
                    "classification_scope_popularity_tier,"
                    "classification_confidence,classification_notes,"
                    "classification_generator_models,classification_generator_run_id",
                    "urn:cts:greekLit:tlg0012.tlg002,epic,archaic,"
                    '"c. 8th-7th century BCE",traditional,100,canonical,'
                    "Epic Poetry,100,canonical,"
                    "high,Generated from classifier consensus,"
                    "deepseek/deepseek-v3.2;openai/gpt-oss-120b,run-2026-05-15",
                ]
            ),
            encoding="utf-8",
        )

        classifications = load_work_classifications(csv_path)

    assert len(classifications) == 1
    classification = classifications[0]
    assert classification.work_id == "urn:cts:greekLit:tlg0012.tlg002"
    assert classification.category == "epic"
    assert classification.period == "archaic"
    assert classification.date_range == "c. 8th-7th century BCE"
    assert classification.authorship_status == "traditional"
    assert classification.popularity_score == CANONICAL_POPULARITY_SCORE
    assert classification.popularity_tier == "canonical"
    assert classification.scope == "Epic Poetry"
    assert classification.scope_popularity_score == CANONICAL_POPULARITY_SCORE
    assert classification.scope_popularity_tier == "canonical"
    assert classification.confidence == "high"
    assert classification.note == "Generated from classifier consensus"
    assert classification.generator_models == "deepseek/deepseek-v3.2;openai/gpt-oss-120b"
    assert classification.generator_run_id == "run-2026-05-15"
    assert classification.source_file.endswith("classifications.csv")


def test_load_work_classifications_reads_discovery_group_and_tags() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "work_id,classification_discovery_group_id,"
                    "classification_discovery_tags,"
                    "classification_global_popularity_score,"
                    "classification_global_popularity_tier,"
                    "classification_group_popularity_score,"
                    "classification_group_popularity_tier,"
                    "classification_period,classification_date_range,"
                    "classification_authorship_status,"
                    "classification_confidence,classification_notes,"
                    "classification_generator_models,classification_generator_run_id",
                    "sanskrit_dcs:dcs_33,medicine,medicine|ayurveda|technical,"
                    "72,major,96,canonical,classical,"
                    '"c. 6th century CE",traditional,high,'
                    "Generated from strict discovery taxonomy,"
                    "deepseek/deepseek-v3.2,run-discovery",
                ]
            ),
            encoding="utf-8",
        )

        classifications = load_work_classifications(csv_path)

    classification = classifications[0]
    assert classification.discovery_group_id == "medicine"
    assert classification.discovery_tags == "medicine|ayurveda|technical"
    assert classification.global_popularity_score == DISCOVERY_GLOBAL_POPULARITY_SCORE
    assert classification.global_popularity_tier == "major"
    assert classification.group_popularity_score == DISCOVERY_GROUP_POPULARITY_SCORE
    assert classification.group_popularity_tier == "canonical"
    assert classification.category == "Medicine"
    assert classification.scope == "Medicine"
    assert classification.popularity_score == DISCOVERY_GLOBAL_POPULARITY_SCORE
    assert classification.scope_popularity_score == DISCOVERY_GROUP_POPULARITY_SCORE


def test_load_work_classifications_rejects_bad_popularity_score() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "work_id,classification_popularity_score",
                    "urn:cts:greekLit:tlg0012.tlg002,very popular",
                ]
            ),
            encoding="utf-8",
        )

        with unittest.TestCase().assertRaisesRegex(ValueError, "classification_popularity_score"):
            load_work_classifications(csv_path)


def test_load_work_classifications_rejects_bad_scope_popularity_score() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "work_id,classification_scope_popularity_score",
                    "urn:cts:greekLit:tlg0012.tlg002,very popular",
                ]
            ),
            encoding="utf-8",
        )

        with unittest.TestCase().assertRaisesRegex(
            ValueError, "classification_scope_popularity_score"
        ):
            load_work_classifications(csv_path)
