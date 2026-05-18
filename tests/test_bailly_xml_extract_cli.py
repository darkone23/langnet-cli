from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from click.testing import CliRunner

from langnet.cli import main


def test_bailly_xml_extract_writes_pdf_derived_structural_jsonl() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _run_bailly_xml_extract_assertion(tmp_path)


def _run_bailly_xml_extract_assertion(tmp_path: Path) -> None:
    (tmp_path / "bailly-2020-p0100.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="100" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="7" size="15" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="104" width="80" height="14" font="2">ἀρχή, ῆς</text>
    <text top="118" left="190" width="5" height="17" font="7"><b>I</b></text>
    <text top="118" left="205" width="120" height="15" font="5">commencement</text>
</page>
</pdf2xml>
""",
        encoding="utf-8",
    )
    (tmp_path / "bailly-2020-p0101.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="101" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="8" size="16" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="91" width="8" height="19" font="8"><b>1</b></text>
    <text top="118" left="110" width="120" height="15" font="5">first continuation</text>
</page>
</pdf2xml>
""",
        encoding="utf-8",
    )
    output = tmp_path / "bailly.jsonl"

    result = CliRunner().invoke(
        main, ["bailly-xml-extract", str(tmp_path), "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["lemma"] == "ἀρχή"
    assert rows[0]["source"] == {"kind": "pdf", "page_start": 100, "page_end": 101}
    assert [(block["path"], block["marker"]) for block in rows[0]["blocks"]] == [
        ("00", "head"),
        ("01", "I"),
        ("01:00", "1"),
    ]
