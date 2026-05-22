from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from langnet.foster_ossa.extraction import (
    extract_pdf_pages,
    iter_page_rows_from_pdftotext,
    write_page_rows_jsonl,
)
from langnet.foster_ossa.models import FosterOssaPage
from langnet.foster_ossa.structure import (
    classify_page_section,
    detect_concept_mentions,
    detect_encounters,
    structured_page_rows,
)
from langnet.foster_ossa.summaries import (
    PROMPT_VERSION,
    completion_options_for_summary,
    experience_rows_from_toc_summary_jsonl,
    generated_summary_json,
    plan_summary_chunks,
    render_toc_summary_markdown,
    validate_generated_summary,
    write_summary_markdown_docs,
)
from langnet.foster_ossa.toc import parse_toc_entries

FIRST_EXPERIENCE_CONTINUATION_PAGE = 50
LAST_FIRST_EXPERIENCE_ENCOUNTER_PAGE = 154
TOC_PRINTED_PAGE_FIRST_ENCOUNTER = 3
THIRD_EXPERIENCE_NUMBER = 3
THIRD_EXPERIENCE_LOCAL_ENCOUNTER = 8
THIRD_EXPERIENCE_GLOBAL_ENCOUNTER = 43
FOURTH_EXPERIENCE_FIRST_GLOBAL_ENCOUNTER = 71
VALID_TOC_SUMMARY_COUNT = 2


def test_iter_page_rows_from_pdftotext_splits_form_feed_pages() -> None:
    text = (
        "\fTitle page\nOSSA LATINITATIS SOLA\n"
        "\fI Encounter 1 (1)\nFunctions produce true meaning.\n"
    )

    pages = list(iter_page_rows_from_pdftotext(text, source_path=Path("ossa.pdf")))

    assert [page.page_number for page in pages] == [1, 2]
    assert pages[0].source_path == "ossa.pdf"
    assert pages[0].extraction_tool == "pdftotext"
    assert "OSSA LATINITATIS" in pages[0].text
    assert pages[0].text_hash
    assert pages[1].text.startswith("I Encounter 1")


def test_iter_page_rows_from_pdftotext_preserves_interior_blank_page_number() -> None:
    text = "\fFirst page\n\f \n\fThird page\n"

    pages = list(iter_page_rows_from_pdftotext(text, source_path=Path("ossa.pdf")))

    assert [page.page_number for page in pages] == [1, 2, 3]
    assert pages[1].text == ""
    assert pages[1].warning == "empty_page"
    assert pages[2].text == "Third page"


def test_write_page_rows_jsonl_writes_one_json_object_per_page() -> None:
    with TemporaryDirectory() as tmp_dir:
        output = Path(tmp_dir) / "foster-ossa-pages.jsonl"
        pages = list(
            iter_page_rows_from_pdftotext(
                "\fPreface\n\fI Encounter 1 (1)\nFirst text\n",
                source_path=Path("ossa.pdf"),
            )
        )

        write_page_rows_jsonl(pages, output)

        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        assert [row["page_number"] for row in rows] == [1, 2]
        assert rows[0]["source_path"] == "ossa.pdf"
        assert rows[1]["text"] == "I Encounter 1 (1)\nFirst text"


def test_write_page_rows_jsonl_expands_output_path() -> None:
    with TemporaryDirectory() as tmp_dir:
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmp_dir
        try:
            output = Path("~/foster-ossa-pages.jsonl")
            pages = list(
                iter_page_rows_from_pdftotext(
                    "\fPreface\n",
                    source_path=Path("ossa.pdf"),
                )
            )

            write_page_rows_jsonl(pages, output)

            assert (Path(tmp_dir) / "foster-ossa-pages.jsonl").exists()
        finally:
            if original_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = original_home


def test_extract_pdf_pages_uses_runner_output_without_real_pdf() -> None:
    with TemporaryDirectory() as tmp_dir:
        source = Path(tmp_dir) / "ossa.pdf"
        source.write_bytes(b"%PDF synthetic")

        def runner(command: list[str]) -> str:
            assert command == ["pdftotext", "-layout", str(source), "-"]
            return "\fOne\n\fTwo\n"

        pages = list(extract_pdf_pages(source, runner=runner))

        assert [page.text for page in pages] == ["One", "Two"]


