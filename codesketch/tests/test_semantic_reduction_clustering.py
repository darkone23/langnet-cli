"""Phase 2 tests for similarity, clustering, and pipeline.

These tests verify:
1. Similarity matrix construction
2. Greedy agglomerative clustering
3. Mode-specific thresholds
4. Deterministic bucket IDs
5. Full pipeline from entry to SenseBucket
"""

import unittest

from langnet.schema import DictionaryDefinition, DictionaryEntry
from langnet.semantic_reducer import (
    MODE_THRESHOLDS,
    Mode,
    SenseBucket,
    WitnessSenseUnit,
    build_similarity_matrix,
    cluster_wsus,
    get_bucket_summary,
    get_neighbors,
    get_similar_pairs,
    get_wsu_summary,
    reduce_entry_to_semantic_structs,
    reduce_to_semantic_structs,
    sort_wsus_by_priority,
)


class TestSimilarityMatrix(unittest.TestCase):
    """Test similarity matrix construction."""

    def test_matrix_shape(self):
        """Matrix should be NxN."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="water", gloss_normalized="water"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:3", gloss_raw="earth", gloss_normalized="earth"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        self.assertEqual(matrix.shape, (3, 3))

    def test_matrix_diagonal_ones(self):
        """Diagonal should be all 1.0 (self-similarity)."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="water", gloss_normalized="water"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        for i in range(len(wsus)):
            self.assertEqual(matrix[i, i], 1.0)

    def test_matrix_symmetric(self):
        """Matrix should be symmetric."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire blaze", gloss_normalized="fire blaze"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        self.assertEqual(matrix[0, 1], matrix[1, 0])

    def test_matrix_empty(self):
        """Empty input should return empty matrix."""
        matrix = build_similarity_matrix([])
        self.assertEqual(matrix.shape, (0, 0))

    def test_identical_glosses_high_similarity(self):
        """Identical glosses should have similarity 1.0."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="ap90", sense_ref="ap90:1", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        self.assertEqual(matrix[0, 1], 1.0)

    def test_similar_glosses_reasonable_similarity(self):
        """Similar glosses should have reasonable similarity."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="ap90",
                sense_ref="ap90:1",
                gloss_raw="fire blaze",
                gloss_normalized="fire blaze",
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        self.assertGreater(matrix[0, 1], 0.3)
        self.assertLess(matrix[0, 1], 1.0)


class TestSimilarPairs(unittest.TestCase):
    """Test similar pair extraction."""

    def test_get_similar_pairs_threshold(self):
        """Should only return pairs above threshold."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:3", gloss_raw="water", gloss_normalized="water"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        pairs = get_similar_pairs(matrix, threshold=0.5)

        fire_fire_pairs = [(i, j) for i, j, _ in pairs if i in (0, 1) and j in (0, 1)]
        self.assertEqual(len(fire_fire_pairs), 1)

    def test_get_similar_pairs_sorted(self):
        """Pairs should be sorted by similarity descending."""
        wsus = [
            WitnessSenseUnit(
                source="mw",
                sense_ref="mw:1",
                gloss_raw="fire flame blaze",
                gloss_normalized="fire flame blaze",
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:3", gloss_raw="water", gloss_normalized="water"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        pairs = get_similar_pairs(matrix, threshold=0.0)

        if len(pairs) >= 2:
            self.assertGreaterEqual(pairs[0][2], pairs[1][2])

    def test_get_similar_pairs_empty(self):
        """Empty matrix should return empty list."""
        matrix = build_similarity_matrix([])
        pairs = get_similar_pairs(matrix, threshold=0.5)
        self.assertEqual(pairs, [])


class TestGetNeighbors(unittest.TestCase):
    """Test neighbor extraction."""

    def test_get_neighbors_above_threshold(self):
        """Should return neighbors above threshold."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:3", gloss_raw="water", gloss_normalized="water"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        neighbors = get_neighbors(matrix, 0, threshold=0.5)

        neighbor_indices = [i for i, _ in neighbors]
        self.assertIn(1, neighbor_indices)
        self.assertNotIn(2, neighbor_indices)

    def test_get_neighbors_sorted(self):
        """Neighbors should be sorted by similarity descending."""
        wsus = [
            WitnessSenseUnit(
                source="mw",
                sense_ref="mw:1",
                gloss_raw="fire flame blaze",
                gloss_normalized="fire flame blaze",
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:3", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        matrix = build_similarity_matrix(wsus)
        neighbors = get_neighbors(matrix, 0, threshold=0.0)

        if len(neighbors) >= 2:
            self.assertGreaterEqual(neighbors[0][1], neighbors[1][1])


class TestClustering(unittest.TestCase):
    """Test greedy agglomerative clustering."""

    def test_cluster_single_wsu(self):
        """Single WSU should produce single bucket."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        buckets = cluster_wsus(wsus)
        self.assertEqual(len(buckets), 1)
        self.assertEqual(buckets[0].sense_id, "B1")

    def test_cluster_identical_glosses(self):
        """Identical glosses should cluster together."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="ap90", sense_ref="ap90:1", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        buckets = cluster_wsus(wsus)
        self.assertEqual(len(buckets), 1)
        self.assertEqual(len(buckets[0].witnesses), 2)

    def test_cluster_different_glosses(self):
        """Very different glosses should be separate buckets."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="water", gloss_normalized="water"
            ),
        ]
        buckets = cluster_wsus(wsus)
        self.assertEqual(len(buckets), 2)

    def test_cluster_mode_open_lower_threshold(self):
        """OPEN mode should cluster more aggressively."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire blaze", gloss_normalized="fire blaze"
            ),
        ]

        open_buckets = cluster_wsus(wsus, mode=Mode.OPEN)
        skeptic_buckets = cluster_wsus(wsus, mode=Mode.SKEPTIC)

        self.assertLessEqual(len(open_buckets), len(skeptic_buckets))

    def test_cluster_mode_skeptic_higher_threshold(self):
        """SKEPTIC mode should be more conservative."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]

        open_buckets = cluster_wsus(wsus, mode=Mode.OPEN)
        skeptic_buckets = cluster_wsus(wsus, mode=Mode.SKEPTIC)

        self.assertEqual(len(open_buckets), 1)
        self.assertEqual(len(skeptic_buckets), 1)

    def test_cluster_deterministic_ids(self):
        """Bucket IDs should be deterministic (B1, B2, ...)."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:2", gloss_raw="water", gloss_normalized="water"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:3", gloss_raw="earth", gloss_normalized="earth"
            ),
        ]

        buckets1 = cluster_wsus(wsus)
        buckets2 = cluster_wsus(wsus)

        ids1 = [b.sense_id for b in buckets1]
        ids2 = [b.sense_id for b in buckets2]
        self.assertEqual(ids1, ids2)
        self.assertEqual(ids1, ["B1", "B2", "B3"])

    def test_cluster_no_witness_overlap(self):
        """Each WSU should appear in exactly one bucket."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="ap90",
                sense_ref="ap90:1",
                gloss_raw="fire blaze",
                gloss_normalized="fire blaze",
            ),
            WitnessSenseUnit(
                source="lsj", sense_ref="lsj:1", gloss_raw="water", gloss_normalized="water"
            ),
        ]
        buckets = cluster_wsus(wsus)

        all_refs = []
        for bucket in buckets:
            for wsu in bucket.witnesses:
                all_refs.append(wsu.sense_ref)

        self.assertEqual(len(all_refs), len(set(all_refs)))

    def test_cluster_empty_input(self):
        """Empty input should return empty list."""
        buckets = cluster_wsus([])
        self.assertEqual(buckets, [])

    def test_cluster_respects_priority_order(self):
        """First WSU in sorted list should be bucket anchor."""
        wsus = [
            WitnessSenseUnit(
                source="cltk", sense_ref="cltk:1", gloss_raw="fire", gloss_normalized="fire"
            ),
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        sorted_wsus = sort_wsus_by_priority(wsus)
        buckets = cluster_wsus(sorted_wsus)

        self.assertEqual(buckets[0].witnesses[0].source, "mw")


class TestBucketCreation(unittest.TestCase):
    """Test SenseBucket creation from WSUs."""

    def test_bucket_display_gloss(self):
        """Display gloss should be from first (highest priority) WSU."""
        wsus = [
            WitnessSenseUnit(
                source="mw",
                sense_ref="mw:1",
                gloss_raw="fire, flame",
                gloss_normalized="fire flame",
            ),
            WitnessSenseUnit(
                source="ap90", sense_ref="ap90:1", gloss_raw="blaze", gloss_normalized="blaze"
            ),
        ]
        buckets = cluster_wsus(wsus)
        self.assertEqual(buckets[0].display_gloss, "fire, flame")

    def test_bucket_confidence(self):
        """Bucket should have confidence score."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        buckets = cluster_wsus(wsus)
        self.assertIsNotNone(buckets[0].confidence)
        self.assertGreater(buckets[0].confidence, 0.0)
        self.assertLessEqual(buckets[0].confidence, 1.0)

    def test_bucket_aggregates_domains(self):
        """Bucket should aggregate domains from all witnesses."""
        wsus = [
            WitnessSenseUnit(
                source="mw",
                sense_ref="mw:1",
                gloss_raw="fire",
                gloss_normalized="fire",
                domains=["religion"],
            ),
            WitnessSenseUnit(
                source="ap90",
                sense_ref="ap90:1",
                gloss_raw="fire",
                gloss_normalized="fire",
                domains=["ritual"],
            ),
        ]
        buckets = cluster_wsus(wsus)
        self.assertIn("religion", buckets[0].domains)
        self.assertIn("ritual", buckets[0].domains)


class TestPipeline(unittest.TestCase):
    """Test full pipeline from entry to buckets."""

    def test_reduce_entry_basic(self):
        """Should reduce DictionaryEntry to SenseBuckets."""
        entry = DictionaryEntry(
            word="agni",
            language="san",
            source="mw",
            definitions=[
                DictionaryDefinition(definition="fire", pos="noun", source_ref="mw:1"),
                DictionaryDefinition(definition="sacrificial fire", pos="noun", source_ref="mw:2"),
            ],
        )
        buckets = reduce_entry_to_semantic_structs(entry)

        self.assertGreater(len(buckets), 0)
        self.assertIsInstance(buckets[0], SenseBucket)

    def test_reduce_entries_multiple(self):
        """Should reduce multiple entries."""
        entries = [
            DictionaryEntry(
                word="agni",
                language="san",
                source="mw",
                definitions=[
                    DictionaryDefinition(definition="fire", pos="noun", source_ref="mw:1")
                ],
            ),
            DictionaryEntry(
                word="agni",
                language="san",
                source="ap90",
                definitions=[
                    DictionaryDefinition(definition="fire", pos="noun", source_ref="ap90:1")
                ],
            ),
        ]
        buckets = reduce_to_semantic_structs(entries)

        self.assertGreater(len(buckets), 0)

    def test_reduce_empty_entries(self):
        """Empty entries should return empty list."""
        buckets = reduce_to_semantic_structs([])
        self.assertEqual(buckets, [])

    def test_reduce_entry_empty_definitions(self):
        """Entry with no definitions should return empty list."""
        entry = DictionaryEntry(word="test", language="lat", source="mw", definitions=[])
        buckets = reduce_entry_to_semantic_structs(entry)
        self.assertEqual(buckets, [])


class TestSummaries(unittest.TestCase):
    """Test summary functions."""

    def test_get_wsu_summary(self):
        """Should return WSU summary."""
        wsus = [
            WitnessSenseUnit(
                source="mw",
                sense_ref="mw:1",
                gloss_raw="fire",
                gloss_normalized="fire",
                domains=["religion"],
            ),
            WitnessSenseUnit(
                source="ap90",
                sense_ref="ap90:1",
                gloss_raw="fire",
                gloss_normalized="fire",
                domains=["ritual"],
            ),
        ]
        summary = get_wsu_summary(wsus)

        self.assertEqual(summary["count"], 2)
        self.assertIn("mw", summary["sources"])
        self.assertIn("religion", summary["domains"])

    def test_get_wsu_summary_empty(self):
        """Empty WSU list should return empty summary."""
        summary = get_wsu_summary([])
        self.assertEqual(summary["count"], 0)

    def test_get_bucket_summary(self):
        """Should return bucket summaries."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire", gloss_normalized="fire"
            ),
        ]
        buckets = cluster_wsus(wsus)
        summaries = get_bucket_summary(buckets)

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["sense_id"], "B1")
        self.assertEqual(summaries[0]["witness_count"], 1)


