from __future__ import annotations

from langnet.normalizer.greek_transliterator import transliterate


def test_transliterate_basic_words() -> None:
    cases = {
        "anthropos": "ανθροποσ",  # no macron → omicron; best-effort
        "logos": "λογοσ",
        "hēmera": "ημερα",
        "hemera": "εμερα",
        "rhētor": "ρητορ",
        "psuche": "ψυχε",
        "oinos": "οινοσ",
    }
    for latin, greek in cases.items():
        res = transliterate(latin)
        assert res.search_key == greek
        assert res.betacode, "betacode should not be empty"


def test_final_sigma_normalized() -> None:
    res = transliterate("logos")
    assert res.search_key.endswith("σ")
    # display should preserve final sigma shape
    assert res.display and res.display.endswith(("σ", "ς"))
