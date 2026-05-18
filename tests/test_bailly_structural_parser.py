from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from langnet.parsing.bailly import compare_bailly_structure, parse_bailly_app_markdown

AGELAIOS_MARKDOWN = """[Bailly.app](https://bailly.app/)

###### Recherches récentes

153060

- [**ἀγελαῖος**, α, ον [ᾰγ] I qui forme un troupeau](https://bailly.app/agelaios)

[Signets](https://bailly.app/signets)

[ἀγελαιοκομική](https://bailly.app/agelaiokomikê)

# ἀγελαῖος

[ἀγελαιοτροφία](https://bailly.app/agelaiotrophia)

ἀγελαῖος,α, ον
[ᾰγ]

I qui forme un troupeau,
d'où :

1 qui paît en pleine
campagne : βοῦς ἀγελαῖαι, Od. 10, 410, etc. ; Soph. Aj. 175,
troupeau de génisses ||

2 qui paît encore au
milieu du troupeau, c. à d. qui n'a pas
été soumis au joug, Il. 11, 729 ||

3 réuni en troupe,
Hdt. 2, 93 ; Arstt. Pol. 1, 2, 10

II du troupeau, de la
foule, de la multitude, en parl. de pers.

Étym. ἀγέλη.

Assigner des étiquettes"""


SHORT_ENTRY_MARKDOWN = """[Bailly.app](https://bailly.app/)

# ἀγελαιοκομική

[ἀγελάζομαι](https://bailly.app/agelazomai)

ἀγελαιο·κομική,ῆς
(ἡ) [ᾰ]
s. e. τέχνη,
l'art de soigner les troupeaux, Plat. Pol. 275e.

Étym. ἀγελαῖος, κομέω.

Assigner des étiquettes"""


def test_parse_bailly_app_markdown_preserves_ordered_structural_paths() -> None:
    entry = parse_bailly_app_markdown(
        AGELAIOS_MARKDOWN,
        source_url="https://bailly.app/agelaios",
    )

    assert entry["lemma"] == "ἀγελαῖος"
    assert entry["source"] == {
        "kind": "bailly_app_markdown",
        "url": "https://bailly.app/agelaios",
    }
    assert [(block["path"], block["marker"]) for block in entry["blocks"]] == [
        ("00", "head"),
        ("01", "I"),
        ("01:00", "1"),
        ("01:01", "2"),
        ("01:02", "3"),
        ("02", "II"),
        ("03", "Étym."),
    ]

    block_text_by_path = {block["path"]: block["text"] for block in entry["blocks"]}
    assert block_text_by_path["01"] == "qui forme un troupeau, d'où :"
    assert block_text_by_path["01:00"].startswith("qui paît en pleine campagne")
    assert "Soph. Aj. 175" in block_text_by_path["01:00"]
    assert block_text_by_path["02"].startswith("du troupeau, de la foule")
    assert block_text_by_path["03"] == "ἀγέλη."
    assert all("Assigner des étiquettes" not in block["text"] for block in entry["blocks"])


def test_parse_bailly_app_markdown_keeps_simple_entries_as_head_and_notes() -> None:
    entry = parse_bailly_app_markdown(SHORT_ENTRY_MARKDOWN)

    assert entry["lemma"] == "ἀγελαιοκομική"
    assert [(block["path"], block["marker"]) for block in entry["blocks"]] == [
        ("00", "head"),
        ("01", "Étym."),
    ]
    assert entry["blocks"][0]["text"] == (
        "ἀγελαιο·κομική,ῆς (ἡ) [ᾰ] s. e. τέχνη, l'art de soigner les troupeaux, Plat. Pol. 275e."
    )
    assert entry["blocks"][1]["text"] == "ἀγελαῖος, κομέω."


