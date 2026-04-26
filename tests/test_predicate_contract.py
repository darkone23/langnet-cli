from __future__ import annotations

import json
from pathlib import Path

from langnet.execution import predicates


def test_documented_predicates_have_constants() -> None:
    reference_path = Path("docs/technical/predicates_evidence.json")
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    documented = {predicate for group in reference["predicates"].values() for predicate in group}
    constants = {
        value
        for name, value in vars(predicates).items()
        if name.isupper() and isinstance(value, str)
    }

    assert documented <= constants


def test_morphology_predicate_is_valid_on_forms() -> None:
    assert predicates.validate_predicate_scope("form:agni", predicates.HAS_MORPHOLOGY)
