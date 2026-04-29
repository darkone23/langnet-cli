from typing import cast

from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery

from langnet.execution.handlers import heritage
from langnet.planner.core import PlannerConfig, ToolPlanner

THIRD_PERSON = 3


def _variant_features(variant: dict[str, object]) -> dict[str, object]:
    features = variant["features"]
    assert isinstance(features, dict)
    return cast(dict[str, object], features)


def test_heritage_analysis_parser_captures_nominal_and_verbal_features() -> None:
    nominal = heritage._parse_analysis_code("m. sg. voc.")
    assert nominal["pos"] == "noun"
    assert nominal["gender"] == "masculine"
    assert nominal["number"] == "singular"
    assert nominal["case"] == "vocative"

    verb = heritage._parse_analysis_code("3rd sg. pres. act. ind. [1]")
    assert verb["pos"] == "verb"
    assert verb["person"] == THIRD_PERSON
    assert verb["number"] == "singular"
    assert verb["tense"] == "present"
    assert verb["voice"] == "active"
    assert verb["mood"] == "indicative"
    assert verb["verb_class"] == 1


def test_heritage_analysis_parser_preserves_compound_roles_and_variants() -> None:
    initial = heritage._parse_analysis_code("iic.")
    assert initial["pos"] == "compound_member"
    assert initial["compound_role"] == "initial"

    variants = heritage._parse_analysis_variants("n. sg. loc.|n. sg. voc.|n. sg. loc.")
    assert [variant["analysis"] for variant in variants] == ["n. sg. loc.", "n. sg. voc."]
    assert _variant_features(variants[0])["case"] == "locative"
    assert _variant_features(variants[1])["case"] == "vocative"


def test_sanskrit_plan_uses_heritage_semicolon_query_parameters() -> None:
    normalized = NormalizedQuery(
        original="krishna",
        language=LanguageHint.LANGUAGE_HINT_SAN,
        candidates=[
            CanonicalCandidate(
                lemma="kṛṣṇa",
                encodings={"velthuis": "k.r.s.na", "iast": "kṛṣṇa", "slp1": "kfzRa"},
                sources=["heritage_sktsearch"],
            )
        ],
        normalizations=[],
    )
    plan = ToolPlanner(PlannerConfig(heritage_max_results=3)).build(normalized)
    heritage_call = next(call for call in plan.tool_calls if call.tool == "fetch.heritage")

    assert heritage_call.params is not None
    query = heritage_call.params["__http_query"]
    assert "t=VH;lex=SH;font=roma" in query
    assert "text=k.r.s.na" in query
    assert "max=3" in query
    assert "&" not in query
