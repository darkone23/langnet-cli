from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path

from langnet.reader.adapters import ParsedBook, parse_perseus_tei_with_fallback_urn
from langnet.reader.models import (
    ReaderCitationReference,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceFile,
    ReaderSourceMetadata,
)

OGL_COLLECTIONS = {
    "opengreekandlatin_latin",
    "opengreekandlatin_csel",
    "opengreekandlatin_patrologia",
    "opengreekandlatin_church_fathers",
}

_EXCLUDED_XML_NAMES = {
    "__cts__.xml",
    "build.xml",
    "catalog.xml",
    "expath-pkg.xml",
    "package.xml",
    "pom.xml",
    "repo.xml",
}
_EXCLUDED_PATH_PARTS = {
    ".git",
    ".github",
    "build",
    "dist",
    "target",
    "schema",
    "schemas",
    "xsl",
    "xslt",
}
_ALTERNATE_VIEW_PARTS = {
    "Volumes": "alternate_view_volumes",
    "corrected": "alternate_view_corrected",
    "split": "alternate_view_split",
    "volumes": "alternate_view_volumes",
}


@dataclass(frozen=True)
class OglSourceCandidate:
    collection_id: str
    source_path: Path
    source_root: Path
    source_view: str
    source_priority: int
    source_id: str
    cts_work_urn: str | None
    cts_edition_urn: str | None
    synthetic_work_id: str | None
    cts_groupname: str | None
    cts_title: str | None
    cts_edition_label: str | None
    cts_edition_description: str | None
    edition_key: str
    import_policy: str
    import_status: str
    skip_reason: str = ""
    segment_count: int = 0
    parse_error: str = ""


def discover_ogl_sources(root: Path, collection_id: str) -> list[OglSourceCandidate]:
    if collection_id not in OGL_COLLECTIONS:
        msg = f"unsupported OpenGreek+Latin collection: {collection_id}"
        raise ValueError(msg)
    if not root.exists():
        return []

    path_candidates = [
        _path_candidate(root, collection_id, path)
        for path in sorted(root.rglob("*.xml"))
        if is_ogl_source_xml(path)
    ]
    if not path_candidates:
        return []
    best_priority = min(candidate.source_priority for candidate in path_candidates)
    candidates: list[OglSourceCandidate] = []
    for candidate in path_candidates:
        if candidate.source_priority != best_priority:
            candidates.append(
                replace(
                    candidate,
                    import_status="skipped_alternate_view",
                    skip_reason=candidate.source_view,
                )
            )
            continue
        candidates.append(_parsed_candidate(candidate))
    return _apply_default_import_policy(candidates)


def selected_ogl_sources(root: Path, collection_id: str) -> list[OglSourceCandidate]:
    return [
        candidate
        for candidate in discover_ogl_sources(root, collection_id)
        if candidate.import_status == "text_imported"
    ]


def parse_ogl_tei(candidate: OglSourceCandidate) -> ParsedBook:
    parsed = parse_perseus_tei_with_fallback_urn(
        candidate.source_path,
        collection_id=candidate.collection_id,
        fallback_namespace="langnet",
        prefer_fallback_namespace=True,
    )
    parsed = _apply_ogl_cts_inventory_metadata(parsed, candidate)
    return _with_collection_scoped_catalog_ids(parsed, candidate.collection_id)


def ogl_source_files(candidates: list[OglSourceCandidate]) -> list[ReaderSourceFile]:
    return [
        ReaderSourceFile(
            collection_id=candidate.collection_id,
            source_path=candidate.source_path,
            file_role="opengreekandlatin_tei",
            file_status=_source_file_status(candidate),
            source_id=candidate.source_id,
            source_hash=None,
            size_bytes=candidate.source_path.stat().st_size
            if candidate.source_path.exists()
            else None,
        )
        for candidate in candidates
    ]


