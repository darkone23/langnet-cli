from __future__ import annotations

import csv
import tempfile
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any

from langnet.reader.bulk_classification import (
    DEFAULT_CLASSIFICATION_SHUFFLE_SEED,
    ClassificationEscalationConfig,
    ClassificationRunConfig,
    classification_batch_payload,
    classify_work_csv,
    export_classification_escalation_csv,
    load_classification_input_rows,
    select_classification_escalation_rows,
)

CANONICAL_POPULARITY_SCORE = 100
ESCALATION_SELECTED_COUNT = 1
PARTIAL_BATCH_SPLIT_THRESHOLD = 2
FOUR_WORK_COUNT = 4
RETRIED_BATCH_COUNT = 3
TWO_WORK_COUNT = 2


def test_classify_work_csv_writes_generated_rows_from_model_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author,author_id,word_count",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer,"
                    "urn:cts:greekLit:tlg0012,121109",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            return (
                '{"rows":[{'
                '"work_id":"urn:cts:greekLit:tlg0012.tlg002",'
                '"classification_category":"epic",'
                '"classification_period":"archaic",'
                '"classification_date_range":"c. 8th-7th century BCE",'
                '"classification_authorship_status":"traditional",'
                '"classification_popularity_score":100,'
                '"classification_popularity_tier":"canonical",'
                '"classification_confidence":"high",'
                '"classification_notes":"Generated from bulk classifier consensus"'
                "}]}"
            )

        summary = classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )

        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary == {
        "input_count": 1,
        "generated_count": 1,
        "batch_count": 1,
        "shuffle_seed": DEFAULT_CLASSIFICATION_SHUFFLE_SEED,
        "batch_order": "stratified",
        "output_profile": "slim",
        "output_csv": str(output_csv),
        "model": "openai:test-model",
        "run_id": "run-test",
        "concurrency": 1,
    }
    assert rows[0]["work_id"] == "urn:cts:greekLit:tlg0012.tlg002"
    assert rows[0]["title"] == "Odyssey"
    assert rows[0]["classification_category"] == "epic"
    assert rows[0]["classification_popularity_score"] == str(CANONICAL_POPULARITY_SCORE)
    assert rows[0]["classification_generator_models"] == "openai:test-model"
    assert rows[0]["classification_generator_run_id"] == "run-test"


def test_classify_work_csv_normalizes_discovery_tag_arrays_to_pipe_csv() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author,author_id,word_count",
                    "sanskrit_dcs:dcs_33,san,Carakasaṃhitā,,dcs_33,120000",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            return (
                '{"rows":[{'
                '"work_id":"sanskrit_dcs:dcs_33",'
                '"classification_discovery_group_id":"medicine",'
                '"classification_discovery_tags":["medicine","ayurveda","technical"],'
                '"classification_global_popularity_score":72,'
                '"classification_global_popularity_tier":"major",'
                '"classification_group_popularity_score":96,'
                '"classification_group_popularity_tier":"canonical",'
                '"classification_popularity_score":11,'
                '"classification_popularity_tier":"obscure",'
                '"classification_scope_popularity_score":12,'
                '"classification_scope_popularity_tier":"obscure",'
                '"classification_period":"classical",'
                '"classification_date_range":"c. 1st millennium CE",'
                '"classification_authorship_status":"traditional",'
                '"classification_confidence":"high",'
                '"classification_notes":"Generated from strict discovery taxonomy"'
                "}]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )

        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["classification_discovery_group_id"] == "medicine"
    assert rows[0]["classification_discovery_tags"] == "medicine|ayurveda|technical"
    assert rows[0]["classification_global_popularity_score"] == "72"
    assert rows[0]["classification_group_popularity_score"] == "96"
    assert rows[0]["classification_popularity_score"] == "72"
    assert rows[0]["classification_popularity_tier"] == "major"
    assert rows[0]["classification_scope_popularity_score"] == "96"
    assert rows[0]["classification_scope_popularity_tier"] == "canonical"
    assert rows[0]["classification_category"] == "Medicine"
    assert rows[0]["classification_scope"] == "Ayurveda"


def test_classify_work_csv_coerces_model_taxonomy_drift_to_strict_csv() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author,author_id,word_count",
                    "work-1,san,Minor Work,,dcs_1,100",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            return (
                '{"rows":[{'
                '"work_id":"work-1",'
                '"classification_discovery_group_id":"sanskrit_poetics",'
                '"classification_discovery_tags":["poetics","one_off_generated_tag"],'
                '"classification_global_popularity_score":12,'
                '"classification_global_popularity_tier":"specialist",'
                '"classification_group_popularity_score":20,'
                '"classification_group_popularity_tier":"specialist",'
                '"classification_period":"classical",'
                '"classification_authorship_status":"traditional",'
                '"classification_confidence":"medium",'
                '"classification_notes":"Generated with a non-controlled tag"'
                "}]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )

        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["classification_discovery_group_id"] == "poetics"
    assert rows[0]["classification_discovery_tags"] == "poetics"


def test_load_classification_input_rows_skips_blank_work_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_csv = Path(tmpdir) / "classification-export.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey",
                    ",grc,",
                ]
            ),
            encoding="utf-8",
        )

        rows = load_classification_input_rows(input_csv)

    assert len(rows) == 1
    assert rows[0]["title"] == "Odyssey"


