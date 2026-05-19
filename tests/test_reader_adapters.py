from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.adapters import (
    _legacy_greek_beta_to_unicode,
    normalize_digiliblt_author,
    parse_dcs_conllu,
    parse_dcs_conllu_group,
    parse_digiliblt_tei,
    parse_legacy_text_dump,
    parse_legacy_text_dump_with_idt,
    parse_perseus_tei,
    parse_sanskrit_json,
    parse_sanskrit_numbered_text,
    parse_sanskrit_plain_text,
    parse_sanskrit_plain_text_group,
    resolve_digiliblt_author,
)

FIXTURES = Path("tests/fixtures/reader")


def test_parse_perseus_tei_builds_line_segments_and_cts_addresses() -> None:
    result = parse_perseus_tei(FIXTURES / "perseus_odyssey.xml")

    assert result.work.work_id == "urn:cts:greekLit:tlg0012.tlg002"
    assert result.work.author == "Homer"
    assert result.edition.edition_id == "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2"
    segments_by_citation = {segment.citation_path: segment for segment in result.segments}
    addresses = {address.address for address in result.addresses}
    assert segments_by_citation["1.8"].text == "νήπιοι, οἳ κατὰ βοῦς Ὑπερίονος Ἠελίοιο"
    assert segments_by_citation["3.74"].text == "ψυχὰς παρθέμενοι"
    assert "urn:cts:greekLit:tlg0012.tlg002:1.8" in addresses
    assert "urn:cts:greekLit:tlg0012.tlg002:3.74" in addresses


def test_parse_perseus_tei_builds_translation_section_segments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "thucydides_translation.xml"
        path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>The Peloponnesian War</title>
        <author>Thucydides</author>
      </titleStmt>
      <publicationStmt><p>Fixture</p></publicationStmt>
      <sourceDesc><p>Fixture</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="translation" xml:lang="eng" n="urn:cts:greekLit:tlg0003.tlg001.1st1K-eng1">
        <div type="textpart" subtype="book" n="1">
          <div type="textpart" subtype="chapter" n="1">
            <div type="textpart" subtype="section" n="1">
              <p>Thucydides wrote the history.</p>
            </div>
          </div>
        </div>
      </div>
    </body>
  </text>
</TEI>
""",
            encoding="utf-8",
        )

        result = parse_perseus_tei(path)

    assert result.work.work_id == "urn:cts:greekLit:tlg0003.tlg001"
    assert result.edition.edition_id == "urn:cts:greekLit:tlg0003.tlg001.1st1K-eng1"
    assert result.work.language == "eng"
    assert result.segments[0].segment_kind == "section"
    assert result.segments[0].citation_path == "1.1.1"
    assert result.segments[0].text == "Thucydides wrote the history."
    assert result.addresses[0].address == "urn:cts:greekLit:tlg0003.tlg001:1.1.1"


def test_parse_perseus_tei_disambiguates_duplicate_line_citations() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "duplicate_lines.xml"
        path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Greek Anthology</title>
        <author>Anonymous</author>
      </titleStmt>
      <publicationStmt><p>Fixture</p></publicationStmt>
      <sourceDesc><p>Fixture</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="edition" xml:lang="grc" n="urn:cts:greekLit:tlg7000.tlg001.perseus-grc10">
        <div type="textpart" subtype="book" n="15">
          <div type="textpart" subtype="epigram" n="22">
            <l n="1">first version</l>
            <l n="1">second version</l>
          </div>
        </div>
      </div>
    </body>
  </text>
</TEI>
""",
            encoding="utf-8",
        )

        result = parse_perseus_tei(path)

    assert [segment.citation_path for segment in result.segments] == ["15.22.1", "15.22.1.2"]
    assert [segment.text for segment in result.segments] == ["first version", "second version"]
    assert [address.address for address in result.addresses] == [
        "urn:cts:greekLit:tlg7000.tlg001:15.22.1",
        "urn:cts:greekLit:tlg7000.tlg001:15.22.1.2",
    ]