def ogl_source_metadata(candidates: list[OglSourceCandidate]) -> list[ReaderSourceMetadata]:
    rows: list[ReaderSourceMetadata] = []
    for candidate in candidates:
        values = {
            "import_status": candidate.import_status,
            "source_view": candidate.source_view,
            "source_priority": str(candidate.source_priority),
            "import_policy": candidate.import_policy,
            "edition_key": candidate.edition_key,
            "segment_count": str(candidate.segment_count),
            "has_real_cts_urn": "true" if candidate.cts_edition_urn else "false",
            "synthetic_identity_used": "true" if candidate.synthetic_work_id else "false",
        }
        if candidate.skip_reason:
            values["import_skip_reason"] = candidate.skip_reason
        if candidate.parse_error:
            values["parse_error"] = candidate.parse_error
        if candidate.cts_work_urn:
            values["cts_work_urn"] = candidate.cts_work_urn
        if candidate.cts_edition_urn:
            values["cts_edition_urn"] = candidate.cts_edition_urn
        if candidate.synthetic_work_id:
            values["synthetic_work_id"] = candidate.synthetic_work_id
        if candidate.cts_groupname:
            values["cts_groupname"] = candidate.cts_groupname
        if candidate.cts_title:
            values["cts_title"] = candidate.cts_title
        if candidate.cts_edition_label:
            values["cts_edition_label"] = candidate.cts_edition_label
        if candidate.cts_edition_description:
            values["cts_edition_description"] = candidate.cts_edition_description
        if candidate.cts_work_urn or candidate.synthetic_work_id:
            values["catalog_work_id"] = _ogl_catalog_id(
                candidate.collection_id,
                candidate.cts_work_urn or candidate.synthetic_work_id or candidate.edition_key,
            )
        if candidate.cts_edition_urn or candidate.edition_key:
            values["catalog_edition_id"] = _ogl_catalog_id(
                candidate.collection_id,
                candidate.cts_edition_urn or candidate.edition_key,
            )

        rows.extend(
            ReaderSourceMetadata(
                collection_id=candidate.collection_id,
                subject_kind="source_file",
                subject_id=candidate.source_id,
                key=key,
                value=value,
                source_path=candidate.source_path,
            )
            for key, value in values.items()
            if value
        )
    return rows


def is_ogl_source_xml(path: Path) -> bool:
    if path.name.startswith("__"):
        return False
    if path.suffix.lower() != ".xml":
        return False
    if path.name in _EXCLUDED_XML_NAMES:
        return False
    if any(part in _EXCLUDED_PATH_PARTS for part in path.parts):
        return False
    return looks_like_ogl_tei(path)


def looks_like_ogl_tei(path: Path) -> bool:
    try:
        prefix = path.read_text(encoding="utf-8", errors="ignore")[:65536]
    except OSError:
        return False
    return "<TEI" in prefix or "<teiCorpus" in prefix


def _with_collection_scoped_catalog_ids(parsed: ParsedBook, collection_id: str) -> ParsedBook:
    old_work_id = parsed.work.work_id
    old_edition_id = parsed.edition.edition_id
    new_work_id = _ogl_catalog_id(collection_id, old_work_id)
    new_edition_id = _ogl_catalog_id(collection_id, old_edition_id)

    return ParsedBook(
        work=replace(parsed.work, work_id=new_work_id),
        edition=replace(parsed.edition, work_id=new_work_id, edition_id=new_edition_id),
        segments=[
            _with_catalog_segment_ids(
                segment,
                old_work_id=old_work_id,
                new_work_id=new_work_id,
                new_edition_id=new_edition_id,
            )
            for segment in parsed.segments
        ],
        addresses=[
            _with_catalog_address_ids(
                address,
                old_work_id=old_work_id,
                new_work_id=new_work_id,
            )
            for address in parsed.addresses
        ],
        citation_references=[
            _with_catalog_citation_reference_ids(
                reference,
                old_work_id=old_work_id,
                new_work_id=new_work_id,
            )
            for reference in parsed.citation_references
        ],
    )


def _with_catalog_segment_ids(
    segment: ReaderSegment,
    *,
    old_work_id: str,
    new_work_id: str,
    new_edition_id: str,
) -> ReaderSegment:
    return replace(
        segment,
        segment_id=_replace_catalog_id_prefix(segment.segment_id, old_work_id, new_work_id),
        work_id=new_work_id,
        edition_id=new_edition_id,
    )


def _with_catalog_address_ids(
    address: ReaderSegmentAddress,
    *,
    old_work_id: str,
    new_work_id: str,
) -> ReaderSegmentAddress:
    return replace(
        address,
        segment_id=_replace_catalog_id_prefix(address.segment_id, old_work_id, new_work_id),
    )


def _with_catalog_citation_reference_ids(
    reference: ReaderCitationReference,
    *,
    old_work_id: str,
    new_work_id: str,
) -> ReaderCitationReference:
    return replace(
        reference,
        work_id=new_work_id,
        segment_id=_replace_catalog_id_prefix(reference.segment_id, old_work_id, new_work_id),
    )


def _replace_catalog_id_prefix(value: str, old_prefix: str, new_prefix: str) -> str:
    if value == old_prefix:
        return new_prefix
    old_with_sep = f"{old_prefix}:"
    if value.startswith(old_with_sep):
        return f"{new_prefix}:{value[len(old_with_sep):]}"
    return f"{new_prefix}:{value}"