def test_classification_batch_payload_includes_language_specific_label_guidance() -> None:
    payload = classification_batch_payload(
        rows=[
            {"work_id": "work-grc", "language": "grc", "title": "Odyssey"},
            {"work_id": "work-lat", "language": "lat", "title": "Aeneid"},
            {"work_id": "work-san", "language": "san", "title": "Bhagavadgita"},
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    assert payload["allowed_values"]["classification_period"]["grc"] == [
        "Archaic",
        "Classical",
        "Hellenistic",
        "Roman Imperial",
        "Late Antique",
        "Byzantine",
        "Medieval",
        "Early Modern",
        "Modern",
        "Uncertain",
    ]
    assert "Augustan" in payload["allowed_values"]["classification_period"]["lat"]
    assert "Vedic" in payload["allowed_values"]["classification_period"]["san"]
    assert payload["allowed_values"]["classification_popularity_tier"] == [
        "canonical",
        "major",
        "common",
        "specialist",
        "obscure",
    ]
    assert payload["allowed_values"]["classification_scope_popularity_tier"] == [
        "canonical",
        "major",
        "common",
        "specialist",
        "obscure",
    ]
    assert "Greek Medicine" in payload["allowed_values"]["classification_scope"]["grc"]
    assert "Latin Grammar" in payload["allowed_values"]["classification_scope"]["lat"]
    assert "Śaiva Tantra" in payload["allowed_values"]["classification_scope"]["san"]
    assert payload["language_guidance"]["san"]["category_additions"] == [
        "Vedic Text",
        "Itihasa",
        "Purana",
        "Sutra",
        "Kavya",
        "Buddhist Scripture",
        "Jain Text",
        "Dharmashastra",
        "Tantra",
        "Stotra",
    ]
    assert "classification_scope" not in payload["output_fields"]
    assert "classification_scope_popularity_score" not in payload["output_fields"]
    assert "classification_discovery_group_id" in payload["output_fields"]
    assert "classification_discovery_tags" in payload["output_fields"]
    assert payload["allowed_values"]["classification_discovery_group_id"][0]["id"] == "epic"
    assert any(
        group["id"] == "medicine" and group["label"] == "Medicine"
        for group in payload["allowed_values"]["classification_discovery_group_id"]
    )
    assert any(
        tag["id"] == "ayurveda" and tag["description"]
        for tag in payload["allowed_values"]["classification_discovery_tags"]
    )


def test_classification_batch_payload_full_profile_includes_compatibility_fields() -> None:
    payload = classification_batch_payload(
        rows=[
            {"work_id": "work-lat", "language": "lat", "title": "De apibus"},
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
        output_profile="full",
    )

    assert "classification_scope" in payload["output_fields"]
    assert "classification_scope_popularity_score" in payload["output_fields"]
    assert "classification_generator_models" in payload["output_fields"]


def test_classification_batch_payload_marks_prior_generated_metadata_as_non_evidence() -> None:
    payload = classification_batch_payload(
        rows=[
            {
                "work_id": "bhg",
                "language": "san",
                "title": "Bhagavadgītā",
                "classification_discovery_group_id": "religion",
                "classification_global_popularity_score": "98",
                "classification_confidence": "high",
                "classification_notes": "Prior Flash pass.",
            },
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    guidance_text = " ".join(payload["instructions"])
    prior = payload["rows"][0]["classifier_context"]["prior_generated_classification"]

    assert prior["metadata_status"] == "prior_generated_metadata_not_source_evidence"
    assert prior["classification_discovery_group_id"] == "religion"
    assert "not as source evidence" in guidance_text


def test_classify_work_csv_slim_profile_derives_compatibility_fields() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "bhg,san,Bhagavadgītā,Vyāsa",
                ]
            ),
            encoding="utf-8",
        )

        def classify(payload: dict[str, Any]) -> str:
            assert "classification_scope" not in payload["output_fields"]
            return (
                '{"rows":[{'
                '"work_id":"bhg",'
                '"classification_discovery_group_id":"religion",'
                '"classification_discovery_tags":["vedanta","itihasa"],'
                '"classification_global_popularity_score":98,'
                '"classification_global_popularity_tier":"canonical",'
                '"classification_group_popularity_score":98,'
                '"classification_group_popularity_tier":"canonical",'
                '"classification_period":"Epic",'
                '"classification_authorship_status":"traditional",'
                '"classification_confidence":"high",'
                '"classification_notes":"Generated slim discovery metadata."'
                "}]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["classification_discovery_group_id"] == "religion"
    assert rows[0]["classification_discovery_tags"] == "vedanta|itihasa"
    assert rows[0]["classification_category"] == "Religion"
    assert rows[0]["classification_scope"] == "Other Sanskrit Literature"
    assert rows[0]["classification_popularity_score"] == "98"
    assert rows[0]["classification_scope_popularity_score"] == "98"


def test_select_classification_escalation_rows_prioritizes_popular_and_low_confidence() -> None:
    rows = [
        {
            "work_id": "minor",
            "classification_global_popularity_score": "20",
            "classification_group_popularity_score": "25",
            "classification_confidence": "high",
        },
        {
            "work_id": "canonical",
            "classification_global_popularity_score": "97",
            "classification_global_popularity_tier": "canonical",
            "classification_confidence": "high",
        },
        {
            "work_id": "group-leader",
            "classification_global_popularity_score": "45",
            "classification_group_popularity_score": "93",
            "classification_confidence": "medium",
        },
        {
            "work_id": "uncertain",
            "classification_global_popularity_score": "8",
            "classification_group_popularity_score": "12",
            "classification_confidence": "low",
        },
    ]

    selected_rows, reason_counts = select_classification_escalation_rows(rows)

    assert [row["work_id"] for row in selected_rows] == [
        "canonical",
        "group-leader",
        "uncertain",
    ]
    assert reason_counts == {
        "global_score": 1,
        "global_tier": 1,
        "group_score": 1,
        "confidence": 1,
    }


def test_export_classification_escalation_csv_writes_priority_queue() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "generated.csv"
        output_csv = root / "pro-audit-input.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,classification_global_popularity_score,"
                    "classification_global_popularity_tier,classification_confidence",
                    "minor,grc,Minor,15,specialist,high",
                    "iliad,grc,Iliad,100,canonical,high",
                    "fragment,grc,Fragmenta,5,obscure,low",
                ]
            ),
            encoding="utf-8",
        )

        summary = export_classification_escalation_csv(
            config=ClassificationEscalationConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                limit=ESCALATION_SELECTED_COUNT,
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["selected_count"] == 1
    assert summary["reason_counts"]["global_score"] == 1
    assert rows[0]["work_id"] == "iliad"
    assert "classification_generator_models" in rows[0]


def test_classification_batch_payload_notes_guidance_uses_standalone_scholarly_prose() -> None:
    payload = classification_batch_payload(
        rows=[
            {
                "work_id": "work-san-json",
                "language": "san",
                "title": "Brahmasūtra",
                "source_id": "corpus_sa_bAdarAyaNa-brahmasUtra",
            },
            {
                "work_id": "work-san-text",
                "language": "san",
                "title": "Brahmasūtra",
                "source_id": "GRETIL_sa_bAdarAyaNa-brahmasUtra",
            },
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    guidance_text = " ".join(payload["instructions"])

    assert "standalone scholarly prose" in guidance_text
    assert "work's scholarly role" in guidance_text
    assert "JSON version" not in guidance_text
    assert "GRETIL" not in guidance_text
    assert "DCS" not in guidance_text


def test_classification_batch_payload_notes_treat_source_ids_as_matching_context() -> None:
    payload = classification_batch_payload(
        rows=[
            {
                "work_id": "work-san-text",
                "language": "san",
                "title": "Brahmasūtra",
                "source_id": "GRETIL_sa_bAdarAyaNa-brahmasUtra",
            },
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    guidance_text = " ".join(payload["instructions"])

    assert "Use source_id and work_id for row matching and edition awareness." in guidance_text
    assert "Write classification_notes around title, author" in guidance_text
    assert "source collection names" in guidance_text


def test_classification_batch_payload_includes_source_metadata_summary_context() -> None:
    payload = classification_batch_payload(
        rows=[
            {
                "work_id": "sanskrit_dcs:dcs_123",
                "language": "san",
                "title": "Abhidharmakośa",
                "source_id": "dcs_123",
                "source_metadata_summary": (
                    "dcs_scope_hint=Buddhist Scripture; dcs_subject=Buddhist; "
                    "dcs_time_slot=classical"
                ),
            },
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    guidance_text = " ".join(payload["instructions"])
    row = payload["rows"][0]

    assert row["source_metadata_summary"] == (
        "dcs_scope_hint=Buddhist Scripture; dcs_subject=Buddhist; dcs_time_slot=classical"
    )
    assert row["classifier_context"]["source_metadata_summary"] == (
        "dcs_scope_hint=Buddhist Scripture; dcs_subject=Buddhist; dcs_time_slot=classical"
    )
    assert "Use source_metadata_summary as source-backed catalog evidence." in guidance_text
    assert "Synthesize final labels from the whole row." in guidance_text


def test_classification_batch_payload_popularity_is_language_corpus_relative() -> None:
    payload = classification_batch_payload(
        rows=[
            {"work_id": "work-lat", "language": "lat", "title": "De apibus"},
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    guidance_text = " ".join(payload["instructions"])

    assert "within the whole language corpus" in guidance_text
    assert "not within a specialty" in guidance_text
    assert "niche topic" in guidance_text
    assert payload["popularity_rubric"] == [
        {
            "tier": "canonical",
            "score_range": "90-100",
            "meaning": "Central across the language corpus and broad curricula.",
        },
        {
            "tier": "major",
            "score_range": "70-89",
            "meaning": "Widely studied across the language tradition.",
        },
        {
            "tier": "common",
            "score_range": "40-69",
            "meaning": "Often read or cited beyond a narrow specialty.",
        },
        {
            "tier": "specialist",
            "score_range": "10-39",
            "meaning": "Important mainly within a specialty or research subfield.",
        },
        {
            "tier": "obscure",
            "score_range": "0-9",
            "meaning": "Rarely read, fragmentary, marginal, or minimally attested.",
        },
    ]
    assert "Choose classification_discovery_group_id from its allowed values" in guidance_text
    assert "Use classification_group_popularity_score from 0 to 100" in guidance_text


def test_classification_batch_payload_marks_generic_fragment_titles_for_disambiguation() -> None:
    payload = classification_batch_payload(
        rows=[
            {
                "work_id": "lat-frag",
                "language": "lat",
                "title": "fragmentum",
                "author": "A. Caecina",
                "author_id": "phi0442",
                "source_id": "lat0442.002",
                "cts_work_urn": "urn:cts:latinLit:phi0442.phi002",
                "word_count": "51",
            },
            {
                "work_id": "lat-frr",
                "language": "lat",
                "title": "Liber Bene Dictorum, frr. duo",
                "author": "A. Cascellius",
                "author_id": "phi0466",
                "source_id": "lat0466.001",
                "word_count": "15",
            },
            {
                "work_id": "grc-od",
                "language": "grc",
                "title": "Odyssey",
                "author": "Homer",
                "author_id": "tlg0012",
                "source_id": "tlg0012.002",
            },
        ],
        model="openai:test-model",
        run_id="run-test",
        batch_index=1,
    )

    guidance_text = " ".join(payload["instructions"])
    rows = payload["rows"]

    assert "Generic titles such as Fragmenta, fragmentum, fragments, frr." in guidance_text
    assert "Use author, author_id, source_id, cts_work_urn, word_count" in guidance_text
    assert "classification_scope should prefer the recoverable topical or genre domain" in (
        guidance_text
    )
    assert "reserve Fragmentary Literature for indeterminate fragments" in guidance_text
    assert rows[0]["classifier_context"]["title_specificity"] == "generic_fragmentary"
    assert rows[0]["classifier_context"]["disambiguation_fields"] == {
        "author": "A. Caecina",
        "author_id": "phi0442",
        "source_id": "lat0442.002",
        "cts_work_urn": "urn:cts:latinLit:phi0442.phi002",
        "word_count": "51",
    }
    assert "generic fragmentary title" in rows[0]["classifier_context"]["note"]
    assert rows[1]["classifier_context"]["title_specificity"] == "generic_fragmentary"
    assert rows[2]["classifier_context"]["title_specificity"] == "specific"


def test_classify_work_csv_accepts_short_model_field_aliases() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            return (
                '{"rows":[{'
                '"work_id":"urn:cts:greekLit:tlg0012.tlg002",'
                '"category":"epic",'
                '"period":"archaic",'
                '"date_range":"c. 8th-7th century BCE",'
                '"authorship_status":"traditional",'
                '"popularity_score":100,'
                '"popularity_tier":"canonical",'
                '"confidence":"high",'
                '"notes":"Generated from short aliases"'
                "}]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["classification_category"] == "epic"
    assert rows[0]["classification_period"] == "archaic"
    assert rows[0]["classification_popularity_score"] == str(CANONICAL_POPULARITY_SCORE)
    assert rows[0]["classification_notes"] == "Generated from short aliases"


def test_classify_work_csv_accepts_nested_classification_object() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            return (
                '{"rows":[{'
                '"work_id":"urn:cts:greekLit:tlg0012.tlg002",'
                '"classification":{'
                '"category":"epic",'
                '"period":"archaic",'
                '"popularity_score":100,'
                '"confidence":"high"'
                "}}]}"
            )

        summary = classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["generated_count"] == 1
    assert rows[0]["classification_category"] == "epic"
    assert rows[0]["classification_popularity_score"] == str(CANONICAL_POPULARITY_SCORE)


def test_classify_work_csv_summary_counts_only_rows_with_generated_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )

        summary = classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=lambda _payload: '{"rows":[{"work_id":"urn:cts:greekLit:tlg0012.tlg002"}]}',
        )

    assert summary["input_count"] == 1
    assert summary["generated_count"] == 0


def test_classify_work_csv_can_save_raw_model_responses() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        raw_response_dir = root / "raw"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
                raw_response_dir=raw_response_dir,
            ),
            classify=lambda _payload: '{"rows":[{"work_id":"urn:cts:greekLit:tlg0012.tlg002"}]}',
        )

        assert (raw_response_dir / "batch-0001.json").read_text(encoding="utf-8") == (
            '{"rows":[{"work_id":"urn:cts:greekLit:tlg0012.tlg002"}]}'
        )


def test_classify_work_csv_reuses_existing_raw_model_responses() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        raw_response_dir = root / "raw"
        raw_response_dir.mkdir()
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )
        (raw_response_dir / "batch-0001.json").write_text(
            '{"rows":[{'
            '"work_id":"urn:cts:greekLit:tlg0012.tlg002",'
            '"classification_category":"epic",'
            '"classification_popularity_score":100,'
            '"classification_notes":"Generated from cached raw response."'
            "}]}",
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            raise AssertionError("existing raw response should be reused")

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=1,
                raw_response_dir=raw_response_dir,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["classification_category"] == "epic"
    assert rows[0]["classification_notes"] == "Generated from cached raw response."


def test_classify_work_csv_refreshes_invalid_cached_raw_response() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        raw_response_dir = root / "raw"
        raw_response_dir.mkdir()
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:latinLit:phi0690.phi003,lat,Catilinarian Orations,Cicero",
                ]
            ),
            encoding="utf-8",
        )
        cached_response_path = raw_response_dir / "batch-0001.json"
        cached_response_path.write_text("{", encoding="utf-8")

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=1,
                raw_response_dir=raw_response_dir,
            ),
            classify=lambda _payload: (
                '{"rows":[{'
                '"work_id":"urn:cts:latinLit:phi0690.phi003",'
                '"classification_category":"rhetoric",'
                '"classification_popularity_score":90,'
                '"classification_notes":"Generated after invalid cache refresh."'
                "}]}"
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))
        cached_response_text = cached_response_path.read_text(encoding="utf-8")

    assert rows[0]["classification_category"] == "rhetoric"
    assert cached_response_text.startswith('{"rows"')


def test_classify_work_csv_does_not_cache_invalid_model_response() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        raw_response_dir = root / "raw"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:latinLit:phi0690.phi003,lat,Catilinarian Orations,Cicero",
                ]
            ),
            encoding="utf-8",
        )

        with suppress(Exception):
            classify_work_csv(
                config=ClassificationRunConfig(
                    input_csv=input_csv,
                    output_csv=output_csv,
                    model="openai:test-model",
                    run_id="run-test",
                    batch_size=1,
                    raw_response_dir=raw_response_dir,
                ),
                classify=lambda _payload: "{",
            )

        assert not (raw_response_dir / "batch-0001.json").exists()


