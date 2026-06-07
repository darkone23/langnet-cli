from __future__ import annotations

import json
from pathlib import Path

from langnet.reader.source_acquisition import PlWikisourceStageConfig, stage_pl_wikisource


def test_stage_pl_wikisource_preserves_column_markers_and_segments(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    staging = tmp_path / "staging"
    raw_dir.mkdir()
    staging.mkdir()
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                "source_id: patrologia_latina:pl122",
                "raw_storage: " + str(raw_dir),
                "staging_storage: " + str(staging),
            ]
        ),
        encoding="utf-8",
    )
    works = staging / "works.tsv"
    works.write_text(
        "\t".join(
            [
                "source_id",
                "title",
                "author",
                "language",
                "series",
                "volume_id",
                "columns",
                "work_url",
                "status",
                "boundary_confidence",
                "quality_status",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "latin_wikisource_pl122",
                "De praedestinatione",
                "Joannes Scotus Eriugena",
                "lat",
                "Patrologia Latina",
                "PL122",
                "0347-0440A",
                "https://la.wikisource.org/wiki/De_praedestinatione_(Joannes_Scotus_Erigena)",
                "staged_sample",
                "high",
                "machine_text_needs_segmentation",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (raw_dir / "de-praedestinatione.md").write_text(
        """# De praedestinatione (Joannes Scotus Erigena)

EPUB PDF TXT

Iohannes Scotus EriugenaDe praedestinatione0saeculo IX

De praedestinatione

JOANNIS SCOTI DE DIVINA PRAEDESTINATIONE LIBER.
PRAEFATIO.
122.0355A| MONITUM AD LECTOREM. Joannes Scotus periculosiorem vix poterat provinciam suscipere.

CAPITULUM I.
122.0376D| Omnis divina praedestinatio una est.
""",
        encoding="utf-8",
    )

    payload = stage_pl_wikisource(PlWikisourceStageConfig(manifest_path=manifest))

    assert payload["mode"] == "stage-pl-wikisource"
    assert payload["work_count"] == 1
    assert payload["segment_count"] >= 2
    output_path = Path(payload["items"][0]["segments_path"])
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["volume_id"] == "PL122"
    assert any("122.0355A" in row["column_markers"] for row in rows)
    assert not any("MONITUM AD LECTOREM" in row["text"] for row in rows)
    assert not any("De praedestinatione" in row["text"] for row in rows)
    assert any(row["citation_path"] == "122.0376D" for row in rows)
    assert all("EPUB" not in row["text"] for row in rows)


def test_stage_pl_wikisource_skips_toc_and_preface_markers(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    staging = tmp_path / "staging"
    raw_dir.mkdir()
    staging.mkdir()
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                "source_id: patrologia_latina:pl122",
                "raw_storage: " + str(raw_dir),
                "staging_storage: " + str(staging),
            ]
        ),
        encoding="utf-8",
    )
    works = staging / "works.tsv"
    works.write_text(
        "\t".join(
            [
                "source_id",
                "title",
                "author",
                "language",
                "series",
                "volume_id",
                "columns",
                "work_url",
                "status",
                "boundary_confidence",
                "quality_status",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "latin_wikisource_pl122",
                "De divisione naturae",
                "Joannes Scotus Eriugena",
                "lat",
                "Patrologia Latina",
                "PL122",
                "0441-1022D",
                "https://la.wikisource.org/wiki/De_divisione_naturae_(Joannes_Scotus_Eriugena)",
                "staged_sample",
                "high",
                "machine_text_needs_segmentation",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (raw_dir / "de-divisione-naturae.md").write_text(
        """# De divisione naturae

- MONITUM AD LECTOREM. Joannes Scotus Eriugena
122.1022B De divisione naturae
Editio princeps A
Cod. ms. Parisiensis S. Germani in editione principe adhibitus B
ΠΕΡΙ ΦΥΣΕΩΣ ΜΕΡΙΣΜΟΥ ID EST DE DIVISIONE NATURAE. LIBER PRIMUS
122.0441A| MAGISTER. Saepe mihi cogitanti, diligentiusque quantum vires suppetunt inquirenti...
""",
        encoding="utf-8",
    )

    payload = stage_pl_wikisource(PlWikisourceStageConfig(manifest_path=manifest))
    output_path = Path(payload["items"][0]["segments_path"])
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    texts = [row["text"] for row in rows]
    assert not any("MONITUM AD LECTOREM" in text for text in texts)
    assert not any("122.1022B De divisione naturae" in text for text in texts)
    assert not any("Editio princeps A" in text for text in texts)
    assert any("MAGISTER." in text for text in texts)


def test_stage_pl_wikisource_stops_before_wikisource_footer(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    staging = tmp_path / "staging"
    raw_dir.mkdir()
    staging.mkdir()
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                "source_id: patrologia_latina:pl122",
                "raw_storage: " + str(raw_dir),
                "staging_storage: " + str(staging),
            ]
        ),
        encoding="utf-8",
    )
    works = staging / "works.tsv"
    works.write_text(
        "\t".join(
            [
                "source_id",
                "title",
                "author",
                "language",
                "series",
                "volume_id",
                "columns",
                "work_url",
                "status",
                "boundary_confidence",
                "quality_status",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "latin_wikisource_pl122",
                "Versus",
                "Joannes Scotus Eriugena",
                "lat",
                "Patrologia Latina",
                "PL122",
                "1221C-1240C",
                "https://la.wikisource.org/wiki/Versus_(Joannes_Scotus_Erigena)",
                "staged_sample",
                "medium",
                "metadata_only",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (raw_dir / "versus.md").write_text(
        """# Versus (Joannes Scotus Erigena)

Hellenas Troasque suos cantarat Homerus,

122.1221D| Ipsis usus erat plaudere per populos.

Receptum de "https://la.wikisource.org/w/index.php?title=Versus_(Joannes_Scotus_Erigena)&oldid=257785"

Categoriae:

- Opera omnia - Opera quae Iohannes Scotus Eriugena scripsit
- Novissima mutatio die 25 Februarii 2026 hora 18:24 facta.
Quaerere
Something went wrong
""",
        encoding="utf-8",
    )

    payload = stage_pl_wikisource(PlWikisourceStageConfig(manifest_path=manifest))
    output_path = Path(payload["items"][0]["segments_path"])
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    texts = [row["text"] for row in rows]
    assert any("Hellenas Troasque" in text for text in texts)
    assert any("122.1221D" in row["column_markers"] for row in rows)
    assert not any("Receptum de" in text for text in texts)
    assert not any("Categoriae" in text for text in texts)
    assert not any("Novissima mutatio" in text for text in texts)
    assert not any("Something went wrong" in text for text in texts)
