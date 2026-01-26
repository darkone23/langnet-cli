from decimal import Decimal
from typing import Iterator, Optional
from xml.etree import ElementTree

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
