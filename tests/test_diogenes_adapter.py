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


if __name__ == "__main__":
    unittest.main()
