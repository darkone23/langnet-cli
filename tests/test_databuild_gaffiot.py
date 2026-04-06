from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.gaffiot import GaffiotBuildConfig, GaffiotBuilder


def _make_gaffiot_xml(path: Path) -> None:
    xml = """
    <TEI>
      <text>
        <entryFree>
          <orth>amor</orth>
          <def>amor <lb/> ardor <lb/> caritas</def>
        </entryFree>
        <entryFree>
          <orth>bellum</orth>
          <def>bellum <lb/> proelium</def>
        </entryFree>
      </text>
    </TEI>
    """
    path.write_text(xml, encoding="utf-8")


def test_gaffiot_plain_text_preserves_line_breaks() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source_path = base / "gaffiot.xml"
        _make_gaffiot_xml(source_path)

        output_path = base / "lex_gaffiot.duckdb"
        builder = GaffiotBuilder(
            GaffiotBuildConfig(
                source_path=source_path,
                output_path=output_path,
                batch_size=10,
                wipe_existing=True,
            )
        )

        result = builder.build()
        assert result.status == BuildStatus.SUCCESS, result.message
        assert output_path.exists()

        conn = duckdb.connect(str(output_path))
        try:
            rows = conn.execute(
                "SELECT entry_id, headword_raw, plain_text FROM entries_fr ORDER BY entry_id"
            ).fetchall()
        finally:
            conn.close()

        assert rows[0][1] == "amor"
        assert rows[0][2] == "ardor\ncaritas"
        assert "\n" in rows[0][2]

        assert rows[1][1] == "bellum"
        assert rows[1][2] == "proelium"
