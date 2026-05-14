from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

from langnet.reader.adapters import (
    LegacyIdtWork,
    parse_legacy_idt_metadata,
    parse_legacy_text_dump_with_idt,
)
from langnet.reader.models import ReaderSegment, ReaderSourceFile, ReaderSourceMetadata

TLG_CANON_WORK_ID_PARTS = 2


class _ListItemParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []
        self._in_li = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "li":
            self._in_li = True
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "li" or not self._in_li:
            return
        text = _normalize_text("".join(self._parts))
        if text:
            self.items.append(text)
        self._in_li = False
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_li:
            self._parts.append(data)


def legacy_source_files(
    root: Path,
    collection_id: str,
    *,
    hash_files: bool = True,
) -> list[ReaderSourceFile]:
    if not root.exists():
        return []
    return [
        ReaderSourceFile(
            collection_id=collection_id,
            source_path=path,
            file_role=_legacy_file_role(path),
            file_status=_legacy_file_status(path),
            source_id=path.stem,
            source_hash=_file_hash(path) if hash_files else None,
            size_bytes=path.stat().st_size,
        )
        for path in sorted(root.iterdir())
        if path.is_file()
    ]


def legacy_source_metadata(root: Path, collection_id: str) -> list[ReaderSourceMetadata]:
    if not root.exists():
        return []
    rows: list[ReaderSourceMetadata] = []
    authtab = root / "authtab.dir"
    if authtab.exists():
        rows.extend(parse_legacy_authtab(authtab, collection_id=collection_id))
    for idt_path in sorted(root.glob("*.idt")):
        rows.extend(parse_legacy_idt_source_metadata(idt_path, collection_id=collection_id))
    if collection_id == "tlg":
        for canon_path in sorted(root.glob("doccan*.txt")):
            rows.extend(parse_tlg_canon_source_metadata(canon_path, collection_id=collection_id))
    for html_path in sorted(root.glob("*.php")):
        rows.extend(parse_html_author_index(html_path, collection_id=collection_id))
    return rows


def parse_legacy_authtab(
    path: Path,
    *,
    collection_id: str,
) -> list[ReaderSourceMetadata]:
    rows: list[ReaderSourceMetadata] = []
    base_language = ""
    for raw_entry in path.read_bytes().split(b"\xff"):
        if not raw_entry:
            continue
        entry = raw_entry.decode("latin-1", errors="ignore")
        if entry.startswith("*"):
            marker = re.search(r"\x83([A-Za-z])", entry)
            base_language = _diogenes_language(marker.group(1)) if marker else base_language
            continue
        match = re.search(r"\b([A-Z]{3})([A-Za-z0-9]{4})\s+([^\x83]+)", entry)
        if not match:
            continue
        prefix, number, name = match.groups()
        source_id = f"{prefix.lower()}{number.lower()}"
        lang_marker = re.search(r"\x83([A-Za-z])", entry)
        language = _diogenes_language(lang_marker.group(1)) if lang_marker else base_language
        rows.append(
            ReaderSourceMetadata(
                collection_id=collection_id,
                subject_kind="author",
                subject_id=source_id,
                key="authtab_author_name",
                value=_normalize_text(name),
                source_path=path,
            )
        )
        if language:
            rows.append(
                ReaderSourceMetadata(
                    collection_id=collection_id,
                    subject_kind="author",
                    subject_id=source_id,
                    key="authtab_language",
                    value=language,
                    source_path=path,
                )
            )
    return rows


def parse_legacy_idt_source_metadata(
    path: Path,
    *,
    collection_id: str,
) -> list[ReaderSourceMetadata]:
    rows: list[ReaderSourceMetadata] = []
    author_subject = path.stem
    for work in parse_legacy_idt_metadata(path):
        rows.extend(_idt_author_metadata(path, collection_id, author_subject, work))
        rows.extend(_idt_work_metadata(path, collection_id, author_subject, work))
    return _dedupe_metadata(rows)