def test_classify_work_csv_can_run_model_batches_concurrently() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "work-1,lat,Aeneid,Virgil",
                    "work-2,lat,Metamorphoses,Ovid",
                ]
            ),
            encoding="utf-8",
        )
        barrier = threading.Barrier(2, timeout=2)

        def classify(payload: dict[str, Any]) -> str:
            barrier.wait()
            row = payload["rows"][0]
            return (
                '{"rows":[{'
                f'"work_id":"{row["work_id"]}",'
                '"classification_discovery_group_id":"epic",'
                '"classification_discovery_tags":["epic"],'
                '"classification_global_popularity_score":90,'
                '"classification_global_popularity_tier":"canonical",'
                '"classification_group_popularity_score":90,'
                '"classification_group_popularity_tier":"canonical",'
                '"classification_notes":"Generated concurrently."'
                "}]}"
            )

        summary = classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=1,
                concurrency=2,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["concurrency"] == TWO_WORK_COUNT
    assert summary["generated_count"] == TWO_WORK_COUNT
    assert [row["work_id"] for row in rows] == ["work-1", "work-2"]


def test_classify_work_csv_accepts_single_object_for_one_row_batch() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=1,
            ),
            classify=lambda _payload: (
                '{"classification_category":"epic","classification_popularity_score":100}'
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["work_id"] == "urn:cts:greekLit:tlg0012.tlg002"
    assert rows[0]["classification_category"] == "epic"


def test_classify_work_csv_overrides_model_supplied_provenance() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer",
                ]
            ),
            encoding="utf-8",
        )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=1,
            ),
            classify=lambda _payload: (
                '{"classification_category":"epic",'
                '"classification_generator_models":["other-model"],'
                '"classification_generator_run_id":"model-run"}'
            ),
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["classification_generator_models"] == "openai:test-model"
    assert rows[0]["classification_generator_run_id"] == "run-test"