def test_classify_page_section_identifies_major_book_regions() -> None:
    assert classify_page_section(3, "THE MERE BONES OF LATIN") == "front_matter"
    assert classify_page_section(49, "PRIMA\nEXPERIENTIA\nfirst experience") == ("first_experience")
    assert classify_page_section(165, "Reading Sheets—First Experience") == (
        "reading_sheets_first_experience"
    )
    assert classify_page_section(166, "A continuation reading-sheet page") == (
        "reading_sheets_first_experience"
    )
    assert classify_page_section(776, "BIBLIOGRAPHIA\nbibliography") == "bibliography"
    assert classify_page_section(823, "roles or cases and functions") == "indexes"


def test_detect_encounters_reads_experience_and_encounter_numbers() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=49,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="I Encounter 1 (1)\nFirst principles",
        ),
        FosterOssaPage.from_text(
            page_number=50,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="I Encounter 2 (2)\nNouns and functions",
        ),
    ]

    encounters = detect_encounters(pages)

    assert [(item.experience, item.encounter, item.page_start) for item in encounters] == [
        (1, 1, 49),
        (1, 2, 50),
    ]
    assert encounters[0].title == "First principles"


def test_detect_encounters_prefers_title_page_line_over_running_header() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=49,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="encounter 1\nOSSIUM GLUTEN",
        ),
        FosterOssaPage.from_text(
            page_number=FIRST_EXPERIENCE_CONTINUATION_PAGE,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="4 I Encounter 1 (1)\nContinuation",
        ),
        FosterOssaPage.from_text(
            page_number=56,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="encounter 2\nASINUS - CAPRA",
        ),
    ]

    encounters = detect_encounters(pages)

    assert [(item.encounter_id, item.page_start, item.page_end) for item in encounters] == [
        ("1.1", 49, FIRST_EXPERIENCE_CONTINUATION_PAGE),
        ("1.2", 56, 56),
    ]
    assert encounters[0].title == "OSSIUM GLUTEN"


def test_detect_encounters_extends_final_encounter_to_last_page() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=49,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="I Encounter 1 (1)\nFirst principles",
        ),
        FosterOssaPage.from_text(
            page_number=FIRST_EXPERIENCE_CONTINUATION_PAGE,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="Continuation with nom. subject",
        ),
    ]

    encounters = detect_encounters(pages)
    mentions = detect_concept_mentions(pages, encounters)

    assert encounters[0].page_end == FIRST_EXPERIENCE_CONTINUATION_PAGE
    nom = next(mention for mention in mentions if mention.normalized_term == "nom")
    assert nom.encounter_id == "1.1"


def test_detect_encounters_stops_before_non_encounter_sections() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=LAST_FIRST_EXPERIENCE_ENCOUNTER_PAGE,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="I Encounter 35 (35)\nFinal first experience topic",
        ),
        FosterOssaPage.from_text(
            page_number=155,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="Reading Sheets—First Experience\nnom. subject",
        ),
    ]

    encounters = detect_encounters(pages)
    mentions = detect_concept_mentions(pages, encounters)

    assert encounters[0].page_end == LAST_FIRST_EXPERIENCE_ENCOUNTER_PAGE
    nom = next(mention for mention in mentions if mention.normalized_term == "nom")
    assert nom.encounter_id is None


def test_detect_encounters_ignores_encounter_mentions_in_reading_sheets() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=155,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="Reading Sheets—First Experience\nI Encounter 35 (35)\nnom. subject",
        ),
    ]

    encounters = detect_encounters(pages)
    mentions = detect_concept_mentions(pages, encounters)

    assert encounters == []
    nom = next(mention for mention in mentions if mention.normalized_term == "nom")
    assert nom.encounter_id is None


def test_detect_encounters_ignores_encounter_mentions_in_front_matter() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=20,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="Contents\nI Encounter 1 (1) First principles",
        ),
    ]

    assert detect_encounters(pages) == []


def test_detect_encounters_ignores_table_of_contents_experience_headings() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=20,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="PRIMA EXPERIENTIA\nI Encounter 1 (1) First principles",
        ),
    ]

    assert classify_page_section(20, pages[0].text) == "front_matter"
    assert detect_encounters(pages) == []


