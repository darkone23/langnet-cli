from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast


def _load_lupus_fixture() -> Mapping[str, Any]:
    fixture_path = Path(__file__).parent / "fixtures" / "lupus_claims_wsu.json"
    return cast(Mapping[str, Any], json.loads(fixture_path.read_text(encoding="utf-8")))


def test_lupus_wsu_fixture_pairs_senses_with_glosses() -> None:
    fixture = _load_lupus_fixture()
    claims = fixture["claims"]
    assert isinstance(claims, Sequence)

    linked_senses: set[str] = set()
    gloss_senses: set[str] = set()

    for claim_raw in claims:
        assert isinstance(claim_raw, Mapping)
        claim = cast(Mapping[str, Any], claim_raw)
        assert claim["claim_id"]
        assert claim["predicate"] == "has_sense"
        assert claim["provenance_chain"]

        value = claim["value"]
        assert isinstance(value, Mapping)
        triples = value["triples"]
        assert isinstance(triples, Sequence)

        for triple_raw in triples:
            assert isinstance(triple_raw, Mapping)
            triple = cast(Mapping[str, Any], triple_raw)
            predicate = triple["predicate"]
            metadata = triple["metadata"]
            assert isinstance(metadata, Mapping)
            evidence = metadata["evidence"]
            assert isinstance(evidence, Mapping)
            assert evidence["call_id"] == claim["call_id"]
            assert evidence["derivation_id"] == claim["derivation_id"]
            assert evidence["claim_id"] == claim["claim_id"]

            if predicate == "has_sense":
                sense_anchor = triple["object"]
                assert isinstance(sense_anchor, str)
                linked_senses.add(sense_anchor)
            elif predicate == "gloss":
                sense_anchor = triple["subject"]
                assert isinstance(sense_anchor, str)
                assert triple["object"]
                gloss_senses.add(sense_anchor)

    assert linked_senses
    assert linked_senses == gloss_senses
