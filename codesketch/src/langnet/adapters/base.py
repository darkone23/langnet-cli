from __future__ import annotations

import betacode.conv
from langnet.schema import Citation

# Common POS indicators
NOUN_INDICATORS = ["n", "noun", "m.", "f.", "n.", "substantive"]
VERB_INDICATORS = ["v", "verb", "ω"]
ADJECTIVE_INDICATORS = ["adj", "adjective"]
PRONOUN_INDICATORS = ["pron", "pronoun"]

# URL parsing
MIN_URL_PARTS = 3


class BaseBackendAdapter:
    """Base class for backend-specific adapters."""

    def adapt(self, data: dict, language: str, word: str):
        raise NotImplementedError

    def _extract_pos_from_entry(self, entry_text: str) -> str:
        if not entry_text:
            return "unknown"

        entry_text = entry_text.lower()
        pos_indicators = {
            "noun": NOUN_INDICATORS,
            "verb": VERB_INDICATORS,
            "adjective": ADJECTIVE_INDICATORS,
            "pronoun": PRONOUN_INDICATORS,
            "adverb": ["adv", "adverb"],
            "conjunction": ["conj", "conjunction"],
            "preposition": ["prep", "preposition"],
        }
        for pos, indicators in pos_indicators.items():
            if any(indicator in entry_text for indicator in indicators):
                return pos
        return "unknown"

    def _create_citation_from_logeion(self, logeion_url: str) -> Citation:
        if logeion_url.startswith("https://logeion.uchicago.edu/"):
            return Citation(url=logeion_url)
        if logeion_url.startswith("perseus:"):
            parts = logeion_url.split(":")
            if len(parts) >= MIN_URL_PARTS:
                return Citation(
                    url=logeion_url,
                    title=f"Perseus {parts[2]}",
                    page=parts[-1] if len(parts) > MIN_URL_PARTS else None,
                )
        return Citation(url=logeion_url)

    def _create_citation_from_perseus(self, perseus_ref: str) -> Citation:
        return Citation(
            url=perseus_ref, title=perseus_ref.split(":")[-1] if ":" in perseus_ref else perseus_ref
        )


class DiogenesLanguages:
    GREEK = "grk"
    LATIN = "lat"

    parse_langs = {GREEK, LATIN}

    @staticmethod
    def greek_to_code(greek):
        code = betacode.conv.uni_to_beta(greek)
        return code.translate(str.maketrans("", "", "0123456789"))

    @staticmethod
    def code_to_greek(beta):
        return betacode.conv.beta_to_uni(beta)
