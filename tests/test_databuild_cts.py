from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.cts import CtsBuildConfig, CtsUrnBuilder

CTS_NS = "http://chs.harvard.edu/xmlns/cts"


def _write_xml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cts_builder_minimal_perseus_and_legacy() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        perseus_root = base / "perseus"
        legacy_root = base / "Classics-Data"
        out_path = base / "cts.duckdb"

        textgroup_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ti:textgroup xmlns:ti="{CTS_NS}" urn="urn:cts:latinLit:phi0959">
  <ti:groupname xml:lang="lat">Vergilius</ti:groupname>
</ti:textgroup>
"""
        work_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ti:work xmlns:ti="{CTS_NS}" urn="urn:cts:latinLit:phi0959.phi006">
  <ti:title xml:lang="lat">Aeneid</ti:title>
  <ti:edition urn="urn:cts:latinLit:phi0959.phi006.perseus-lat2">
    <ti:label>Aen.</ti:label>
    <ti:description>Perseus Latin edition</ti:description>
  </ti:edition>
</ti:work>
"""
        _write_xml(
            perseus_root / "canonical-latinLit" / "data" / "phi0959" / "__cts__.xml", textgroup_xml
        )
        _write_xml(
            perseus_root / "canonical-latinLit" / "data" / "phi0959" / "phi006" / "__cts__.xml",
            work_xml,
        )

        # Minimal greekLit fixture to avoid missing-root warnings
        grc_textgroup_xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ti:textgroup xmlns:ti=\"{CTS_NS}\" urn=\"urn:cts:greekLit:tlg0012\">
  <ti:groupname xml:lang=\"grc\">Homer</ti:groupname>
</ti:textgroup>
"""
        grc_work_xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ti:work xmlns:ti=\"{CTS_NS}\" urn=\"urn:cts:greekLit:tlg0012.tlg001\">
  <ti:title xml:lang=\"grc\">Iliad</ti:title>
  <ti:edition urn=\"urn:cts:greekLit:tlg0012.tlg001.perseus-grc2\">
    <ti:label>Il.</ti:label>
    <ti:description>Perseus Greek edition</ti:description>
  </ti:edition>
</ti:work>
"""
        _write_xml(
            perseus_root / "canonical-greekLit" / "data" / "tlg0012" / "__cts__.xml",
            grc_textgroup_xml,
        )
        _write_xml(
            perseus_root / "canonical-greekLit" / "data" / "tlg0012" / "tlg001" / "__cts__.xml",
            grc_work_xml,
        )

        legacy_catalog = legacy_root / "Perseus_catalog" / "Perseus_parsed_catalog.txt"
        legacy_catalog.parent.mkdir(parents=True, exist_ok=True)
        legacy_catalog.write_text(
            "urn:cts:latinLit:phi0959\tlat\tLegacy Author\tLegacy Work\tlegacy\t-\tlegacy_source\n",
            encoding="utf-8",
        )

        config = CtsBuildConfig(
            perseus_dir=perseus_root,
            legacy_dir=legacy_root,
            output_path=out_path,
            include_legacy=True,
            wipe_existing=True,
        )
        builder = CtsUrnBuilder(config)
        result = builder.build()
        assert result.status == BuildStatus.SUCCESS, result.message
        assert out_path.exists()

        def _fetch_single_value(result, default=0):
            row = result.fetchone()
            return row[0] if row is not None else default

        conn = duckdb.connect(str(out_path))
        try:
            authors = _fetch_single_value(conn.execute("SELECT COUNT(*) FROM author_index"))
            works = _fetch_single_value(conn.execute("SELECT COUNT(*) FROM works"))
            editions = _fetch_single_value(conn.execute("SELECT COUNT(*) FROM editions"))
            title_result = conn.execute(
                "SELECT work_title FROM works WHERE work_urn='urn:cts:latinLit:phi0959.phi006'"
            ).fetchone()
            title = title_result[0] if title_result is not None else ""
        finally:
            conn.close()

        EXPECTED_AUTHOR_COUNT = 2  # Latin + Greek
        EXPECTED_WORK_COUNT = 3  # Perseus + Greek + legacy
        EXPECTED_EDITION_COUNT = 2
        assert authors == EXPECTED_AUTHOR_COUNT
        assert works == EXPECTED_WORK_COUNT
        assert editions == EXPECTED_EDITION_COUNT
        assert title == "Aeneid"
