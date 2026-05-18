from __future__ import annotations

# ruff: noqa: E501, PLR2004
from io import StringIO
from pathlib import Path

from langnet.parsing.bailly_pdf_xml import (
    classify_bailly_page,
    extract_book_entries_from_pages,
    extract_page_entries,
    iter_poppler_pages,
    page_lines,
)

PAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="90" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="13" size="8" family="BPEVAH+LibertinusSerif" color="#000000"/>
    <fontspec id="14" size="8" family="PVQLQT+LibertinusSerif" color="#000000"/>
    <fontspec id="15" size="8" family="WCPBCW+MTGreek90" color="#000000"/>
    <fontspec id="30" size="8" family="WCPBCW+MTGreek90-Semibold" color="#000000"/>
    <fontspec id="31" size="10" family="PVJWQL+LibertinusSerif-Semibold" color="#000000"/>
    <fontspec id="35" size="8" family="PVJWQL+LibertinusSerif-Semibold" color="#000000"/>
    <text top="151" left="104" width="103" height="14" font="30">ἀγελαῖος, α, ον</text>
    <text top="151" left="212" width="5" height="15" font="14">[</text>
    <text top="152" left="217" width="15" height="14" font="15">ᾰγ</text>
    <text top="151" left="232" width="5" height="15" font="14">]</text>
    <text top="149" left="242" width="5" height="17" font="35"><b>I</b></text>
    <text top="151" left="253" width="132" height="15" font="14">qui forme un troupeau,</text>
    <text top="151" left="390" width="31" height="15" font="13"><i>d’où :</i></text>
    <text top="149" left="427" width="8" height="19" font="31"><b>1</b></text>
    <text top="167" left="91" width="175" height="15" font="14">qui paît en pleine campagne :</text>
    <text top="168" left="272" width="89" height="14" font="15">βοῦς ἀγελαῖαι,</text>
</page>
</pdf2xml>
"""

EXTRACTION_PAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="90" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="3" size="13" family="BPEVAH+LibertinusSerif" color="#000000"/>
    <fontspec id="4" size="16" family="WCPBCW+MTGreek90" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="7" size="15" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <fontspec id="8" size="16" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="104" width="118" height="14" font="2">ἀγελαιο·κομική, ῆς</text>
    <text top="118" left="225" width="4" height="15" font="5">(</text>
    <text top="119" left="229" width="8" height="14" font="4">ἡ</text>
    <text top="118" left="237" width="13" height="15" font="5">) [</text>
    <text top="119" left="250" width="8" height="14" font="4">ᾰ</text>
    <text top="118" left="257" width="5" height="15" font="5">]</text>
    <text top="118" left="266" width="20" height="15" font="3"><i>s. e.</i></text>
    <text top="119" left="291" width="38" height="14" font="4">τέχνη,</text>
    <text top="118" left="333" width="103" height="15" font="5">l’art de soigner les</text>
    <text top="134" left="91" width="59" height="15" font="5">troupeaux,</text>
    <text top="134" left="153" width="30" height="15" font="5">Plat.</text>
    <text top="134" left="187" width="41" height="15" font="3"><i>Pol. 275</i></text>
    <text top="134" left="231" width="13" height="15" font="5">e (</text>
    <text top="136" left="244" width="98" height="14" font="4">ἀγελαῖος, κομέω</text>
    <text top="134" left="342" width="7" height="15" font="5">).</text>
    <text top="151" left="104" width="103" height="14" font="2">ἀγελαῖος, α, ον</text>
    <text top="151" left="212" width="5" height="15" font="5">[</text>
    <text top="152" left="217" width="15" height="14" font="4">ᾰγ</text>
    <text top="151" left="232" width="5" height="15" font="5">]</text>
    <text top="149" left="242" width="5" height="17" font="7"><b>I</b></text>
    <text top="151" left="253" width="132" height="15" font="5">qui forme un troupeau,</text>
    <text top="151" left="390" width="31" height="15" font="3"><i>d’où :</i></text>
    <text top="149" left="427" width="8" height="19" font="8"><b>1</b></text>
    <text top="167" left="91" width="175" height="15" font="5">qui paît en pleine campagne :</text>
    <text top="168" left="272" width="89" height="14" font="4">βοῦς ἀγελαῖαι,</text>
    <text top="167" left="367" width="20" height="15" font="5">Od.</text>
    <text top="167" left="393" width="42" height="15" font="3"><i>10, 410,</i></text>
    <text top="183" left="91" width="25" height="15" font="3"><i>etc. ;</i></text>
    <text top="183" left="122" width="31" height="15" font="5">Soph.</text>
    <text top="183" left="158" width="41" height="15" font="3"><i>Aj. 175,</i></text>
    <text top="183" left="202" width="126" height="15" font="5">troupeau de génisses ||</text>
    <text top="182" left="333" width="8" height="19" font="8"><b>2</b></text>
    <text top="183" left="351" width="84" height="15" font="5">qui paît encore</text>
    <text top="200" left="91" width="124" height="15" font="5">au milieu du troupeau,</text>
    <text top="200" left="218" width="30" height="15" font="3"><i>c. à d.</i></text>
    <text top="200" left="253" width="167" height="15" font="5">qui n’a pas été soumis au joug,</text>
    <text top="200" left="423" width="13" height="15" font="5">Il.</text>
    <text top="216" left="91" width="37" height="15" font="3"><i>11, 729</i></text>
    <text top="216" left="133" width="6" height="15" font="5">||</text>
    <text top="215" left="143" width="8" height="19" font="8"><b>3</b></text>
    <text top="216" left="161" width="90" height="15" font="5">réuni en troupe,</text>
    <text top="264" left="331" width="10" height="17" font="7"><b>II</b></text>
    <text top="266" left="347" width="88" height="15" font="5">du troupeau, de</text>
    <text top="282" left="91" width="137" height="15" font="5">la foule, de la multitude,</text>
    <text top="315" left="367" width="4" height="15" font="5">(</text>
    <text top="316" left="371" width="35" height="14" font="4">ἀγέλη</text>
    <text top="315" left="407" width="7" height="15" font="5">).</text>
    <text top="332" left="104" width="121" height="14" font="2">ἀγελαιοτροφία, ας</text>
    <text top="331" left="229" width="4" height="15" font="5">(</text>
    <text top="333" left="233" width="8" height="14" font="4">ἡ</text>
    <text top="331" left="240" width="51" height="15" font="5">) l’élève (</text>
</page>
</pdf2xml>
"""