class TestDeterminism(unittest.TestCase):
    """Test determinism guarantees."""

    def test_same_input_same_output(self):
        """Same input should produce identical output."""
        entry = DictionaryEntry(
            word="agni",
            language="san",
            source="mw",
            definitions=[
                DictionaryDefinition(definition="fire", pos="noun", source_ref="mw:1"),
                DictionaryDefinition(definition="water", pos="noun", source_ref="mw:2"),
            ],
        )

        buckets1 = reduce_entry_to_semantic_structs(entry)
        buckets2 = reduce_entry_to_semantic_structs(entry)

        self.assertEqual(len(buckets1), len(buckets2))
        for b1, b2 in zip(buckets1, buckets2):
            self.assertEqual(b1.sense_id, b2.sense_id)
            self.assertEqual(b1.display_gloss, b2.display_gloss)

    def test_bucket_count_stable(self):
        """Bucket count should be stable for same input."""
        wsus = [
            WitnessSenseUnit(
                source="mw", sense_ref="mw:1", gloss_raw="fire flame", gloss_normalized="fire flame"
            ),
            WitnessSenseUnit(
                source="ap90",
                sense_ref="ap90:1",
                gloss_raw="fire blaze",
                gloss_normalized="fire blaze",
            ),
            WitnessSenseUnit(
                source="lsj", sense_ref="lsj:1", gloss_raw="water", gloss_normalized="water"
            ),
        ]

        counts = [len(cluster_wsus(wsus)) for _ in range(5)]
        self.assertEqual(len(set(counts)), 1)


if __name__ == "__main__":
    unittest.main()
