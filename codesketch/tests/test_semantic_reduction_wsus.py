"""Phase 1 tests for WSU extraction and gloss normalization.

These tests verify:
1. WitnessSenseUnit dataclass structure
2. Gloss normalization functions
3. WSU extraction from DictionaryDefinition/DictionaryEntry
4. Similarity functions (Jaccard, Dice, Cosine)
"""

import unittest

from langnet.schema import DictionaryBlock, DictionaryDefinition, DictionaryEntry
from langnet.semantic_reducer import (
    ABBREVIATIONS,
    DEFAULT_STOPWORDS,
    MODE_THRESHOLDS,
    SOURCE_PRIORITY,
    Mode,
    SenseBucket,
    Source,
    WitnessSenseUnit,
    cosine_similarity,
    dice_similarity,
    extract_wsu_from_block,
    extract_wsu_from_definition,
    extract_wsus_from_entries,
    extract_wsus_from_entry,
    get_similarity_function,
    jaccard_similarity,
    lemmatize_gloss,
    normalize_gloss,
    sort_wsus_by_priority,
    tokenize,
    wsu_to_dict,
)


class TestWitnessSenseUnit(unittest.TestCase):
    """Test WitnessSenseUnit dataclass."""

    def test_wsu_creation(self):
        """Should create WSU with all fields."""
        wsu = WitnessSenseUnit(
            source="mw",
            sense_ref="mw:890",
            gloss_raw="fire, sacrificial fire",
            gloss_normalized="fire sacrificial fire",
            domains=["religion"],
            register=["vedic"],
            confidence=0.95,
            ordering=0,
        )
        self.assertEqual(wsu.source, "mw")
        self.assertEqual(wsu.sense_ref, "mw:890")
        self.assertEqual(wsu.gloss_raw, "fire, sacrificial fire")
        self.assertEqual(wsu.domains, ["religion"])
        self.assertEqual(wsu.register, ["vedic"])
        self.assertEqual(wsu.confidence, 0.95)

    def test_wsu_hashable(self):
        """WSU should be hashable by sense_ref."""
        wsu1 = WitnessSenseUnit(
            source="mw", sense_ref="mw:890", gloss_raw="fire", gloss_normalized="fire"
        )
        wsu2 = WitnessSenseUnit(
            source="mw", sense_ref="mw:890", gloss_raw="fire", gloss_normalized="fire"
        )
        wsu3 = WitnessSenseUnit(
            source="ap90", sense_ref="ap90:123", gloss_raw="fire", gloss_normalized="fire"
        )

        self.assertEqual(hash(wsu1), hash(wsu2))
        self.assertNotEqual(hash(wsu1), hash(wsu3))

    def test_wsu_equality(self):
        """WSU equality should be based on sense_ref."""
        wsu1 = WitnessSenseUnit(
            source="mw", sense_ref="mw:890", gloss_raw="fire", gloss_normalized="fire"
        )
        wsu2 = WitnessSenseUnit(
            source="mw", sense_ref="mw:890", gloss_raw="different", gloss_normalized="different"
        )
        wsu3 = WitnessSenseUnit(
            source="mw", sense_ref="mw:891", gloss_raw="fire", gloss_normalized="fire"
        )

        self.assertEqual(wsu1, wsu2)
        self.assertNotEqual(wsu1, wsu3)

    def test_wsu_defaults(self):
        """WSU should have sensible defaults."""
        wsu = WitnessSenseUnit(
            source="mw", sense_ref="mw:890", gloss_raw="fire", gloss_normalized="fire"
        )
        self.assertEqual(wsu.domains, [])
        self.assertEqual(wsu.register, [])
        self.assertIsNone(wsu.confidence)
        self.assertEqual(wsu.ordering, 0)


