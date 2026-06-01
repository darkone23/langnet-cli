from __future__ import annotations

import re
import unicodedata

_ROMAN_VALUES = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}
_ROMAN_RE = re.compile(r"[ivxlcdm]+", re.IGNORECASE)
_CHAPTER_LABEL_NUMBER_RE = re.compile(
    r"^(?P<label>.+?)\s+(?P<number>[0-9ivxlcdm]+)$", re.IGNORECASE
)
_NUMBER_RE = re.compile(r"^[0-9ivxlcdm]+$", re.IGNORECASE)
_REFERENCE_TOKEN_RE = re.compile(r"[^\W\d_]+|\d+", re.UNICODE)

_DCS_REFERENCE_ALIASES = {
    "astadhyayi": ("Aṣṭādhyāyī", "Astadhyayi", "Aṣṭ", "Pāṇ.", "Pāṇ", "Pan.", "Pan"),
    "bhagi": ("BhaGī", "BhG", "Bhagavadgītā", "Bhagavadgita"),
    "chu": ("ChU", "ChUp", "ChUp.", "Chāndogyopaniṣad", "Chandogyopanisad"),
    "kathup": ("KaṭhUp", "KathUp", "Kaṭhopaniṣad"),
    "manus": ("ManuS", "Manu", "Mn."),
}


def normalize_citation_reference(reference: str) -> str:
    tokens = _REFERENCE_TOKEN_RE.findall(reference.replace(",", " ").replace(".", " "))
    normalized: list[str] = []
    for index, token in enumerate(tokens):
        key = _strip_marks(token).casefold()
        if index > 0 and _ROMAN_RE.fullmatch(key):
            normalized.append(str(_roman_to_int(key)))
        else:
            normalized.append("".join(ch for ch in key if ch.isalnum()))
    return "".join(normalized)


def dcs_native_citation_references(
    *,
    chapter: str,
    sent_counter: str,
) -> tuple[str, ...]:
    if not chapter.strip() or not sent_counter.strip():
        return ()
    chapter_ref = _dcs_chapter_reference(chapter)
    if chapter_ref is None:
        return ()
    label, chapter_numbers = chapter_ref
    numbers = (*chapter_numbers, _normalize_number(sent_counter))
    aliases = _DCS_REFERENCE_ALIASES.get(_strip_marks(label).casefold(), (label,))
    refs = [f"{alias} {'.'.join(numbers)}" for alias in aliases]
    return tuple(dict.fromkeys(refs))


def _dcs_chapter_reference(chapter: str) -> tuple[str, tuple[str, ...]] | None:
    pending_numbers: list[str] = []
    for raw_part in reversed([part.strip() for part in chapter.split(",") if part.strip()]):
        match = _CHAPTER_LABEL_NUMBER_RE.fullmatch(raw_part)
        if match:
            number = _normalize_number(match.group("number"))
            return match.group("label").strip(), (number, *reversed(pending_numbers))
        if _NUMBER_RE.fullmatch(raw_part):
            pending_numbers.append(_normalize_number(raw_part))
            continue
        if pending_numbers:
            return raw_part, tuple(reversed(pending_numbers))
    return None


def _normalize_number(value: str) -> str:
    key = value.strip().strip(",.;:").casefold()
    if _ROMAN_RE.fullmatch(key):
        return str(_roman_to_int(key))
    return key


def _roman_to_int(value: str) -> int:
    total = 0
    previous = 0
    for char in reversed(value.casefold()):
        current = _ROMAN_VALUES[char]
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total


def _strip_marks(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