def parse_html_author_index(
    path: Path,
    *,
    collection_id: str,
) -> list[ReaderSourceMetadata]:
    parser = _ListItemParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return [
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="collection",
            subject_id=path.name,
            key="cd_index_author",
            value=item,
            source_path=path,
        )
        for item in parser.items
    ]


def parse_tlg_canon_source_metadata(
    path: Path,
    *,
    collection_id: str,
) -> list[ReaderSourceMetadata]:
    idt_path = path.with_suffix(".idt")
    if not idt_path.exists():
        return []
    rows: list[ReaderSourceMetadata] = []
    for book in parse_legacy_text_dump_with_idt(
        path,
        idt_path=idt_path,
        collection_id=collection_id,
        language="grc",
    ):
        rows.extend(tlg_canon_metadata_from_segments(path, collection_id, book.segments))
    return _dedupe_metadata(rows)


def tlg_canon_metadata_from_segments(  # noqa: C901
    path: Path,
    collection_id: str,
    segments: list[ReaderSegment],
) -> list[ReaderSourceMetadata]:
    rows: list[ReaderSourceMetadata] = []
    author_numbers_by_entry: dict[str, str] = {}
    pending_work_subjects: dict[tuple[str, str], str] = {}
    for segment in segments:
        citation_path = segment.citation_path
        text = _normalize_text(segment.text)
        if not text:
            continue
        author_match = re.fullmatch(r"(?P<entry>\d+)\.a\.(?P<line>[12])", citation_path)
        if author_match:
            entry = author_match.group("entry")
            if author_match.group("line") == "1" and re.fullmatch(r"\d{4}", text):
                author_numbers_by_entry[entry] = text
                subject_id = f"tlg{text}"
                rows.append(
                    ReaderSourceMetadata(
                        collection_id=collection_id,
                        subject_kind="author",
                        subject_id=subject_id,
                        key="tlg_canon_entry",
                        value=entry,
                        source_path=path,
                    )
                )
            elif author_match.group("line") == "2":
                author_number = author_numbers_by_entry.get(entry)
                if author_number is None:
                    continue
                name, category = _split_tlg_canon_author_category(text)
                subject_id = f"tlg{author_number}"
                rows.append(
                    ReaderSourceMetadata(
                        collection_id=collection_id,
                        subject_kind="author",
                        subject_id=subject_id,
                        key="tlg_canon_author_name",
                        value=name,
                        source_path=path,
                    )
                )
                if category:
                    rows.append(
                        ReaderSourceMetadata(
                            collection_id=collection_id,
                            subject_kind="author",
                            subject_id=subject_id,
                            key="tlg_canon_category",
                            value=category,
                            source_path=path,
                        )
                    )
            continue

        work_match = re.fullmatch(r"(?P<entry>\d+)\.(?P<work>\d+)\.(?P<line>[12])", citation_path)
        if not work_match:
            continue
        entry = work_match.group("entry")
        work_number = work_match.group("work")
        author_number = author_numbers_by_entry.get(entry)
        if author_number is None:
            continue
        if work_match.group("line") == "1":
            ids = re.findall(r"\d+", text)
            if len(ids) >= TLG_CANON_WORK_ID_PARTS:
                subject_id = f"tlg{ids[0]}.tlg{ids[1].zfill(3)}"
                pending_work_subjects[(entry, work_number)] = subject_id
                rows.append(
                    ReaderSourceMetadata(
                        collection_id=collection_id,
                        subject_kind="work",
                        subject_id=subject_id,
                        key="tlg_canon_work_number",
                        value=ids[1].zfill(3),
                        source_path=path,
                    )
                )
        elif work_match.group("line") == "2":
            subject_id = pending_work_subjects.get(
                (entry, work_number),
                f"tlg{author_number}.tlg{work_number.zfill(3)}",
            )
            rows.append(
                ReaderSourceMetadata(
                    collection_id=collection_id,
                    subject_kind="work",
                    subject_id=subject_id,
                    key="tlg_canon_work_title",
                    value=text,
                    source_path=path,
                )
            )
    return rows


