from __future__ import annotations

import csv
import tempfile
import threading
from pathlib import Path
from typing import Any

from langnet.reader.author_bulk_classification import (
    AuthorClassificationRunConfig,
    author_classification_batch_payload,
    classify_author_csv,
)

AUTHOR_FIXTURE_COUNT = 2


def test_author_classification_batch_payload_includes_allowed_values() -> None:
    payload = author_classification_batch_payload(
        rows=[
            {
                "author_id": "phi0690",
                "author_language": "lat",
                "author_display_name": "P. Vergilius Maro (Virgil)",
            }
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    assert payload["task"] == "reader_author_classification"
    assert any("work_title" in instruction for instruction in payload["instructions"])
    assert any("Anonymi" in instruction for instruction in payload["instructions"])
    assert payload["allowed_values"]["author_agent_kind"][0]["id"] == "person"
    assert any(
        item["id"] == "pseudonymous"
        for item in payload["allowed_values"]["author_historicity_status"]
    )


def test_classify_author_csv_writes_generated_rows_from_model_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "author-export.csv"
        output_csv = root / "author-generated.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_display_name,work_count,word_count",
                    "phi0690,lat,P. Vergilius Maro (Virgil),3,90000",
                ]
            ),
            encoding="utf-8",
        )

        classify_author_csv(
            config=AuthorClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=lambda _payload: (
                '{"rows":[{'
                '"author_id":"phi0690",'
                '"author_language":"lat",'
                '"author_canonical_name":"Virgil",'
                '"author_agent_kind":"person",'
                '"author_historicity_status":"historical",'
                '"author_period":"Augustan",'
                '"author_region":"Italy",'
                '"author_bio":"Roman poet of the Aeneid.",'
                '"author_prominence_score":100,'
                '"author_prominence_tier":"canonical",'
                '"author_confidence":"high",'
                '"author_notes":"Canonical Latin poet."'
                "}]}"
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["author_canonical_name"] == "Virgil"
    assert rows[0]["author_agent_kind"] == "person"
    assert rows[0]["author_region"] == "Italy"
    assert rows[0]["author_generator_models"] == "openai:test-model"
    assert rows[0]["author_generator_run_id"] == "run-test"


def test_classify_author_csv_normalizes_controlled_value_aliases() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "author-export.csv"
        output_csv = root / "author-generated.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_display_name,work_count,word_count",
                    "adisesa,san,Ādiśeṣa,1,100",
                ]
            ),
            encoding="utf-8",
        )

        classify_author_csv(
            config=AuthorClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=lambda _payload: (
                '{"rows":[{'
                '"author_id":"adisesa",'
                '"author_language":"san",'
                '"author_agent_kind":"mythic",'
                '"author_historicity_status":"mythological",'
                '"author_prominence_score":10,'
                '"author_prominence_tier":"niche",'
                '"author_confidence":"certain",'
                '"author_notes":"Mythic figure."'
                "}]}"
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["author_agent_kind"] == "person"
    assert rows[0]["author_historicity_status"] == "mythic"
    assert rows[0]["author_prominence_tier"] == "specialist"
    assert rows[0]["author_confidence"] == "medium"


def test_classify_author_csv_fills_missing_required_controlled_values() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "author-export.csv"
        output_csv = root / "author-generated.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_display_name,work_count,word_count",
                    "tlg0693,grc,Albinus,2,14756",
                ]
            ),
            encoding="utf-8",
        )

        classify_author_csv(
            config=AuthorClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=lambda _payload: (
                '{"rows":[{'
                '"author_id":"tlg0693",'
                '"author_language":"grc",'
                '"author_canonical_name":"Albinus",'
                '"author_notes":"Missing controlled fields."'
                "}]}"
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["author_agent_kind"] == "ambiguous"
    assert rows[0]["author_historicity_status"] == "uncertain"


def test_classify_author_csv_can_run_batches_concurrently() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "author-export.csv"
        output_csv = root / "author-generated.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_display_name",
                    "phi0690,lat,Virgil",
                    "civ0005,lat,English Bible (KJV or AV)",
                ]
            ),
            encoding="utf-8",
        )
        barrier = threading.Barrier(AUTHOR_FIXTURE_COUNT, timeout=2)

        def classify(payload: dict[str, Any]) -> str:
            barrier.wait()
            row = payload["rows"][0]
            kind = "person" if row["author_id"] == "phi0690" else "collective"
            return (
                '{"rows":[{'
                f'"author_id":"{row["author_id"]}",'
                f'"author_language":"{row["author_language"]}",'
                f'"author_agent_kind":"{kind}",'
                '"author_historicity_status":"historical",'
                '"author_prominence_score":50,'
                '"author_prominence_tier":"common",'
                '"author_confidence":"medium",'
                '"author_notes":"Generated concurrently."'
                "}]}"
            )

        summary = classify_author_csv(
            config=AuthorClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=1,
                concurrency=AUTHOR_FIXTURE_COUNT,
            ),
            classify=classify,
        )

    assert summary["generated_count"] == AUTHOR_FIXTURE_COUNT
    assert summary["concurrency"] == AUTHOR_FIXTURE_COUNT