def test_detect_concept_mentions_finds_source_terms_with_context() -> None:
    page = FosterOssaPage.from_text(
        page_number=23,
        source_path="ossa.pdf",
        extraction_tool="pdftotext",
        text=(
            "The list of the seven Functions includes nom. subject, acc. object, "
            "and gen. possession."
        ),
    )

    mentions = detect_concept_mentions([page])

    normalized = {(mention.term, mention.category) for mention in mentions}
    assert ("nom.", "abbreviation") in normalized
    assert ("acc.", "abbreviation") in normalized
    assert ("gen.", "abbreviation") in normalized
    assert ("Functions", "method") in normalized
    functions_mention = next(mention for mention in mentions if mention.term == "Functions")
    assert functions_mention.normalized_term == "functions"
    assert all(mention.context for mention in mentions)


def test_structured_page_rows_add_section_without_mutating_text() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=3,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="THE MERE BONES OF LATIN",
        ),
        FosterOssaPage.from_text(
            page_number=49,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text="I Encounter 1 (1)\nFunctions produce true meaning.",
        ),
    ]

    rows = structured_page_rows(pages)

    assert rows[0].section == "front_matter"
    assert rows[1].section == "first_experience"
    assert rows[1].text == "I Encounter 1 (1)\nFunctions produce true meaning."


def test_parse_toc_entries_reads_experience_encounter_and_page_offset() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=9,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text=(
                "CONTINENTUR\n"
                "prima experientia                                             1\n"
                "First Experience\n"
                "1. Ossium Gluten: Sententiarum Latinarum Ordo = Exitus Et\n"
                "   Vocabula. Signa Personarum In Verbis                         3\n"
                "   the Bones' Glue: the structure of Latin sentences = terminations "
                "and vocabulary.\n"
                "2. asinus—capra—vehiculum.\n"
                "   Duplex Principium In Neutris Supremum                       10\n"
                "   Block I nouns. super double principle in neuters\n"
            ),
        )
    ]

    entries = parse_toc_entries(pages)

    assert [
        (entry.encounter_id, entry.printed_page, entry.inferred_page_number) for entry in entries
    ] == [
        ("1.1", TOC_PRINTED_PAGE_FIRST_ENCOUNTER, 49),
        ("1.2", 10, 56),
    ]
    assert entries[0].latin_title == (
        "Ossium Gluten: Sententiarum Latinarum Ordo = Exitus Et "
        "Vocabula. Signa Personarum In Verbis"
    )
    assert entries[0].english_title.startswith("the Bones' Glue")


def test_parse_toc_entries_uses_global_encounter_number_to_correct_experience() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=12,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text=(
                "TERTIA EXPERIENTIA 251\n"
                "8 (43) Latina in lingua quam varie et difficulter 290\n"
                "quam in the Latin language with various usages and difficulties\n"
            ),
        )
    ]

    entries = parse_toc_entries(pages)

    assert entries[0].experience == THIRD_EXPERIENCE_NUMBER
    assert entries[0].encounter == THIRD_EXPERIENCE_LOCAL_ENCOUNTER
    assert entries[0].global_encounter == THIRD_EXPERIENCE_GLOBAL_ENCOUNTER
    assert entries[0].encounter_id == "3.8"


def test_parse_toc_entries_does_not_treat_title_experience_words_as_heading() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=12,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text=(
                "TERTIA EXPERIENTIA 251\n"
                "3 (38) Repetitio ex prima experientia nominum: is = es;\n"
                "       vocativus 265\n"
                "       repetition of nouns from the First Experience: is = es;\n"
            ),
        )
    ]

    entries = parse_toc_entries(pages)

    assert entries[0].encounter_id == "3.3"
    assert "prima experientia" in entries[0].latin_title


def test_parse_toc_entries_normalizes_spaced_global_encounter_digits() -> None:
    pages = [
        FosterOssaPage.from_text(
            page_number=14,
            source_path="ossa.pdf",
            extraction_tool="pdftotext",
            text=("QVARTA EXPERIENTIA 455\n1 (7 1) Oratio obliqua 459\n        reported speech\n"),
        )
    ]

    entries = parse_toc_entries(pages)

    assert entries[0].global_encounter == FOURTH_EXPERIENCE_FIRST_GLOBAL_ENCOUNTER
    assert entries[0].encounter_id == "4.1"


