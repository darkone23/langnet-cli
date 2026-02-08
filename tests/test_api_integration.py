import logging
import unittest

from langnet.core import LangnetWiring, LangnetWiringConfig

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


def find_entries_by_source(entries, source):
    """Helper to find all entries from a specific source."""
    return [e for e in entries if e.source == source]


def get_first_entry_by_source(entries, source):
    """Helper to get first entry from a specific source."""
    for entry in entries:
        if entry.source == source:
            return entry
    return None


class TestGreekSpacyIntegration(unittest.TestCase):
    def setUp(self):
        self.wiring = LangnetWiring(LangnetWiringConfig(warmup_backends=False))

    def test_greek_query_includes_diogenes_response(self):
        entries = self.wiring.engine.handle_query("grc", "λόγος")

        sources = [e.source for e in entries]
        self.assertIn("diogenes", sources, "Should have diogenes entries")

        diogenes_entry = get_first_entry_by_source(entries, "diogenes")
        self.assertIsNotNone(diogenes_entry, "Should have diogenes entry")
        self.assertIsInstance(diogenes_entry, object)

    def test_greek_query_has_entries(self):
        entries = self.wiring.engine.handle_query("grc", "οὐσία")
        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have at least one entry for Greek word")


class TestLatinQueryIntegration(unittest.TestCase):
    def setUp(self):
        self.wiring = LangnetWiring(LangnetWiringConfig(warmup_backends=False))

    def test_latin_query_aggregates_sources(self):
        entries = self.wiring.engine.handle_query("lat", "lupus")

        sources = [e.source for e in entries]
        self.assertIn("diogenes", sources, "Should have diogenes entries")
        self.assertIn("whitakers", sources, "Should have whitakers entries")
        self.assertIn("cltk", sources, "Should have cltk entries")

    def test_latin_query_cltk_has_headword(self):
        entries = self.wiring.engine.handle_query("lat", "lupus")

        cltk_entry = get_first_entry_by_source(entries, "cltk")
        self.assertIsNotNone(cltk_entry, "Should have cltk entry")
        if cltk_entry:
            cltk_result = cltk_entry.metadata
            self.assertIsInstance(cltk_result, dict)
            # CLTK metadata currently surfaces canonical_form; older runs used headword.
            self.assertTrue(
                "headword" in cltk_result or "canonical_form" in cltk_result,
                "CLTK entry should expose a headword or canonical form",
            )


if __name__ == "__main__":
    unittest.main()
