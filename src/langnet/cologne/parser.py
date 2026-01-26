from decimal import Decimal
from typing import Iterator, Optional
from xml.etree import ElementTree
import re

from .models import CdslEntry


def parse_xml_entry(raw_data: str) -> Optional[CdslEntry]:
    try:
        root = ElementTree.fromstring(raw_data)
    except ElementTree.ParseError:
        return None

    header = root.find("h")
    body = root.find("body")
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
        body_content = ElementTree.tostring(
            body_elem, encoding="unicode", method="text"
        )
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
    hom_positions = []

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


def iter_entries(data: str, limit: Optional[int] = None) -> Iterator[CdslEntry]:
    count = 0
    for line in data.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
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
    if info_elem is not None:
        lex_attr = info_elem.get("lex", "")
        if lex_attr:
            genders = []
            if lex_attr == "mfn":
                genders = ["masculine", "feminine", "neuter"]
            elif "mfn" in lex_attr:
                genders = ["masculine", "feminine", "neuter"]
            else:
                for part in lex_attr.split(":"):
                    part = part.strip()
                    if part in GENDER_MAP:
                        genders.append(GENDER_MAP[part])
            if genders:
                result["gender"] = genders

            if "#" in lex_attr:
                decl_match = re.search(r"#([A-Z])", lex_attr)
                if decl_match:
                    grammar_tags["declension"] = decl_match.group(1)

    lex_elem = body.find("lex")
    if lex_elem is not None:
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

        if "mfn" in lex_text:
            if "gender" not in result or result["gender"] != [
                "masculine",
                "feminine",
                "neuter",
            ]:
                result["gender"] = ["masculine", "feminine", "neuter"]

        if "comp" in lex_text.lower():
            grammar_tags["compound"] = True

        for ab in lex_elem.findall("ab"):
            if ab.text:
                if "abbreviations" not in grammar_tags:
                    grammar_tags["abbreviations"] = []
                grammar_tags["abbreviations"].append(ab.text.strip())

    body_text = ""
    if body.text:
        body_text += body.text
    for child in body:
        if child.tail:
            body_text += child.tail

    if "comp" in body_text.lower():
        grammar_tags["compound"] = True

    children = list(body)
    for i, child in enumerate(children):
        if child.tag == "s" and child.text:
            prev_tail = ""
            if i > 0:
                prev_elem = children[i - 1]
                prev_tail = prev_elem.tail or ""
            if (
                "√" in prev_tail
                or "radical" in prev_tail.lower()
                or "root" in prev_tail.lower()
            ):
                result["etymology"] = {"type": "verb_root", "root": child.text}
                break

    if "etymology" not in result:
        if (
            "√" in body_text
            or "radical" in body_text.lower()
            or "root" in body_text.lower()
        ):
            result["etymology"] = {"type": "verb_root"}
            root_match = re.search(r"[\u221A√]\s*([a-zA-Z]+)", body_text)
            if root_match:
                result["etymology"]["root"] = root_match.group(1)

    sanskrit_elems = body.findall("s")
    for s_elem in sanskrit_elems:
        if s_elem.text and s_elem.text.strip():
            result["sanskrit_form"] = s_elem.text.strip()
            break

    ls_elems = body.findall("ls")
    if ls_elems:
        references = []
        for ls in ls_elems:
            if ls.text:
                references.append({"source": ls.text.strip(), "type": "lexicon"})
        if references:
            result["references"] = references

    s1_elems = body.findall("s1")
    if s1_elems:
        if "references" not in result:
            result["references"] = []
        for s1 in s1_elems:
            if s1.text:
                result["references"].append(
                    {"source": s1.text.strip(), "type": "cross_reference"}
                )

    if grammar_tags:
        result["grammar_tags"] = grammar_tags

    return result

    body = root.find("body")
    if body is None:
        return result

    grammar_tags: dict = {}

    info_elem = body.find("info")
    if info_elem is not None:
        lex_attr = info_elem.get("lex", "")
        if lex_attr:
            genders = []
            if lex_attr == "mfn":
                genders = ["masculine", "feminine", "neuter"]
            elif "mfn" in lex_attr:
                genders = ["masculine", "feminine", "neuter"]
            else:
                for part in lex_attr.split(":"):
                    part = part.strip()
                    if part in GENDER_MAP:
                        genders.append(GENDER_MAP[part])
            if genders:
                result["gender"] = genders

            if "#" in lex_attr:
                decl_match = re.search(r"#([A-Z])", lex_attr)
                if decl_match:
                    grammar_tags["declension"] = decl_match.group(1)

    lex_elem = body.find("lex")
    if lex_elem is not None:
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

        if "mfn" in lex_text:
            if "gender" not in result or result["gender"] != [
                "masculine",
                "feminine",
                "neuter",
            ]:
                result["gender"] = ["masculine", "feminine", "neuter"]

        if "comp" in lex_text.lower():
            grammar_tags["compound"] = True

        for ab in lex_elem.findall("ab"):
            if ab.text:
                if "abbreviations" not in grammar_tags:
                    grammar_tags["abbreviations"] = []
                grammar_tags["abbreviations"].append(ab.text.strip())

    body_text = ""
    if body.text:
        body_text += body.text
    for child in body:
        if child.tail:
            body_text += child.tail

    if "comp" in body_text.lower():
        grammar_tags["compound"] = True

    if "comp" in body_text.lower():
        grammar_tags["compound"] = True

    for child in body:
        if child.tag == "s" and child.text:
            if (
                "√" in (child.tail or "")
                or "radical" in (child.tail or "").lower()
                or "root" in (child.tail or "").lower()
            ):
                result["etymology"] = {"type": "verb_root", "root": child.text}
                break

    if "etymology" not in result:
        if (
            "√" in body_text
            or "radical" in body_text.lower()
            or "root" in body_text.lower()
        ):
            result["etymology"] = {"type": "verb_root"}
            root_match = re.search(r"[\u221A√]\s*([a-zA-Z]+)", body_text)
            if root_match:
                result["etymology"]["root"] = root_match.group(1)

    sanskrit_elems = body.findall("s")
    for s_elem in sanskrit_elems:
        if s_elem.text and s_elem.text.strip():
            result["sanskrit_form"] = s_elem.text.strip()
            break

    ls_elems = body.findall("ls")
    if ls_elems:
        references = []
        for ls in ls_elems:
            if ls.text:
                references.append({"source": ls.text.strip(), "type": "lexicon"})
        if references:
            result["references"] = references

    s1_elems = body.findall("s1")
    if s1_elems:
        if "references" not in result:
            result["references"] = []
        for s1 in s1_elems:
            if s1.text:
                result["references"].append(
                    {"source": s1.text.strip(), "type": "cross_reference"}
                )

    if grammar_tags:
        result["grammar_tags"] = grammar_tags

    return result

    body = root.find("body")
    if body is None:
        return result

    grammar_tags: dict = {}

    info_elem = body.find("info")
    if info_elem is not None:
        lex_attr = info_elem.get("lex", "")
        if lex_attr:
            genders = []
            if lex_attr == "mfn":
                genders = ["masculine", "feminine", "neuter"]
            elif "mfn" in lex_attr:
                genders = ["masculine", "feminine", "neuter"]
            else:
                for part in lex_attr.split(":"):
                    part = part.strip()
                    if part in GENDER_MAP:
                        genders.append(GENDER_MAP[part])
            if genders:
                result["gender"] = genders

            if "#" in lex_attr:
                decl_match = re.search(r"#([A-Z])", lex_attr)
                if decl_match:
                    grammar_tags["declension"] = decl_match.group(1)

    lex_elem = body.find("lex")
    if lex_elem is not None:
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

        if "mfn" in lex_text:
            if "gender" not in result or result["gender"] != [
                "masculine",
                "feminine",
                "neuter",
            ]:
                result["gender"] = ["masculine", "feminine", "neuter"]

        if "comp" in lex_text.lower():
            grammar_tags["compound"] = True

        for ab in lex_elem.findall("ab"):
            if ab.text:
                if "abbreviations" not in grammar_tags:
                    grammar_tags["abbreviations"] = []
                grammar_tags["abbreviations"].append(ab.text.strip())

    body_text = ""
    if body.text:
        body_text += body.text
    for child in body:
        if child.tail:
            body_text += child.tail

    if "comp" in body_text.lower():
        grammar_tags["compound"] = True

    if "\u221a" in body_text or "√" in body_text:
        result["etymology"] = {"type": "verb_root"}
        root_match = re.search(r"[\u221A√]\s*([a-zA-Z]+)", body_text)
        if not root_match:
            root_match = re.search(
                r"\(\s*[\u221A√]\s*<s>\s*([a-zA-Z]+)\s*</s>\s*\)", body_text
            )
        if not root_match:
            root_match = re.search(r"\(\s*[\u221A√]\s*([a-zA-Z]+)\s*\)", body_text)
        if root_match:
            result["etymology"]["root"] = root_match.group(1)

    sanskrit_elems = body.findall("s")
    for s_elem in sanskrit_elems:
        if s_elem.text and s_elem.text.strip():
            result["sanskrit_form"] = s_elem.text.strip()
            break

    ls_elems = body.findall("ls")
    if ls_elems:
        references = []
        for ls in ls_elems:
            if ls.text:
                references.append({"source": ls.text.strip(), "type": "lexicon"})
        if references:
            result["references"] = references

    s1_elems = body.findall("s1")
    if s1_elems:
        if "references" not in result:
            result["references"] = []
        for s1 in s1_elems:
            if s1.text:
                result["references"].append(
                    {"source": s1.text.strip(), "type": "cross_reference"}
                )

    if grammar_tags:
        result["grammar_tags"] = grammar_tags

    return result