def test_plan_summary_chunks_uses_local_input_hash() -> None:
    rows = [
        {
            "page_number": 49,
            "section": "first_experience",
            "text": "I Encounter 1 (1)\nFunctions produce true meaning.",
            "text_hash": "stored-page-hash",
        }
    ]

    plans = plan_summary_chunks(rows, scope="page", model="openai:test-model")

    assert len(plans) == 1
    plan = plans[0]
    assert plan.source_ref == "page:49"
    assert plan.scope == "page"
    assert plan.model == "openai:test-model"
    assert plan.prompt_version == PROMPT_VERSION
    assert plan.input_text == (
        "Foster Ossa page 49 [first_experience]\n\n"
        "I Encounter 1 (1)\nFunctions produce true meaning."
    )
    assert plan.input_hash == sha256(plan.input_text.encode("utf-8")).hexdigest()


def test_plan_summary_chunks_supports_toc_entry_scope() -> None:
    rows = [
        {
            "source_ref": "toc:1.1",
            "encounter_id": "1.1",
            "latin_title": "Ossium Gluten",
            "english_title": "the Bones' Glue",
            "page_start": 49,
            "page_end": 55,
            "text": "Functions produce true meaning.",
            "text_hash": "stored-span-hash",
        }
    ]

    plans = plan_summary_chunks(rows, scope="toc-entry", model="openai:test-model")

    assert len(plans) == 1
    plan = plans[0]
    assert plan.source_ref == "toc:1.1"
    assert plan.scope == "toc-entry"
    assert plan.prompt_version == "foster-ossa-toc-summary-v2"
    assert "Encounter: 1.1" in plan.input_text
    assert "Source pages: page:49-page:55" in plan.input_text
    assert "Return raw JSON only" in plan.input_text
    assert "Do not wrap the JSON in markdown fences" in plan.input_text
    assert "source_ref must exactly equal Source" in plan.input_text
    assert "source_refs must include at least one page:* reference copied from Source pages" in (
        plan.input_text
    )
    assert "Expected JSON keys" in plan.input_text
    assert plan.input_hash == sha256(plan.input_text.encode("utf-8")).hexdigest()


def test_validate_generated_summary_accepts_toc_entry_schema_json() -> None:
    issues = validate_generated_summary(
        scope="toc-entry",
        generated_text=json.dumps(
            {
                "source_ref": "toc:1.1",
                "encounter_id": "1.1",
                "title": "Ossium Gluten",
                "page_span": "49-55",
                "foster_terms": [],
                "traditional_terms": [],
                "method_claims": [],
                "learner_actions": [],
                "examples_present": [],
                "not_supported_or_unclear": [],
                "source_refs": ["page:49"],
            }
        ),
    )

    assert issues == []


def test_validate_generated_summary_reports_missing_toc_entry_schema_keys() -> None:
    issues = validate_generated_summary(
        scope="toc-entry",
        generated_text=json.dumps({"source_ref": "toc:1.1"}),
    )

    assert "missing required key: method_claims" in issues


def test_validate_generated_summary_requires_expected_source_ref() -> None:
    issues = validate_generated_summary(
        scope="toc-entry",
        generated_text=json.dumps(
            {
                "source_ref": "1.7",
                "encounter_id": "1.7",
                "title": "Times",
                "page_span": "74-78",
                "foster_terms": [],
                "traditional_terms": [],
                "method_claims": [],
                "learner_actions": [],
                "examples_present": [],
                "not_supported_or_unclear": [],
                "source_refs": ["page:74"],
            }
        ),
        expected_source_ref="toc:1.7",
    )

    assert "source_ref must equal toc:1.7" in issues


def test_validate_generated_summary_requires_page_source_ref_for_toc_entry() -> None:
    payload = {
        "source_ref": "toc:1.1",
        "encounter_id": "1.1",
        "title": "Ossium Gluten",
        "page_span": "49-55",
        "foster_terms": [],
        "traditional_terms": [],
        "method_claims": [],
        "learner_actions": [],
        "examples_present": [],
        "not_supported_or_unclear": [],
        "source_refs": ["toc:1.1"],
    }

    issues = validate_generated_summary(
        scope="toc-entry",
        generated_text=json.dumps(payload),
    )

    assert "source_refs must include at least one page:* reference" in issues


