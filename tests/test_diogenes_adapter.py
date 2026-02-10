import unittest
from typing import cast

from langnet.adapters.diogenes import DiogenesBackendAdapter


class TestDiogenesAdapter(unittest.TestCase):
    def test_perseus_morphology_deduplicated(self):
        adapter = DiogenesBackendAdapter()
        data = {
            "chunks": [
                {
                    "chunk_type": "PerseusAnalysisHeader",
                    "morphology": {
                        "morphs": [
                            {
                                "stem": ["sēdat", "sedo"],
                                "tags": ["pres", "ind", "act", "3rd", "sg"],
                                "foster_codes": ["TIME_NOW", "DOING", "SINGLE"],
                            }
                        ]
                    },
                }
            ]
        }

        entries = adapter.adapt(data, language="lat", word="sedat", timings={})
        self.assertEqual(len(entries), 1)
        morph = entries[0].morphology
        assert morph is not None

        self.assertEqual(morph.foster_codes, ["TIME_NOW", "DOING", "SINGLE"])
        raw = cast(list[dict[str, object]], morph.features.get("raw"))
        self.assertIsInstance(raw, list)
        first_raw = raw[0]
        self.assertNotIn("foster_codes", first_raw)
        self.assertNotIn("tags", first_raw)

    def test_dictionary_block_hides_raw_citations(self):
        adapter = DiogenesBackendAdapter()
        data = {
            "chunks": [
                {
                    "chunk_type": "DiogenesMatchingReference",
                    "definitions": {
                        "term": "sedat",
                        "blocks": [
                            {
                                "entry": "sedat entry",
                                "entryid": "1",
                                "citations": {
                                    "urn:cts:latinLit:phi1294.phi002:1.1": "Verg. A. 1.1"
                                },
                                "original_citations": {
                                    "Verg. A. 1.1": "urn:cts:latinLit:phi1294.phi002:1.1"
                                },
                            }
                        ],
                    },
                }
            ]
        }

        entries = adapter.adapt(data, language="lat", word="sedat", timings={})
        self.assertEqual(len(entries), 1)
        blocks = entries[0].dictionary_blocks
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        # Raw citation lists are omitted
        self.assertEqual(block.citations, {})
        self.assertEqual(block.original_citations, {})
        # Details remain populated for consumers
        self.assertIn("urn:cts:latinLit:phi1294.phi002:1.1", block.citation_details)


if __name__ == "__main__":
    unittest.main()