def test_iter_poppler_pages_preserves_text_geometry_font_and_style() -> None:
    page = next(iter_poppler_pages(StringIO(PAGE_XML)))

    assert page.number == 90
    assert page.width == 892
    assert page.height == 1262
    assert page.fonts["30"].family == "WCPBCW+MTGreek90-Semibold"
    assert page.texts[0].text == "ἀγελαῖος, α, ον"
    assert page.texts[0].left == 104
    assert page.texts[0].font_id == "30"
    assert page.texts[4].text == "I"
    assert page.texts[4].bold is True
    assert page.texts[6].italic is True


def test_page_lines_groups_nearby_text_chunks_without_flattening_layout() -> None:
    page = next(iter_poppler_pages(StringIO(PAGE_XML)))

    lines = page_lines(page)

    assert len(lines) == 2
    assert lines[0].page == 90
    assert lines[0].top == 149
    assert lines[0].left == 104
    assert lines[0].text == "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau, d’où : 1"
    assert lines[0].chunks[4].text == "I"
    assert lines[0].chunks[7].text == "1"
    assert lines[1].text == "qui paît en pleine campagne : βοῦς ἀγελαῖαι,"
    assert lines[1].left == 91


def test_extract_page_entries_splits_headwords_and_marker_paths_from_layout() -> None:
    page = next(iter_poppler_pages(StringIO(EXTRACTION_PAGE_XML)))

    entries = extract_page_entries(page)
    agelaios = next(entry for entry in entries if entry["lemma"] == "ἀγελαῖος")

    assert agelaios["entry_id"] == "bailly-p090-c1-0002"
    assert agelaios["lemma_norm"] == "agelaios"
    assert [(block["path"], block["marker"]) for block in agelaios["blocks"]] == [
        ("00", "head"),
        ("01", "I"),
        ("01:00", "1"),
        ("01:01", "2"),
        ("01:02", "3"),
        ("02", "II"),
    ]
    assert agelaios["blocks"][0]["text"] == "ἀγελαῖος, α, ον [ ᾰγ ]"
    assert agelaios["blocks"][1]["text"] == "qui forme un troupeau, d’où :"
    assert agelaios["blocks"][2]["text"].startswith("qui paît en pleine campagne")
    assert "Soph. Aj. 175" in agelaios["blocks"][2]["text"]
    assert agelaios["blocks"][3]["text"].startswith("qui paît encore")
    assert agelaios["blocks"][4]["text"].startswith("réuni en troupe")
    assert agelaios["blocks"][5]["text"].startswith("du troupeau, de la foule")
    assert agelaios["blocks"][2]["layout"]["page"] == 90
    assert agelaios["blocks"][2]["layout"]["column"] == 1