def test_validate_generated_summary_reports_wrong_toc_entry_field_types() -> None:
    issues = validate_generated_summary(
        scope="toc-entry",
        generated_text=json.dumps(
            {
                "source_ref": "toc:1.1",
                "encounter_id": "1.1",
                "title": {"latin": "Ossium Gluten"},
                "page_span": "49-55",
                "foster_terms": [],
                "traditional_terms": [],
                "method_claims": [],
                "learner_actions": [],
                "examples_present": True,
                "not_supported_or_unclear": "none",
                "source_refs": ["page:49"],
            }
        ),
    )

    assert "title must be a string" in issues
    assert "examples_present must be an array" in issues
    assert "not_supported_or_unclear must be an array" in issues


def test_validate_generated_summary_accepts_experience_schema_json() -> None:
    issues = validate_generated_summary(
        scope="experience",
        generated_text=json.dumps(
            {
                "source_ref": "experience:1",
                "experience": 1,
                "toc_entry_count": 8,
                "method_throughline": [],
                "core_foster_terms": [],
                "traditional_bridge_terms": [],
                "learner_sequence": [],
                "platform_taxonomy_implications": [],
                "source_refs": ["toc:1.1", "page:49"],
                "not_supported_or_unclear": [],
            }
        ),
    )

    assert issues == []


def test_validate_generated_summary_requires_page_source_ref_for_experience() -> None:
    issues = validate_generated_summary(
        scope="experience",
        generated_text=json.dumps(
            {
                "source_ref": "experience:1",
                "experience": 1,
                "toc_entry_count": 8,
                "method_throughline": [],
                "core_foster_terms": [],
                "traditional_bridge_terms": [],
                "learner_sequence": [],
                "platform_taxonomy_implications": [],
                "source_refs": ["toc:1.1"],
                "not_supported_or_unclear": [],
            }
        ),
    )

    assert "source_refs must include at least one page:* reference" in issues


def test_generated_summary_json_normalizes_markdown_fenced_json() -> None:
    payload = {
        "source_ref": "toc:1.1",
        "encounter_id": "1.1",
        "title": "Ossium Gluten",
        "page_span": "49-55",
        "foster_terms": [],
        "traditional_terms": [],
        "method_claims": [],
        "learner_actions": [],
        "examples_present": [],
        "not_supported_or_unclear": [],
        "source_refs": ["page:49"],
    }
    generated_text = "```json\n" + json.dumps(payload) + "\n```"

    normalized = generated_summary_json(scope="toc-entry", generated_text=generated_text)

    assert json.loads(normalized)["source_refs"] == ["page:49"]