def test_parse_perseus_tei_builds_legacy_milestone_sections_without_edition_div() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "phi0914.phi0011.perseus-lat2.xml"
        path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Ab Urbe Condita</title>
        <author>Titus Livius</author>
      </titleStmt>
      <publicationStmt><p>Fixture</p></publicationStmt>
      <sourceDesc><p>Fixture</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text xml:lang="la">
    <body>
      <div type="book" n="1">
        <p>
          <milestone unit="chapter" n="pr"/>
          <milestone unit="section" n="1"/>
          facturusne operae pretium sim
          <milestone unit="section" n="2"/>
          si a primordio urbis res populi Romani perscripserim
        </p>
        <p>
          <milestone unit="section" n="3"/>
          utcumque erit
        </p>
      </div>
    </body>
  </text>
</TEI>
""",
            encoding="utf-8",
        )

        result = parse_perseus_tei(path)

    assert result.work.work_id == "urn:cts:latinLit:phi0914.phi0011"
    assert result.edition.edition_id == "urn:cts:latinLit:phi0914.phi0011.perseus-lat2"
    assert result.work.language == "lat"
    assert [segment.citation_path for segment in result.segments] == [
        "1.pr.1",
        "1.pr.2",
        "1.pr.3",
    ]
    assert result.segments[0].text == "facturusne operae pretium sim"


def test_parse_perseus_tei_repairs_legacy_named_entities() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "phi0692.phi001.perseus-lat1.xml"
        path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Elegiae</title>
        <author>Propertius</author>
      </titleStmt>
      <publicationStmt><p>Fixture</p></publicationStmt>
      <sourceDesc><p>Fixture &Perseus.OCR;</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text xml:lang="la">
    <body>
      <div1 type="poem" n="1">
        <p>Cynthia prima suis miserum me cepit ocellis &dagger;</p>
      </div1>
    </body>
  </text>
</TEI>
""",
            encoding="utf-8",
        )

        result = parse_perseus_tei(path)

    assert result.work.work_id == "urn:cts:latinLit:phi0692.phi001"
    assert result.segments[0].citation_path == "1"
    assert result.segments[0].text.endswith("†")


def test_parse_perseus_tei_recovers_malformed_legacy_xml() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "stoa0023.stoa001.perseus-eng3.xml"
        path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI>
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>The Roman History</title>
        <author>Ammianus Marcellinus</author>
      </titleStmt>
      <publicationStmt><p>Fixture</p></publicationStmt>
      <sourceDesc><p>Fixture</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text xml:lang="en">
    <body>
      <div1 type="book" n="1"><p>recovered text &mdash;</p></div1>
    </body>
  </text>
</TEI>
</body></text></TEI>
""",
            encoding="utf-8",
        )

        result = parse_perseus_tei(path)

    assert result.work.work_id == "urn:cts:latinLit:stoa0023.stoa001"
    assert result.work.language == "eng"
    assert result.segments[0].text == "recovered text —"


def test_parse_perseus_tei_uses_textpart_when_lines_are_unnumbered() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "phi0550.phi001.perseus-eng1.xml"
        path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>De Rerum Natura</title>
        <author>Lucretius</author>
      </titleStmt>
      <publicationStmt><p>Fixture</p></publicationStmt>
      <sourceDesc><p>Fixture</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="translation" xml:lang="eng" n="urn:cts:latinLit:phi0550.phi001.perseus-eng1">
        <div type="textpart" subtype="book" n="1">
          <div type="textpart" subtype="card" n="1">
            <l>Mother of Rome</l>
            <l>Dear Venus</l>
          </div>
        </div>
      </div>
    </body>
  </text>
</TEI>
""",
            encoding="utf-8",
        )

        result = parse_perseus_tei(path)

    assert [segment.citation_path for segment in result.segments] == ["1.1"]
    assert result.segments[0].segment_kind == "card"
    assert result.segments[0].text == "Mother of Rome Dear Venus"


def test_parse_digiliblt_tei_builds_paragraph_segments() -> None:
    result = parse_digiliblt_tei(FIXTURES / "digiliblt_sample.xml")

    assert result.work.collection_id == "digiliblt"
    assert result.work.title == "De controuersiis agrorum"
    assert result.work.author == "Siculus Flaccus"
    assert result.segments[0].segment_kind == "paragraph"
    assert "aduersantur" in result.segments[0].text


