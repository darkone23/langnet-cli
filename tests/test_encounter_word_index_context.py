from __future__ import annotations

from langnet.cli import _encounter_word_index_preferred_anchors


def test_encounter_word_index_prefers_primary_candidate_over_component_exact_anchors() -> None:
    anchors = [
        {
            "query": "jyotin",
            "candidate_rank": 0,
            "anchor_status": "nearest",
            "canonical_key": "jyotir",
            "source": "cdsl",
            "dictionary": "mw",
            "index_entry_id": "word-index:san:cdsl:mw:jyotir",
        },
        {
            "query": "ina",
            "candidate_rank": 1,
            "anchor_status": "exact",
            "canonical_key": "ina",
            "source": "cdsl",
            "dictionary": "mw",
            "index_entry_id": "word-index:san:cdsl:mw:ina",
        },
    ]

    preferred = _encounter_word_index_preferred_anchors(anchors)

    assert [anchor["canonical_key"] for anchor in preferred] == ["jyotir"]