def _ogl_catalog_id(collection_id: str, source_id: str) -> str:
    return f"urn:langnet:ogl:{collection_id}:{source_id}"


def _ogl_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in slug.split("-") if part) or "unknown"


def _path_candidate(root: Path, collection_id: str, path: Path) -> OglSourceCandidate:
    source_view = _source_view(root, path)
    source_id = _source_id(root, path)
    return OglSourceCandidate(
        collection_id=collection_id,
        source_path=path,
        source_root=root,
        source_view=source_view,
        source_priority=_source_priority(source_view),
        source_id=source_id,
        cts_work_urn=None,
        cts_edition_urn=None,
        synthetic_work_id=None,
        cts_groupname=None,
        cts_title=None,
        cts_edition_label=None,
        cts_edition_description=None,
        edition_key=source_id,
        import_policy="default",
        import_status="candidate",
    )


def _parsed_candidate(candidate: OglSourceCandidate) -> OglSourceCandidate:
    try:
        parsed = parse_perseus_tei_with_fallback_urn(
            candidate.source_path,
            collection_id=candidate.collection_id,
            fallback_namespace="langnet",
            prefer_fallback_namespace=True,
        )
    except Exception as exc:  # noqa: BLE001
        return replace(
            candidate,
            cts_work_urn=None,
            cts_edition_urn=None,
            synthetic_work_id=None,
            cts_groupname=None,
            cts_title=None,
            cts_edition_label=None,
            cts_edition_description=None,
            import_status="parse_error",
            skip_reason="parse_error",
            parse_error=str(exc),
        )

    inventory = _cts_inventory_metadata(candidate.source_path)
    cts_edition_urn = parsed.edition.cts_edition_urn
    has_real_cts_urn = bool(
        cts_edition_urn and not cts_edition_urn.startswith("urn:cts:langnet:")
    )
    synthetic_work_id = (
        parsed.work.work_id if parsed.work.work_id.startswith("urn:cts:langnet:") else None
    )
    return replace(
        candidate,
        cts_work_urn=parsed.work.cts_work_urn if has_real_cts_urn else None,
        cts_edition_urn=cts_edition_urn if has_real_cts_urn else None,
        synthetic_work_id=synthetic_work_id,
        cts_groupname=inventory["groupname"],
        cts_title=inventory["title"],
        cts_edition_label=inventory["edition_label"],
        cts_edition_description=inventory["edition_description"],
        edition_key=parsed.edition.edition_id,
        import_status="candidate",
        segment_count=len(parsed.segments),
    )


def _apply_default_import_policy(
    candidates: list[OglSourceCandidate],
) -> list[OglSourceCandidate]:
    if not candidates:
        return []

    preferred = [
        candidate
        for candidate in sorted(candidates, key=_candidate_sort_key)
        if candidate.import_status != "parse_error"
        and candidate.source_priority == _best_priority(candidates)
    ]
    selected_work_ids: set[str] = set()
    selected_paths: set[Path] = set()
    updates: dict[Path, OglSourceCandidate] = {}

    for candidate in preferred:
        if candidate.segment_count <= 0:
            updates[candidate.source_path] = replace(
                candidate,
                import_status="skipped_no_segments",
                skip_reason="no_text_segments",
            )
            continue
        work_key = candidate.cts_work_urn or candidate.synthetic_work_id or candidate.edition_key
        if work_key in selected_work_ids:
            updates[candidate.source_path] = replace(
                candidate,
                import_status="skipped_duplicate",
                skip_reason="duplicate_work_id",
            )
            continue
        selected_work_ids.add(work_key)
        selected_paths.add(candidate.source_path)
        updates[candidate.source_path] = replace(candidate, import_status="text_imported")

    for candidate in candidates:
        if candidate.source_path in updates:
            continue
        if candidate.import_status == "parse_error":
            updates[candidate.source_path] = candidate
            continue
        if candidate.source_priority != _best_priority(candidates):
            updates[candidate.source_path] = replace(
                candidate,
                import_status="skipped_alternate_view",
                skip_reason=candidate.source_view,
            )
            continue
        if candidate.source_path not in selected_paths:
            updates[candidate.source_path] = replace(
                candidate,
                import_status="skipped_duplicate",
                skip_reason="duplicate_work_id",
            )

    return [updates[candidate.source_path] for candidate in candidates]


def _best_priority(candidates: list[OglSourceCandidate]) -> int:
    eligible = [
        candidate.source_priority
        for candidate in candidates
        if candidate.import_status != "parse_error"
    ]
    return min(eligible) if eligible else 0