class TestGlossNormalization(unittest.TestCase):
    """Test gloss normalization functions."""

    def test_normalize_lowercase(self):
        """Should lowercase by default."""
        result = normalize_gloss("FIRE, Sacrificial Fire")
        self.assertEqual(result, "fire, sacrificial fire")

    def test_normalize_unicode(self):
        """Should apply NFKC normalization."""
        result = normalize_gloss("café")
        self.assertIn("caf", result)

    def test_normalize_whitespace(self):
        """Should collapse multiple whitespace."""
        result = normalize_gloss("fire   sacrificial    fire")
        self.assertEqual(result, "fire sacrificial fire")

    def test_normalize_preserves_punctuation(self):
        """Should preserve punctuation by default."""
        result = normalize_gloss("fire, sacrificial fire;")
        self.assertIn(",", result)
        self.assertIn(";", result)

    def test_normalize_remove_punctuation(self):
        """Should remove punctuation when requested."""
        result = normalize_gloss("fire, sacrificial fire;", remove_punctuation=True)
        self.assertNotIn(",", result)
        self.assertNotIn(";", result)

    def test_normalize_expand_abbreviations(self):
        """Should expand abbreviations when requested."""
        result = normalize_gloss("adj. of fire", expand_abbreviations=True)
        self.assertIn("adjective", result)

    def test_normalize_stopwords(self):
        """Should remove stopwords when provided."""
        result = normalize_gloss("the fire of the gods", stopwords=DEFAULT_STOPWORDS)
        self.assertNotIn("the", result.split())
        self.assertNotIn("of", result.split())

    def test_normalize_idempotent(self):
        """Normalization should be idempotent for already normalized text."""
        text = "fire sacrificial fire"
        result = normalize_gloss(text)
        result2 = normalize_gloss(result)
        self.assertEqual(result, result2)

    def test_tokenize(self):
        """Should split gloss into tokens, removing punctuation."""
        tokens = tokenize("Fire, Sacrificial Fire")
        self.assertEqual(tokens, ["fire", "sacrificial", "fire"])

    def test_lemmatize_gloss_basic(self):
        """Should lemmatize gloss text."""
        lemmas = lemmatize_gloss("fire, sacrificial flame")
        self.assertIn("fire", lemmas)
        self.assertIn("flame", lemmas)

    def test_lemmatize_gloss_inflected(self):
        """Should normalize inflected forms."""
        lemmas = lemmatize_gloss("the gods of fire")
        self.assertIn("god", lemmas)
        self.assertIn("fire", lemmas)

    def test_lemmatize_gloss_removes_punctuation(self):
        """Should not include punctuation in output."""
        lemmas = lemmatize_gloss("fire, flame; blaze.")
        for punct in [",", ";", "."]:
            self.assertNotIn(punct, lemmas)

    def test_preprocess_cdsl_gloss_basic(self):
        """Should strip grammatical metadata from CDSL glosses."""
        from langnet.semantic_reducer.wsu_extractor import _preprocess_cdsl_gloss

        result = _preprocess_cdsl_gloss("agni/   m. (√ ag, Uṇ.) fire, sacrificial fire")
        self.assertNotIn("agni/", result)
        self.assertIn("fire", result)

    def test_preprocess_cdsl_gloss_complex_gender(self):
        """Should handle complex gender markers."""
        from langnet.semantic_reducer.wsu_extractor import _preprocess_cdsl_gloss

        result = _preprocess_cdsl_gloss("deva/   mf(I)n. (fr. 3. div) heavenly, divine")
        self.assertNotIn("mf(I)n.", result)
        self.assertIn("heavenly", result)

    def test_preprocess_cdsl_gloss_no_change(self):
        """Should not modify glosses without grammatical prefix."""
        from langnet.semantic_reducer.wsu_extractor import _preprocess_cdsl_gloss

        result = _preprocess_cdsl_gloss("simple definition without slash")
        self.assertEqual(result, "simple definition without slash")


