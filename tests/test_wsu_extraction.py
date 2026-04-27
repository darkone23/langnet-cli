from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from langnet.reduction import extract_witness_sense_units

EXPECTED_LUPUS_WITNESS_COUNT = 4


def _load_lupus_claims() -> list[Mapping[str, Any]]:
    fixture_path = Path(__file__).parent / "fixtures" / "lupus_claims_wsu.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    claims = fixture["claims"]
    return [cast(Mapping[str, Any], claim) for claim in claims]


def test_extract_witness_sense_units_from_lupus_fixture() -> None:
    witnesses = extract_witness_sense_units(_load_lupus_claims())

    assert len(witnesses) == EXPECTED_LUPUS_WITNESS_COUNT
    assert {w.gloss for w in witnesses} == {"wolf", "wild dog", "pike"}
    assert all(w.wsu_id.startswith("wsu:") for w in witnesses)
    assert all(w.claim_id for w in witnesses)
    assert all(w.sense_anchor.startswith("sense:") for w in witnesses)
    assert all(w.lexeme_anchor.startswith("lex:") for w in witnesses)
    assert all(w.evidence["claim_id"] == w.claim_id for w in witnesses)


def test_extract_witness_sense_units_is_deterministic() -> None:
    first = extract_witness_sense_units(_load_lupus_claims())
    second = extract_witness_sense_units(_load_lupus_claims())

    assert [w.wsu_id for w in first] == [w.wsu_id for w in second]


def test_extract_witness_sense_units_preserves_display_metadata() -> None:
    claims = [
        {
            "claim_id": "claim-cdsl-dharma",
            "tool": "claim.cdsl.sense",
            "value": {
                "triples": [
                    {
                        "subject": "lex:darma",
                        "predicate": "has_sense",
                        "object": "sense:lex:darma#one",
                        "metadata": {
                            "display_iast": "dharma",
                            "display_slp1": "Darma",
                            "display_gloss": "law, duty",
                            "source_entry": {"source_ref": "mw:100", "key_slp1": "Darma"},
                            "source_segments": [
                                {
                                    "index": 0,
                                    "raw_text": "law, duty",
                                    "display_text": "law, duty",
                                }
                            ],
                            "source_notes": {
                                "source_reference_segments": ["Mn."],
                                "recognized_abbreviations": ["Mn"],
                            },
                            "source_encoding": "slp1",
                            "evidence": {"source_tool": "cdsl", "claim_id": "claim-cdsl-dharma"},
                        },
                    },
                    {
                        "subject": "sense:lex:darma#one",
                        "predicate": "gloss",
                        "object": "law, duty",
                        "metadata": {
                            "display_iast": "dharma",
                            "display_slp1": "Darma",
                            "display_gloss": "law, duty",
                            "source_entry": {"source_ref": "mw:100", "key_slp1": "Darma"},
                            "source_segments": [
                                {
                                    "index": 0,
                                    "raw_text": "law, duty",
                                    "display_text": "law, duty",
                                }
                            ],
                            "source_notes": {
                                "source_reference_segments": ["Mn."],
                                "recognized_abbreviations": ["Mn"],
                            },
                            "source_encoding": "slp1",
                            "evidence": {"source_tool": "cdsl", "claim_id": "claim-cdsl-dharma"},
                        },
                    },
                ]
            },
        }
    ]

    witness = extract_witness_sense_units(cast(list[Mapping[str, Any]], claims))[0]

    assert witness.evidence["display_iast"] == "dharma"
    assert witness.evidence["display_slp1"] == "Darma"
    assert witness.evidence["display_gloss"] == "law, duty"
    assert witness.evidence["source_entry"] == {"source_ref": "mw:100", "key_slp1": "Darma"}
    assert witness.evidence["source_segments"] == [
        {"index": 0, "raw_text": "law, duty", "display_text": "law, duty"}
    ]
    assert witness.evidence["source_notes"] == {
        "source_reference_segments": ["Mn."],
        "recognized_abbreviations": ["Mn"],
    }
    assert witness.evidence["source_encoding"] == "slp1"
