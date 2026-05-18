from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langnet.reader.author_classification import load_author_classifications

PROMINENCE_SCORE = 92


def test_load_author_classifications_reads_generated_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "author-classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_canonical_name,"
                    "author_agent_kind,author_historicity_status,"
                    "author_period,author_date_range,author_region,"
                    "author_cultural_context,author_bio,"
                    "author_prominence_score,author_prominence_tier,"
                    "author_confidence,author_notes,"
                    "author_generator_models,author_generator_run_id",
                    "tlg0001,grc,Homer,person,legendary,archaic,"
                    '"c. 8th-7th century BCE",Ionia,Greek epic,'
                    '"Traditional poet of the Iliad and Odyssey.",'
                    "92,canonical,high,Traditional epic poet,model-a,run-1",
                ]
            ),
            encoding="utf-8",
        )

        classifications = load_author_classifications(csv_path)

    assert len(classifications) == 1
    classification = classifications[0]
    assert classification.author_id == "tlg0001"
    assert classification.language == "grc"
    assert classification.canonical_name == "Homer"
    assert classification.agent_kind == "person"
    assert classification.historicity_status == "legendary"
    assert classification.period == "archaic"
    assert classification.date_range == "c. 8th-7th century BCE"
    assert classification.region == "Ionia"
    assert classification.cultural_context == "Greek epic"
    assert classification.bio == "Traditional poet of the Iliad and Odyssey."
    assert classification.prominence_score == PROMINENCE_SCORE
    assert classification.prominence_tier == "canonical"
    assert classification.confidence == "high"
    assert classification.note == "Traditional epic poet"
    assert classification.generator_models == "model-a"
    assert classification.generator_run_id == "run-1"
    assert classification.source_file.endswith("author-classifications.csv")


def test_load_author_classifications_rejects_unknown_agent_kind() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "author-classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_agent_kind,"
                    "author_historicity_status,author_prominence_score",
                    "acts,grc,text,not_applicable,10",
                ]
            ),
            encoding="utf-8",
        )

        with unittest.TestCase().assertRaisesRegex(ValueError, "author_agent_kind"):
            load_author_classifications(csv_path)


def test_load_author_classifications_rejects_bad_prominence_score() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "author-classifications.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_agent_kind,"
                    "author_historicity_status,author_prominence_score",
                    "acts,grc,work_title,not_applicable,very",
                ]
            ),
            encoding="utf-8",
        )

        with unittest.TestCase().assertRaisesRegex(ValueError, "author_prominence_score"):
            load_author_classifications(csv_path)
