import json
from pathlib import Path

FIXTURE_DIR = Path("tests/fixtures/reader_word_context_golden")
FIXTURE_EXPECTED_QUERIES = {
    "latin.json": {
        ("lat", "corpore"),
        ("lat", "amor"),
        ("lat", "arma"),
        ("lat", "virum"),
        ("lat", "est"),
        ("lat", "dixit"),
    },
    "greek.json": {
        ("grc", "λόγος"),
        ("grc", "μῆνιν"),
        ("grc", "θεὰ"),
    },
    "sanskrit.json": {
        ("san", "agni"),
        ("san", "dharma"),
        ("san", "karman"),
    },
}


def test_word_context_golden_fixtures_cover_starter_forms() -> None:
    for filename, expected_queries in FIXTURE_EXPECTED_QUERIES.items():
        rows = json.loads((FIXTURE_DIR / filename).read_text())
        queries = {(row["language"], row["query"]) for row in rows}

        assert queries == expected_queries


def test_word_context_golden_rows_define_validation_policy() -> None:
    rows = [
        row
        for filename in FIXTURE_EXPECTED_QUERIES
        for row in json.loads((FIXTURE_DIR / filename).read_text())
    ]

    for row in rows:
        assert row["language"] in {"lat", "grc", "san"}
        assert row["query"]
        assert row["expected_normalized_candidates"]
        assert row["query"] in row["expected_normalized_candidates"]
        assert row["expected_caveat_policy"] in {
            "ambiguity_allowed",
            "must_have_caveat",
            "no_caveats",
            "index_unavailable_caveat",
        }
        assert row["reader_hits_policy"] in {
            "index_dependent",
            "must_have_hits",
            "index_unavailable",
        }
        assert row["expected_lexical_status"] == "available"
        assert row["expected_min_lexical_items"] >= 1
        assert row["expected_lexical_lemmas_any"]
        assert row["expected_lexical_sources_any"]
        assert row["expected_morphology_status"] == "available"
        assert row["expected_min_morphology_items"] >= 1
        assert row["expected_morphology_lemmas_any"]
        assert row["expected_morphology_sources_any"]