def test_classify_work_csv_splits_and_retries_partial_batch_responses() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "work-1,grc,Odyssey,Homer",
                    "work-2,grc,Iliad,Homer",
                    "work-3,lat,Aeneid,Virgil",
                    "work-4,san,Bhagavadgita,Traditional",
                ]
            ),
            encoding="utf-8",
        )
        seen_batch_sizes: list[int] = []

        def classify(payload: dict[str, Any]) -> str:
            rows = payload["rows"]
            assert isinstance(rows, list)
            seen_batch_sizes.append(len(rows))
            if len(rows) > PARTIAL_BATCH_SPLIT_THRESHOLD:
                return (
                    '{"rows":[{'
                    f'"work_id":"{rows[0]["work_id"]}",'
                    '"classification_category":"partial",'
                    '"classification_popularity_score":1'
                    "}]}"
                )
            return (
                '{"rows":['
                + ",".join(
                    "{"
                    f'"work_id":"{row["work_id"]}",'
                    '"classification_category":"literature",'
                    '"classification_popularity_score":50,'
                    '"classification_notes":"Generated note for this work."'
                    "}"
                    for row in rows
                )
                + "]}"
            )

        summary = classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=4,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["generated_count"] == FOUR_WORK_COUNT
    assert summary["batch_count"] == RETRIED_BATCH_COUNT
    assert seen_batch_sizes == [FOUR_WORK_COUNT, TWO_WORK_COUNT, TWO_WORK_COUNT]
    assert [row["classification_category"] for row in rows] == [
        "literature",
        "literature",
        "literature",
        "literature",
    ]


