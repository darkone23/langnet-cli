import unittest

from langnet.foster.apply import apply_foster_view


class TestFosterApply(unittest.TestCase):
    def test_apply_foster_view_diogenes_latin(self):
        result = {
            "diogenes": {
                "chunks": [
                    {
                        "chunk_type": "PerseusAnalysisHeader",
                        "morphology": {"morphs": [{"stem": ["lup"], "tags": ["nom", "sg", "m"]}]},
                    }
                ]
            }
        }
        modified = apply_foster_view(result)
        self.assertIn("foster_codes", modified["diogenes"]["chunks"][0]["morphology"]["morphs"][0])
        self.assertEqual(
            modified["diogenes"]["chunks"][0]["morphology"]["morphs"][0]["foster_codes"],
            ["NAMING", "SINGLE", "MALE"],
        )

    def test_apply_foster_view_diogenes_greek(self):
        result = {
            "diogenes": {
                "chunks": [
                    {
                        "chunk_type": "PerseusAnalysisHeader",
                        "morphology": {"morphs": [{"stem": ["logos"], "tags": ["nom", "sg", "m"]}]},
                    }
                ]
            }
        }
        modified = apply_foster_view(result)
        self.assertIn("foster_codes", modified["diogenes"]["chunks"][0]["morphology"]["morphs"][0])
        self.assertEqual(
            modified["diogenes"]["chunks"][0]["morphology"]["morphs"][0]["foster_codes"],
            ["NAMING", "SINGLE", "MALE"],
        )

    def test_apply_foster_view_cltk_greek(self):
        result = {
            "cltk": {
                "greek_morphology": {
                    "morphological_features": {
                        "case": "nom",
                        "tense": "pres",
                        "gender": "m",
                        "number": "sg",
                    }
                }
            }
        }
        modified = apply_foster_view(result)
        self.assertIn("foster_codes", modified["cltk"]["greek_morphology"])
        foster_codes = modified["cltk"]["greek_morphology"]["foster_codes"]
        self.assertEqual(foster_codes["case"], "NAMING")
        self.assertEqual(foster_codes["tense"], "TIME_NOW")
        self.assertEqual(foster_codes["gender"], "MALE")
        self.assertEqual(foster_codes["number"], "SINGLE")
        self.assertEqual(foster_codes["case"], "NAMING")

    def test_apply_foster_view_sanskrit(self):
        result = {
            "dictionaries": {
                "mw": [
                    {
                        "id": "1",
                        "meaning": "fire",
                        "grammar_tags": {"case": "1", "gender": "m", "number": "sg"},
                    }
                ]
            }
        }
        modified = apply_foster_view(result)
        self.assertIn("foster_codes", modified["dictionaries"]["mw"][0])
        foster_codes = modified["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(foster_codes["case"], "NAMING")
        self.assertEqual(foster_codes["gender"], "MALE")
        self.assertEqual(foster_codes["number"], "SINGLE")

    def test_apply_foster_view_sanskrit_gender_from_entry(self):
        result = {
            "dictionaries": {
                "mw": [
                    {
                        "id": "2",
                        "meaning": "proper noun",
                        "gender": ["masculine"],
                    }
                ]
            }
        }
        modified = apply_foster_view(result)
        self.assertIn("foster_codes", modified["dictionaries"]["mw"][0])
        foster_codes = modified["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(foster_codes["gender"], "MALE")
        self.assertNotIn("case", foster_codes)  # only gender available

    def test_apply_foster_view_sanskrit_vocative(self):
        result = {
            "dictionaries": {
                "mw": [
                    {
                        "id": "3",
                        "meaning": "address",
                        "grammar_tags": {"case": "voc.", "number": "pl"},
                    }
                ]
            }
        }
        modified = apply_foster_view(result)
        foster_codes = modified["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(foster_codes["case"], "OH")
        self.assertEqual(foster_codes["number"], "GROUP")

    def test_apply_foster_view_unmapped_tags_unchanged(self):
        result = {
            "diogenes": {
                "chunks": [
                    {
                        "chunk_type": "PerseusAnalysisHeader",
                        "morphology": {"morphs": [{"stem": ["test"], "tags": ["unknown_tag"]}]},
                    }
                ]
            }
        }
        modified = apply_foster_view(result)
        self.assertNotIn(
            "foster_codes", modified["diogenes"]["chunks"][0]["morphology"]["morphs"][0]
        )


if __name__ == "__main__":
    unittest.main()
