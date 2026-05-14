from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.databuild.cts import CtsBuildConfig, CtsUrnBuilder


def test_cts_auth_parser_preserves_tlg_pseudo_prefix_before_markup() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_path = Path(tmpdir) / "authtab.dir"
        auth_path.write_bytes(
            b"*TLG\x83g\xff"
            b"TLG0530 Pseudo-&1Galenus &Med.\xff"
            b"TLG2798 Pseudo-&1Dionysius Areopagita &Scr. Eccl. et Theol.\xff"
        )
        builder = CtsUrnBuilder(CtsBuildConfig())

        authors = builder._parse_auth_file(auth_path)

    assert authors["tlg0530"]["name"] == "Pseudo-Galenus"
    assert authors["tlg2798"]["name"] == "Pseudo-Dionysius Areopagita"


def test_cts_packard_parser_preserves_non_phi_latin_stem_prefix() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        idt_path = root / "civ0005.idt"
        idt_path.write_bytes(
            _packard_idt_entry(0, "English Bible (KJV or AV)") + _packard_idt_entry(1, "Genesis")
        )
        builder = CtsUrnBuilder(CtsBuildConfig())

        works = builder._parse_single_idt(idt_path, {}, is_greek=False)

    assert works[0].author_id == "civ0005"
    assert works[0].work_urn == "urn:cts:latinLit:civ0005.phi001"


def _packard_idt_entry(entry_type: int, value: str) -> bytes:
    encoded = value.encode("latin-1")
    return bytes([0x10, entry_type, len(encoded)]) + encoded