def test_classify_work_csv_splits_and_retries_batch_rows_without_notes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "work-1,grc,Odyssey,Homer",
                    "work-2,grc,Iliad,Homer",
                ]
            ),
            encoding="utf-8",
        )
        seen_batch_sizes: list[int] = []

        def classify(payload: dict[str, Any]) -> str:
            rows = payload["rows"]
            assert isinstance(rows, list)
            seen_batch_sizes.append(len(rows))
            if len(rows) > 1:
                return (
                    '{"rows":['
                    + ",".join(
                        "{"
                        f'"work_id":"{row["work_id"]}",'
                        '"classification_category":"epic",'
                        '"classification_popularity_score":90'
                        "}"
                        for row in rows
                    )
                    + "]}"
                )
            return (
                '{"rows":[{'
                f'"work_id":"{rows[0]["work_id"]}",'
                '"classification_category":"epic",'
                '"classification_popularity_score":90,'
                '"classification_notes":"Generated note for this work."'
                "}]}"
            )

        summary = classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=25,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["generated_count"] == TWO_WORK_COUNT
    assert summary["batch_count"] == RETRIED_BATCH_COUNT
    assert seen_batch_sizes == [TWO_WORK_COUNT, 1, 1]
    assert [row["classification_notes"] for row in rows] == [
        "Generated note for this work.",
        "Generated note for this work.",
    ]


