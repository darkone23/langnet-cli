from __future__ import annotations

from langnet.reader.search_normalization import (
    normalize_query_for_search,
    normalize_segment_for_search,
)


def test_latin_search_normalization_adds_classical_spelling_variants() -> None:
    segment = normalize_segment_for_search("lat", "Iulius venit; Julius vivit.")
    query = normalize_query_for_search("lat", "Julius vivit")

    assert segment.display_text == "Iulius venit; Julius vivit."
    assert segment.search_text == "iulius venit julius vivit"
    assert "iulius uiuit" in segment.search_text_folded
    assert "julius vivit" in query.query_variants
    assert "iulius uiuit" in query.query_variants


def test_greek_search_normalization_folds_accents_and_final_sigma() -> None:
    segment = normalize_segment_for_search("grc", "Λόγος τις ἐστίν.")
    query = normalize_query_for_search("grc", "λογος")

    assert segment.search_text == "λόγοσ τισ ἐστίν"
    assert segment.search_text_folded == "λογοσ τισ εστιν"
    assert segment.token_text == "λογοσ τισ εστιν"
    assert "λογοσ" in query.query_variants


def test_sanskrit_search_normalization_matches_iast_ascii_and_nasal_variants() -> None:
    segment = normalize_segment_for_search("san", "Śaṃkara uvāca.")
    query = normalize_query_for_search("san", "sankara")

    assert segment.search_text == "śaṃkara uvāca"
    assert segment.search_text_folded == "sankara uvaca"
    assert "sankara" in query.query_variants
    assert "samkara" in query.query_variants


def test_sanskrit_query_normalization_expands_devanagari_to_iast_variants() -> None:
    query = normalize_query_for_search("san", "स्वरूपे")

    assert "svarupe" in query.query_variants
    assert "svarūpe" in query.query_variants


def test_search_normalization_treats_punctuation_as_token_boundaries() -> None:
    segment = normalize_segment_for_search("lat", "arma, virumque; cano.")

    assert segment.token_text == "arma virumque cano"
    assert "," not in segment.search_text
    assert ";" not in segment.search_text
