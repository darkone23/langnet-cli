from typing import cast

from langnet.execution import predicates
from langnet.execution.handlers.diogenes import _build_definition_triples, _to_cts_urn


def test_diogenes_perseus_reference_converts_to_cts_urn() -> None:
    assert _to_cts_urn("perseus:abo:phi,0690,001:2:63") == "urn:cts:latinLit:phi0690.phi001:2.63"
    assert _to_cts_urn("perseus:abo:tlg,0012,001:1:1") == "urn:cts:greekLit:tlg0012.tlg001:1.1"


def test_unresolved_citation_strings_remain_source_visible() -> None:
    triples = _build_definition_triples(
        {
            "term": "lupus",
            "blocks": [
                {
                    "entry": "a wolf",
                    "citations": {
                        "Cic. Or. 48, 160": "Cic. Or. 48, 160",
                        "perseus:abo:phi,0690,001:2:63": "Verg. E. 2, 63",
                    },
                }
            ],
        },
        ["lupus"],
        "lex:lupus",
        {"source_tool": "diogenes", "response_id": "resp-1"},
    )

    citations = [triple for triple in triples if triple["predicate"] == predicates.HAS_CITATION]
    first_metadata = cast(dict[str, object], citations[0]["metadata"])
    second_metadata = cast(dict[str, object], citations[1]["metadata"])

    assert citations[0]["object"] == "Cic. Or. 48, 160"
    assert first_metadata["citation_text"] == "Cic. Or. 48, 160"
    assert first_metadata["citation_ref"] == "Cic. Or. 48, 160"

    assert citations[1]["object"] == "urn:cts:latinLit:phi0690.phi001:2.63"
    assert second_metadata["citation_text"] == "Verg. E. 2, 63"
    assert second_metadata["citation_ref"] == "perseus:abo:phi,0690,001:2:63"