def test_classify_work_csv_shuffle_seed_spreads_catalog_order_batches() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "plato-1,grc,Dialog 1,Plato",
                    "plato-2,grc,Dialog 2,Plato",
                    "plato-3,grc,Dialog 3,Plato",
                    "plato-4,grc,Dialog 4,Plato",
                    "homer-1,grc,Iliad,Homer",
                    "homer-2,grc,Odyssey,Homer",
                    "aristotle-1,grc,Categories,Aristotle",
                    "aristotle-2,grc,Metaphysics,Aristotle",
                ]
            ),
            encoding="utf-8",
        )
        batch_work_ids: list[list[str]] = []

        def classify(payload: dict[str, Any]) -> str:
            rows = payload["rows"]
            assert isinstance(rows, list)
            batch_work_ids.append([str(row["work_id"]) for row in rows])
            return (
                '{"rows":['
                + ",".join(
                    "{"
                    f'"work_id":"{row["work_id"]}",'
                    '"classification_category":"Philosophy",'
                    '"classification_popularity_score":25,'
                    '"classification_scope":"Greek Philosophy",'
                    '"classification_scope_popularity_score":50,'
                    '"classification_notes":"Generated note for this work."'
                    "}"
                    for row in rows
                )
                + "]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=4,
                shuffle_seed="readiness",
            ),
            classify=classify,
        )
        output_rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert batch_work_ids[0] != ["plato-1", "plato-2", "plato-3", "plato-4"]
    assert [row["work_id"] for row in output_rows] == [
        "plato-1",
        "plato-2",
        "plato-3",
        "plato-4",
        "homer-1",
        "homer-2",
        "aristotle-1",
        "aristotle-2",
    ]