def test_completion_options_request_deterministic_json_for_structured_scopes() -> None:
    toc_plan = plan_summary_chunks(
        [
            {
                "source_ref": "toc:1.1",
                "encounter_id": "1.1",
                "latin_title": "Ossium Gluten",
                "english_title": "the Bones' Glue",
                "page_start": 49,
                "page_end": 55,
                "text": "Functions produce true meaning.",
            }
        ],
        scope="toc-entry",
        model="openai:test-model",
    )[0]
    page_plan = plan_summary_chunks(
        [
            {
                "page_number": 49,
                "section": "first_experience",
                "text": "Functions produce true meaning.",
            }
        ],
        scope="page",
        model="openai:test-model",
    )[0]

    assert completion_options_for_summary(toc_plan) == {
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    assert completion_options_for_summary(page_plan) == {"temperature": 0}


def test_experience_rows_from_toc_summary_jsonl_groups_valid_toc_summaries() -> None:
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "toc-summaries.jsonl"
        first = {
            "source_ref": "toc:1.1",
            "scope": "toc-entry",
            "validation_status": "generated_valid",
            "generated_json": json.dumps(
                {
                    "source_ref": "toc:1.1",
                    "encounter_id": "1.1",
                    "title": "Ossium Gluten",
                    "method_claims": ["Functions matter."],
                    "learner_actions": ["Read endings."],
                    "source_refs": ["page:49"],
                }
            ),
        }
        second = {
            "source_ref": "toc:1.2",
            "scope": "toc-entry",
            "validation_status": "generated_valid",
            "generated_json": json.dumps(
                {
                    "source_ref": "toc:1.2",
                    "encounter_id": "1.2",
                    "title": "Block I nouns",
                    "method_claims": ["Use the dictionary entry."],
                    "learner_actions": ["Reverse forms."],
                    "source_refs": ["page:56"],
                }
            ),
        }
        invalid = {
            "source_ref": "toc:1.3",
            "scope": "toc-entry",
            "validation_status": "generated_invalid",
            "generated_text": "{}",
        }
        path.write_text(
            "\n".join(json.dumps(row) for row in [first, second, invalid]) + "\n",
            encoding="utf-8",
        )

        rows = experience_rows_from_toc_summary_jsonl(path)

        assert len(rows) == 1
        assert rows[0]["source_ref"] == "experience:1"
        assert rows[0]["experience"] == 1
        assert rows[0]["toc_entry_count"] == VALID_TOC_SUMMARY_COUNT
        assert rows[0]["source_refs"] == ["toc:1.1", "toc:1.2"]
        assert "Functions matter" in rows[0]["text"]


def test_plan_summary_chunks_supports_experience_scope() -> None:
    rows = [
        {
            "source_ref": "experience:1",
            "experience": 1,
            "toc_entry_count": 2,
            "source_refs": ["toc:1.1", "toc:1.2"],
            "text": '[{"source_ref":"toc:1.1"}]',
            "text_hash": "experience-hash",
        }
    ]

    plans = plan_summary_chunks(rows, scope="experience", model="openai:test-model")

    assert len(plans) == 1
    assert plans[0].source_ref == "experience:1"
    assert plans[0].prompt_version == "foster-ossa-experience-summary-v2"
    assert "TOC summaries included: 2" in plans[0].input_text
    assert "Return raw JSON only" in plans[0].input_text


def test_render_toc_summary_markdown_uses_claims_actions_and_source_refs() -> None:
    summary = {
        "source_ref": "toc:1.1",
        "encounter_id": "1.1",
        "title": "Ossium Gluten",
        "method_claims": ["Functions, not word order alone, carry sentence meaning."],
        "learner_actions": ["Read endings before relying on word order."],
        "not_supported_or_unclear": ["No uncertainty in this small fixture."],
        "source_refs": ["page:49", "page:50"],
    }

    markdown = render_toc_summary_markdown(summary)

    assert markdown.startswith("## toc:1.1 - Ossium Gluten")
    assert "- Functions, not word order alone, carry sentence meaning." in markdown
    assert "- Read endings before relying on word order." in markdown
    assert "`page:49`" in markdown
    assert "No uncertainty" in markdown


def test_write_summary_markdown_docs_writes_index_and_experience_file() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        input_path = base / "toc-summaries.jsonl"
        output_dir = base / "docs"
        input_path.write_text(
            json.dumps(
                {
                    "source_ref": "toc:1.1",
                    "scope": "toc-entry",
                    "validation_status": "generated_valid",
                    "generated_json": json.dumps(
                        {
                            "source_ref": "toc:1.1",
                            "encounter_id": "1.1",
                            "title": "Ossium Gluten",
                            "method_claims": ["Functions matter."],
                            "learner_actions": ["Read endings."],
                            "not_supported_or_unclear": [],
                            "source_refs": ["page:49"],
                        }
                    ),
                }
            )
            + "\n",
            encoding="utf-8",
        )

        written = write_summary_markdown_docs(input_path=input_path, output_dir=output_dir)

        assert written == [output_dir / "README.md", output_dir / "experience-1.md"]
        index_text = (output_dir / "README.md").read_text(encoding="utf-8")
        assert "# Foster Ossa Generated Summary Documents" in index_text
        assert "Experience 2 is present in the source extraction" in index_text
        experience_text = (output_dir / "experience-1.md").read_text(encoding="utf-8")
        assert "## toc:1.1 - Ossium Gluten" in experience_text
        assert "`page:49`" in experience_text
