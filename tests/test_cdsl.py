import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import cast

from langnet.cologne.core import (
    CdslIndex,
    build_dict,
    normalize_key,
    to_slp1,
)
from langnet.cologne.models import (
    CdslEntry,
    SanskritDictionaryEntry,
)
from langnet.cologne.parser import (
    extract_headwords,
    parse_grammatical_info,
    parse_xml_entry,
)


class TestCdslModels(unittest.TestCase):
    def test_entry_creation(self):
        entry = CdslEntry(
            dict_id="MW",
            key="agni",
            key_normalized="agni",
            lnum=Decimal("1.0"),
            data="<H1><h><key1>agni</key1></h></H1>",
        )
        self.assertEqual(entry.dict_id, "MW")
        self.assertEqual(entry.key, "agni")
        self.assertEqual(entry.lnum, Decimal("1.0"))

    def test_entry_with_key2(self):
        entry = CdslEntry(
            dict_id="MW",
            key="agni",
            key_normalized="agni",
            key2="ahoratra",
            key2_normalized="ahoratra",
            lnum=Decimal("1.0"),
            data="<H1><h><key1>agni</key1><key2>ahoratra</key2></h></H1>",
        )
        self.assertEqual(entry.key2, "ahoratra")
        self.assertEqual(entry.key2_normalized, "ahoratra")


class TestCdslParser(unittest.TestCase):
    def test_parse_simple_entry(self):
        xml_data = """<H1>
<h><key1>agni</key1></h>
<body>Agni, fire, the god of fire.</body>
<tail><L>1</L><pc>001-a</pc></tail>
</H1>"""
        entry = parse_xml_entry(xml_data)
        self.assertIsNotNone(entry)
        entry = cast(CdslEntry, entry)
        self.assertEqual(entry.key, "agni")
        self.assertEqual(entry.key_normalized, "agni")
        self.assertEqual(entry.lnum, Decimal("1"))
        self.assertIsNotNone(entry.body)
        self.assertEqual(entry.page_ref, "001-a")

    def test_parse_entry_with_key2(self):
        xml_data = """<H1>
<h><key1>agni</key1><key2>ahoratra</key2></h>
<body>Multi-word entry.</body>
<tail><L>2</L></tail>
</H1>"""
        entry = parse_xml_entry(xml_data)
        self.assertIsNotNone(entry)
        entry = cast(CdslEntry, entry)
        self.assertEqual(entry.key, "agni")
        self.assertEqual(entry.key2, "ahoratra")

    def test_parse_invalid_xml(self):
        entry = parse_xml_entry("<not-valid-xml")
        self.assertIsNone(entry)

    def test_extract_headwords(self):
        entry = CdslEntry(
            dict_id="MW",
            key="agni",
            key_normalized="agni",
            key2="ahoratra",
            key2_normalized="ahoratra",
            lnum=Decimal("1"),
        )
        headwords = extract_headwords(entry)
        self.assertEqual(len(headwords), 2)
        self.assertEqual(headwords[0], ("agni", "agni", True))
        self.assertEqual(headwords[1], ("ahoratra", "ahoratra", False))

    def test_extract_headwords_single(self):
        entry = CdslEntry(
            dict_id="MW",
            key="agni",
            key_normalized="agni",
            lnum=Decimal("1"),
        )
        headwords = extract_headwords(entry)
        self.assertEqual(len(headwords), 1)
        self.assertEqual(headwords[0], ("agni", "agni", True))


class TestCdslCore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_mwe.db"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_normalize_key(self):
        self.assertEqual(normalize_key("Agni"), "agni")
        self.assertEqual(normalize_key("  AGNI  "), "agni")
        self.assertEqual(normalize_key("agni"), "agni")

    def test_to_slp1_basic(self):
        result = to_slp1("agni")
        self.assertEqual(result, "agni")

    def test_build_dict(self):
        from langnet.config import config

        dict_dir = config.cdsl_dict_dir
        if not (dict_dir / "MWE" / "web" / "sqlite" / "mwe.sqlite").exists():
            self.skipTest("MWE source data not available")

        count = build_dict(dict_dir / "MWE", self.db_path, "MWE", limit=100)
        self.assertGreater(count, 0)

        with CdslIndex(self.db_path) as index:
            info = index.get_info("MWE")
            self.assertEqual(info["entry_count"], count)

    def test_lookup(self):
        from langnet.config import config

        dict_dir = config.cdsl_dict_dir
        if not (dict_dir / "MWE" / "web" / "sqlite" / "mwe.sqlite").exists():
            self.skipTest("MWE source data not available")

        build_dict(dict_dir / "MWE", self.db_path, "MWE", limit=500)

        with CdslIndex(self.db_path) as index:
            results = index.lookup("MWE", "a")
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0].key, "a")

    def test_prefix_search(self):
        from langnet.config import config

        dict_dir = config.cdsl_dict_dir
        if not (dict_dir / "MWE" / "web" / "sqlite" / "mwe.sqlite").exists():
            self.skipTest("MWE source data not available")

        build_dict(dict_dir / "MWE", self.db_path, "MWE", limit=500)

        with CdslIndex(self.db_path) as index:
            results = index.prefix_search("MWE", "ab", limit=10)
            self.assertGreater(len(results), 0)
            for key, lnum in results:
                self.assertTrue(key.lower().startswith("ab"))

    def test_list_dicts(self):
        dict_dir = Path(os.getenv("CDSL_DICT_DIR", str(Path.home() / "cdsl_data" / "dict")))
        if not (dict_dir / "MWE" / "web" / "sqlite" / "mwe.sqlite").exists():
            self.skipTest("MWE source data not available")

        build_dict(dict_dir / "MWE", self.db_path, "MWE", limit=100)

        with CdslIndex(self.db_path) as index:
            dicts = index.list_dicts()
            self.assertIn("MWE", dicts)


