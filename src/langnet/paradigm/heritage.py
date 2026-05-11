from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from langnet.paradigm.models import ParadigmBlock, ParadigmForm, ParadigmPayload, ParadigmSlot

CASE_LABELS = {
    "nominative": "nominative",
    "vocative": "vocative",
    "accusative": "accusative",
    "instrumental": "instrumental",
    "dative": "dative",
    "ablative": "ablative",
    "genitive": "genitive",
    "locative": "locative",
}

NUMBER_LABELS = {
    "singular": "singular",
    "dual": "dual",
    "plural": "plural",
}
MIN_TABLE_ROW_CELLS = 2
PERSON_LABELS = {
    "first": "1",
    "1st": "1",
    "1": "1",
    "second": "2",
    "2nd": "2",
    "2": "2",
    "third": "3",
    "3rd": "3",
    "3": "3",
}
TENSE_LABELS = {
    "present": {"tense": "present"},
    "imperfect": {"tense": "imperfect"},
    "future": {"tense": "future"},
    "future2": {"tense": "future2"},
    "perfect": {"tense": "perfect"},
    "aorist": {"tense": "aorist"},
    "conditional": {"mood": "conditional"},
    "optative": {"mood": "optative"},
    "imperative": {"mood": "imperative"},
}
VOICE_LABELS = {
    "active": "active",
    "middle": "middle",
    "passive": "passive",
}


def parse_heritage_declension_html(
    html: str,
    *,
    lemma: str,
    gender: str,
    request_url: str | None = None,
) -> ParadigmPayload:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.inflexion")
    warnings: list[str] = []
    if table is None:
        warnings.append("heritage_declension_table_not_found")
        slots: list[ParadigmSlot] = []
    else:
        slots = _declension_slots(table)

    return ParadigmPayload(
        language="san",
        lemma=lemma,
        kind="declension",
        source="heritage:sktdeclin",
        source_request={
            "url": request_url or "",
            "params": {"q": lemma, "g": gender},
        },
        paradigms=[
            ParadigmBlock(
                label=f"{lemma} declension",
                dimensions=["case", "number"],
                slots=slots,
            )
        ],
        warnings=warnings,
    )


def parse_heritage_conjugation_html(
    html: str,
    *,
    root: str,
    present_class: str,
    request_url: str | None = None,
) -> ParadigmPayload:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table.inflexion")
    warnings: list[str] = []
    blocks = [_conjugation_block(table, index) for index, table in enumerate(tables, start=1)]
    blocks = [block for block in blocks if block.slots]
    if not blocks:
        warnings.append("heritage_conjugation_tables_not_found")

    return ParadigmPayload(
        language="san",
        lemma=root,
        kind="conjugation",
        source="heritage:sktconjug",
        source_request={
            "url": request_url or "",
            "params": {"q": root, "c": present_class},
        },
        paradigms=blocks,
        warnings=warnings,
    )


def _declension_slots(table: Tag) -> list[ParadigmSlot]:
    rows = table.find_all("tr")
    if not rows:
        return []
    column_labels = [_cell_text(cell) for cell in rows[0].find_all(["th", "td"])][1:]
    numbers = [_normalize_number(label) for label in column_labels]
    slots: list[ParadigmSlot] = []
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if len(cells) < MIN_TABLE_ROW_CELLS:
            continue
        case = _normalize_case(_cell_text(cells[0]))
        for number, cell in zip(numbers, cells[1:], strict=False):
            forms = _cell_forms(cell)
            if not forms:
                continue
            slots.append(
                ParadigmSlot(
                    features={"case": case, "number": number},
                    forms=forms,
                    source_label=f"{_cell_text(cells[0])} / {number}",
                    is_ambiguous=len(forms) > 1,
                )
            )
    return slots


def _conjugation_block(table: Tag, index: int) -> ParadigmBlock:
    rows = table.find_all("tr")
    if not rows:
        return ParadigmBlock(label=f"conjugation table {index}", dimensions=[], slots=[])
    context = _conjugation_context(table)
    column_labels = [_cell_text(cell) for cell in rows[0].find_all(["th", "td"])][1:]
    numbers = [_normalize_number(label) for label in column_labels]
    slots: list[ParadigmSlot] = []
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if len(cells) < MIN_TABLE_ROW_CELLS:
            continue
        person_label = _cell_text(cells[0])
        person = _normalize_person(person_label)
        for number, cell in zip(numbers, cells[1:], strict=False):
            forms = _cell_forms(cell)
            if not forms:
                continue
            features = {**context, "person": person, "number": number}
            slots.append(
                ParadigmSlot(
                    features=features,
                    forms=forms,
                    source_label=f"{person_label} / {number}",
                    is_ambiguous=len(forms) > 1,
                )
            )
    dimensions = [key for key in ("tense", "mood", "voice", "person", "number") if key in context]
    dimensions.extend(["person", "number"])
    return ParadigmBlock(
        label=_conjugation_label(context, index),
        dimensions=list(dict.fromkeys(dimensions)),
        slots=slots,
    )


def _conjugation_context(table: Tag) -> dict[str, str]:
    context: dict[str, str] = {}
    tense_label = _nearest_tense_label(table)
    context.update(TENSE_LABELS.get(tense_label.casefold(), {}))
    header_cells = table.find_all("tr")[0].find_all(["th", "td"])
    if header_cells:
        voice = VOICE_LABELS.get(_cell_text(header_cells[0]).casefold())
        if voice:
            context["voice"] = voice
    return context


def _nearest_tense_label(table: Tag) -> str:
    span = table.find_previous("span", class_="b2")
    if isinstance(span, Tag):
        return _cell_text(span)
    heading = table.find_previous(["h1", "h2", "h3", "h4"])
    return _cell_text(heading) if isinstance(heading, Tag) else ""


def _conjugation_label(context: dict[str, str], index: int) -> str:
    parts = [context.get(key, "") for key in ("tense", "mood", "voice")]
    label = " ".join(part.title() for part in parts if part)
    return label or f"conjugation table {index}"


def _cell_text(cell: Tag) -> str:
    return " ".join(cell.get_text(" ", strip=True).split())


def _cell_forms(cell: Tag) -> list[ParadigmForm]:
    form_nodes = cell.select("span.red") or cell.find_all("span")
    texts = [_cell_text(node) for node in form_nodes if _cell_text(node)]
    if not texts:
        text = _cell_text(cell)
        texts = [text] if text else []
    return [
        ParadigmForm(text=text, normalized=text, source_key=text)
        for text in dict.fromkeys(texts)
        if text not in {"-", "—"}
    ]


def _normalize_case(label: str) -> str:
    return CASE_LABELS.get(label.casefold(), label.casefold())


def _normalize_number(label: str) -> str:
    return NUMBER_LABELS.get(label.casefold(), label.casefold())


def _normalize_person(label: str) -> str:
    return PERSON_LABELS.get(label.casefold(), label.casefold())
