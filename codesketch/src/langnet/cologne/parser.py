import re
from collections.abc import Iterator
from decimal import Decimal
from xml.etree import ElementTree

from .models import CdslEntry

CDSL_ENTRY_MIN_PARTS = 3


def parse_xml_entry(raw_data: str) -> CdslEntry | None:
    try:
        root = ElementTree.fromstring(raw_data)
    except ElementTree.ParseError:
        return None

    header = root.find("h")
    tail = root.find("tail")

    key1_elem = header.find("key1") if header is not None else None
    key1 = key1_elem.text if key1_elem is not None and key1_elem.text else ""

    key2_elem = header.find("key2") if header is not None else None
    key2 = key2_elem.text if key2_elem is not None and key2_elem.text else None

    lnum_elem = tail.find("L") if tail is not None else None
    lnum_str = lnum_elem.text if lnum_elem is not None and lnum_elem.text else "0"
    try:
        lnum = Decimal(lnum_str)
    except Exception:
        lnum = Decimal("0")

    pc_elem = tail.find("pc") if tail is not None else None
    page_ref = pc_elem.text if pc_elem is not None and pc_elem.text else None

    body_elem = root.find("body")
    body_content = None
    if body_elem is not None:
        body_content = ElementTree.tostring(body_elem, encoding="unicode", method="text")
        body_content = body_content.strip() if body_content else None

    normalized_key = key1.lower() if key1 else ""
    normalized_key2 = key2.lower() if key2 else None

    return CdslEntry(
        dict_id="",
        key=key1,
        key_normalized=normalized_key,
        key2=key2,
        key2_normalized=normalized_key2,
        lnum=lnum,
        data=raw_data,
        body=body_content,
        page_ref=page_ref,
    )


def extract_headwords(entry: CdslEntry) -> list[tuple[str, str, bool]]:
    results = []
    if entry.key:
        results.append((entry.key, entry.key_normalized, True))
    if entry.key2:
        results.append((entry.key2, entry.key2_normalized, False))
    return results


def extract_homonyms(entry: CdslEntry) -> list[dict]:
    if not entry.body:
        return []

    homonyms = []
    body_lower = entry.body.lower()

    pos = 0
    while True:
        idx = body_lower.find("<hom>", pos)
        if idx == -1:
            break
        end_idx = body_lower.find("</hom>", idx + 5)
        if end_idx == -1:
            break
        homonym_text = entry.body[idx + 5 : end_idx].strip()
        if homonym_text and homonym_text[0].isdigit():
            hom_num = int(homonym_text[0])
            homonyms.append(
                {
                    "homonym_num": hom_num,
                    "body": entry.body,
                }
            )
        pos = end_idx + 6

    if not homonyms:
        homonyms.append(
            {
                "homonym_num": 1,
                "body": entry.body,
            }
        )

    return homonyms


def iter_entries(data: str, limit: int | None = None) -> Iterator[CdslEntry]:
    count = 0
    for raw_line in data.split("\n"):
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue
        parts = stripped_line.split("|", CDSL_ENTRY_MIN_PARTS - 1)
        if len(parts) < CDSL_ENTRY_MIN_PARTS:
            continue
        key, lnum_str, xml_data = parts
        try:
            lnum = Decimal(lnum_str)
        except Exception:
            continue

        entry = parse_xml_entry(xml_data)
        if entry:
            entry.dict_id = ""
            entry.key = key
            entry.key_normalized = key.lower()
            entry.lnum = lnum
            yield entry
            count += 1
            if limit and count >= limit:
                break


GENDER_MAP = {
    "m": "masculine",
    "f": "feminine",
    "n": "neuter",
}

CASE_MAP = {
    "1": "1",
    "nom": "1",
    "nominative": "1",
    "2": "2",
    "gen": "2",
    "genitive": "2",
    "3": "3",
    "inst": "3",
    "instrumental": "3",
    "dat": "4",
    "dative": "4",
    "4": "4",
    "acc": "5",
    "accusative": "5",
    "5": "5",
    "abl": "6",
    "ablative": "6",
    "6": "6",
    "loc": "7",
    "locative": "7",
    "7": "7",
    "voc": "8",
    "vocative": "8",
    "8": "8",
}

NUMBER_MAP = {
    "sg": "sg",
    "singular": "sg",
    "pl": "pl",
    "plural": "pl",
    "du": "du",
    "dual": "du",
}


def _parse_gender_from_lex(lex_attr: str) -> list[str] | None:
    if not lex_attr:
        return None
    if lex_attr == "mfn" or "mfn" in lex_attr:
        return ["masculine", "feminine", "neuter"]
    return [GENDER_MAP[p.strip()] for p in lex_attr.split(":") if p.strip() in GENDER_MAP]


def _extract_declension(lex_attr: str) -> str | None:
    if "#" not in lex_attr:
        return None
    decl_match = re.search(r"#([A-Z])", lex_attr)
    return decl_match.group(1) if decl_match else None


def _parse_lexicon_element(lex_elem) -> tuple[dict, dict]:
    result = {}
    grammar_tags = {}

    lex_text = ""
    if lex_elem.text:
        lex_text += lex_elem.text
    for sub in lex_elem:
        if sub.tail:
            lex_text += sub.tail
    lex_text = lex_text.strip()

    pos_match = re.match(r"^([a-z\.]+)", lex_text)
    if pos_match:
        result["pos"] = pos_match.group(1)

    if "mfn" in lex_text and (
        "gender" not in result or result.get("gender") != ["masculine", "feminine", "neuter"]
    ):
        result["gender"] = ["masculine", "feminine", "neuter"]

    if "comp" in lex_text.lower():
        grammar_tags["compound"] = True

    for ab in lex_elem.findall("ab"):
        if ab.text:
            ab_text = ab.text.strip()
            grammar_tags.setdefault("abbreviations", []).append(ab_text)
            if "comp" in ab_text.lower():
                grammar_tags["compound"] = True

    return result, grammar_tags


