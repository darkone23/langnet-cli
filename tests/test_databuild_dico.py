from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.dico import DicoBuildConfig, DicoBuilder


def _make_dico_html(path: Path) -> None:
    html = """
    <html><body>
    <div class="latin12">
    <span class="deva" lang="sa">&#x0906;&#x092E;&#x094D;</span>
    <a class="navy" name="aam#1"><i><span class="latin12">&#257;m_1</span></i></a>
    interj. ah!
    <p></p>
    <span class="deva" lang="sa">&#x0906;&#x092E;</span>
    <a class="navy" name="aama"><i><span class="latin12">&#257;ma</span></i></a>
    adj. cru.
    </div>
    </body></html>
    """
    path.write_text(html, encoding="utf-8")


def test_dico_builder_minimal_html() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source_dir = base / "DICO"
        source_dir.mkdir(parents=True, exist_ok=True)
        html_path = source_dir / "10.html"
        _make_dico_html(html_path)

        out_path = base / "lex_dico.duckdb"
        config = DicoBuildConfig(
            source_dir=source_dir,
            output_path=out_path,
            limit=None,
            batch_size=10,
            wipe_existing=True,
        )
        builder = DicoBuilder(config)
        result = builder.build()
        assert result.status == BuildStatus.SUCCESS, result.message
        assert out_path.exists()

        conn = duckdb.connect(str(out_path))
        try:
            entry_count = conn.execute("SELECT COUNT(*) FROM entries_fr").fetchone()[0]
            assert entry_count == 2
            entry = conn.execute(
                "SELECT entry_id, headword_deva, headword_roma, variant_num, plain_text "
                "FROM entries_fr WHERE entry_id='aam#1'"
            ).fetchone()
            assert entry is not None
            assert entry[0] == "aam#1"
            assert "आम्" in entry[1]
            assert entry[2].lower().startswith("ā")
            assert entry[3] == 1
            assert entry[4] and "interj" in entry[4].lower()

            en_count = conn.execute("SELECT COUNT(*) FROM entries_en").fetchone()[0]
            assert en_count == 0
        finally:
            conn.close()
