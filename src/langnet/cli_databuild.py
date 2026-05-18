from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path

import click
from returns.result import Failure, Success


def _ensure_logging(level: int = logging.INFO) -> None:
    """
    Initialize a basic logging configuration if none is set.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def _print_build_result(result) -> None:
    status = result.status.value if hasattr(result, "status") else "unknown"
    click.echo(f"status: {status}")
    click.echo(f"output: {result.output_path}")
    if result.message:
        click.echo(f"message: {result.message}")
    if result.stats:
        if isinstance(result.stats, Success):
            stats_val = result.stats.unwrap()
            stats_dict = asdict(stats_val) if is_dataclass(stats_val) else {"value": stats_val}
            for key, value in sorted(stats_dict.items()):
                click.echo(f"{key}: {value}")
        else:
            err = result.stats.failure() if isinstance(result.stats, Failure) else result.stats
            err_dict = asdict(err) if is_dataclass(err) else {"error": str(err)}
            click.echo("error stats:")
            for key, value in sorted(err_dict.items()):
                click.echo(f"{key}: {value}")


@dataclass
class BuildCtsConfig:
    perseus_dir: str
    phi_cdrom_dir: str
    output: str | None
    include_packard: bool
    wipe: bool
    force: bool
    max_works: int | None


@dataclass
class BuildCdslConfig:
    dict_id: str
    source_dir: str
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildGaffiotConfig:
    source_path: str | None
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildDicoConfig:
    source_dir: str | None
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildBaillyConfig:
    source_path: str
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildLewis1890Config:
    source_path: str | None
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildDiogenesConfig:
    language: str
    mode: str
    endpoint: str
    source_path: str | None
    output: str | None
    seed_word: str | None
    max_entries: int | None
    batch_size: int
    request_timeout_s: float
    polite_delay_s: float
    wipe: bool
    force: bool


@dataclass
class BuildWhitakersConfig:
    source_path: str | None
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildReaderConfig:
    perseus_dir: str | None
    digiliblt_dir: str | None
    phi_latin_dir: str | None
    tlg_e_dir: str | None
    sanskrit_dir: str | None
    alias_dir: str | None
    metadata_overlay_dir: str | None
    metadata_attribution_dir: str | None
    contained_work_dir: str | None
    work_map_dir: str | None
    output_root: str | None
    limit: int | None
    wipe: bool
    force: bool
    progress_every: int | None
    source_paths: tuple[str, ...]


def _build_cts_impl(config: BuildCtsConfig) -> None:
    _ensure_logging()
    from langnet.databuild.cts import CtsBuildConfig, CtsUrnBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_cts_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_cts_path()
    cts_config = CtsBuildConfig(
        perseus_dir=Path(config.perseus_dir).expanduser(),
        phi_cdrom_dir=Path(config.phi_cdrom_dir).expanduser(),
        output_path=output_path,
        include_packard=config.include_packard,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
        max_works=config.max_works,
    )
    builder = CtsUrnBuilder(cts_config)
    result = builder.build()
    _print_build_result(result)


def _build_cdsl_impl(config: BuildCdslConfig) -> None:
    _ensure_logging()
    from langnet.databuild.cdsl import CdslBuildConfig, CdslBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_cdsl_path  # noqa: PLC0415

    output_path = (
        Path(config.output).expanduser() if config.output else default_cdsl_path(config.dict_id)
    )
    builder_config = CdslBuildConfig(
        dict_id=config.dict_id,
        source_dir=Path(config.source_dir).expanduser(),
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = CdslBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_gaffiot_impl(config: BuildGaffiotConfig) -> None:
    _ensure_logging()
    from langnet.databuild.gaffiot import GaffiotBuildConfig, GaffiotBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_gaffiot_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_gaffiot_path()
    builder_config = GaffiotBuildConfig(
        source_path=Path(config.source_path).expanduser() if config.source_path else None,
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = GaffiotBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_dico_impl(config: BuildDicoConfig) -> None:
    _ensure_logging()
    from langnet.databuild.dico import DicoBuildConfig, DicoBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_dico_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_dico_path()
    builder_config = DicoBuildConfig(
        source_dir=Path(config.source_dir).expanduser() if config.source_dir else None,
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = DicoBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_bailly_impl(config: BuildBaillyConfig) -> None:
    _ensure_logging()
    from langnet.databuild.bailly import BaillyBuildConfig, BaillyBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_bailly_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_bailly_path()
    builder_config = BaillyBuildConfig(
        source_path=Path(config.source_path).expanduser(),
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = BaillyBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_lewis_1890_impl(config: BuildLewis1890Config) -> None:
    _ensure_logging()
    from langnet.databuild.lewis_1890 import (  # noqa: PLC0415
        Lewis1890BuildConfig,
        Lewis1890Builder,
    )
    from langnet.databuild.paths import default_lewis_1890_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_lewis_1890_path()
    builder_config = Lewis1890BuildConfig(
        source_path=Path(config.source_path).expanduser() if config.source_path else None,
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = Lewis1890Builder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_diogenes_impl(config: BuildDiogenesConfig) -> None:
    _ensure_logging()
    from langnet.databuild.diogenes import (  # noqa: PLC0415
        DiogenesBuildConfig,
        DiogenesBuilder,
    )
    from langnet.databuild.paths import default_diogenes_path  # noqa: PLC0415

    language = "grc" if config.language.lower() in {"grc", "grk", "greek"} else "lat"
    output_path = (
        Path(config.output).expanduser() if config.output else default_diogenes_path(language)
    )
    builder_config = DiogenesBuildConfig(
        language=language,  # type: ignore[arg-type]
        mode=config.mode,  # type: ignore[arg-type]
        endpoint=config.endpoint,
        source_path=Path(config.source_path).expanduser() if config.source_path else None,
        output_path=output_path,
        seed_word=config.seed_word,
        max_entries=config.max_entries,
        batch_size=config.batch_size,
        request_timeout_s=config.request_timeout_s,
        polite_delay_s=config.polite_delay_s,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = DiogenesBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_whitakers_impl(config: BuildWhitakersConfig) -> None:
    _ensure_logging()
    from langnet.databuild.paths import default_whitakers_path  # noqa: PLC0415
    from langnet.databuild.whitakers import (  # noqa: PLC0415
        WhitakersBuildConfig,
        WhitakersBuilder,
    )

    output_path = Path(config.output).expanduser() if config.output else default_whitakers_path()
    builder_config = WhitakersBuildConfig(
        source_path=Path(config.source_path).expanduser() if config.source_path else None,
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = WhitakersBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_reader_impl(config: BuildReaderConfig) -> None:
    _ensure_logging()
    from langnet.reader.builder import (  # noqa: PLC0415
        ReaderBuildConfig,
        ReaderBuilder,
        ReaderBuildProgress,
    )

    def progress_callback(progress: ReaderBuildProgress) -> None:
        click.echo(
            "progress: "
            f"parsed_sources={progress.parsed_sources} "
            f"artifact_count={progress.artifact_count} "
            f"segment_count={progress.segment_count} "
            f"latest_source={progress.latest_source}"
        )

    builder_config = ReaderBuildConfig(
        perseus_dir=Path(config.perseus_dir).expanduser() if config.perseus_dir else None,
        digiliblt_dir=Path(config.digiliblt_dir).expanduser() if config.digiliblt_dir else None,
        phi_latin_dir=Path(config.phi_latin_dir).expanduser() if config.phi_latin_dir else None,
        tlg_e_dir=Path(config.tlg_e_dir).expanduser() if config.tlg_e_dir else None,
        sanskrit_dir=Path(config.sanskrit_dir).expanduser() if config.sanskrit_dir else None,
        alias_dir=Path(config.alias_dir).expanduser() if config.alias_dir else None,
        metadata_overlay_dir=(
            Path(config.metadata_overlay_dir).expanduser() if config.metadata_overlay_dir else None
        ),
        metadata_attribution_dir=(
            Path(config.metadata_attribution_dir).expanduser()
            if config.metadata_attribution_dir
            else None
        ),
        contained_work_dir=(
            Path(config.contained_work_dir).expanduser() if config.contained_work_dir else None
        ),
        work_map_dir=Path(config.work_map_dir).expanduser() if config.work_map_dir else None,
        output_root=Path(config.output_root).expanduser() if config.output_root else None,
        limit=config.limit,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
        progress_every=config.progress_every,
        progress_callback=progress_callback if config.progress_every else None,
        source_paths=tuple(Path(path).expanduser() for path in config.source_paths),
    )
    result = ReaderBuilder(builder_config).build()
    _print_build_result(result)


@click.group()
def databuild():
    """Offline data/index builders."""


@databuild.command("cts")
@click.option(
    "--perseus-dir",
    type=click.Path(),
    default=str(Path.home() / "perseus"),
    show_default=True,
    help="Perseus corpus root (expects canonical-latinLit and canonical-greekLit).",
)
@click.option(
    "--phi-cdrom-dir",
    type=click.Path(),
    default=str(Path.home() / "Classics-Data"),
    show_default=True,
    help="Packard PHI/TLG corpus root (authtab/idt).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/cts_urn.duckdb)",
)
@click.option(
    "--include-packard/--no-packard",
    default=True,
    show_default=True,
    help="Include Packard PHI/TLG authtab/idt data when available.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
@click.option("--max-works", type=int, help="Limit number of works ingested (sampling/debug).")
def build_cts(  # noqa: PLR0913
    perseus_dir: str,
    phi_cdrom_dir: str,
    output: str | None,
    include_packard: bool,
    wipe: bool,
    force: bool,
    max_works: int | None,
):
    """Build CTS URN index (Perseus + Packard/legacy)."""
    config = BuildCtsConfig(
        perseus_dir=perseus_dir,
        phi_cdrom_dir=phi_cdrom_dir,
        output=output,
        include_packard=include_packard,
        wipe=wipe,
        force=force,
        max_works=max_works,
    )
    _build_cts_impl(config)


@databuild.command("cdsl")
@click.argument("dict_id")
@click.option(
    "--source-dir",
    type=click.Path(),
    default=str(Path.home() / "cdsl_data" / "dict"),
    show_default=True,
    help=(
        "CDSL dictionary root containing subdirectories per dictionary (with web/sqlite/*.sqlite)."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/cdsl_<dict>.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_cdsl(  # noqa: PLR0913
    dict_id: str,
    source_dir: str,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build CDSL dictionary index for a specific dictionary id (e.g., MW, AP90)."""
    config = BuildCdslConfig(
        dict_id=dict_id,
        source_dir=source_dir,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_cdsl_impl(config)


@databuild.command("gaffiot")
@click.option(
    "--source",
    "source_path",
    type=click.Path(),
    default=None,
    help="Path to gaffiot-unicode.xml (defaults to ~/digital-gaffiot-json/gaffiot-unicode.xml).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_gaffiot.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=500,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_gaffiot(  # noqa: PLR0913
    source_path: str | None,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build Gaffiot French→Latin index."""
    config = BuildGaffiotConfig(
        source_path=source_path,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_gaffiot_impl(config)


@databuild.command("dico")
@click.option(
    "--source-dir",
    type=click.Path(),
    default=None,
    help=(
        "Path to DICO HTML directory "
        "(defaults to ~/langnet-tools/sanskrit-heritage/webroot/htdocs/DICO/)."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_dico.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=500,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_dico(  # noqa: PLR0913
    source_dir: str | None,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build DICO French→Sanskrit index."""
    config = BuildDicoConfig(
        source_dir=source_dir,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_dico_impl(config)


@databuild.command("bailly")
@click.option(
    "--source",
    "source_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to PDF-derived Bailly structural JSONL.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_bailly.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=500,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_bailly(  # noqa: PLR0913
    source_path: str,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build Bailly Greek→French index from PDF-derived structural JSONL."""
    config = BuildBaillyConfig(
        source_path=source_path,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_bailly_impl(config)


@databuild.command("lewis-1890")
@click.option(
    "--source",
    "source_path",
    type=click.Path(),
    default=None,
    help=(
        "Path to CLTK lewis.yaml "
        "(defaults to ~/cltk_data/lat/lexicon/cltk_lat_lewis_elementary_lexicon/lewis.yaml)."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_lewis_1890.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=500,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_lewis_1890(  # noqa: PLR0913
    source_path: str | None,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build Lewis 1890 Latin→English index from CLTK source."""
    config = BuildLewis1890Config(
        source_path=source_path,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_lewis_1890_impl(config)


@databuild.command("diogenes-index")
@click.argument("language", type=click.Choice(["lat", "grc", "grk", "latin", "greek"]))
@click.option(
    "--endpoint",
    default="http://localhost:8888/Perseus.cgi",
    show_default=True,
    help="Diogenes Perseus.cgi endpoint.",
)
@click.option(
    "--mode",
    type=click.Choice(["auto", "direct", "crawl"]),
    default="auto",
    show_default=True,
    help="Build from local XML source when available, or crawl Diogenes CGI links.",
)
@click.option(
    "--source",
    "source_path",
    type=click.Path(),
    default=None,
    help="Path to Diogenes XML dictionary source; auto-detected when omitted.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_diogenes_<lang>.duckdb)",
)
@click.option(
    "--seed-word",
    default=None,
    help="Seed dictionary lookup; defaults to 'amo' for Latin and 'apo' for Greek.",
)
@click.option(
    "--max-entries",
    type=int,
    default=1000,
    show_default=True,
    help="Maximum entries to crawl; pass 0 for no explicit crawl limit.",
)
@click.option(
    "--batch-size",
    type=int,
    default=5000,
    show_default=True,
    help="Rows per insert batch.",
)
@click.option(
    "--request-timeout",
    "request_timeout_s",
    type=float,
    default=10.0,
    show_default=True,
    help="HTTP timeout per Diogenes request, in seconds.",
)
@click.option(
    "--polite-delay",
    "polite_delay_s",
    type=float,
    default=0.0,
    show_default=True,
    help="Sleep between crawled entries, in seconds.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_diogenes_index(  # noqa: PLR0913
    language: str,
    endpoint: str,
    mode: str,
    source_path: str | None,
    output: str | None,
    seed_word: str | None,
    max_entries: int | None,
    batch_size: int,
    request_timeout_s: float,
    polite_delay_s: float,
    wipe: bool,
    force: bool,
):
    """Build a Diogenes word index by crawling previous/next dictionary links."""
    config = BuildDiogenesConfig(
        language=language,
        mode=mode,
        endpoint=endpoint,
        source_path=source_path,
        output=output,
        seed_word=seed_word,
        max_entries=None if max_entries == 0 else max_entries,
        batch_size=batch_size,
        request_timeout_s=request_timeout_s,
        polite_delay_s=polite_delay_s,
        wipe=wipe,
        force=force,
    )
    _build_diogenes_impl(config)


@databuild.command("whitakers-index")
@click.option(
    "--source",
    "source_path",
    type=click.Path(),
    default=None,
    help="Path to Whitaker's DICTLINE.GEN (defaults to ../whitakers-words/DICTLINE.GEN).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_whitakers.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=5000,
    show_default=True,
    help="Rows per insert batch.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_whitakers_index(  # noqa: PLR0913
    source_path: str | None,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build a Whitaker's Words Latin dictionary index."""
    config = BuildWhitakersConfig(
        source_path=source_path,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_whitakers_impl(config)


@databuild.command("reader")
@click.option(
    "--perseus-dir",
    type=click.Path(),
    default=None,
    help="Perseus corpus root or fixture directory.",
)
@click.option(
    "--digiliblt-dir",
    type=click.Path(),
    default=None,
    help="digilibLT TEI corpus root.",
)
@click.option(
    "--phi-latin-dir",
    type=click.Path(),
    default=None,
    help="PHI Latin text dump directory.",
)
@click.option(
    "--tlg-e-dir",
    type=click.Path(),
    default=None,
    help="TLG Greek text dump directory.",
)
@click.option(
    "--sanskrit-dir",
    type=click.Path(),
    default=None,
    help="Sanskrit JSON/plain text corpus root.",
)
@click.option(
    "--alias-dir",
    type=click.Path(),
    default="data/curated/reader_aliases",
    show_default=True,
    help="Composed reader alias directory.",
)
@click.option(
    "--metadata-overlay-dir",
    type=click.Path(),
    default="data/curated/reader_metadata",
    show_default=True,
    help="Curated reader metadata overlay directory.",
)
@click.option(
    "--metadata-attribution-dir",
    type=click.Path(),
    default="data/curated/reader_attributions",
    show_default=True,
    help="Curated reader metadata attribution directory.",
)
@click.option(
    "--contained-work-dir",
    type=click.Path(),
    default="data/curated/reader_contained_works",
    show_default=True,
    help="Curated contained/virtual reader work directory.",
)
@click.option(
    "--work-map-dir",
    type=click.Path(),
    default="data/curated/reader_work_maps",
    show_default=True,
    help="Curated reader work-map/table-of-contents directory.",
)
@click.option(
    "--output-root",
    type=click.Path(),
    help="Output reader root (defaults to data/build/reader).",
)
@click.option("--limit", type=int, help="Limit number of parsed books for testing.")
@click.option(
    "--source-path",
    "source_paths",
    type=click.Path(exists=True),
    multiple=True,
    help="Rebuild only the selected source file(s); use with --no-wipe for source-slice repair.",
)
@click.option(
    "--progress-every",
    type=int,
    default=None,
    help="Print reader build progress every N parsed books.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_reader(  # noqa: PLR0913
    perseus_dir: str | None,
    digiliblt_dir: str | None,
    phi_latin_dir: str | None,
    tlg_e_dir: str | None,
    sanskrit_dir: str | None,
    alias_dir: str | None,
    metadata_overlay_dir: str | None,
    metadata_attribution_dir: str | None,
    contained_work_dir: str | None,
    work_map_dir: str | None,
    output_root: str | None,
    limit: int | None,
    source_paths: tuple[str, ...],
    progress_every: int | None,
    wipe: bool,
    force: bool,
) -> None:
    """Build the reader corpus catalog."""
    _build_reader_impl(
        BuildReaderConfig(
            perseus_dir=perseus_dir,
            digiliblt_dir=digiliblt_dir,
            phi_latin_dir=phi_latin_dir,
            tlg_e_dir=tlg_e_dir,
            sanskrit_dir=sanskrit_dir,
            alias_dir=alias_dir,
            metadata_overlay_dir=metadata_overlay_dir,
            metadata_attribution_dir=metadata_attribution_dir,
            contained_work_dir=contained_work_dir,
            work_map_dir=work_map_dir,
            output_root=output_root,
            limit=limit,
            source_paths=source_paths,
            progress_every=progress_every,
            wipe=wipe,
            force=force,
        )
    )
