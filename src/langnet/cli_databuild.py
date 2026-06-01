from __future__ import annotations

import logging
import multiprocessing
import queue as queue_module
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

import click
import orjson
from returns.result import Failure, Success

from langnet.word_of_day import WordCandidate


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
class BuildFosterOssaConfig:
    source_path: str
    output: str | None
    limit: int | None
    wipe: bool
    force: bool


@dataclass
class BuildReaderConfig:
    perseus_dir: str | None
    first1k_greek_dir: str | None
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


def _build_foster_ossa_impl(config: BuildFosterOssaConfig) -> None:
    _ensure_logging()
    from langnet.databuild.foster_ossa import (  # noqa: PLC0415
        FosterOssaBuildConfig,
        FosterOssaBuilder,
    )
    from langnet.databuild.paths import default_foster_ossa_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_foster_ossa_path()
    builder_config = FosterOssaBuildConfig(
        source_path=Path(config.source_path).expanduser(),
        output_path=output_path,
        limit=config.limit,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    result = FosterOssaBuilder(builder_config).build()
    _print_build_result(result)
    if result.status.value == "failed":
        raise click.ClickException(result.message or "Foster Ossa build failed")


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
        first1k_greek_dir=(
            Path(config.first1k_greek_dir).expanduser() if config.first1k_greek_dir else None
        ),
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


@databuild.command("foster-ossa")
@click.option(
    "--source",
    "source_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to PDF-derived Foster Ossa page JSONL.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/foster_ossa.duckdb)",
)
@click.option("--limit", type=click.IntRange(min=0), help="Limit pages for testing.")
@click.option(
    "--wipe/--no-wipe",
    default=True,
    show_default=True,
    help="Delete existing DB before building.",
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_foster_ossa(
    source_path: str,
    output: str | None,
    limit: int | None,
    wipe: bool,
    force: bool,
) -> None:
    """Build local Foster Ossa extraction index from page JSONL."""
    config = BuildFosterOssaConfig(
        source_path=source_path,
        output=output,
        limit=limit,
        wipe=wipe,
        force=force,
    )
    _build_foster_ossa_impl(config)


@databuild.command("motd-pool")
@click.option(
    "--profile",
    "build_profile",
    type=click.Choice(["prod", "smoke"]),
    default="prod",
    show_default=True,
    help=(
        "Build profile. prod uses OpenRouter/LLM candidate synthesis by default; "
        "smoke uses the deterministic curated inventory for quick local checks."
    ),
)
@click.option(
    "--candidate-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "LLM-curated candidate JSON with items[]. Each item should include language, query, "
        "difficulty, didactic_score, and didactic_rationale."
    ),
)
@click.option(
    "--candidate-source",
    type=click.Choice(["auto", "candidate-json", "curated", "llm"]),
    default=None,
    help=(
        "Override candidate source. Defaults from --profile: prod => llm, smoke => curated. "
        "auto uses LLM synthesis when available and falls back to curated inventories; "
        "candidate-json uses a reviewed LLM-curated JSON file."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output DuckDB path (defaults to data/build/motd_pool.duckdb).",
)
@click.option(
    "--per-language",
    default=None,
    type=click.IntRange(1),
    help=(
        "Cards to validate and store per language. Defaults from --profile: prod => 30, smoke => 3."
    ),
)
@click.option(
    "--level",
    type=click.Choice(["beginner", "intermediate", "deep"]),
    default="beginner",
    show_default=True,
)
@click.option("--dictionary", default="motd-fast", show_default=True)
@click.option("--timeout-ms", default=1200000, type=click.IntRange(1), show_default=True)
@click.option(
    "--probe-timeout-ms",
    default=12000,
    type=click.IntRange(1000),
    show_default=True,
    help="Maximum time for one dictionary validation probe before rejecting that candidate.",
)
@click.option(
    "--recommendation-model",
    default="openai:google/gemini-2.5-flash",
    show_default=True,
    help="Model id used when --candidate-source llm is selected.",
)
@click.option("--nonce", default=None, help="Optional entropy for LLM candidate synthesis.")
@click.option(
    "--wipe/--no-wipe",
    default=True,
    show_default=True,
    help="Delete existing rows before inserting generated cards.",
)
@click.option(
    "--output-json/--text",
    "json_output",
    default=False,
    show_default=True,
    help="Emit machine-readable build summary.",
)
def build_motd_pool(  # noqa: C901, PLR0912, PLR0913, PLR0915
    build_profile: str,
    candidate_json: Path | None,
    candidate_source: str | None,
    output: Path | None,
    per_language: int | None,
    level: str,
    dictionary: str,
    timeout_ms: int,
    probe_timeout_ms: int,
    recommendation_model: str,
    nonce: str | None,
    wipe: bool,
    json_output: bool,
) -> None:
    """Build the precomputed word-of-day pool from curated, LLM, or JSON candidates."""
    from langnet.cli import (  # noqa: PLC0415
        _encounter_bucket_gloss,
        _encounter_bucket_learner_gloss,
        _word_of_day_candidate_pools,
    )
    from langnet.motd_pool import (  # noqa: PLC0415
        MotdCandidateMetadata,
        MotdCandidateSet,
        build_motd_pool,
        cards_from_word_of_day_payload,
        default_motd_pool_path,
        load_motd_candidate_json,
        validate_motd_pool,
    )
    from langnet.word_of_day import (  # noqa: PLC0415
        SUPPORTED_LANGUAGES,
        WordOfDayOptions,
        generate_word_of_day_payload,
    )

    started = time.monotonic()
    languages = list(SUPPORTED_LANGUAGES)
    resolved_candidate_source = candidate_source or _motd_pool_profile_candidate_source(
        build_profile
    )
    resolved_per_language = per_language or _motd_pool_profile_per_language(build_profile)
    candidate_request_count = _motd_pool_candidate_request_count(
        build_profile=build_profile,
        candidate_source=resolved_candidate_source,
        per_language=resolved_per_language,
    )
    output_path = output or default_motd_pool_path()
    candidate_set: MotdCandidateSet | None = None
    warnings: list[object] = []
    _motd_pool_log(
        json_output=json_output,
        message=(
            "MOTD pool build starting: "
            f"profile={build_profile}, candidate_source={resolved_candidate_source}, "
            f"per_language={resolved_per_language}, "
            f"candidate_request_count={candidate_request_count}, "
            f"level={level}, dictionary={dictionary}, probe_timeout_ms={probe_timeout_ms}, "
            f"output={output_path}"
        ),
    )
    if resolved_candidate_source == "candidate-json":
        if candidate_json is None:
            raise click.UsageError(
                "--candidate-json is required for --candidate-source candidate-json."
            )
        _motd_pool_log(json_output=json_output, message=f"Loading candidate JSON: {candidate_json}")
        candidate_set = load_motd_candidate_json(candidate_json)
        candidate_pools = candidate_set.pools
        candidate_metadata = candidate_set.metadata
        source_ref = str(candidate_json)
        _motd_pool_log(
            json_output=json_output,
            message=(
                "Loaded candidate JSON pools: "
                + ", ".join(
                    f"{language}={len(items)}" for language, items in candidate_pools.items()
                )
            ),
        )
    elif resolved_candidate_source in {"auto", "llm"}:
        synthesis_warnings: list[dict[str, str]] = []
        pools: dict[str, list[WordCandidate]] = {}
        seen_candidates: set[str] = set()
        batch_count = _motd_pool_candidate_batch_count(
            build_profile=build_profile,
            candidate_source=resolved_candidate_source,
            per_language=resolved_per_language,
        )
        max_batches = _motd_pool_candidate_max_batches(
            build_profile=build_profile,
            candidate_source=resolved_candidate_source,
            per_language=resolved_per_language,
        )
        for batch_index in range(max_batches):
            if _motd_pool_pools_are_full(
                pools,
                languages=languages,
                target_per_language=candidate_request_count,
            ):
                break
            batch_nonce = _motd_pool_batch_nonce(nonce, batch_index)
            _motd_pool_log(
                json_output=json_output,
                message=(
                    "Requesting OpenRouter candidate synthesis batch "
                    f"{batch_index + 1}/{max_batches}: model={recommendation_model}, "
                    f"source={resolved_candidate_source}, request_count={batch_count}"
                ),
            )
            try:
                batch_pools = _word_of_day_candidate_pools(
                    languages=languages,
                    count=batch_count,
                    level=level,
                    avoid_terms=sorted(seen_candidates),
                    nonce=batch_nonce,
                    rotation_key=f"motd-pool-build:{batch_index}",
                    candidate_source=resolved_candidate_source,
                    recommendation_model=recommendation_model,
                    started=started,
                    timeout_ms=timeout_ms,
                    warnings=synthesis_warnings,
                )
            except Exception as exc:
                warning = {
                    "language": "",
                    "query": "",
                    "message": (
                        f"LLM candidate synthesis batch {batch_index + 1} failed; "
                        f"continuing with prior batches. {type(exc).__name__}: {exc}"
                    ),
                }
                synthesis_warnings.append(warning)
                _motd_pool_log(json_output=json_output, message=warning["message"])
                continue
            if not batch_pools:
                break
            added = _motd_pool_merge_candidate_pools(
                pools,
                batch_pools,
                seen_candidates=seen_candidates,
            )
            _motd_pool_log(
                json_output=json_output,
                message=(
                    f"Synthesized batch {batch_index + 1}: added={added}, "
                    + ", ".join(
                        f"{language}={len(pools.get(language, []))}" for language in languages
                    )
                ),
            )
        warnings.extend(synthesis_warnings)
        candidate_pools = pools or None
        if not candidate_pools and resolved_candidate_source == "llm":
            raise click.ClickException("LLM candidate synthesis returned no usable candidates.")
        metadata_pools = pools or {}
        if pools:
            _motd_pool_log(
                json_output=json_output,
                message=(
                    "Synthesized candidate pools: "
                    + ", ".join(f"{language}={len(items)}" for language, items in pools.items())
                ),
            )
        else:
            _motd_pool_log(
                json_output=json_output,
                message="No LLM candidate pools returned; generator will use curated fallback.",
            )
        candidate_metadata = {
            f"{candidate.language}:{candidate.query}".lower(): MotdCandidateMetadata(
                language=candidate.language,
                query=candidate.query,
                didactic_score=candidate.didactic_score,
                didactic_rationale=candidate.didactic_rationale,
                source_ref=f"llm:{recommendation_model}",
            )
            for language_candidates in metadata_pools.values()
            for candidate in language_candidates
        }
        source_ref = f"llm:{recommendation_model}"
    else:
        _motd_pool_log(
            json_output=json_output,
            message="Using deterministic curated candidate inventory.",
        )
        candidate_pools = None
        candidate_metadata = {}
        source_ref = "curated"

    cards = []
    for language in languages:
        remaining_timeout = max(1, timeout_ms - int((time.monotonic() - started) * 1000))
        _motd_pool_log(
            json_output=json_output,
            message=(
                f"Validating {language} cards: target={resolved_per_language}, "
                f"remaining_timeout_ms={remaining_timeout}"
            ),
        )
        options = WordOfDayOptions(
            count=resolved_per_language,
            level=level,
            dictionary="all" if dictionary == "motd-fast" else dictionary,
            reader_lang="en",
            translation_mode="cache",
            max_source_chars=140,
            include_ambiguous=True,
            require_clean_primary=False,
            timeout_ms=remaining_timeout,
            seed=f"motd-pool:{language}:{level}",
            fresh=False,
            candidate_source=resolved_candidate_source,
        )

        def probe(probe_language: str, query: str):
            return _motd_pool_probe_reduction_with_timeout(
                language=probe_language,
                text=query,
                dictionary=dictionary,
                normalize=True,
                diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
                diogenes_parse_endpoint=None,
                heritage_base="http://localhost:48080",
                db_path=None,
                no_cache=False,
                include_cltk=False,
                translation_mode="cache",
                translation_cache_db="data/cache/langnet.duckdb",
                translation_model="openai:gpt-4o-mini",
                timeout_seconds=probe_timeout_ms / 1000,
            )

        payload = generate_word_of_day_payload(
            languages=[language],
            options=options,
            probe_encounter=probe,
            bucket_gloss=_encounter_bucket_gloss,
            bucket_learner_gloss=lambda bucket: _encounter_bucket_learner_gloss(
                bucket,
                max_chars=80,
            ),
            candidate_pools=candidate_pools,
        )
        payload_warnings = payload.get("warnings") or []
        warnings.extend(payload_warnings)
        language_cards = cards_from_word_of_day_payload(
            payload,
            candidate_metadata=candidate_metadata,
            source=(
                "llm-curated-json"
                if isinstance(candidate_set, MotdCandidateSet)
                else resolved_candidate_source
            )
            if resolved_candidate_source == "candidate-json"
            else resolved_candidate_source,
            source_ref=source_ref,
            level=level,
        )
        cards.extend(language_cards)
        _motd_pool_log(
            json_output=json_output,
            message=(
                f"Validated {language}: accepted={len(language_cards)}, "
                f"warnings={len(payload_warnings)}"
            ),
        )

    _motd_pool_log(
        json_output=json_output,
        message=f"Writing {len(cards)} cards to {output_path} (wipe={wipe}).",
    )
    build_summary = build_motd_pool(output_path, cards, replace=wipe)
    validation = validate_motd_pool(output_path, per_language=resolved_per_language)
    issues = validation.get("issues")
    if not isinstance(issues, list):
        issues = []
    summary = {
        "schema_version": "langnet.motd_pool.build.v1",
        "output": str(output_path),
        "profile": build_profile,
        "candidate_source": resolved_candidate_source,
        "requested_per_language": resolved_per_language,
        "candidate_request_count": candidate_request_count,
        "inserted": build_summary.get("inserted"),
        "language_counts": validation.get("language_counts"),
        "ok": validation.get("ok"),
        "issues": issues,
        "warnings": warnings[:25],
    }
    _motd_pool_log(
        json_output=json_output,
        message=(
            f"Validation complete: ok={summary['ok']}, "
            f"language_counts={summary['language_counts']}, issues={len(issues)}"
        ),
    )
    if json_output:
        click.echo(orjson.dumps(summary, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    click.echo(f"profile: {summary['profile']}")
    click.echo(f"output: {output_path}")
    click.echo(f"candidate_source: {summary['candidate_source']}")
    click.echo(f"requested_per_language: {summary['requested_per_language']}")
    click.echo(f"candidate_request_count: {summary['candidate_request_count']}")
    click.echo(f"inserted: {summary['inserted']}")
    click.echo(f"language_counts: {summary['language_counts']}")
    click.echo(f"ok: {summary['ok']}")
    for issue in issues:
        if isinstance(issue, dict):
            click.echo(f"- {issue.get('code')}: {issue.get('message')}")


def _motd_pool_profile_candidate_source(build_profile: str) -> str:
    return "curated" if build_profile == "smoke" else "llm"


def _motd_pool_profile_per_language(build_profile: str) -> int:
    return 3 if build_profile == "smoke" else 30


def _motd_pool_candidate_request_count(
    *,
    build_profile: str,
    candidate_source: str,
    per_language: int,
) -> int:
    if build_profile == "prod" and candidate_source in {"auto", "llm"}:
        return per_language * 4
    return per_language


def _motd_pool_candidate_batch_count(
    *,
    build_profile: str,
    candidate_source: str,
    per_language: int,
) -> int:
    if build_profile == "prod" and candidate_source in {"auto", "llm"}:
        return min(per_language, 10)
    return per_language


def _motd_pool_candidate_max_batches(
    *,
    build_profile: str,
    candidate_source: str,
    per_language: int,
) -> int:
    if build_profile == "prod" and candidate_source in {"auto", "llm"}:
        candidate_request_count = _motd_pool_candidate_request_count(
            build_profile=build_profile,
            candidate_source=candidate_source,
            per_language=per_language,
        )
        batch_count = _motd_pool_candidate_batch_count(
            build_profile=build_profile,
            candidate_source=candidate_source,
            per_language=per_language,
        )
        return max(1, (candidate_request_count + batch_count - 1) // batch_count)
    return 1


def _motd_pool_pools_are_full(
    pools: Mapping[str, Sequence[WordCandidate]],
    *,
    languages: Sequence[str],
    target_per_language: int,
) -> bool:
    return all(len(pools.get(language, ())) >= target_per_language for language in languages)


def _motd_pool_batch_nonce(nonce: str | None, batch_index: int) -> str:
    prefix = nonce or "motd-pool-prod"
    return f"{prefix}:batch-{batch_index + 1}"


def _motd_pool_merge_candidate_pools(
    target: dict[str, list[WordCandidate]],
    source: Mapping[str, Sequence[WordCandidate]],
    *,
    seen_candidates: set[str],
) -> int:
    added = 0
    for language, candidates in source.items():
        language_items = target.setdefault(language, [])
        for candidate in candidates:
            key = _motd_pool_candidate_key(candidate)
            if not key or key in seen_candidates:
                continue
            seen_candidates.add(key)
            language_items.append(candidate)
            added += 1
    return added


def _motd_pool_candidate_key(candidate: WordCandidate) -> str:
    language = str(getattr(candidate, "language", "") or "").lower()
    query = str(getattr(candidate, "query", "") or "").lower()
    if not language or not query:
        return ""
    return f"{language}:{query}"


def _motd_pool_probe_reduction_with_timeout(
    *,
    timeout_seconds: float,
    **kwargs: Any,
) -> object:
    ctx = multiprocessing.get_context("fork")
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_motd_pool_probe_worker,
        args=(dict(kwargs), result_queue),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1)
        if process.is_alive():
            process.kill()
            process.join(1)
        language = kwargs.get("language")
        text = kwargs.get("text")
        raise TimeoutError(
            f"dictionary probe timed out after {timeout_seconds:.1f}s for {language}:{text}"
        )
    try:
        status, payload = result_queue.get_nowait()
    except queue_module.Empty as exc:
        raise click.ClickException(
            f"dictionary probe exited without a response (exit code {process.exitcode})."
        ) from exc
    if status == "ok":
        return payload
    raise click.ClickException(str(payload))


def _motd_pool_probe_worker(kwargs: dict[str, Any], result_queue) -> None:
    try:
        from langnet.cli import _word_of_day_probe_reduction  # noqa: PLC0415

        result_queue.put(("ok", _word_of_day_probe_reduction(**kwargs)))
    except Exception as exc:  # noqa: BLE001
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _motd_pool_log(*, json_output: bool, message: str) -> None:
    click.echo(f"[motd-pool] {message}", err=json_output)


@databuild.command("reader")
@click.option(
    "--perseus-dir",
    type=click.Path(),
    default=None,
    help="Perseus corpus root or fixture directory.",
)
@click.option(
    "--first1k-greek-dir",
    type=click.Path(),
    default=None,
    help="First1KGreek repository root or data directory.",
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
    first1k_greek_dir: str | None,
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
            first1k_greek_dir=first1k_greek_dir,
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