def test_classify_bailly_pages_uses_dictionary_body_boundaries() -> None:
    assert classify_bailly_page(1) == "front_matter"
    assert classify_bailly_page(80) == "front_matter"
    assert classify_bailly_page(81) == "dictionary_body"
    assert classify_bailly_page(2574) == "dictionary_body"
    assert classify_bailly_page(2575) == "back_matter"
    assert classify_bailly_page(2576) == "back_matter"


def test_extract_book_entries_attaches_continuation_pages_to_active_entry() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="100" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="7" size="15" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="104" width="80" height="14" font="2">ἀρχή, ῆς</text>
    <text top="118" left="190" width="5" height="17" font="7"><b>I</b></text>
    <text top="118" left="205" width="120" height="15" font="5">commencement</text>
</page>
<page number="101" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="8" size="16" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="91" width="8" height="19" font="8"><b>1</b></text>
    <text top="118" left="110" width="120" height="15" font="5">first continuation</text>
</page>
<page number="102" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <text top="118" left="104" width="80" height="14" font="2">ἄρχω</text>
    <text top="118" left="190" width="120" height="15" font="5">to rule</text>
</page>
</pdf2xml>
"""
    pages = list(iter_poppler_pages(StringIO(xml)))

    entries = extract_book_entries_from_pages(pages)

    assert [entry["lemma"] for entry in entries] == ["ἀρχή", "ἄρχω"]
    assert entries[0]["source"] == {"kind": "pdf", "page_start": 100, "page_end": 101}
    assert [(block["path"], block["marker"]) for block in entries[0]["blocks"]] == [
        ("00", "head"),
        ("01", "I"),
        ("01:00", "1"),
    ]
    assert entries[0]["blocks"][2]["text"] == "first continuation"
    assert entries[0]["blocks"][2]["layout"]["page"] == 101
    assert entries[1]["source"] == {"kind": "pdf", "page_start": 102, "page_end": 102}


def test_extract_book_entries_preserves_letter_roman_number_marker_depth() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="110" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="7" size="15" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <fontspec id="8" size="16" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="104" width="80" height="14" font="2">γίγνομαι</text>
    <text top="118" left="190" width="5" height="17" font="7"><b>A</b></text>
    <text top="118" left="205" width="120" height="15" font="5">propr. devenir</text>
    <text top="134" left="190" width="5" height="17" font="7"><b>B</b></text>
    <text top="134" left="205" width="120" height="15" font="5">p. suite :</text>
    <text top="150" left="220" width="5" height="17" font="7"><b>I</b></text>
    <text top="150" left="235" width="120" height="15" font="5">naître</text>
    <text top="166" left="220" width="10" height="17" font="7"><b>II</b></text>
    <text top="166" left="240" width="120" height="15" font="5">choses :</text>
    <text top="182" left="245" width="8" height="19" font="8"><b>1</b></text>
    <text top="182" left="265" width="120" height="15" font="5">phénomènes</text>
</page>
</pdf2xml>
"""
    page = next(iter_poppler_pages(StringIO(xml)))

    entries = extract_book_entries_from_pages([page])

    assert [(block["path"], block["marker"]) for block in entries[0]["blocks"]] == [
        ("00", "head"),
        ("01", "A"),
        ("02", "B"),
        ("02:00", "I"),
        ("02:01", "II"),
        ("02:01:00", "1"),
    ]


def test_extract_book_entries_treats_fleche_font_as_top_level_marker() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="110" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="7" size="15" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <fontspec id="8" size="16" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <fontspec id="9" size="16" family="QETXMO+fleche" color="#000000"/>
    <text top="118" left="104" width="80" height="14" font="2">γίγνομαι</text>
    <text top="118" left="190" width="10" height="17" font="7"><b>III</b></text>
    <text top="118" left="210" width="120" height="15" font="5">devenir</text>
    <text top="134" left="190" width="8" height="19" font="8"><b>1</b></text>
    <text top="134" left="210" width="120" height="15" font="5">avec un attrib.</text>
    <text top="150" left="104" width="12" height="16" font="9">D</text>
    <text top="150" left="145" width="8" height="19" font="8"><b>1</b></text>
    <text top="150" left="165" width="120" height="15" font="5">Syntaxe :</text>
    <text top="166" left="145" width="8" height="19" font="8"><b>2</b></text>
    <text top="166" left="165" width="120" height="15" font="5">Formes :</text>
