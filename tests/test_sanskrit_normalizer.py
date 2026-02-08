import unittest

from langnet.engine.sanskrit_normalizer import (
    SanskritQueryNormalizer,
    SanskritNormalizationResult,
)
from langnet.normalization.models import CanonicalQuery, Encoding, Language


class StubPipeline:
    def __init__(self, canonical_text: str, alternates: list[str] | None = None):
        self._initialized = True
        self.canonical_text = canonical_text
        self.alternates = alternates or []

    def initialize(self):
        self._initialized = True

    def normalize_query(self, language: str, query: str) -> CanonicalQuery:
        return CanonicalQuery(
            original_query=query,
            language=Language(language),
            canonical_text=self.canonical_text,
            alternate_forms=self.alternates,
            detected_encoding=Encoding.ASCII,
        )


class StubHeritageClient:
    def __init__(self, canonical_text: str):
        self.canonical_text = canonical_text

    def fetch_canonical_via_sktsearch(self, word: str):
        return {"canonical_text": self.canonical_text}


class SanskritNormalizerTests(unittest.TestCase):
    def test_pipeline_normalization_prefers_pipeline_forms(self):
        pipeline = StubPipeline(canonical_text="agni devah", alternates=["agni"])
        normalizer = SanskritQueryNormalizer(heritage_client=None, normalization_pipeline=pipeline)

        result: SanskritNormalizationResult = normalizer.normalize("agnI")

        self.assertEqual(result.canonical_heritage, "agni")
        self.assertEqual(result.canonical_tokens, ["agni", "devah"])
        self.assertIn("agni", result.slp1_candidates)
        self.assertTrue(result.canonical_slp1)

    def test_heritage_fallback_used_when_pipeline_missing(self):
        heritage = StubHeritageClient(canonical_text="agnI")
        normalizer = SanskritQueryNormalizer(heritage_client=heritage, normalization_pipeline=None)

        result: SanskritNormalizationResult = normalizer.normalize("agnI")

        self.assertEqual(result.canonical_heritage, "agnI")
        self.assertTrue(result.canonical_slp1)
        self.assertGreaterEqual(len(result.slp1_candidates), 1)


if __name__ == "__main__":
    unittest.main()
