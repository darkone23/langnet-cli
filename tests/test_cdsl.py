import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import cast

from langnet.cologne.models import CdslEntry, DictMetadata, CdslQueryResult
from langnet.cologne.parser import parse_xml_entry, extract_headwords, extract_homonyms
from langnet.cologne.core import (
    CdslIndex,
    CdslIndexBuilder,
    build_dict,
    normalize_key,
    to_slp1,
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
        dict_dir = Path(
            os.getenv("CDSL_DICT_DIR", str(Path.home() / "cdsl_data" / "dict"))
        )
        if not (dict_dir / "MWE" / "web" / "sqlite" / "mwe.sqlite").exists():
            self.skipTest("MWE source data not available")

        build_dict(dict_dir / "MWE", self.db_path, "MWE", limit=100)

        with CdslIndex(self.db_path) as index:
            dicts = index.list_dicts()
            self.assertIn("MWE", dicts)


if __name__ == "__main__":
    unittest.main()
