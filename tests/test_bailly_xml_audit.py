# ruff: noqa: PLR2004

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from langnet.parsing.bailly_pdf_xml import BaillyXmlPageAudit, audit_bailly_xml_pages


def test_audit_bailly_xml_pages_reports_coverage_and_dictionary_pages(tmp_path: Path) -> None:
    source = Path("/home/nixos/digital-bailly-pdf/xml-pages/bailly-2020-p0090.xml")
    if not source.exists():
        return
    fixture = tmp_path / "bailly-2020-p0090.xml"
    fixture.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    report = audit_bailly_xml_pages(tmp_path)

    assert report.page_count == 1
    assert report.min_page == 90
    assert report.max_page == 90
    assert report.missing_pages == []
    assert report.pages[0].section == "dictionary_body"
    assert report.pages[0].page == 90
    assert report.pages[0].entry_count == 59
    assert report.pages[0].first_lemma == "ἀγελαδόν"
    assert report.pages[0].last_lemma == "ἀγέροχος"


def test_audit_report_as_rows_is_stable_for_tsv_output() -> None:
    audit = BaillyXmlPageAudit(
        page=90,
        path="bailly-2020-p0090.xml",
        section="dictionary_body",
        text_node_count=901,
        entry_count=59,
        first_lemma="ἀγελαδόν",
        last_lemma="ἀγέροχος",
        warning="",
    )

    assert audit.as_tsv_row() == [
        "90",
        "bailly-2020-p0090.xml",
        "dictionary_body",
        "901",
        "59",
        "ἀγελαδόν",
        "ἀγέροχος",
        "",
    ]


def test_dictionary_body_page_with_text_and_no_headword_is_continuation_candidate() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _assert_continuation_candidate_audit(tmp_path)


def _assert_continuation_candidate_audit(tmp_path: Path) -> None:
    (tmp_path / "bailly-2020-p0544.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="544" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <text top="118" left="91" width="120" height="15" font="5">continuation only</text>
</page>
</pdf2xml>
""",
        encoding="utf-8",
    )

    report = audit_bailly_xml_pages(tmp_path)

    assert report.pages[0].warning == "continuation_candidate"
