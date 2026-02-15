#!/usr/bin/env python3
"""
Tests for Sanskrit canonicalization and normalization.
"""

import os
import sys
import unittest
from typing import cast

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.normalization.sanskrit import SanskritNormalizer  # noqa: E402


class FakeHeritageClient:
    def __init__(self, canonical_map: dict[str, str]):
        self.canonical_map = canonical_map

    def fetch_canonical_via_sktsearch(self, query: str, timeout=None):
        canonical = self.canonical_map.get(query)
        return {
            "original_query": query,
            "canonical_text": canonical,
            "match_method": "sktsearch" if canonical else "none",
            "entry_url": "/test",
        }

    def fetch_canonical_sanskrit(self, query: str, lexicon: str | None = None, timeout=None):
        return {
            "original_query": query,
            "canonical_sanskrit": self.canonical_map.get(query),
            "match_method": "fallback" if self.canonical_map.get(query) else "not_found",
            "entry_url": "/fallback",
            "lexicon": lexicon,
        }


class TestSanskritCanonicalization(unittest.TestCase):
    def test_sktsearch_canonicalization_and_slp1_agni(self):
        normalizer = SanskritNormalizer(heritage_client=FakeHeritageClient({"agni": "agnii"}))
        result = normalizer.normalize("agni")

        self.assertEqual(result.canonical_text, "agnii")
        self.assertTrue(any(alt == "agnI" for alt in result.alternate_forms))
        metadata = result.enrichment_metadata
        if metadata is None:
            self.fail("Expected enrichment_metadata to be populated")
        metadata_map = cast(dict[str, object], metadata)
        self.assertEqual(metadata_map.get("canonical_text"), "agnii")
        self.assertIn("Canonical match", " ".join(result.normalization_notes))

    def test_sktsearch_canonicalization_and_slp1_vrika(self):
        normalizer = SanskritNormalizer(heritage_client=FakeHeritageClient({"vrika": "v.rka"}))
        result = normalizer.normalize("vrika")

        self.assertEqual(result.canonical_text, "v.rka")
        self.assertTrue(any(alt == "vfka" for alt in result.alternate_forms))
        metadata = result.enrichment_metadata
        if metadata is None:
            self.fail("Expected enrichment_metadata to be populated")
        metadata_map = cast(dict[str, object], metadata)
        self.assertEqual(metadata_map.get("canonical_text"), "v.rka")
        self.assertIn("Canonical match", " ".join(result.normalization_notes))

    def test_iast_fallback_to_velthuis_when_sktsearch_empty(self):
        normalizer = SanskritNormalizer(heritage_client=FakeHeritageClient({}))

        result = normalizer.normalize("agnī")

        self.assertEqual(result.canonical_text, "agnii")
        # Should still provide an slp1 alternate even without Heritage help
        self.assertTrue(any(alt == "agnI" for alt in result.alternate_forms))