class TestSimilarityFunctions(unittest.TestCase):
    """Test similarity calculation functions."""

    def test_jaccard_identical(self):
        """Identical sets should have Jaccard similarity 1.0."""
        tokens = ["fire", "sacrificial"]
        self.assertEqual(jaccard_similarity(tokens, tokens), 1.0)

    def test_jaccard_disjoint(self):
        """Disjoint sets should have Jaccard similarity 0.0."""
        self.assertEqual(jaccard_similarity(["fire"], ["water"]), 0.0)

    def test_jaccard_partial(self):
        """Partially overlapping sets."""
        similarity = jaccard_similarity(["fire", "sacrificial"], ["fire", "altar"])
        expected = 1.0 / 3.0
        self.assertAlmostEqual(similarity, expected, places=3)

    def test_jaccard_empty(self):
        """Empty inputs should return 0.0."""
        self.assertEqual(jaccard_similarity([], ["fire"]), 0.0)
        self.assertEqual(jaccard_similarity(["fire"], []), 0.0)
        self.assertEqual(jaccard_similarity([], []), 0.0)

    def test_dice_identical(self):
        """Identical sets should have Dice similarity 1.0."""
        tokens = ["fire", "sacrificial"]
        self.assertEqual(dice_similarity(tokens, tokens), 1.0)

    def test_dice_empty(self):
        """Empty inputs should return 0.0."""
        self.assertEqual(dice_similarity([], ["fire"]), 0.0)

    def test_cosine_identical(self):
        """Identical vectors should have cosine similarity 1.0."""
        tokens = ["fire", "fire", "sacrificial"]
        self.assertAlmostEqual(cosine_similarity(tokens, tokens), 1.0, places=3)

    def test_cosine_empty(self):
        """Empty inputs should return 0.0."""
        self.assertEqual(cosine_similarity([], ["fire"]), 0.0)

    def test_get_similarity_function(self):
        """Should return correct function by name."""
        self.assertEqual(get_similarity_function("jaccard"), jaccard_similarity)
        self.assertEqual(get_similarity_function("dice"), dice_similarity)
        self.assertEqual(get_similarity_function("cosine"), cosine_similarity)

    def test_get_similarity_function_invalid(self):
        """Should raise for unknown function."""
        with self.assertRaises(ValueError):
            get_similarity_function("unknown")