def _source_file_status(candidate: OglSourceCandidate) -> str:
    if candidate.import_status == "text_imported":
        return "text"
    if candidate.import_status == "parse_error":
        return "error"
    return "skipped"


def _apply_ogl_cts_inventory_metadata(
    parsed: ParsedBook,
    candidate: OglSourceCandidate,
) -> ParsedBook:
    title = _preferred_ogl_title(parsed.work.title, parsed.work.source_id, candidate)
    author = _preferred_ogl_author(parsed.work.author, title, candidate)
    author_id = _preferred_ogl_author_id(parsed, author, candidate)
    language = _preferred_ogl_language(parsed, candidate)
    edition_label = candidate.cts_edition_label or parsed.edition.label
    if (
        title == parsed.work.title
        and author == parsed.work.author
        and author_id == parsed.work.author_id
        and language == parsed.work.language
        and language == parsed.edition.language
        and edition_label == parsed.edition.label
    ):
        return parsed
    return ParsedBook(
        work=replace(parsed.work, title=title, author=author, author_id=author_id, language=language),
        edition=replace(parsed.edition, label=edition_label, language=language),
        segments=parsed.segments,
        addresses=parsed.addresses,
        citation_references=parsed.citation_references,
    )


def _preferred_ogl_title(
    parsed_title: str,
    source_id: str,
    candidate: OglSourceCandidate,
) -> str:
    if not candidate.cts_title:
        return parsed_title
    if _is_weak_ogl_title(parsed_title, source_id):
        return candidate.cts_title
    return parsed_title


def _preferred_ogl_author(
    parsed_author: str,
    parsed_title: str,
    candidate: OglSourceCandidate,
) -> str:
    if not candidate.cts_groupname:
        if parsed_author.strip().lower() in {"", "unknown", "anonymous"}:
            return (
                _inferred_ogl_author_from_title(candidate.cts_title or parsed_title)
                or parsed_author
            )
        return parsed_author
    if parsed_author.strip().lower() in {"", "unknown", "anonymous"}:
        return candidate.cts_groupname
    return parsed_author


def _preferred_ogl_author_id(
    parsed: ParsedBook,
    author: str,
    candidate: OglSourceCandidate,
) -> str | None:
    if not parsed.work.cts_work_urn or not parsed.work.cts_work_urn.startswith("urn:cts:langnet:"):
        return parsed.work.author_id
    if not author or author.strip().lower() in {"", "unknown"}:
        return parsed.work.author_id
    return f"urn:langnet:ogl-author:{candidate.collection_id}:{_ogl_slug(author)}"


def _preferred_ogl_language(parsed: ParsedBook, candidate: OglSourceCandidate) -> str:
    if parsed.work.language and parsed.work.language != "und":
        return parsed.work.language
    declared = _tei_declared_languages(candidate.source_path)
    for language in ("grc", "lat", "san"):
        if language in declared:
            return language
    if candidate.collection_id == "opengreekandlatin_church_fathers" and "en" in declared:
        return "grc"
    return parsed.work.language or parsed.edition.language or "und"


def _tei_declared_languages(path: Path) -> set[str]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return set()
    namespace = {"tei": "http://www.tei-c.org/ns/1.0"}
    return {
        value
        for element in root.findall(".//tei:profileDesc/tei:langUsage/tei:language", namespace)
        if (value := element.attrib.get("ident"))
    }


def _is_weak_ogl_title(title: str, source_id: str) -> bool:
    normalized = " ".join(title.strip().lower().split())
    return normalized in {
        "",
        "unknown",
        "untitled",
        "text",
        source_id.lower(),
        "patrologiae cursus completus. series latina (pl)",
    }