def _split_tlg_canon_author_category(text: str) -> tuple[str, str]:
    bracket_match = re.fullmatch(r"(?P<name>[<\[][^\]>]+[>\]])(?:\s+(?P<category>.+))?", text)
    if bracket_match:
        name = _clean_tlg_canon_author_name(bracket_match.group("name"))
        category = _clean_tlg_canon_category(bracket_match.group("category") or "")
        return name, category
    tokens = text.split()
    category_tokens: list[str] = []
    while tokens and _looks_like_tlg_category_token(tokens[-1], category_tokens):
        category_tokens.append(tokens.pop())
    if not category_tokens:
        return _clean_tlg_canon_author_name(text), ""
    return (
        _clean_tlg_canon_author_name(" ".join(tokens)),
        _clean_tlg_canon_category(" ".join(reversed(category_tokens))),
    )


def _clean_tlg_canon_author_name(text: str) -> str:
    value = text.strip().strip("<>[]")
    value = " ".join(_title_upper_token(token) for token in value.split())
    return _normalize_text(value)


def _title_upper_token(token: str) -> str:
    return token.title() if token.isupper() and len(token) > 1 else token


def _clean_tlg_canon_category(text: str) -> str:
    return _normalize_text(text.strip().strip("<>[]"))


def _looks_like_tlg_category_token(token: str, category_tokens: list[str]) -> bool:
    stripped = token.strip("<>")
    if stripped == "et" and category_tokens:
        return True
    if re.fullmatch(r"[A-Z][a-z]+", stripped) and category_tokens:
        return True
    return bool(re.fullmatch(r"[A-Z][A-Za-z]+\.", stripped))


def _idt_author_metadata(
    path: Path,
    collection_id: str,
    author_subject: str,
    work: LegacyIdtWork,
) -> list[ReaderSourceMetadata]:
    return [
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="author",
            subject_id=author_subject,
            key="idt_author_id",
            value=work.author_id,
            source_path=path,
        ),
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="author",
            subject_id=author_subject,
            key="idt_author_name",
            value=work.author_name,
            source_path=path,
        ),
    ]


def _idt_work_metadata(
    path: Path,
    collection_id: str,
    author_subject: str,
    work: LegacyIdtWork,
) -> list[ReaderSourceMetadata]:
    work_subject = f"{author_subject}.{work.work_number}"
    rows = [
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="work",
            subject_id=work_subject,
            key="idt_title",
            value=work.work_name,
            source_path=path,
        ),
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="work",
            subject_id=work_subject,
            key="idt_start_block",
            value=str(work.start_block),
            source_path=path,
        ),
    ]
    if work.level_labels:
        rows.append(
            ReaderSourceMetadata(
                collection_id=collection_id,
                subject_kind="work",
                subject_id=work_subject,
                key="idt_citation_levels",
                value="|".join(work.level_labels),
                source_path=path,
            )
        )
    return rows


def _legacy_file_role(path: Path) -> str:
    if path.name == "authtab.dir":
        return "diogenes_authtab"
    if path.suffix == ".php" and "author" in path.name:
        return "html_author_index"
    return {
        ".idt": "diogenes_idt",
        ".txt": "diogenes_text",
        ".inx": "diogenes_word_index",
        ".bin": "diogenes_binary_index",
        ".dir": "diogenes_directory",
    }.get(path.suffix, "diogenes_support")


def _legacy_file_status(path: Path) -> str:
    role = _legacy_file_role(path)
    if role == "diogenes_text":
        return "text"
    if role in {"diogenes_authtab", "diogenes_idt", "html_author_index"}:
        return "metadata"
    return "support"


def _diogenes_language(marker: str) -> str:
    if marker == "g":
        return "grc"
    if marker in {"l", "e", "h"}:
        return "lat"
    return marker


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedupe_metadata(rows: list[ReaderSourceMetadata]) -> list[ReaderSourceMetadata]:
    seen: set[tuple[str, str, str, str, str, Path]] = set()
    deduped: list[ReaderSourceMetadata] = []
    for row in rows:
        key = (
            row.collection_id,
            row.subject_kind,
            row.subject_id,
            row.key,
            row.value,
            row.source_path,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