class TestWSUExtraction(unittest.TestCase):
    """Test WSU extraction from dictionary objects."""

    def test_extract_wsu_from_definition(self):
        """Should extract WSU from DictionaryDefinition."""
        definition = DictionaryDefinition(
            definition="fire, sacrificial fire",
            pos="noun",
            source_ref="mw:890",
            domains=["religion"],
            register=["vedic"],
        )
        wsu = extract_wsu_from_definition(definition, "mw", ordering=0)

        self.assertIsNotNone(wsu)
        if wsu is not None:
            self.assertEqual(wsu.source, "mw")
            self.assertEqual(wsu.sense_ref, "mw:890")
            self.assertEqual(wsu.gloss_raw, "fire, sacrificial fire")
            self.assertEqual(wsu.domains, ["religion"])
            self.assertEqual(wsu.register, ["vedic"])

    def test_extract_wsu_empty_definition(self):
        """Should return None for empty definition."""
        definition = DictionaryDefinition(definition="   ", pos="noun")
        wsu = extract_wsu_from_definition(definition, "mw")
        self.assertIsNone(wsu)

    def test_extract_wsu_generates_ref(self):
        """Should generate sense_ref if missing."""
        definition = DictionaryDefinition(definition="fire", pos="noun")
        wsu = extract_wsu_from_definition(definition, "mw", ordering=5)

        self.assertIsNotNone(wsu)
        if wsu is not None:
            self.assertEqual(wsu.sense_ref, "mw:5")

    def test_extract_wsus_from_entry(self):
        """Should extract all WSUs from DictionaryEntry."""
        entry = DictionaryEntry(
            word="agni",
            language="san",
            source="mw",
            definitions=[
                DictionaryDefinition(definition="fire", pos="noun", source_ref="mw:890"),
                DictionaryDefinition(
                    definition="sacrificial fire", pos="noun", source_ref="mw:891"
                ),
            ],
        )
        wsus = extract_wsus_from_entry(entry)

        self.assertEqual(len(wsus), 2)
        self.assertEqual(wsus[0].sense_ref, "mw:890")
        self.assertEqual(wsus[1].sense_ref, "mw:891")

    def test_extract_wsus_from_entries(self):
        """Should extract all WSUs from multiple entries."""
        entries = [
            DictionaryEntry(
                word="agni",
                language="san",
                source="mw",
                definitions=[
                    DictionaryDefinition(definition="fire", pos="noun", source_ref="mw:890"),
                ],
            ),
            DictionaryEntry(
                word="agni",
                language="san",
                source="ap90",
                definitions=[
                    DictionaryDefinition(definition="fire", pos="noun", source_ref="ap90:123"),
                ],
            ),
        ]
        wsus = extract_wsus_from_entries(entries)

        self.assertEqual(len(wsus), 2)
        sources = {wsu.source for wsu in wsus}
        self.assertEqual(sources, {"mw", "ap90"})

    def test_extract_wsu_from_block(self):
        """Should extract WSU from DictionaryBlock (Diogenes)."""
        block = DictionaryBlock(entry="lupus, i, m. a wolf", entryid="00")
        wsu = extract_wsu_from_block(block, "diogenes", ordering=0)

        self.assertIsNotNone(wsu)
        if wsu is not None:
            self.assertEqual(wsu.source, "diogenes")
            self.assertEqual(wsu.sense_ref, "diogenes:00")
            self.assertEqual(wsu.gloss_raw, "lupus, i, m. a wolf")

    def test_extract_wsu_from_block_empty(self):
        """Should return None for empty block."""
        block = DictionaryBlock(entry="   ", entryid="00")
        wsu = extract_wsu_from_block(block, "diogenes")
        self.assertIsNone(wsu)

    def test_extract_wsus_from_entry_with_blocks(self):
        """Should extract WSUs from dictionary_blocks (Diogenes-style)."""
        entry = DictionaryEntry(
            word="lupus",
            language="lat",
            source="diogenes",
            definitions=[],
            dictionary_blocks=[
                DictionaryBlock(entry="lupus, i, m. a wolf", entryid="00"),
                DictionaryBlock(entry="lupus, i, m. the wolf (constellation)", entryid="01"),
            ],
        )
        wsus = extract_wsus_from_entry(entry)

        self.assertEqual(len(wsus), 2)
        self.assertEqual(wsus[0].sense_ref, "diogenes:00")
        self.assertEqual(wsus[1].sense_ref, "diogenes:01")

    def test_extract_wsus_from_entry_mixed(self):
        """Should extract WSUs from both definitions and blocks."""
        entry = DictionaryEntry(
            word="test",
            language="lat",
            source="mixed",
            definitions=[
                DictionaryDefinition(definition="def 1", pos="noun"),
            ],
            dictionary_blocks=[
                DictionaryBlock(entry="block 1", entryid="00"),
            ],
        )
        wsus = extract_wsus_from_entry(entry)

        self.assertEqual(len(wsus), 2)
        self.assertEqual(wsus[0].gloss_raw, "def 1")
        self.assertEqual(wsus[1].gloss_raw, "block 1")


class TestWSUSorting(unittest.TestCase):
    """Test WSU sorting by priority."""

    def test_sort_by_source_priority(self):
        """Should sort WSUs by source priority."""
        wsus = [
            WitnessSenseUnit(
                source="cltk", sense_ref="cltk:1", gloss_raw="a", gloss_normalized="a"
            ),
            WitnessSenseUnit(source="mw", sense_ref="mw:1", gloss_raw="b", gloss_normalized="b"),
            WitnessSenseUnit(
                source="ap90", sense_ref="ap90:1", gloss_raw="c", gloss_normalized="c"
            ),
        ]

        sorted_wsus = sort_wsus_by_priority(wsus)

        self.assertEqual(sorted_wsus[0].source, "mw")
        self.assertEqual(sorted_wsus[1].source, "ap90")
        self.assertEqual(sorted_wsus[2].source, "cltk")

    def test_sort_stable_within_source(self):
        """Should maintain stable order within same source."""
        wsus = [
            WitnessSenseUnit(source="mw", sense_ref="mw:2", gloss_raw="b", gloss_normalized="b"),
            WitnessSenseUnit(source="mw", sense_ref="mw:1", gloss_raw="a", gloss_normalized="a"),
        ]

        sorted_wsus = sort_wsus_by_priority(wsus)

        self.assertEqual(sorted_wsus[0].sense_ref, "mw:1")
        self.assertEqual(sorted_wsus[1].sense_ref, "mw:2")


