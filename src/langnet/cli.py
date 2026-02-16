from __future__ import annotations

import json

import click
import duckdb
from query_spec import LanguageHint

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.config import HeritageConfig
from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.whitakers.client import WhitakerClient


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


def _build_heritage_client(base_url: str | None) -> HeritageHTTPClient:
    if base_url:
        cfg = HeritageConfig(base_url=base_url, cgi_path="/cgi-bin/skt/")
        return HeritageHTTPClient(config=cfg)
    return HeritageHTTPClient()


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
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def normalize(language: str, text: str, diogenes_endpoint: str, heritage_base: str, output: str):
    """
    Normalize a query and show canonical candidates from authoritative backends.

    Examples:
      langnet-cli normalize san shiva
      langnet-cli normalize grc λόγος
      langnet-cli normalize lat lupus
    """

    lang_hint = _parse_language(language)

    conn = duckdb.connect(database=":memory:")
    dio_config = DiogenesConfig(endpoint=diogenes_endpoint)
    service = NormalizationService(
        conn,
        heritage_client=_build_heritage_client(heritage_base),
        diogenes_config=dio_config,
        whitaker_client=WhitakerClient(),
    )

    result = service.normalize(text, lang_hint)
    _print_result(result, output)


if __name__ == "__main__":
    main()
