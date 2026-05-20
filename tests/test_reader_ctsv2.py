from __future__ import annotations

from langnet.reader.ctsv2 import (
    ctsv2_segment_address,
    ctsv2_text_id,
    parse_ctsv2_resource,
)


def test_ctsv2_text_id_uses_title_and_incipit() -> None:
    assert (
        ctsv2_text_id("lat", "Aeneid", "Arma virumque cano, Troiae qui primus ab oris")
        == "urn:ctsv2:lat:aeneid-arma-virumque-cano"
    )
    assert (
        ctsv2_text_id("san", "Bhagavadgītā", "dhṛtarāṣṭra uvāca")
        == "urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca"
    )
    assert (
        ctsv2_text_id("grc", "Anametresis Pontou", "1 χρὴ γινώσκειν")
        == "urn:ctsv2:grc:anametresis-pontou-chre-ginoskein"
    )


def test_parse_ctsv2_resource_accepts_urn_query_params() -> None:
    parsed = parse_ctsv2_resource(
        "urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23&witness=phi0690.phi003"
    )

    assert parsed is not None
    assert parsed.text_id == "urn:ctsv2:lat:aeneid-arma-virumque-cano"
    assert parsed.ref == "1.23"
    assert parsed.witness == "phi0690.phi003"


def test_parse_ctsv2_resource_accepts_uri_form() -> None:
    parsed = parse_ctsv2_resource(
        "ctsv2://lat/aeneid-arma-virumque-cano?ref=1.23&witness=phi0690.phi003"
    )

    assert parsed is not None
    assert parsed.text_id == "urn:ctsv2:lat:aeneid-arma-virumque-cano"
    assert parsed.ref == "1.23"
    assert parsed.witness == "phi0690.phi003"


def test_ctsv2_segment_address_uses_ref_query() -> None:
    assert (
        ctsv2_segment_address("urn:ctsv2:lat:aeneid-arma-virumque-cano", "1.23")
        == "urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23"
    )
