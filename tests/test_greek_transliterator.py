from __future__ import annotations

from langnet.normalizer.greek_transliterator import transliterate, transliterate_variants


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


def test_exact_reader_transliterations_prefer_real_headwords() -> None:
    assert transliterate_variants("homo")[0].search_key == "ὁμός"
    assert transliterate_variants("homos")[0].search_key == "ὁμός"


def test_bare_os_does_not_prioritize_omega_variant() -> None:
    variants = transliterate_variants("logos")

    assert variants[0].search_key == "λογοσ"
    assert variants[0].search_key != "λωγοσ"