def test_parse_bailly_app_markdown_preserves_letter_roman_number_hierarchy() -> None:
    markdown = """# γίγνομαι

γίγνομαι (impf. ἐγιγνόμην)

Apropr. devenir

Bp. suite :

I naître

IIen parl. de choses :

1en parl. de phénomènes physiques

2en parl. du temps

ESyntaxe :

1La 3e pers. sg.

2Dans la traduction

Assigner des étiquettes"""

    entry = parse_bailly_app_markdown(markdown)

    assert [(block["path"], block["marker"]) for block in entry["blocks"]] == [
        ("00", "head"),
        ("01", "A"),
        ("02", "B"),
        ("02:00", "I"),
        ("02:01", "II"),
        ("02:01:00", "1"),
        ("02:01:01", "2"),
        ("03", "E"),
        ("03:00", "1"),
        ("03:01", "2"),
    ]
    assert entry["blocks"][1]["text"] == "propr. devenir"
    assert entry["blocks"][4]["text"] == "en parl. de choses :"
    assert entry["blocks"][7]["text"] == "Syntaxe :"


def test_compare_bailly_structure_accepts_matching_pdf_extraction_blocks() -> None:
    gold = parse_bailly_app_markdown(AGELAIOS_MARKDOWN)
    extracted = {
        "lemma": "ἀγελαῖος",
        "source": {"kind": "bailly_pdf"},
        "blocks": [
            {
                "path": "00",
                "marker": "head",
                "text": "ἀγελαῖος,α, ον [ᾰγ]",
                "layout": {"page": 12, "column": 1, "line_start_x": 72.0},
            },
            {
                "path": "01",
                "marker": "I",
                "text": "qui forme un troupeau, d'où :",
                "layout": {"page": 12, "column": 1, "line_start_x": 72.0},
            },
            {
                "path": "01:00",
                "marker": "1",
                "text": "qui paît en pleine campagne : βοῦς ἀγελαῖαι, Od. 10, 410, etc. ; "
                "Soph. Aj. 175, troupeau de génisses ||",
                "layout": {"page": 12, "column": 1, "line_start_x": 86.0},
            },
            {
                "path": "01:01",
                "marker": "2",
                "text": "qui paît encore au milieu du troupeau, c. à d. qui n'a pas été soumis "
                "au joug, Il. 11, 729 ||",
                "layout": {"page": 12, "column": 1, "line_start_x": 86.0},
            },
            {
                "path": "01:02",
                "marker": "3",
                "text": "réuni en troupe, Hdt. 2, 93 ; Arstt. Pol. 1, 2, 10",
                "layout": {"page": 12, "column": 1, "line_start_x": 86.0},
            },
            {
                "path": "02",
                "marker": "II",
                "text": "du troupeau, de la foule, de la multitude, en parl. de pers.",
                "layout": {"page": 12, "column": 1, "line_start_x": 72.0},
            },
            {
                "path": "03",
                "marker": "Étym.",
                "text": "ἀγέλη.",
                "layout": {"page": 12, "column": 1, "line_start_x": 72.0},
            },
        ],
    }

    comparison = compare_bailly_structure(
        cast(Sequence[Mapping[str, object]], gold["blocks"]),
        cast(Sequence[Mapping[str, object]], extracted["blocks"]),
    )

    assert comparison == {
        "matched": True,
        "missing": [],
        "mismatched": [],
    }


def test_compare_bailly_structure_reports_path_marker_and_anchor_failures() -> None:
    gold = parse_bailly_app_markdown(AGELAIOS_MARKDOWN)
    extracted = {
        "blocks": [
            {"path": "00", "marker": "head", "text": "ἀγελαῖος,α, ον [ᾰγ]"},
            {"path": "01", "marker": "I", "text": "qui forme un troupeau, d'où :"},
            {"path": "02", "marker": "II", "text": "du troupeau, de la foule"},
        ]
    }

    comparison = compare_bailly_structure(gold["blocks"], extracted["blocks"])

    assert comparison["matched"] is False
    assert comparison["missing"] == ["01:00", "01:01", "01:02", "03"]
    assert comparison["mismatched"] == []
