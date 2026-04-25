"""Tests for Diogenes entry parser with Lark grammar."""

from __future__ import annotations

import unittest

from langnet.parsing.diogenes_parser import (
    DiogenesEntryParser,
    parse_diogenes_entry,
    parse_perseus_morph,
)


class DiogenesParserBasicTests(unittest.TestCase):
    """Basic parsing tests for Diogenes entries."""

    def setUp(self) -> None:
        """Set up parser instance."""
        self.parser = DiogenesEntryParser()

    def test_parse_simple_noun_header(self) -> None:
        """Parse simple noun entry header: 'lupus, -i, m.'"""
        text = "lupus, -i, m."
        result = self.parser.parse(text)

        self.assertEqual(result["header"]["lemma"], "lupus")
        self.assertIn("-i", result["header"]["principal_parts"])
        self.assertEqual(result["header"]["gender"], "m")

    def test_parse_verb_principal_parts(self) -> None:
        """Parse verb with principal parts: 'amo, amare, amavi, amatum'"""
        text = "amo, amare, amavi, amatum, v."
        result = self.parser.parse(text)

        self.assertEqual(result["header"]["lemma"], "amo")
        self.assertIn("amare", result["header"]["principal_parts"])
        self.assertIn("amavi", result["header"]["principal_parts"])
        self.assertIn("amatum", result["header"]["principal_parts"])
        self.assertEqual(result["header"]["pos"], "v")

    def test_parse_entry_with_root_symbol(self) -> None:
        """Parse entry with etymology: 'lupus, -i, m. (√lup)'"""
        text = "lupus, -i, m. (√lup)"
        result = self.parser.parse(text)

        self.assertEqual(result["header"]["lemma"], "lupus")
        self.assertEqual(result["header"]["root"], "lup")

    def test_parse_adjective_entry(self) -> None:
        """Parse adjective entry: 'bonus, -a, -um, adj.'"""
        text = "bonus, -a, -um, adj."
        result = self.parser.parse(text)

        self.assertEqual(result["header"]["lemma"], "bonus")
        self.assertIn("-a", result["header"]["principal_parts"])
        self.assertIn("-um", result["header"]["principal_parts"])
        self.assertEqual(result["header"]["pos"], "adj")


class DiogenesSenseParsingTests(unittest.TestCase):
    """Tests for parsing sense blocks."""

    def setUp(self) -> None:
        """Set up parser instance."""
        self.parser = DiogenesEntryParser()

    def test_parse_simple_sense_block(self) -> None:
        """Parse simple sense: 'I. a wolf'"""
        text = "lupus, -i, m. I. a wolf"
        result = self.parser.parse(text)

        self.assertEqual(len(result["senses"]), 1)
        sense = result["senses"][0]
        self.assertEqual(sense["level"], "I")
        self.assertEqual(sense["gloss"], "a wolf")
        self.assertIsNone(sense["qualifier"])

    def test_parse_sense_with_qualifier(self) -> None:
        """Parse sense with qualifier: 'A. lit., a wolf'"""
        # Realistic format: nested senses on separate lines
        text = """lupus, -i, m.
        I. general meaning
           A. lit., a wolf"""
        result = self.parser.parse(text)

        # Should parse nested sense (A under I)
        # Find sense with qualifier
        lit_senses = [s for s in result["senses"] if s.get("qualifier") == "lit"]
        self.assertTrue(len(lit_senses) > 0)
        sense = lit_senses[0]
        self.assertEqual(sense["gloss"], "a wolf")

    def test_parse_multiple_senses(self) -> None:
        """Parse entry with multiple top-level senses."""
        text = """lupus, -i, m.
        I. a wolf
        II. a fish"""
        result = self.parser.parse(text)

        # Should have at least 2 senses
        self.assertGreaterEqual(len(result["senses"]), 2)

        # Check for Roman numeral levels
        levels = [s["level"] for s in result["senses"]]
        self.assertIn("I", levels)
        self.assertIn("II", levels)

    def test_parse_sense_with_citations(self) -> None:
        """Parse sense with citations: 'I. a wolf, Cic.; Hor.'"""
        text = "lupus, -i, m. I. a wolf Cic.; Hor."
        result = self.parser.parse(text)

        self.assertEqual(len(result["senses"]), 1)
        sense = result["senses"][0]
        self.assertIn("Cic", sense["citations"])
        self.assertIn("Hor", sense["citations"])