</page>
</pdf2xml>
"""
    page = next(iter_poppler_pages(StringIO(xml)))

    entries = extract_book_entries_from_pages([page])

    assert [(block["path"], block["marker"]) for block in entries[0]["blocks"]] == [
        ("00", "head"),
        ("01", "III"),
        ("01:00", "1"),
        ("02", "E"),
        ("02:00", "1"),
        ("02:01", "2"),
    ]
    assert entries[0]["blocks"][3]["layout"]["marker_x"] == 104


def test_extract_book_entries_repairs_line_break_hyphenation() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<pdf2xml producer="poppler" version="25.10.0">
<page number="120" position="absolute" top="0" left="0" height="1262" width="892">
    <fontspec id="2" size="14" family="CEBKHF+Hippias-Identity-H" color="#000000"/>
    <fontspec id="4" size="16" family="WCPBCW+MTGreek90" color="#000000"/>
    <fontspec id="5" size="13" family="ATEVQI+LinLibertineO-Identity-H" color="#000000"/>
    <fontspec id="7" size="15" family="PVJWQL+LibertinusSerif-Semibold-Identity-H" color="#000000"/>
    <text top="118" left="104" width="80" height="14" font="2">ἥρως, ωος</text>
    <text top="118" left="190" width="5" height="17" font="7"><b>I</b></text>
    <text top="118" left="205" width="230" height="15" font="5">maître, chef, noble, en parl. des chefs mi-</text>
    <text top="134" left="91" width="210" height="15" font="5">litaires des Grecs devant Troie ; le héraut Mu-</text>
    <text top="150" left="91" width="100" height="15" font="5">lios</text>
    <text top="166" left="91" width="5" height="17" font="7"><b>II</b></text>
    <text top="166" left="110" width="80" height="14" font="4">θε-</text>
    <text top="166" left="195" width="130" height="14" font="4">ὸν ἢ δαίμο-</text>
    <text top="182" left="91" width="80" height="14" font="4">νας</text>
</page>
</pdf2xml>
"""
    page = next(iter_poppler_pages(StringIO(xml)))

    entries = extract_book_entries_from_pages([page])
    entry = entries[0]
    block_text = "\n".join(block["text"] for block in entry["blocks"])

    assert "mi- litaires" not in entry["raw_text"]
    assert "Mu- lios" not in entry["raw_text"]
    assert "θε- ὸν" not in entry["raw_text"]
    assert "δαίμο- νας" not in entry["raw_text"]
    assert "militaires" in entry["raw_text"]
    assert "Mulios" in entry["raw_text"]
    assert "θεὸν" in entry["raw_text"]
    assert "δαίμονας" in entry["raw_text"]
    assert "militaires" in block_text
    assert "θεὸν ἢ δαίμονας" in block_text


def test_real_gignomai_pages_keep_entry_open_across_continuation_pages() -> None:
    entries = _real_entries_for_pages([543, 544, 545])
    if not entries:
        return

    gignomai = next(entry for entry in entries if entry["lemma"] == "γίγνομαι")

    assert gignomai["source"] == {"kind": "pdf", "page_start": 543, "page_end": 545}
    assert [(block["path"], block["marker"]) for block in gignomai["blocks"][:16]] == [
        ("00", "head"),
        ("01", "A"),
        ("02", "B"),
        ("02:00", "I"),
        ("02:01", "II"),
        ("02:01:00", "1"),
        ("02:01:01", "2"),
        ("02:01:02", "3"),
        ("02:01:03", "4"),
        ("02:01:04", "5"),
        ("02:02", "III"),
        ("02:02:00", "1"),
        ("02:02:01", "2"),
        ("03", "E"),
        ("03:00", "1"),
        ("03:01", "2"),
    ]
    assert gignomai["blocks"][13]["text"] == ""
    assert "Syntaxe" in gignomai["blocks"][14]["text"]


def test_real_ei_pages_keep_entry_open_until_next_headword() -> None:
    entries = _real_entries_for_pages([746, 747, 748, 749])
    if not entries:
        return

    ei = next(entry for entry in entries if entry["lemma"] == "εἰ")

    assert ei["source"] == {"kind": "pdf", "page_start": 746, "page_end": 749}
    assert ei["blocks"][0]["marker"] == "head"
    assert ei["blocks"][0]["text"].startswith("εἰ, épq. et dor. αἰ")
    assert any(
        block["marker"] == "D" and "εἰ joint à des pronoms" in block["text"]
        for block in ei["blocks"]
    )
    assert entries[entries.index(ei) + 1]["lemma"] == "1 εἶ"


def _real_entries_for_pages(page_numbers: list[int]) -> list[dict[str, object]]:
    base = Path("/home/nixos/digital-bailly-pdf/xml-pages")
    paths = [base / f"bailly-2020-p{page_number:04d}.xml" for page_number in page_numbers]
    if not all(path.exists() for path in paths):
        return []
    pages = []
    for path in paths:
        pages.extend(iter_poppler_pages(path))
    return extract_book_entries_from_pages(pages)
