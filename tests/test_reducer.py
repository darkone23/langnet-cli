from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from langnet.reduction import reduce_claims

EXPECTED_WOLF_WITNESSES = 2


def _load_lupus_claims() -> list[Mapping[str, Any]]:
    fixture_path = Path(__file__).parent / "fixtures" / "lupus_claims_wsu.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return [cast(Mapping[str, Any], claim) for claim in fixture["claims"]]


def test_reduce_claims_exact_buckets_from_fixture() -> None:
    result = reduce_claims(query="lupus", language="lat", claims=_load_lupus_claims())

    assert result.query == "lupus"
    assert result.language == "lat"
    assert {bucket.display_gloss for bucket in result.buckets} == {"wolf", "wild dog", "pike"}
    wolf = next(bucket for bucket in result.buckets if bucket.display_gloss == "wolf")
    assert wolf.confidence_label == "multi-witness"
    assert len(wolf.witnesses) == EXPECTED_WOLF_WITNESSES