class PerseusMorphParsingTests(unittest.TestCase):
    """Tests for Perseus morphology parsing."""

    def test_parse_perseus_noun_morph(self) -> None:
        """Parse Perseus noun morphology: 'lupus: noun masc nom sg'"""
        text = "lupus: noun masc nom sg"
        result = parse_perseus_morph(text)

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["pos"], "noun")
            self.assertIn("masc", result["features"])
            self.assertIn("nom", result["features"])
            self.assertIn("sg", result["features"])

    def test_parse_perseus_verb_morph(self) -> None:
        """Parse Perseus verb morphology: 'amo, amare: verb 1st pres act ind'"""
        text = "amo, amare: verb 1st pres act ind"
        result = parse_perseus_morph(text)

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["pos"], "verb")
            self.assertEqual(result["forms"], ["amo", "amare"])
            self.assertIn("1st", result["features"])
            self.assertIn("pres", result["features"])

    def test_parse_perseus_morph_with_gloss(self) -> None:
        """Parse Perseus morph with parenthetical gloss: 'lupus (wolf): noun'"""
        text = "lupus (wolf): noun masc nom sg"
        result = parse_perseus_morph(text)

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["pos"], "noun")
            # Forms should include the base form
            self.assertTrue(any("lupus" in form for form in result["forms"]))

    def test_parse_perseus_morph_invalid(self) -> None:
        """Parse invalid Perseus morphology returns None."""
        text = "just some random text without a colon"
        result = parse_perseus_morph(text)

        self.assertIsNone(result)


class DiogenesParserConvenienceTests(unittest.TestCase):
    """Tests for convenience functions."""

    def test_parse_diogenes_entry_function(self) -> None:
        """Test parse_diogenes_entry convenience function."""
        text = "lupus, -i, m. I. a wolf"
        result = parse_diogenes_entry(text)

        self.assertEqual(result["header"]["lemma"], "lupus")
        self.assertEqual(len(result["senses"]), 1)

    def test_parse_safe_returns_none_on_error(self) -> None:
        """Test parse_safe returns None for invalid input."""
        parser = DiogenesEntryParser()
        result = parser.parse_safe("completely invalid @#$ syntax !!!")

        # Should return None instead of raising exception
        self.assertIsNone(result)

    def test_parse_safe_returns_result_on_success(self) -> None:
        """Test parse_safe returns ParsedEntry for valid input."""
        parser = DiogenesEntryParser()
        result = parser.parse_safe("lupus, -i, m.")

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["header"]["lemma"], "lupus")


class DiogenesParserEdgeCasesTests(unittest.TestCase):
    """Edge case tests for parser."""

    def setUp(self) -> None:
        """Set up parser instance."""
        self.parser = DiogenesEntryParser()

    def test_parse_entry_with_multiple_genders(self) -> None:
        """Parse entry with multiple genders: 'dies, -ei, m. or f.'"""
        text = "dies, -ei, m. or f."
        result = self.parser.parse(text)

        self.assertEqual(result["header"]["lemma"], "dies")
        # Should capture compound gender
        self.assertIn("or", result["header"]["gender"])  # type: ignore[arg-type]

    def test_parse_entry_minimal(self) -> None:
        """Parse minimal entry: just lemma."""
        text = "lupus"
        result = self.parser.parse(text)

        self.assertEqual(result["header"]["lemma"], "lupus")
        # Other fields should be empty/None
        self.assertEqual(result["header"]["principal_parts"], [])

    def test_parse_entry_with_greek_text(self) -> None:
        """Parse entry containing Greek characters."""
        text = "λόγος, -ου, m. I. word"
        result = self.parser.parse(text)

        # Should handle Greek lemma
        self.assertIn("λόγος", result["header"]["lemma"])


class DiogenesParserIntegrationTests(unittest.TestCase):
    """Integration tests with realistic entry formats."""

    def setUp(self) -> None:
        """Set up parser instance."""
        self.parser = DiogenesEntryParser()

    def test_parse_complex_entry(self) -> None:
        """Parse complex entry with multiple senses and sub-senses."""
        text = """lupus, -i, m. (√lup)
        I. a wolf
           A. lit., Cic.; Verg.
           B. transf., a greedy person, Plaut.
        II. a fish, Plin."""

        result = self.parser.parse(text)

        # Should parse header
        self.assertEqual(result["header"]["lemma"], "lupus")
        self.assertEqual(result["header"]["root"], "lup")

        # Should parse multiple senses
        self.assertGreaterEqual(len(result["senses"]), 2)

        # Should have citations in at least one sense
        all_citations = []
        for sense in result["senses"]:
            all_citations.extend(sense.get("citations", []))

        self.assertTrue(len(all_citations) > 0)

    def test_parse_verb_entry_complete(self) -> None:
        """Parse complete verb entry with all principal parts."""
        text = """amo, amare, amavi, amatum, v.
        I. to love
           A. of persons, Cic.
           B. of things, to be fond of, Hor.
        II. to be wont, freq."""

        result = self.parser.parse(text)

        # Check principal parts
        self.assertEqual(result["header"]["lemma"], "amo")
        self.assertEqual(result["header"]["pos"], "v")
        self.assertIn("amare", result["header"]["principal_parts"])
        self.assertIn("amavi", result["header"]["principal_parts"])
        self.assertIn("amatum", result["header"]["principal_parts"])

        # Check senses
        self.assertGreaterEqual(len(result["senses"]), 1)


if __name__ == "__main__":
    unittest.main()