def test_classify_work_csv_stratified_batch_order_interleaves_author_clusters() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "plato-1,grc,Dialog 1,Plato",
                    "plato-2,grc,Dialog 2,Plato",
                    "plato-3,grc,Dialog 3,Plato",
                    "plato-4,grc,Dialog 4,Plato",
                    "homer-1,grc,Iliad,Homer",
                    "homer-2,grc,Odyssey,Homer",
                    "aristotle-1,grc,Categories,Aristotle",
                    "aristotle-2,grc,Metaphysics,Aristotle",
                ]
            ),
            encoding="utf-8",
        )
        batch_authors: list[list[str]] = []

        def classify(payload: dict[str, Any]) -> str:
            rows = payload["rows"]
            assert isinstance(rows, list)
            batch_authors.append([str(row["author"]) for row in rows])
            return (
                '{"rows":['
                + ",".join(
                    "{"
                    f'"work_id":"{row["work_id"]}",'
                    '"classification_discovery_group_id":"philosophy",'
                    '"classification_global_popularity_score":25,'
                    '"classification_global_popularity_tier":"specialist",'
                    '"classification_group_popularity_score":50,'
                    '"classification_group_popularity_tier":"common",'
                    '"classification_notes":"Generated note for this work."'
                    "}"
                    for row in rows
                )
                + "]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=4,
            ),
            classify=classify,
        )
        output_rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert batch_authors[0] != ["Plato", "Plato", "Plato", "Plato"]
    assert len(set(batch_authors[0])) > 1
    assert [row["work_id"] for row in output_rows] == [
        "plato-1",
        "plato-2",
        "plato-3",
        "plato-4",
        "homer-1",
        "homer-2",
        "aristotle-1",
        "aristotle-2",
    ]


