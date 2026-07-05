from pathlib import Path
from typing import cast

from langnet.reader.service import ReaderService


def test_word_context_uses_lexical_evidence_provider() -> None:
    calls: list[dict[str, object]] = []

    def lexical_provider(*, query: str, language: str, candidates: list[str]) -> dict[str, object]:
        calls.append({"query": query, "language": language, "candidates": candidates})
        return {
            "status": "available",
            "items": [
                {
                    "lemma": "arma",
                    "source_tool": "lewis_1890",
                    "source_label": "Lewis 1890",
                    "gloss": "arms; weapons",
                    "source_ref": "lewis_1890:arma",
                }
            ],
            "note": "Encounter-derived lexical evidence.",
        }

    payload = ReaderService(Path("missing-catalog.duckdb")).word_context_payload(
        query="arma",
        language="lat",
        index_path=Path("missing-search-index.lance"),
        lexical_evidence_provider=lexical_provider,
    )

    assert calls[0]["query"] == "arma"
    assert calls[0]["language"] == "lat"
    assert "arma" in cast(list[str], calls[0]["candidates"])
    assert payload["lexical_evidence"]["status"] == "available"
    assert payload["lexical_evidence"]["items"] == [
        {
            "lemma": "arma",
            "source_tool": "lewis_1890",
            "source_label": "Lewis 1890",
            "gloss": "arms; weapons",
            "source_ref": "lewis_1890:arma",
        }
    ]
    assert any(step["name"] == "lexical_evidence" for step in payload["timing"]["steps"])


def test_word_context_uses_morphology_provider() -> None:
    calls: list[dict[str, object]] = []

    def morphology_provider(
        *,
        query: str,
        language: str,
        candidates: list[str],
    ) -> dict[str, object]:
        calls.append({"query": query, "language": language, "candidates": candidates})
        return {
            "status": "available",
            "items": [
                {
                    "source_tool": "whitaker",
                    "form": "arma",
                    "lemma": "arma",
                    "analysis": "neut. nom./acc. pl.",
                }
            ],
            "note": "Encounter-derived morphology evidence.",
        }

    payload = ReaderService(Path("missing-catalog.duckdb")).word_context_payload(
        query="arma",
        language="lat",
        index_path=Path("missing-search-index.lance"),
        morphology_provider=morphology_provider,
    )

    assert calls[0]["query"] == "arma"
    assert calls[0]["language"] == "lat"
    assert "arma" in cast(list[str], calls[0]["candidates"])
    assert payload["morphology"] == {
        "status": "available",
        "items": [
            {
                "source_tool": "whitaker",
                "form": "arma",
                "lemma": "arma",
                "analysis": "neut. nom./acc. pl.",
            }
        ],
        "note": "Encounter-derived morphology evidence.",
    }
    assert any(step["name"] == "morphology" for step in payload["timing"]["steps"])
    assert payload["foster_bridge"]["status"] == "available"
    foster_ids = [match["id"] for match in payload["foster_bridge"]["matches"]]
    assert "object-form" in foster_ids or "subject-form" in foster_ids


def test_word_context_foster_bridge_no_matches_when_morphology_absent() -> None:
    payload = ReaderService(Path("missing-catalog.duckdb")).word_context_payload(
        query="arma",
        language="lat",
        index_path=Path("missing-search-index.lance"),
    )

    assert payload["foster_bridge"]["status"] == "no_matches"
    assert payload["foster_bridge"]["matches"] == []


def test_word_context_foster_bridge_no_matches_for_irrelevant_analysis() -> None:
    def morphology_provider(
        *,
        query: str,
        language: str,
        candidates: list[str],
    ) -> dict[str, object]:
        return {
            "status": "available",
            "items": [
                {
                    "source_tool": "whitaker",
                    "form": "amat",
                    "lemma": "amo",
                    "analysis": "verb; 3rd sg. pres. act. indic.",
                }
            ],
            "note": "No case features.",
        }

    payload = ReaderService(Path("missing-catalog.duckdb")).word_context_payload(
        query="amat",
        language="lat",
        index_path=Path("missing-search-index.lance"),
        morphology_provider=morphology_provider,
    )

    assert payload["foster_bridge"]["status"] == "no_matches"
    assert payload["foster_bridge"]["matches"] == []
