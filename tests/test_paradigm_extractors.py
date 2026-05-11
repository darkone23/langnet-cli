from __future__ import annotations

from langnet.paradigm.extractors import (
    extract_greek_grammar_evidence,
    extract_latin_grammar_evidence,
    extract_sanskrit_grammar_evidence,
)


def test_latin_dictionary_metadata_derives_first_declension() -> None:
    evidence = extract_latin_grammar_evidence(
        {
            "lemma": "puella",
            "part_of_speech": "noun",
            "genitive_singular": "puellae",
            "gender": "feminine",
            "source": "gaffiot",
        }
    )

    assert len(evidence) == 1
    assert evidence[0].lemma == "puella"
    assert evidence[0].features["declension"] == "1"
    assert evidence[0].features["gender"] == "feminine"
    assert evidence[0].confidence == "high"


def test_latin_dictionary_metadata_derives_third_declension() -> None:
    evidence = extract_latin_grammar_evidence(
        {
            "lemma": "rex",
            "part_of_speech": "noun",
            "genitive_singular": "regis",
            "gender": "masculine",
            "source": "gaffiot",
        }
    )

    assert evidence[0].features["declension"] == "3"


def test_sanskrit_dictionary_metadata_preserves_heritage_gender_request_value() -> None:
    evidence = extract_sanskrit_grammar_evidence(
        {
            "lemma": "putra",
            "part_of_speech": "noun",
            "gender": "masculine",
            "source": "cdsl:mw",
        }
    )

    assert evidence[0].lemma == "putra"
    assert evidence[0].features["gender"] == "masculine"
    assert evidence[0].features["heritage_gender"] == "Mas"


def test_greek_dictionary_metadata_derives_second_declension_masculine() -> None:
    evidence = extract_greek_grammar_evidence(
        {
            "lemma": "λόγος",
            "part_of_speech": "noun",
            "genitive_singular": "λόγου",
            "article": "ὁ",
            "gender": "masculine",
            "source": "diogenes:lsj",
        }
    )

    assert evidence[0].lemma == "λόγος"
    assert evidence[0].features["declension"] == "2"
    assert evidence[0].features["gender"] == "masculine"


def test_missing_dictionary_metadata_stays_low_confidence() -> None:
    evidence = extract_sanskrit_grammar_evidence(
        {
            "lemma": "agni",
            "part_of_speech": "noun",
            "source": "cdsl:mw",
        }
    )

    assert evidence[0].lemma == "agni"
    assert evidence[0].confidence == "low"
    assert "heritage_gender" not in evidence[0].features