def test_resolve_digiliblt_author_uses_conservative_blank_author_evidence() -> None:
    assert resolve_digiliblt_author(
        explicit_author=None,
        title="Rufinus, Commentaria in metra Terentiana",
        source_desc="",
    ) == ("Rufinus Antiochensis", "resolved_from_title")
    assert resolve_digiliblt_author(
        explicit_author=None,
        title="Ars Bobiensis",
        source_desc="La grammatica dell' Anonymus Bobiensis",
    ) == ("Anonymous", "verified_anonymous")
    assert resolve_digiliblt_author(
        explicit_author=None,
        title="Asclepius",
        source_desc="Corpus Hermeticum",
    ) == ("Anonymous", "resolved_from_title")
    assert resolve_digiliblt_author(
        explicit_author=None,
        title="Appendix Probi",
        source_desc="Appendix Probi, edd. S. Asperti - M. Passalacqua, Firenze 2014",
    ) == ("Probus (Ps.)", "resolved_from_title")


def test_normalize_digiliblt_author_collapses_high_confidence_variants() -> None:
    assert normalize_digiliblt_author("Donatus, Aelius") == "Aelius Donatus"
    assert normalize_digiliblt_author("Seruius") == "Servius"
    assert normalize_digiliblt_author("Gargilius Martialis Ps.") == ("Gargilius Martialis (Ps.)")


def test_parse_sanskrit_json_builds_line_segments_from_tokens() -> None:
    result = parse_sanskrit_json(FIXTURES / "sanskrit_raghuvamsa.json")

    assert result.work.language == "san"
    assert result.work.title == "Raghuvaṃśa"
    assert result.work.author == "Kālidāsa"
    assert result.segments[0].text == "vāc artha iva"
    assert result.segments[0].citation_path == "1"


def test_parse_sanskrit_json_derives_gretil_author_from_filename() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_kAlidAsa-raghuvaMza.json"
        path.write_text(
            '{"text":"Raghuvaṃśa","lines":[[{"w":"vāc"},{"w":"artha"}]]}',
            encoding="utf-8",
        )

        result = parse_sanskrit_json(path)

    assert result.work.author == "Kālidāsa"


def test_parse_sanskrit_plain_text_builds_retrievable_lines() -> None:
    result = parse_sanskrit_plain_text(
        FIXTURES / "sanskrit_plain.txt",
        collection_id="sanskrit_texts",
        language="san",
    )

    assert result.work.language == "san"
    assert result.work.collection_id == "sanskrit_texts"
    assert result.segments[0].segment_kind == "line"
    assert result.segments[0].citation_path == "1"


def test_parse_sanskrit_plain_text_derives_gretil_author_from_filename() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_kAlidAsa-raghuvaMza.txt"
        path.write_text("namaḥ śivāya", encoding="utf-8")

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Kālidāsa"
    assert result.work.title == "Raghuvaṃśa"


def test_parse_sanskrit_plain_text_derives_gretil_title_without_author_prefix() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_agnipurANa.txt"
        path.write_text("namaḥ śivāya", encoding="utf-8")

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Unknown"
    assert result.work.title == "Agnipurāṇa"


def test_parse_sanskrit_plain_text_does_not_treat_title_prefix_as_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_aSTasAhasrikA-prajJApAramitA.txt"
        path.write_text("namaḥ śivāya", encoding="utf-8")

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Unknown"
    assert result.work.title == "Aṣṭasāhasrikā Prajñāpāramitā"


def test_parse_sanskrit_plain_text_keeps_or_title_prefix() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_IzopaniSad-or-IzAvAsyopaniSadkANva-recension-comm.txt"
        path.write_text("namaḥ śivāya", encoding="utf-8")

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Unknown"
    assert result.work.title == "Īśopaniṣad Or Īśāvāsyopaniṣadkāṇva Recension"


def test_parse_sanskrit_plain_text_keeps_variant_marker_with_title_prefix() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_maitreyavyAkaraNa-C.txt"
        path.write_text("namaḥ śivāya", encoding="utf-8")

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Unknown"
    assert result.work.title == "Maitreyavyākaraṇa C"


def test_parse_sanskrit_plain_text_does_not_treat_larger_as_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_larger-prajJApAramitA.txt"
        path.write_text("namaḥ śivāya", encoding="utf-8")

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Unknown"
    assert result.work.title == "Larger Prajñāpāramitā"


def test_parse_sanskrit_plain_text_prefers_header_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_ghaTakarparakAvya-comm.txt"
        path.write_text(
            "#Author:Abhinavagupta\n#Text:Ghaṭakarparakāvyavivṛti\nnamaḥ śivāya",
            encoding="utf-8",
        )

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Abhinavagupta"
    assert result.work.title == "Ghaṭakarparakāvyavivṛti"