def _parse_etymology(body, body_text: str, result: dict):
    children = list(body)
    for i, child in enumerate(children):
        if child.tag == "s" and child.text:
            prev_tail = ""
            if i > 0:
                prev_elem = children[i - 1]
                prev_tail = prev_elem.tail or ""
            if "√" in prev_tail or "radical" in prev_tail.lower() or "root" in prev_tail.lower():
                result["etymology"] = {"type": "verb_root", "root": child.text}
                return

    if "etymology" not in result and (
        "√" in body_text or "radical" in body_text.lower() or "root" in body_text.lower()
    ):
        result["etymology"] = {"type": "verb_root"}
        root_match = re.search(r"[\u221A√]\s*([a-zA-Z]+)", body_text)
        if root_match:
            result["etymology"]["root"] = root_match.group(1)


def _parse_references(body, result: dict):
    references = []

    # Parse ls elements (lexicon source citations)
    ls_elems = body.findall("ls")
    for ls in ls_elems:
        source_text = ls.text.strip() if ls.text else ""

        # Handle n="..." attribute (implied continuation from previous reference)
        if "n" in ls.attrib and ls.attrib["n"]:
            implied_prefix = ls.attrib["n"].strip()
            source_text = f"{implied_prefix} {source_text}" if source_text else implied_prefix

        if source_text:
            references.append({"source": source_text, "type": "lexicon"})

    # Parse s1 elements (cross-references)
    s1_elems = body.findall("s1")
    for s1 in s1_elems:
        if s1.text:
            references.append({"source": s1.text.strip(), "type": "cross_reference"})

    if references:
        result["references"] = references


def _find_sanskrit_form(body):
    for s_elem in body.findall("s"):
        if s_elem.text and s_elem.text.strip():
            return s_elem.text.strip()
    return None


def _extract_case_from_body(body_text: str) -> str | None:
    body_lower = body_text.lower()
    for pattern, case_num in CASE_MAP.items():
        if (
            f"case {pattern}" in body_lower
            or f" case {pattern}" in body_lower
            or f"({pattern})" in body_lower
            or f" {pattern}." in body_lower
        ) and case_num in ("1", "2", "3", "4", "5", "6", "7", "8"):
            return case_num
    return None


def _extract_number_from_body(body_text: str) -> str | None:
    body_lower = body_text.lower()
    for pattern, num_code in NUMBER_MAP.items():
        if f" {pattern}." in body_lower or f"({pattern})" in body_lower:
            return num_code
    return None


def _extract_grammar_from_info(info_elem, grammar_tags: dict, result: dict) -> None:
    if info_elem is None:
        return
    lex_attr = info_elem.get("lex", "")
    genders = _parse_gender_from_lex(lex_attr)
    if genders:
        result["gender"] = genders
    decl = _extract_declension(lex_attr)
    if decl:
        grammar_tags["declension"] = decl


def _extract_grammar_from_lex(lex_elem, grammar_tags: dict, result: dict) -> None:
    if lex_elem is None:
        return
    lex_result, lex_tags = _parse_lexicon_element(lex_elem)
    result.update(lex_result)
    grammar_tags.update(lex_tags)


def _extract_grammar_from_body(body_text: str, grammar_tags: dict) -> None:
    if "comp" in body_text.lower():
        grammar_tags["compound"] = True
    extracted_case = _extract_case_from_body(body_text)
    if extracted_case:
        grammar_tags["case"] = extracted_case
    extracted_number = _extract_number_from_body(body_text)
    if extracted_number:
        grammar_tags["number"] = extracted_number


def _build_body_text(body) -> str:
    body_text = ""
    if body.text:
        body_text += body.text
    for child in body:
        if child.tail:
            body_text += child.tail
    return body_text


def _parse_etymology_and_references(body, body_text: str, result: dict) -> None:
    _parse_etymology(body, body_text, result)
    _parse_references(body, result)


def parse_grammatical_info(xml_data: str) -> dict:
    result: dict = {}

    try:
        root = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError:
        return result

    body = root.find("body")
    if body is None:
        return result

    grammar_tags: dict = {}
    info_elem = body.find("info")
    _extract_grammar_from_info(info_elem, grammar_tags, result)
    lex_elem = body.find("lex")
    _extract_grammar_from_lex(lex_elem, grammar_tags, result)

    body_text = _build_body_text(body)
    _parse_etymology_and_references(body, body_text, result)

    if grammar_tags:
        result["grammar_tags"] = grammar_tags

    _populate_sanskrit_form(result, root, body)

    return result


def _populate_sanskrit_form(result: dict, root, body) -> None:
    """Populate sanskrit_form preferring explicit body forms over header fallbacks."""
    header = root.find("h")
    if header is not None:
        key2_elem = header.find("key2")
        key2_value = key2_elem.text.strip() if key2_elem is not None and key2_elem.text else ""
        if key2_value:
            result["sanskrit_form"] = key2_value

    if "sanskrit_form" not in result:
        sanskrit_form = _find_sanskrit_form(body)
        if sanskrit_form:
            result["sanskrit_form"] = sanskrit_form

    if "sanskrit_form" not in result and header is not None:
        key1_elem = header.find("key1")
        if key1_elem is not None and key1_elem.text:
            sanskrit_form = key1_elem.text.strip()
            if sanskrit_form:
                result["sanskrit_form"] = sanskrit_form
