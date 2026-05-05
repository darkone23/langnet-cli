from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.diogenes import (
    DiogenesBuildConfig,
    DiogenesBuilder,
    extract_diogenes_index_entry,
    extract_diogenes_navigation,
    extract_diogenes_xml_index_entry,
)

NAV_OFFSET = 123
ENTRY_OFFSET = 200


def _entry_html(offset: int, headword: str) -> str:
    return f"""
    <html><body>
      <hr />
      <div>
        <a onClick="prevEntrylat({offset})">Previous Entry</a>
        <a onClick="nextEntrylat({offset})">Next Entry</a>
      </div>
      <h2><span>{headword}</span>, test header</h2>
      <div id="sense" style="padding-left: 0px;">{headword}, sample definition.</div>
    </body></html>
    """


def test_extract_diogenes_navigation_reads_prev_next_offsets() -> None:
    html = """
    <a onClick="prevEntrygrk(123)">Previous Entry</a>
    <a onClick="nextEntrygrk(123)">Next Entry</a>
    """

    navigation = extract_diogenes_navigation(html)

    assert navigation.current_offset == NAV_OFFSET
    assert navigation.previous_offset == NAV_OFFSET
    assert navigation.next_offset == NAV_OFFSET


def test_extract_diogenes_index_entry_projects_headword_and_lookup() -> None:
    entry = extract_diogenes_index_entry(
        _entry_html(ENTRY_OFFSET, "lupus"),
        language="lat",
        fetched_url="http://example.test/Perseus.cgi?do=parse&lang=lat&q=lupus",
    )

    assert entry is not None
    assert entry.offset == ENTRY_OFFSET
    assert entry.headword == "lupus"
    assert entry.lookup == "lupus"
    assert entry.previous_offset == ENTRY_OFFSET
    assert entry.next_offset == ENTRY_OFFSET


def test_extract_diogenes_xml_index_entry_uses_clean_greek_sort_key() -> None:
    entry = extract_diogenes_xml_index_entry(
        '<div1 key="apo"><head>ἀποϝειπάθθω</head> test</div1>',
        language="grc",
        offset=ENTRY_OFFSET,
        source_path=Path("grc.lsj.xml"),
    )

    assert entry is not None
    assert entry.lookup == "apoeipaqqo"
    assert entry.sort_key == "apoeipaqqo"
    assert "_" not in entry.headword_norm


def test_diogenes_builder_crawls_seed_prev_and_next_entries() -> None:
    pages = {
        ("parse", "a"): _entry_html(100, "a"),
        ("prev_entry", "100"): _entry_html(90, "ab"),
        ("next_entry", "100"): _entry_html(110, "abacus"),
    }
    calls: list[tuple[str, str]] = []

    def fake_fetch(_endpoint: str, params: Mapping[str, str]) -> tuple[int, str, str]:
        key = (params["do"], params["q"])
        calls.append(key)
        return (200, pages.get(key, _entry_html(100, "a")), f"http://example.test/{key[0]}")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "lex_diogenes_lat.duckdb"
        builder = DiogenesBuilder(
            DiogenesBuildConfig(
                language="lat",
                mode="crawl",
                endpoint="http://example.test/Perseus.cgi",
                output_path=output_path,
                seed_word="a",
                max_entries=3,
            ),
            fetch=fake_fetch,
        )

        result = builder.build()

        assert result.status == BuildStatus.SUCCESS, result.message
        with duckdb.connect(str(output_path), read_only=True) as conn:
            rows = conn.execute(
                "SELECT entry_offset, headword FROM entries ORDER BY entry_offset"
            ).fetchall()

    assert rows == [(90, "ab"), (100, "a"), (110, "abacus")]
    assert ("parse", "a") in calls
    assert ("prev_entry", "100") in calls
    assert ("next_entry", "100") in calls


def test_diogenes_builder_imports_direct_xml_source() -> None:
    source = "\n".join(
        [
            '<div1 key="a"><head orth_orig="a">a</head> first letter</div1>',
            '<div1 key="ab"><head orth_orig="ab">ab</head> from</div1>',
            '<div1 key="amo"><head orth_orig="ămo">amo</head> love</div1>',
        ]
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source_path = base / "lat.ls.perseus-eng1.xml"
        source_path.write_text(source, encoding="utf-8")
        output_path = base / "lex_diogenes_lat.duckdb"
        builder = DiogenesBuilder(
            DiogenesBuildConfig(
                language="lat",
                mode="direct",
                source_path=source_path,
                output_path=output_path,
                max_entries=None,
            )
        )

        result = builder.build()

        assert result.status == BuildStatus.SUCCESS, result.message
        with duckdb.connect(str(output_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT entry_offset, headword, lookup, previous_offset, next_offset
                FROM entries ORDER BY entry_offset
                """
            ).fetchall()

    assert [row[1] for row in rows] == ["a", "ab", "ămo"]
    assert [row[2] for row in rows] == ["a", "ab", "amo"]
    assert rows[0][3] is None
    assert rows[0][4] == rows[1][0]
    assert rows[1][3] == rows[0][0]