def test_parse_sanskrit_plain_text_omits_gretil_header_preamble_from_segments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sa_nAgArjuna-dharmasaMgraha.txt"
        path.write_text(
            "\n".join(
                [
                    "#Author:Nāgārjuna",
                    "#Text:Dharmasaṃgraha",
                    "#Data entry:Members of the Digital Sanskrit Buddhist Canon Input Project",
                    "#P.L. Vaidya: Dharmasangraha. Darbhanga 1961.",
                    "",
                    "dharmasaṃgrahaḥ /",
                    "// namo ratnatrayāya //",
                ]
            ),
            encoding="utf-8",
        )

        result = parse_sanskrit_plain_text(
            path,
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.author == "Nāgārjuna"
    assert result.work.title == "Dharmasaṃgraha"
    assert [segment.text for segment in result.segments] == [
        "dharmasaṃgrahaḥ /",
        "// namo ratnatrayāya //",
    ]


def test_parse_sanskrit_plain_text_group_prefers_header_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        split_dir = Path(tmpdir) / "texts" / "Brahmana texts" / "AB"
        split_dir.mkdir(parents=True)
        first = split_dir / "01.txt"
        second = split_dir / "02.txt"
        first.write_text("#Text:Aitareyabrāhmaṇa\natha", encoding="utf-8")
        second.write_text("#Author:Mahidāsa Aitareya\niti", encoding="utf-8")

        result = parse_sanskrit_plain_text_group(
            [first, second],
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.title == "Aitareyabrāhmaṇa"
    assert result.work.author == "Mahidāsa Aitareya"


def test_parse_sanskrit_plain_text_group_keeps_curated_metadata_over_short_header() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        split_dir = Path(tmpdir) / "texts" / "sadvimsabrahmana" / "SB"
        split_dir.mkdir(parents=True)
        path = split_dir / "01.txt"
        path.write_text("#Text:SB\natha", encoding="utf-8")

        result = parse_sanskrit_plain_text_group(
            [path],
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.title == "Ṣaḍviṃśa Brāhmaṇa"
    assert result.work.author == "Anonymous"


def test_parse_sanskrit_plain_text_group_builds_one_addressable_work() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        split_dir = Path(tmpdir) / "texts" / "latyayanashrautasutra" / "split"
        split_dir.mkdir(parents=True)
        first = split_dir / "01-01.txt"
        second = split_dir / "01-02.txt"
        first.write_text("atha vidhyavyapadeśe || 1.1.1 ||\n", encoding="utf-8")
        second.write_text("mantravidhiś ca || 1.2.1 ||\n", encoding="utf-8")

        result = parse_sanskrit_plain_text_group(
            [second, first],
            collection_id="sanskrit_texts",
            language="san",
        )

    assert result.work.title == "Lāṭyāyana Śrautasūtra"
    assert result.work.author == "Lāṭyāyana"
    assert result.work.source_id == "latyayanashrautasutra_split"
    assert [segment.citation_path for segment in result.segments] == ["01-01.1", "01-02.1"]


def test_parse_sanskrit_numbered_text_converts_custom_pdf_encoding() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "output.txt"
        path.write_text(
            """ÞrÁmad-bhÀgavata-purÀÉam
Searchable file header
01010011 janmÀdyasya yato 'nvayÀditarataÌcÀrtheÍvabhijÈaÏ svarÀÊ
01010012 tene brahma hÃdÀ ya Àdikavaye muhyanti yat_sÂrayaÏ
01020101 kÀmasya nendriyaprÁtirlÀbho jÁveta yÀvatÀ
01020101 ataÏ pumbhirdvijaÌreÍÊhÀ varÉÀÌramavibhÀgaÌaÏ
""",
            encoding="utf-8",
        )

        result = parse_sanskrit_numbered_text(path)

    assert result.work.title == "Śrīmad-bhāgavata-purāṇam"
    assert result.work.collection_id == "sanskrit_texts"
    assert result.segments[0].citation_path == "1.1.1.1"
    assert result.segments[0].text == ("janmādyasya yato 'nvayāditarataścārtheṣvabhijñaḥ svarāṭ")
    assert result.segments[1].text == "tene brahma hṛdā ya ādikavaye muhyanti yat sūrayaḥ"
    assert result.segments[1].source_text == "tene brahma hṛdā ya ādikavaye muhyanti yat_sūrayaḥ"
    assert result.segments[2].citation_path == "1.2.10.1"
    assert result.segments[3].citation_path == "1.2.10.1.2"


def test_parse_dcs_conllu_builds_sentence_segments_with_sent_ids() -> None:
    result = parse_dcs_conllu(FIXTURES / "dcs_sample.conllu")

    assert result.work.collection_id == "sanskrit_dcs"
    assert result.work.language == "san"
    assert result.work.title == "Abhidharmakośa"
    assert result.edition.label == "DCS CoNLL-U"
    assert result.segments[0].segment_kind == "sentence"
    assert result.segments[0].citation_path == "478852"
    assert result.segments[0].text == "om namo buddhāya"
    assert result.addresses[0].address == (f"{result.work.work_id}:478852")


def test_parse_dcs_conllu_group_builds_one_work_from_many_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        first = root / "work-1.conllu"
        second = root / "work-2.conllu"
        first.write_text(
            """## text: Grouped Text
## text_id: grouped-1
## chapter: 1
## chapter_id: 10
# text = first sentence
# sent_id = 101
1	first	first	NOUN	_	_	_	_	_	_
""",
            encoding="utf-8",
        )
        second.write_text(
            """## text: Grouped Text
## text_id: grouped-1
## chapter: 2
## chapter_id: 11
# text = second sentence
# sent_id = 102
1	second	second	NOUN	_	_	_	_	_	_
""",
            encoding="utf-8",
        )

        result = parse_dcs_conllu_group([first, second])

    assert result.work.collection_id == "sanskrit_dcs"
    assert result.work.source_id == "dcs_grouped-1"
    assert result.segments[0].citation_path == "101"
    assert result.segments[1].citation_path == "102"
    assert result.segments[1].text == "second sentence"


def test_parse_dcs_conllu_group_disambiguates_duplicate_sentence_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        first = root / "work-1.conllu"
        second = root / "work-2.conllu"
        first.write_text(
            """## text: Grouped Text
## text_id: grouped-1
## chapter: 1
## chapter_id: 10
# text = first sentence
# sent_id = 101
1	first	first	NOUN	_	_	_	_	_	_
""",
            encoding="utf-8",
        )
        second.write_text(
            """## text: Grouped Text
## text_id: grouped-1
## chapter: 2
## chapter_id: 11
# text = repeated sentence id
# sent_id = 101
1	repeated	repeated	NOUN	_	_	_	_	_	_
""",
            encoding="utf-8",
        )

        result = parse_dcs_conllu_group([first, second])

    assert [segment.citation_path for segment in result.segments] == ["101", "11.101"]


def test_parse_legacy_text_dump_preserves_source_markers() -> None:
    result = parse_legacy_text_dump(
        FIXTURES / "phi_legacy.txt",
        collection_id="phi",
        language="lat",
    )

    assert result.work.collection_id == "phi"
    assert result.segments[0].segment_kind in {"section", "line"}
    assert result.segments[0].text.startswith("<phi>")


def test_parse_legacy_text_dump_splits_packard_control_boundaries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "legacy.txt"
        path.write_bytes(b"first line\x80second line\x90third line")

        result = parse_legacy_text_dump(path, collection_id="phi", language="lat")

    assert [segment.text for segment in result.segments] == [
        "first line",
        "second line",
        "third line",
    ]


def test_parse_legacy_text_dump_strips_packard_bookmarks_and_builds_citations() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "lat0914.txt"
        path.write_bytes(
            b"\xef\x80\xb0\xb9\xb1\xb4\xff"
            b"\xef\x81\xb0\xb0\xb1\xff"
            b"\xb1\xaf\xf0\xf2\xff"
            b"facturusne operae pretium sim\x80"
            b"populi Romani perscripserim\x90"
        )

        result = parse_legacy_text_dump(path, collection_id="phi", language="lat")

    assert [segment.citation_path for segment in result.segments] == ["1.pr.1.1", "1.pr.1.2"]
    assert [segment.text for segment in result.segments] == [
        "facturusne operae pretium sim",
        "populi Romani perscripserim",
    ]


def test_parse_legacy_text_dump_converts_greek_beta_segments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "tlg0012.txt"
        path.write_bytes(
            b"\xef\x80\xb0\xb0\xb1\xb2\xff\xef\x81\xb0\xb0\xb1\xff\xb1\x81MH=NIN A)/EIDE QEA\\\x80"
        )

        result = parse_legacy_text_dump(path, collection_id="tlg", language="grc")

    assert result.segments[0].citation_path == "1.1.1.1"
    assert result.segments[0].text == "μῆνιν ἄειδε θεὰ"


def test_parse_legacy_text_dump_drops_binary_control_fragments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "legacy.txt"
        path.write_bytes(b"\xef\x80\xb0\x80actual beta line")

        result = parse_legacy_text_dump(path, collection_id="phi", language="lat")

    assert [segment.text for segment in result.segments] == ["actual beta line"]


def test_parse_legacy_text_dump_with_idt_splits_author_file_into_works() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "lat0002.txt"
        idt_path = root / "lat0002.idt"
        txt_path.write_bytes(
            b"<work-one>\narma virumque\n".ljust(8192, b"\x00") + b"<work-two>\nsecond work text\n"
        )
        idt_path.write_bytes(
            _idt_author_record("0002", "Test Author")
            + _idt_work_record("001", "First Work", 0, ["book", "line"])
            + _idt_work_record("002", "Second Work", 1, ["section", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert [book.work.title for book in books] == ["First Work", "Second Work"]
    assert [book.work.author for book in books] == ["Test Author", "Test Author"]
    assert [book.work.source_id for book in books] == ["lat0002.001", "lat0002.002"]
    assert books[0].segments[0].text == "<work-one>"
    assert books[1].segments[0].text == "<work-two>"


def test_parse_legacy_text_dump_with_idt_marks_english_bible_as_eng() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "civ0005.txt"
        idt_path = root / "civ0005.idt"
        txt_path.write_bytes(b"And both Jesus was called, and his disciples, to the marriage.\n")
        idt_path.write_bytes(
            _idt_author_record("0005", "English Bible (KJV or AV)")
            + _idt_work_record("058", "John", 0, ["chapter", "verse"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].work.language == "eng"
    assert books[0].edition.language == "eng"


def test_parse_legacy_text_dump_with_idt_handles_milton_mixed_english_latin_source() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "civ0007.txt"
        idt_path = root / "civ0007.idt"
        txt_path.write_bytes(
            b"Of man's first disobedience, and the fruit\n".ljust(8192, b"\x00")
            + b"Pro populo Anglicano defensio\n"
        )
        idt_path.write_bytes(
            _idt_author_record("0007", "John Milton (English and Latin)")
            + _idt_work_record("001", "Paradise Lost (English)", 0, ["book", "line"])
            + _idt_work_record(
                "002",
                "Defensionem Regiam (Latin Works, vol. 7, pp. 1-300)",
                1,
                ["book", "line"],
            )
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    by_source = {book.work.source_id: book for book in books}
    assert by_source["civ0007.001"].work.language == "eng"
    assert by_source["civ0007.001"].edition.language == "eng"
    assert by_source["civ0007.002"].work.language == "lat"
    assert by_source["civ0007.002"].edition.language == "lat"


def test_parse_legacy_text_dump_with_idt_keeps_transliterated_bible_from_english_guess() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "civ0001.txt"
        idt_path = root / "civ0001.idt"
        txt_path.write_bytes(b'B.:/R") $ I73YT B.FRF74) ):ELOHI92YM )"T HA $ .FMA73YIM W:/)"T\n')
        idt_path.write_bytes(
            _idt_author_record("0001", "Hebrew Bible (MT or BHS)")
            + _idt_work_record("001", "Genesis", 0, ["chapter", "verse"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].work.language == "heb"
    assert books[0].edition.language == "heb"


def test_parse_legacy_text_dump_with_idt_marks_septuagint_as_greek() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "civ0002.txt"
        idt_path = root / "civ0002.idt"
        txt_path.write_bytes(b"*)EN A)RXH=| E)POIHSEN O( QEOS TON OURANON\n")
        idt_path.write_bytes(
            _idt_author_record("0002", "Septuagint (Old Greek Bible)")
            + _idt_work_record("001", "Genesis", 0, ["chapter", "verse"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].work.language == "grc"
    assert books[0].edition.language == "grc"


def test_parse_legacy_text_dump_with_idt_marks_greek_new_testament_as_greek() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "civ0003.txt"
        idt_path = root / "civ0003.idt"
        txt_path.write_bytes(b"*BIBLOS GENESEWS *)IHSOU *XRISTOU\n")
        idt_path.write_bytes(
            _idt_author_record("0003", "Greek New Testament (NT UBS3 edition)")
            + _idt_work_record("001", "Matthew", 0, ["chapter", "verse"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].work.language == "grc"
    assert books[0].edition.language == "grc"


def test_parse_legacy_text_dump_with_idt_marks_sahidic_coptic_as_coptic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "cop0001.txt"
        idt_path = root / "cop0001.idt"
        txt_path.write_bytes(b"IAKWBOS Ph\\MhAL \\MPNOUTE AUW PjOEIS\n")
        idt_path.write_bytes(
            _idt_author_record("0001", "Sahidic Coptic Bible")
            + _idt_work_record("020", "James", 0, ["chapter", "verse"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].work.language == "cop"
    assert books[0].edition.language == "cop"


def test_parse_legacy_text_dump_with_idt_skips_section_index_records() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg0012.txt"
        idt_path = root / "tlg0012.idt"
        txt_path.write_bytes(b"MH=NIN A)/EIDE\n".ljust(8192, b"\x00") + b"A)NDRA MOI E)/NNEPE\n")
        idt_path.write_bytes(
            _idt_author_record("0012", "Homer")
            + _idt_work_record("001", "Ilias", 0, ["book", "line"])
            + b"\x03\x00\x00\x08\xb1\x0a\xb1"
            + _idt_work_record("002", "Odyssea", 1, ["book", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert [book.work.title for book in books] == ["Ilias", "Odyssea"]


def test_parse_legacy_text_dump_with_idt_splits_same_start_block_by_inline_work_marker() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "lat0836.txt"
        idt_path = root / "lat0836.idt"
        txt_path.write_bytes(
            b"\xef\x80\xb0\xb8\xb3\xb6\xff"
            b"\xef\x81\xb0\xb0\xb1\xff"
            b"\xb0"
            b"first work line\x80"
            b"\xef\x81\xb0\xb0\xb2\xff"
            b"\xb0"
            b"second work line\x80"
        )
        idt_path.write_bytes(
            _idt_author_record("0836", "Celsus")
            + _idt_work_record("001", "De Agricultura", 0, ["fragment", "line"])
            + _idt_work_record("002", "De Medicina", 0, ["book", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    by_source = {book.work.source_id: book for book in books}
    assert by_source["lat0836.001"].segments[0].text == "first work line"
    assert by_source["lat0836.002"].segments[0].text == "second work line"


def test_parse_legacy_text_dump_with_idt_strips_metadata_formatting() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg0012.txt"
        idt_path = root / "tlg0012.idt"
        txt_path.write_bytes(b"MH=NIN A)/EIDE\n")
        idt_path.write_bytes(
            _idt_author_record("0012", "&1Homerus& Epic.")
            + _idt_work_record("001", "{1Ilias}1", 0, ["Book", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert books[0].work.author == "Homerus Epic."
    assert books[0].work.title == "Ilias"


def test_parse_legacy_text_dump_with_idt_decodes_greek_beta_work_title() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg0086.txt"
        idt_path = root / "tlg0086.idt"
        txt_path.write_bytes(b"POLITEI/A\n")
        idt_path.write_bytes(
            _idt_author_record("0086", "Aristoteles")
            + _idt_work_record("003", "*)AQHNAI/WN POLITEI/A", 0, [])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert books[0].work.title == "Ἀθηναίων πολιτεία"


def test_parse_legacy_text_dump_with_idt_decodes_mixed_greek_beta_title() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg4319.txt"
        idt_path = root / "tlg4319.idt"
        txt_path.write_bytes(b"W)/XRA\n")
        idt_path.write_bytes(
            _idt_author_record("4319", "Zosimus")
            + _idt_work_record(
                "026",
                "*PERI\\ SKEUASI/AS W)/XRAS "
                "(fort. pars operis *XEIRO/MHKTA) "
                "(e cod. Venet. Marc. 299, fol. 157r)",
                0,
                [],
            )
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert (
        books[0].work.title == "Περὶ σκευασίας ὤχρας (fort. pars operis Χειρόμηκτα) "
        "(e cod. Venet. Marc. 299, fol. 157r)"
    )


def test_parse_legacy_text_dump_with_idt_repairs_preaccented_mixed_greek_beta_title() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg4319.txt"
        idt_path = root / "tlg4319.idt"
        txt_path.write_bytes(b"W)/XRA\n")
        idt_path.write_bytes(
            _idt_author_record("4319", "Zosimus")
            + _idt_work_record(
                "026",
                "*PERÌ SKEUASÍAS W)/XRAS (fort. pars operis *XEIRÓMHKTA)",
                0,
                [],
            )
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert books[0].work.title == "Περὶ σκευασίας ὤχρας (fort. pars operis Χειρόμηκτα)"


def test_parse_legacy_text_dump_with_idt_keeps_latin_sigla_near_greek_title() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg0072.txt"
        idt_path = root / "tlg0072.idt"
        txt_path.write_bytes(b"KLISIS\n")
        idt_path.write_bytes(
            _idt_author_record("0072", "Apollonius Dyscolus")
            + _idt_work_record(
                "017",
                "Commentarium in anonymi opus PERI\\ KLI/SEWS O)NOMA/TWN (P. Oxy. 15.1801v)",
                0,
                [],
            )
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert (
        books[0].work.title
        == "Commentarium in anonymi opus περὶ κλίσεως ὀνομάτων (P. Oxy. 15.1801v)"
    )


def test_parse_legacy_text_dump_with_idt_sets_cts_work_urn_for_tlg() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "tlg0012.txt"
        idt_path = root / "tlg0012.idt"
        txt_path.write_bytes(
            b"\xef\x80\xb0\xb0\xb1\xb2\xff\xef\x81\xb0\xb0\xb1\xff\xb1\x81MH=NIN A)/EIDE QEA\\\x80"
        )
        idt_path.write_bytes(
            _idt_author_record("0012", "Homer")
            + _idt_work_record("002", "Odyssea", 0, ["book", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="tlg",
            language="grc",
        )

    assert books[0].work.cts_work_urn == "urn:cts:greekLit:tlg0012.tlg002"
    assert books[0].addresses[0].address == (
        f"{books[0].work.work_id}:{books[0].segments[0].citation_path}"
    )


def test_parse_legacy_text_dump_with_idt_sets_cts_work_urn_for_phi() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "lat0914.txt"
        idt_path = root / "lat0914.idt"
        txt_path.write_bytes(b"facturusne operae pretium sim\x80")
        idt_path.write_bytes(
            _idt_author_record("0914", "Livius")
            + _idt_work_record("001", "Ab urbe condita", 0, ["book", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].work.cts_work_urn == "urn:cts:latinLit:phi0914.phi001"


def test_parse_legacy_text_dump_decodes_inline_greek_in_latin_phi_text() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        txt_path = root / "lat0684.txt"
        idt_path = root / "lat0684.idt"
        txt_path.write_bytes(b"quam vocant $ E)TUMOLOGIKH/N & : quae\x80")
        idt_path.write_bytes(
            _idt_author_record("0684", "M. Terentius Varro")
            + _idt_work_record("001", "De Lingua Latina", 0, ["book", "section", "line"])
            + b"\x00"
        )

        books = parse_legacy_text_dump_with_idt(
            txt_path,
            idt_path=idt_path,
            collection_id="phi",
            language="lat",
        )

    assert books[0].segments[0].text == "quam vocant ἐτυμολογικήν : quae"


def test_legacy_greek_beta_converter_handles_legacy_diacritic_order() -> None:
    assert _legacy_greek_beta_to_unicode("(/*WRW|") == "Ὥρῳ"


def _idt_author_record(author_id: str, name: str) -> bytes:
    return _idt_record(1, 0, author_id, name, start_block=0)


def _idt_work_record(
    work_id: str,
    title: str,
    start_block: int,
    labels: list[str],
) -> bytes:
    record = _idt_record(2, 1, work_id, title, start_block=start_block)
    for index, label in enumerate(labels, start=1):
        encoded = label.encode("latin-1")
        record += bytes([0x11, index, len(encoded)]) + encoded
    return record


def _idt_record(
    code: int,
    level: int,
    identifier: str,
    value: str,
    *,
    start_block: int,
) -> bytes:
    value_bytes = value.encode("latin-1")
    return (
        bytes([code, 0, 0, (start_block >> 8) & 0xFF, start_block & 0xFF, 0xEF, 0x80 | level])
        + identifier.encode("ascii")
        + b"\xff"
        + bytes([0x10, level, len(value_bytes)])
        + value_bytes
    )
