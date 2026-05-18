from __future__ import annotations

import unittest

from langnet.reader.discovery_taxonomy import (
    DISCOVERY_GROUPS,
    DISCOVERY_TAGS,
    discovery_group_label,
    normalize_discovery_tags,
    validate_discovery_group_id,
    validate_discovery_tags,
)


def test_discovery_taxonomy_ids_are_strict_csv_safe_values() -> None:
    all_ids = [*DISCOVERY_GROUPS, *DISCOVERY_TAGS]

    assert all_ids
    assert len(DISCOVERY_GROUPS) == len(set(DISCOVERY_GROUPS))
    assert len(DISCOVERY_TAGS) == len(set(DISCOVERY_TAGS))
    for taxonomy_id in all_ids:
        assert taxonomy_id
        assert taxonomy_id == taxonomy_id.strip()
        assert taxonomy_id == taxonomy_id.lower()
        assert "|" not in taxonomy_id
        assert " " not in taxonomy_id


def test_discovery_taxonomy_exposes_labels_and_descriptions() -> None:
    assert discovery_group_label("medicine") == "Medicine"
    assert DISCOVERY_GROUPS["ethics"].description
    assert DISCOVERY_TAGS["ayurveda"].description
    assert DISCOVERY_TAGS["dharmashastra"].description


def test_normalize_discovery_tags_accepts_pipe_strings_and_sequences() -> None:
    assert normalize_discovery_tags("medicine|ayurveda| medicine ") == (
        "medicine",
        "ayurveda",
    )
    assert normalize_discovery_tags(["medicine", "ayurveda", "medicine"]) == (
        "medicine",
        "ayurveda",
    )


def test_validate_discovery_values_reject_generated_freeform_labels() -> None:
    with unittest.TestCase().assertRaisesRegex(ValueError, "discovery group"):
        validate_discovery_group_id("Greek Medicine")

    with unittest.TestCase().assertRaisesRegex(ValueError, "discovery tag"):
        validate_discovery_tags(("Menippean Satire",))
