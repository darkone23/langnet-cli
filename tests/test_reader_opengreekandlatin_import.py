from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langnet.reader.opengreekandlatin import (
    discover_ogl_sources,
    is_ogl_source_xml,
    parse_ogl_tei,
    selected_ogl_sources,
)


def _write_tei(
    path: Path,
    *,
    title: str = "Fixture",
    author: str = "Author",
    urn: str | None = None,
    body: str = '<p n="1">lorem ipsum</p>',
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_attr = f' n="{urn}"' if urn else ""
    path.write_text(
        f"""
        <TEI xml:lang="lat">
          <teiHeader>
            <fileDesc>
              <titleStmt>
                <title>{title}</title>
                <author>{author}</author>
              </titleStmt>
            </fileDesc>
          </teiHeader>
          <text>
            <body>
              <div type="edition"{n_attr}>
                {body}
              </div>
            </body>
          </text>
        </TEI>
        """,
        encoding="utf-8",
    )


class OpenGreekAndLatinImportTest(unittest.TestCase):
    def test_ogl_discovery_prefers_data_over_alternate_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "patrologia"
            _write_tei(
                root / "data" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
                urn="urn:cts:latinLit:stoa0001.stoa001.opp-lat1",
            )
            _write_tei(
                root / "split" / "PL1" / "PL1_1.xml",
                urn="urn:cts:latinLit:stoa0001.stoa001.opp-lat2",
            )

            candidates = discover_ogl_sources(root, "opengreekandlatin_patrologia")

            self.assertEqual(
                [candidate.import_status for candidate in candidates],
                ["text_imported", "skipped_alternate_view"],
            )
            self.assertEqual(candidates[1].skip_reason, "alternate_view_split")
            self.assertEqual(
                selected_ogl_sources(root, "opengreekandlatin_patrologia"),
                [candidates[0]],
            )

    def test_ogl_discovery_marks_duplicate_work_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "csel"
            _write_tei(
                root / "data" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
                urn="urn:cts:latinLit:stoa0001.stoa001.opp-lat1",
                body='<p n="1">first edition</p>',
            )
            _write_tei(
                root / "data" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat2.xml",
                urn="urn:cts:latinLit:stoa0001.stoa001.opp-lat2",
                body='<p n="1">second edition</p>',
            )

            candidates = discover_ogl_sources(root, "opengreekandlatin_csel")

            self.assertEqual(
                [candidate.import_status for candidate in candidates],
                ["text_imported", "skipped_duplicate"],
            )
            self.assertEqual(candidates[1].skip_reason, "duplicate_work_id")

    def test_ogl_root_level_non_cts_files_get_distinct_synthetic_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "church_fathers"
            _write_tei(root / "first.xml", title="First")
            _write_tei(root / "second.xml", title="Second")

            candidates = discover_ogl_sources(root, "opengreekandlatin_church_fathers")
            selected = selected_ogl_sources(root, "opengreekandlatin_church_fathers")
            parsed = [parse_ogl_tei(candidate) for candidate in selected]

            self.assertEqual(
                [candidate.import_status for candidate in candidates],
                ["text_imported", "text_imported"],
            )
            self.assertEqual(len({item.work.work_id for item in parsed}), 2)
            self.assertTrue(
                all(item.work.work_id.startswith("urn:langnet:ogl:") for item in parsed)
            )
            self.assertTrue(
                all(item.work.cts_work_urn.startswith("urn:cts:langnet:") for item in parsed)
            )

    def test_ogl_discovery_marks_zero_segment_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "latin"
            _write_tei(
                root / "data" / "empty.xml",
                urn="urn:cts:latinLit:stoa0001.stoa001.opp-lat1",
                body='<div type="textpart" n="1" />',
            )

            candidates = discover_ogl_sources(root, "opengreekandlatin_latin")

            self.assertEqual(candidates[0].import_status, "skipped_no_segments")
            self.assertEqual(candidates[0].skip_reason, "no_text_segments")

    def test_ogl_filter_excludes_non_text_xml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            text = tmp_path / "data" / "text.xml"
            text.parent.mkdir()
            text.write_text("<TEI><text /></TEI>", encoding="utf-8")
            build = tmp_path / "build.xml"
            build.write_text("<project />", encoding="utf-8")
            target = tmp_path / "target" / "generated.xml"
            target.parent.mkdir()
            target.write_text("<TEI><text /></TEI>", encoding="utf-8")

            self.assertTrue(is_ogl_source_xml(text))
            self.assertFalse(is_ogl_source_xml(build))
            self.assertFalse(is_ogl_source_xml(target))

    def test_ogl_parser_uses_declared_tei_language_when_primary_language_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "church_fathers"
            path = root / "gregory.xml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                """
                <TEI xmlns="http://www.tei-c.org/ns/1.0">
                  <teiHeader>
                    <fileDesc>
                      <titleStmt>
                        <title>Fixture Greek Text</title>
                        <author>Gregory of Nazianzus</author>
                      </titleStmt>
                    </fileDesc>
                    <profileDesc>
                      <langUsage>
                        <language ident="grc">Greek</language>
                        <language ident="en">English</language>
                      </langUsage>
                    </profileDesc>
                  </teiHeader>
                  <text>
                    <body>
                      <div type="edition">
                        <p n="1">λόγος</p>
                      </div>
                    </body>
                  </text>
                </TEI>
                """,
                encoding="utf-8",
            )

            selected = selected_ogl_sources(root, "opengreekandlatin_church_fathers")
            parsed = parse_ogl_tei(selected[0])

            self.assertEqual(parsed.work.language, "grc")
            self.assertEqual(parsed.edition.language, "grc")


if __name__ == "__main__":
    unittest.main()
