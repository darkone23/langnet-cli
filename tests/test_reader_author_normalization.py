from __future__ import annotations

from langnet.reader.author_normalization import (
    canonical_author_from_html_index_item,
    normalize_reader_author,
)


def test_normalizes_pseudo_author_variants_to_one_display() -> None:
    assert normalize_reader_author("Plato (Ps.)") == "Pseudo-Plato"
    assert normalize_reader_author("Ps. Plato") == "Pseudo-Plato"
    assert normalize_reader_author("Pseudo Plato") == "Pseudo-Plato"
    assert normalize_reader_author("Pseudo-Plato") == "Pseudo-Plato"


def test_canonicalizes_anonymous_labels_for_reader_display() -> None:
    assert normalize_reader_author("Anonymous") == "Anonymous"
    assert normalize_reader_author("Anonymus") == "Anonymous"
    assert normalize_reader_author("Unattributed") == "Unattributed"


def test_normalizes_comma_author_names_for_reader_display() -> None:
    assert normalize_reader_author("Ulpianus, Domitius") == "Domitius Ulpianus"
    assert normalize_reader_author("Bassus, Caesius (Ps.)") == "Pseudo-Caesius Bassus"


def test_does_not_keep_empty_pseudo_author_as_display_name() -> None:
    assert normalize_reader_author("Pseudo-") == "Pseudo"


def test_extracts_tlg_pseudo_author_from_html_index_item() -> None:
    assert canonical_author_from_html_index_item("0530 Pseudo-Galenus Med.") == (
        "tlg0530",
        "Pseudo-Galenus",
    )
    assert canonical_author_from_html_index_item(
        "2798 Pseudo-Dionysius Areopagita Scr. Eccl. et Theol."
    ) == ("tlg2798", "Pseudo-Dionysius Areopagita")
    assert canonical_author_from_html_index_item("3168 Pseudo-Codinus Hist.") == (
        "tlg3168",
        "Pseudo-Codinus",
    )