class TestWSUSerialization(unittest.TestCase):
    """Test WSU serialization."""

    def test_wsu_to_dict(self):
        """Should convert WSU to dictionary."""
        wsu = WitnessSenseUnit(
            source="mw",
            sense_ref="mw:890",
            gloss_raw="fire",
            gloss_normalized="fire",
            domains=["religion"],
            register=["vedic"],
            confidence=0.95,
            ordering=0,
        )

        result = wsu_to_dict(wsu)

        self.assertEqual(result["source"], "mw")
        self.assertEqual(result["sense_ref"], "mw:890")
        self.assertEqual(result["gloss_raw"], "fire")
        self.assertEqual(result["domains"], ["religion"])
        self.assertEqual(result["confidence"], 0.95)


class TestTypesAndConstants(unittest.TestCase):
    """Test type definitions and constants."""

    def test_mode_enum(self):
        """Mode should have OPEN and SKEPTIC values."""
        self.assertEqual(Mode.OPEN.value, "open")
        self.assertEqual(Mode.SKEPTIC.value, "skeptic")

    def test_mode_thresholds(self):
        """Should have different thresholds for modes."""
        self.assertLess(MODE_THRESHOLDS[Mode.OPEN], MODE_THRESHOLDS[Mode.SKEPTIC])
        self.assertEqual(MODE_THRESHOLDS[Mode.OPEN], 0.15)
        self.assertEqual(MODE_THRESHOLDS[Mode.SKEPTIC], 0.25)

    def test_source_priority_mw_first(self):
        """MW should have highest priority (lowest number)."""
        self.assertEqual(SOURCE_PRIORITY[Source.MW], 1)

    def test_source_priority_ordering(self):
        """Source priority should be ordered correctly."""
        self.assertLess(SOURCE_PRIORITY[Source.MW], SOURCE_PRIORITY[Source.AP90])
        self.assertLess(SOURCE_PRIORITY[Source.AP90], SOURCE_PRIORITY[Source.HERITAGE])

    def test_abbreviations_exist(self):
        """Should have common abbreviations defined."""
        self.assertIn("adj", ABBREVIATIONS)
        self.assertIn("adv", ABBREVIATIONS)
        self.assertIn("cf", ABBREVIATIONS)

    def test_default_stopwords_exist(self):
        """Should have common stopwords defined."""
        self.assertIn("the", DEFAULT_STOPWORDS)
        self.assertIn("of", DEFAULT_STOPWORDS)
        self.assertIn("a", DEFAULT_STOPWORDS)


class TestSenseBucket(unittest.TestCase):
    """Test SenseBucket dataclass."""

    def test_sense_bucket_creation(self):
        """Should create SenseBucket with all fields."""
        wsu = WitnessSenseUnit(
            source="mw", sense_ref="mw:890", gloss_raw="fire", gloss_normalized="fire"
        )
        bucket = SenseBucket(
            sense_id="B1",
            semantic_constant="FIRE",
            display_gloss="fire, sacrificial fire",
            confidence=0.91,
            witnesses=[wsu],
            domains=["religion"],
        )

        self.assertEqual(bucket.sense_id, "B1")
        self.assertEqual(bucket.semantic_constant, "FIRE")
        self.assertEqual(bucket.confidence, 0.91)
        self.assertEqual(len(bucket.witnesses), 1)


if __name__ == "__main__":
    unittest.main()