def test_classify_work_csv_normalizes_scope_variants_to_controlled_buckets() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author",
                    "grc-1,grc,Lexicon,Grammarian",
                    "lat-1,lat,Fragmentum,Minor Poet",
                    "san-1,san,Śrautasūtrabhāṣya,Agnisvāmin",
                    "grc-2,grc,Physiognomonica,Anonymous",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, Any]) -> str:
            return (
                '{"rows":['
                '{"work_id":"grc-1","classification_category":"Grammar",'
                '"classification_scope":"Greek Grammar & Lexicography",'
                '"classification_popularity_score":12,'
                '"classification_scope_popularity_score":40,'
                '"classification_notes":"Generated note."},'
                '{"work_id":"lat-1","classification_category":"Poetry",'
                '"classification_scope":"Latin Poetry (Fragmentary)",'
                '"classification_popularity_score":3,'
                '"classification_scope_popularity_score":25,'
                '"classification_notes":"Generated note."},'
                '{"work_id":"san-1","classification_category":"Commentary",'
                '"classification_scope":"Śrauta Commentary",'
                '"classification_popularity_score":8,'
                '"classification_scope_popularity_score":35,'
                '"classification_notes":"Generated note."}'
                ',{"work_id":"grc-2","classification_category":"Technical Treatise",'
                '"classification_scope":"Greek Physiognomy",'
                '"classification_popularity_score":4,'
                '"classification_scope_popularity_score":30,'
                '"classification_notes":"Generated note."}'
                "]}"
            )

        classify_work_csv(
            config=ClassificationRunConfig(
                input_csv=input_csv,
                output_csv=output_csv,
                model="openai:test-model",
                run_id="run-test",
                batch_size=10,
            ),
            classify=classify,
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert [row["classification_scope"] for row in rows] == [
        "Greek Lexicography",
        "Latin Fragmentary Literature",
        "Vedic Ritual and Exegesis",
        "Other Greek Literature",
    ]
