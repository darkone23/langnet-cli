from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb

from langnet.citation import CtsCitationResolver, perseus_ref_to_cts_urn


def _write_cts_fixture(path: Path) -> None:
    conn = duckdb.connect(str(path))
    try:
        conn.execute(
            "CREATE TABLE author_index (author_id TEXT PRIMARY KEY, author_name TEXT NOT NULL, "
            "language TEXT, namespace TEXT, author_urn TEXT)"
        )
        conn.execute(
            "CREATE TABLE works (work_urn TEXT PRIMARY KEY, canon_id TEXT, author_id TEXT, "
            "work_title TEXT, work_reference TEXT, cts_urn TEXT, language TEXT, namespace TEXT, "
            "source_path TEXT)"
        )
        conn.execute(
            "INSERT INTO author_index VALUES "
            "('phi0690', 'Vergilius Maro, Publius', 'lat', 'latinLit', "
            "'urn:cts:latinLit:phi0690'), "
            "('tlg0012', 'Homer', 'grc', 'greekLit', 'urn:cts:greekLit:tlg0012')"
        )
        conn.execute(
            "INSERT INTO works VALUES "
            "('urn:cts:latinLit:phi0690.phi001', 'phi0690.phi001', 'phi0690', "
            "'Eclogues', 'phi0690.phi001', 'urn:cts:latinLit:phi0690.phi001', "
            "'lat', 'latinLit', 'fixture'), "
            "('urn:cts:latinLit:phi0690.phi003', 'phi0690.phi003', 'phi0690', "
            "'Aeneid', 'phi0690.phi003', 'urn:cts:latinLit:phi0690.phi003', "
            "'lat', 'latinLit', 'fixture'), "
            "('urn:cts:greekLit:tlg0012.tlg001', 'tlg0012.tlg001', 'tlg0012', "
            "'Iliad', 'tlg0012.tlg001', 'urn:cts:greekLit:tlg0012.tlg001', "
            "'grc', 'greekLit', 'fixture')"
        )
    finally:
        conn.close()


def test_perseus_ref_to_cts_urn_normalizes_locations() -> None:
    assert (
        perseus_ref_to_cts_urn("perseus:abo:phi,0690,001:2:63")
        == "urn:cts:latinLit:phi0690.phi001:2.63"
    )
    assert (
        perseus_ref_to_cts_urn("perseus:abo:tlg,0012,001:1:1")
        == "urn:cts:greekLit:tlg0012.tlg001:1.1"
    )


def test_cts_resolver_hydrates_known_urns_from_duckdb() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "cts.duckdb"
        _write_cts_fixture(db_path)

        resolver = CtsCitationResolver(db_path)
        result = resolver.resolve(
            "perseus:abo:phi,0690,001:2:63",
            citation_text="Verg. E. 2, 63",
            language="lat",
        )

        assert result.resolved is True
        assert result.cts_urn == "urn:cts:latinLit:phi0690.phi001:2.63"
        assert result.author == "Vergilius Maro, Publius"
        assert result.work == "Eclogues"


def test_cts_resolver_preserves_unresolved_refs_and_sanskrit_abbreviations() -> None:
    resolver = CtsCitationResolver(db_path=Path("/definitely/missing/cts.duckdb"))

    unresolved = resolver.resolve("Cic. Or. 48, 160", language="lat")
    assert unresolved.resolved is False
    assert unresolved.citation_ref == "Cic. Or. 48, 160"
    assert unresolved.citation_text == "Cic. Or. 48, 160"

    abbreviation = resolver.resolve("MW", citation_text="MW", language="san")
    assert abbreviation.resolved is False
    assert abbreviation.metadata["display"] == "MW"
    assert abbreviation.metadata["language"] == "san"