def _inferred_ogl_author_from_title(title: str) -> str | None:
    normalized = " ".join(title.upper().split())
    if not normalized:
        return None

    explicit_patterns = (
        ("CYRILLI ", "Cyrillus Alexandrinus"),
        ("NESTORII BLASPHEMIARUM CAPITULA XII", "Cyrillus Alexandrinus"),
        ("THEODORI MOPSUESTENI", "Theodorus Mopsuestenus"),
        ("THEODORETUS MOPSUESTENUS", "Theodorus Mopsuestenus"),
        ("THEODORETUS CYRENSIS", "Theodoretus Cyrensis"),
        ("EUTHERIUS THYANENSIS", "Eutherius Tyanensis"),
        ("FLAVII JOSEPHI", "Flavius Josephus"),
        ("PHILONIS", "Philo Judaeus"),
        ("ORIGENIS", "Origenes"),
        ("ORIGENIAN", "Origenes"),
        ("HIERONYMUS", "Hieronymus"),
        ("HIERONYMI", "Hieronymus"),
        ("MORALIUM LIBRI", "Gregorius I Magnus"),
        ("EPISTOLA III. MAXIMI IMPERATORIS", "Magnus Maximus"),
        ("AMBROSII, ALIORUMQUE EPISCOPORUM", "Ambrosius et alii episcopi"),
        ("DAMASO I PAPAE", "Damasus I"),
        ("DAMASO PAPAE", "Damasus I"),
        ("ECCLESIASTICUS:", "Jesus ben Sira"),
    )
    for pattern, author in explicit_patterns:
        if pattern in normalized:
            return author

    if "CONCIL" in normalized or "SYNOD" in normalized:
        return "Concilium"
    if "KALENDARIUM" in normalized and "CARTHAGINENSIS" in normalized:
        return "Ecclesia Carthaginiensis"
    if "COLLECTIO " in normalized:
        return "Collectio canonum"
    if "INCERT" in normalized:
        return "Incertus"
    if "REMIGIUM" in normalized:
        return "Incertus"
    if "PLACIDI" in normalized or "SCHOLATICAM" in normalized:
        return "Incertus"
    if "ORDO MONASTICUS" in normalized:
        return "Incertus"
    if "PASSIO S. CYPRIANI" in normalized:
        return "Incertus"
    if "DE DECEM DEI NOMINIBUS" in normalized:
        return "Incertus"
    if "LIBER NOMINUM LOCORUM EX ACTIS" in normalized:
        return "Incertus"
    if "SUCCINCTA COMMEMORATIO" in normalized:
        return "Incertus"
    if "NATALES ALIQUOT SANCTORUM" in normalized:
        return "Incertus"
    if "LIBER DE NOMINIBUS HEBRAICIS" in normalized:
        return "Hieronymus"
    if "LIBER DE SITU ET NOMINIBUS LOCORUM HEBRAICORUM" in normalized:
        return "Hieronymus"
    if "LIBER HEBRAICARUM QUAESTIONUM" in normalized:
        return "Hieronymus"
    if "COMMENTARIUS IN ECCLESIASTEN" in normalized:
        return "Hieronymus"
    if "HEBRAIC" in normalized:
        return "Hieronymus"

    editorial_markers = (
        "ADMONITIO",
        "ADDENDA",
        "DOCUMENTA",
        "ELOGIA",
        "EPISTOLA NUNCUPATORIA",
        "MONITUM",
        "NOTITIA HISTORICA",
        "OBSERVATIO CRITICA",
        "OPUSCULA",
        "PROLEGOMENA",
        "SYNOPSIS",
        "TABULA",
        "TABULIS DONARIORUM",
    )
    if any(marker in normalized for marker in editorial_markers):
        return "Patrologia Latina editor"

    return None


def _cts_inventory_metadata(source_path: Path) -> dict[str, str | None]:
    return {
        "groupname": _cts_text(source_path.parent.parent / "__cts__.xml", ".//ti:groupname"),
        "title": _cts_text(source_path.parent / "__cts__.xml", ".//ti:title"),
        "edition_label": _cts_text(source_path.parent / "__cts__.xml", ".//ti:edition/ti:label"),
        "edition_description": _cts_text(
            source_path.parent / "__cts__.xml",
            ".//ti:edition/ti:description",
        ),
    }


def _cts_text(path: Path, xpath: str) -> str | None:
    if not path.exists():
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    element = root.find(xpath, {"ti": "http://chs.harvard.edu/xmlns/cts"})
    if element is None or element.text is None:
        return None
    value = " ".join(element.text.split())
    return value or None


def _source_view(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "external"
    if len(relative.parts) == 1:
        return "root"
    first = relative.parts[0]
    return _ALTERNATE_VIEW_PARTS.get(first, first)


def _source_priority(source_view: str) -> int:
    if source_view == "data":
        return 0
    if source_view == "root":
        return 1
    if source_view.startswith("alternate_view_"):
        return 10
    return 5


def _source_id(root: Path, path: Path) -> str:
    try:
        return "/".join(path.relative_to(root).with_suffix("").parts)
    except ValueError:
        return path.stem


def _candidate_sort_key(candidate: OglSourceCandidate) -> tuple[int, str, str]:
    return (
        candidate.source_priority,
        candidate.cts_edition_urn or candidate.synthetic_work_id or candidate.edition_key,
        str(candidate.source_path),
    )