class TestGrammaticalParser(unittest.TestCase):
    def test_parse_pos_and_gender(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>m.</lex> fire, sacrificial fire<info lex="m"/></body>
            <tail><L>1</L></tail>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertEqual(info["pos"], "m.")
        self.assertEqual(info["gender"], ["masculine"])

    def test_parse_pos_feminine(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agnI</s>   <lex>f.</lex> feminine form<info lex="f"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertEqual(info["pos"], "f.")
        self.assertEqual(info["gender"], ["feminine"])

    def test_parse_pos_neuter(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>n.</lex> neuter form<info lex="n"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertEqual(info["pos"], "n.")
        self.assertEqual(info["gender"], ["neuter"])

    def test_parse_pos_all_genders(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>mfn.</lex> all genders<info lex="m:n"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertEqual(info["pos"], "mfn.")
        self.assertEqual(sorted(info["gender"]), ["feminine", "masculine", "neuter"])

    def test_parse_verb_root(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>m.</lex> (√ <s>ag</s>), fire<info lex="m"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertIsNotNone(info["etymology"])
        self.assertEqual(info["etymology"]["type"], "verb_root")
        self.assertEqual(info["etymology"]["root"], "ag")

    def test_parse_sanskrit_form(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni/</s>   <lex>m.</lex> form<info lex="m"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertEqual(info["sanskrit_form"], "agni/")

    def test_parse_declension(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>mf(<s>A</s>)n.</lex> form<info lex="m:f#A:n"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertIn("grammar_tags", info)
        self.assertEqual(info["grammar_tags"]["declension"], "A")

    def test_parse_compound(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>m. <ab>comp.</ab></lex> compound word<info lex="m"/></body>
            <tail><L>1</L></tail>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertTrue(
            "grammar_tags" in info
            and "compound" in info["grammar_tags"]
            and info["grammar_tags"]["compound"] is True
        )

    def test_parse_abbreviations(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>m. <ab>Uṇ.</ab></lex> form<info lex="m"/></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertIn("grammar_tags", info)
        self.assertIn("abbreviations", info["grammar_tags"])
        # Check for both with and without dot
        self.assertTrue(
            "Uṇ" in info["grammar_tags"]["abbreviations"]
            or "Uṇ." in info["grammar_tags"]["abbreviations"]
        )

    def test_parse_references(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>m.</lex> see <ls>L.</ls> and <ls>TS.</ls></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertGreater(len(info["references"]), 0)
        self.assertEqual(info["references"][0]["type"], "lexicon")

    def test_parse_cross_reference(self):
        xml_data = """<H1>
            <h><key1>agni</key1></h>
            <body><s>agni</s>   <lex>m.</lex> see <s1>agnI</s1></body>
        </H1>"""
        info = parse_grammatical_info(xml_data)
        self.assertGreater(len(info["references"]), 0)
        cross_refs = [r for r in info["references"] if r["type"] == "cross_reference"]
        self.assertGreater(len(cross_refs), 0)


class TestSanskritDictionaryResponse(unittest.TestCase):
    def test_transliteration_structure(self):
        from langnet.cologne.models import (
            SanskritTransliteration,
        )

        trans = SanskritTransliteration(
            input="agni",
            iast="agni",
            hk="agni",
            devanagari="अग्नि",
        )

        self.assertEqual(trans.input, "agni")
        self.assertEqual(trans.iast, "agni")
        self.assertEqual(trans.hk, "agni")
        self.assertEqual(trans.devanagari, "अग्नि")

    def test_dictionary_entry_grammatical_fields(self):
        entry = SanskritDictionaryEntry(
            id="1",
            meaning="fire",
            pos="m.",
            gender=["masculine"],
            sanskrit_form="agni/",
            etymology={"type": "verb_root", "root": "ag"},
            grammar_tags={"declension": "A"},
            references=[{"source": "L.", "type": "lexicon"}],
            page_ref="1,1",
        )

        self.assertEqual(entry.pos, "m.")
        self.assertEqual(entry.gender, ["masculine"])
        self.assertEqual(entry.sanskrit_form, "agni/")
        assert entry.etymology is not None
        self.assertEqual(entry.etymology["type"], "verb_root")
        assert entry.grammar_tags is not None
        self.assertEqual(entry.grammar_tags["declension"], "A")
        assert entry.references is not None
        self.assertEqual(len(entry.references), 1)


if __name__ == "__main__":
    unittest.main()
