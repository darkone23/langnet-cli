from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import click
import duckdb

from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.paths import normalization_db_path
from query_spec import LanguageHint


def _parse_language(lang: str) -> LanguageHint:
    normalized = lang.strip().lower()
    alias_map = {
        "san": LanguageHint.SAN,
        "skt": LanguageHint.SAN,
        "grc": LanguageHint.GRC,
        "el": LanguageHint.GRC,
        "lat": LanguageHint.LAT,
        "la": LanguageHint.LAT,
    }
    if normalized not in alias_map:
        raise click.BadParameter(f"Unsupported language '{lang}'. Use san|grc|lat.")
    return alias_map[normalized]


def _heritage_factory(base_url: str | None, tool_client=None):
    def factory():
        from langnet.heritage.client import HeritageHTTPClient  # noqa: PLC0415
        from langnet.heritage.config import HeritageConfig  # noqa: PLC0415

        if base_url:
            cfg = HeritageConfig(base_url=base_url, cgi_path="/cgi-bin/skt/")
            return HeritageHTTPClient(config=cfg, tool_client=tool_client)
        return HeritageHTTPClient(tool_client=tool_client)

    return factory


def _print_result(result, output: str) -> None:
    payload = {
        "query_hash": result.query_hash,
        "language": result.normalized.language.name.lower(),
        "original": result.normalized.original,
        "candidates": [
            {"lemma": c.lemma, "sources": c.sources, "encodings": c.encodings}
            for c in result.normalized.candidates
        ],
        "steps": [
            {"op": s.operation, "input": s.input, "output": s.output, "tool": s.tool}
            for s in result.normalized.normalizations
        ],
    }
    if output == "json":
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    click.echo(
        f"Query: {payload['original']} [{payload['language']}] (hash={payload['query_hash']})"
    )
    click.echo("Candidates:")
    for c in payload["candidates"]:
        enc_strs = [f"{k}={v}" for k, v in sorted(c["encodings"].items())]
        enc_display = "  ".join(enc_strs) if enc_strs else ""
        click.echo(f"  - {c['lemma']}  sources={c['sources']}")
        if enc_display:
            click.echo(f"      {enc_display}")
    if payload["steps"]:
        click.echo("Steps:")
        for s in payload["steps"]:
            click.echo(f"  - {s['op']}: {s['input']} -> {s['output']} ({s['tool']})")


def _print_build_result(result) -> None:
    status = result.status.value if hasattr(result, "status") else "unknown"
    click.echo(f"status: {status}")
    click.echo(f"output: {result.output_path}")
    if result.message:
        click.echo(f"message: {result.message}")
    if result.stats:
        for key, value in sorted(result.stats.items()):
            click.echo(f"{key}: {value}")


@dataclass
class NormalizeConfig:
    diogenes_endpoint: str
    heritage_base: str
    db_path: str | None
    no_cache: bool
    output: str


def _normalize_impl(config: NormalizeConfig, language: str, text: str) -> None:
    lang_hint = _parse_language(language)

    path = Path(config.db_path).expanduser() if config.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=str(path))
    dio_config = DiogenesConfig(endpoint=config.diogenes_endpoint)

    # Create effects index to capture raw responses
    effects_index = RawResponseIndex(conn)

    def _whitaker_factory():
        from langnet.whitakers.client import WhitakerClient  # noqa: PLC0415

        return WhitakerClient()

    # Don't pass heritage_client factory when we want capturing
    # Let NormalizationService create it with the capturing client
    service = NormalizationService(
        conn,
        heritage_client=None,  # Will be created with capturing in _ensure_normalizer
        diogenes_config=dio_config,
        whitaker_client=_whitaker_factory,  # type: ignore[arg-type]
        use_cache=not config.no_cache,
        effects_index=effects_index,
    )

    result = service.normalize(text, lang_hint)
    _print_result(result, config.output)


@dataclass
class BuildCtsConfig:
    perseus_dir: str
    legacy_dir: str
    output: str | None
    include_legacy: bool
    wipe: bool
    force: bool
    max_works: int | None


def _build_cts_impl(config: BuildCtsConfig) -> None:
    from langnet.databuild.cts import CtsBuildConfig, CtsUrnBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_cts_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_cts_path()
    cts_config = CtsBuildConfig(
        perseus_dir=Path(config.perseus_dir).expanduser(),
        legacy_dir=Path(config.legacy_dir).expanduser(),
        output_path=output_path,
        include_legacy=config.include_legacy,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
        max_works=config.max_works,
    )
    builder = CtsUrnBuilder(cts_config)
    result = builder.build()
    _print_build_result(result)


@dataclass
class BuildCdslConfig:
    dict_id: str
    source_dir: str
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


def _build_cdsl_impl(config: BuildCdslConfig) -> None:
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


@click.group()
def main() -> None:
    """langnet-cli — classical language tools."""


@main.command()
@click.argument("language")
@click.argument("text")
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
    help="Diogenes CGI endpoint.",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform (CGI path is appended automatically).",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help="Path to persistent DuckDB cache for normalization (defaults to data/langnet.duckdb).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip normalization cache lookups and writes for this invocation.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def normalize(  # noqa: PLR0913
    language: str,
    text: str,
    diogenes_endpoint: str,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    output: str,
):
    """
    Normalize a query and show canonical candidates from authoritative backends.

    Examples:
      langnet-cli normalize san shiva
      langnet-cli normalize grc λόγος
      langnet-cli normalize lat lupus
    """
    config = NormalizeConfig(
        diogenes_endpoint=diogenes_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        output=output,
    )
    _normalize_impl(config, language, text)


@main.group()
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
    "--legacy-dir",
    type=click.Path(),
    default=str(Path.home() / "Classics-Data"),
    show_default=True,
    help="Legacy/Packard corpus root (auto-used if present).",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output DuckDB path (defaults to data/cts_urn.duckdb)"
)
@click.option(
    "--include-legacy/--no-legacy",
    default=True,
    show_default=True,
    help="Include Packard/legacy data when available.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
@click.option("--max-works", type=int, help="Limit number of works ingested (sampling/debug).")
def build_cts(  # noqa: PLR0913
    perseus_dir: str,
    legacy_dir: str,
    output: str | None,
    include_legacy: bool,
    wipe: bool,
    force: bool,
    max_works: int | None,
):
    """Build CTS URN index (Perseus + Packard/legacy)."""
    config = BuildCtsConfig(
        perseus_dir=perseus_dir,
        legacy_dir=legacy_dir,
        output=output,
        include_legacy=include_legacy,
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
    help="Output DuckDB path (defaults to data/cdsl_<dict>.duckdb)",
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


if __name__ == "__main__":
    main()
