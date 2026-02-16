"""Phase 0 tests for semantic reduction schema enhancement.

These tests verify:
1. DictionaryDefinition schema has new fields (source_ref, domains, register, confidence)
2. CDSL adapter populates source_ref from MW/AP90 entry IDs
3. Schema changes are backward compatible
"""

import unittest

from cattrs import unstructure
from langnet.adapters.cdsl import CDSLBackendAdapter
from langnet.schema import DictionaryDefinition


class TestSchemaEnhancement(unittest.TestCase):
    """Test the new DictionaryDefinition fields."""

    def test_dictionary_definition_has_source_ref(self):
        """DictionaryDefinition should have source_ref field."""
        d = DictionaryDefinition(definition="test", pos="noun", source_ref="mw:890")
        self.assertEqual(d.source_ref, "mw:890")

    def test_dictionary_definition_has_domains(self):
        """DictionaryDefinition should have domains field."""
        d = DictionaryDefinition(definition="test", pos="noun", domains=["religion", "mythology"])
        self.assertEqual(d.domains, ["religion", "mythology"])

    def test_dictionary_definition_has_register(self):
        """DictionaryDefinition should have register field."""
        d = DictionaryDefinition(definition="test", pos="noun", register=["vedic", "epic"])
        self.assertEqual(d.register, ["vedic", "epic"])

    def test_dictionary_definition_has_confidence(self):
        """DictionaryDefinition should have confidence field."""
        d = DictionaryDefinition(definition="test", pos="noun", confidence=0.95)
        self.assertEqual(d.confidence, 0.95)

    def test_new_fields_default_to_none_or_empty(self):
        """New fields should have sensible defaults."""
        d = DictionaryDefinition(definition="test", pos="noun")
        self.assertIsNone(d.source_ref)
        self.assertEqual(d.domains, [])
        self.assertEqual(d.register, [])
        self.assertIsNone(d.confidence)


class TestCDSLAdapterSourceRef(unittest.TestCase):
    """Test CDSL adapter populates source_ref correctly."""

    def test_build_source_ref_mw(self):
        """_build_source_ref should create mw:ID format for MW dictionary."""
        self.assertEqual(CDSLBackendAdapter._build_source_ref("mw", "890"), "mw:890")
        self.assertEqual(CDSLBackendAdapter._build_source_ref("MW", "890"), "mw:890")

    def test_build_source_ref_ap90(self):
        """_build_source_ref should create ap90:ID format for AP90 dictionary."""
        self.assertEqual(CDSLBackendAdapter._build_source_ref("ap90", "123"), "ap90:123")
        self.assertEqual(CDSLBackendAdapter._build_source_ref("AP90", "123"), "ap90:123")

    def test_build_source_ref_none_id(self):
        """_build_source_ref should return None if entry_id is missing."""
        self.assertIsNone(CDSLBackendAdapter._build_source_ref("mw", None))
        self.assertIsNone(CDSLBackendAdapter._build_source_ref("mw", ""))

    def test_adapter_populates_source_ref(self):
        """CDSL adapter should populate source_ref from entry ID."""
        adapter = CDSLBackendAdapter()
        sample_data = {
            "dictionaries": {
                "mw": [
                    {
                        "id": "890",
                        "meaning": "agni/ m. fire, sacrificial fire",
                        "pos": "m.",
                        "sanskrit_form": "agni/",
                    }
                ]
            }
        }
        entries = adapter.adapt(sample_data, "san", "agni")
        self.assertGreater(len(entries), 0)
        self.assertGreater(len(entries[0].definitions), 0)

        definition = entries[0].definitions[0]
        self.assertIsNotNone(definition.source_ref)
        if definition.source_ref is not None:
            self.assertTrue(definition.source_ref.startswith("mw:"))
            self.assertIn("890", definition.source_ref)


class TestBackwardCompatibility(unittest.TestCase):
    """Test that schema changes are backward compatible."""

    def test_old_code_still_works(self):
        """Code that doesn't use new fields should still work."""
        d = DictionaryDefinition(definition="test definition", pos="noun")
        self.assertEqual(d.definition, "test definition")
        self.assertEqual(d.pos, "noun")

    def test_cattrs_serialization(self):
        """New fields should serialize correctly with cattrs."""
        d = DictionaryDefinition(
            definition="test",
            pos="noun",
            source_ref="mw:890",
            domains=["religion"],
            register=["vedic"],
            confidence=0.95,
        )
        result = unstructure(d)

        self.assertEqual(result["source_ref"], "mw:890")
        self.assertEqual(result["domains"], ["religion"])
        self.assertEqual(result["register"], ["vedic"])
        self.assertEqual(result["confidence"], 0.95)

    def test_dataclass_field_defaults(self):
        """New fields should work with dataclass defaults."""
        d = DictionaryDefinition(definition="test", pos="noun")
        self.assertIsNone(d.source_ref)
        self.assertEqual(d.domains, [])
        self.assertEqual(d.register, [])
        self.assertIsNone(d.confidence)

    def test_new_fields_in_unstructure(self):
        """Unstructured output should include new fields."""
        d = DictionaryDefinition(definition="test", pos="noun", source_ref="ap90:123")
        result = unstructure(d)
        self.assertIn("source_ref", result)
        self.assertEqual(result["source_ref"], "ap90:123")


if __name__ == "__main__":
    unittest.main()
