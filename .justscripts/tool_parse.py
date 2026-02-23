import os
import subprocess
import sys

import orjson
import requests

import duckdb

import click

from langnet.cli import _create_normalization_service, NormalizeConfig
from langnet.storage.db import connect_duckdb
from langnet.storage.paths import normalization_db_path
from langnet.execution.handlers.diogenes import _parse_diogenes_html
from langnet.execution.handlers.whitakers import _parse_whitaker_output
from langnet.execution.clients import get_cltk_fetch_client
from query_spec import LanguageHint


def _parse_language(lang: str) -> str:
    lang_l = lang.lower()
    if lang_l in {"lat", "la", "latin"}:
        return LanguageHint.LANGUAGE_HINT_LAT
    if lang_l in {"grc", "el", "greek"}:
        return LanguageHint.LANGUAGE_HINT_GRC
    if lang_l in {"san", "sa", "sanskrit"}:
        return LanguageHint.LANGUAGE_HINT_SAN
    return LanguageHint.LANGUAGE_HINT_LAT


def _normalize_word(lang: str, word: str) -> str:
    """
    Run the normalizer to pick the best candidate spelling/transliteration.
    Falls back to the input on any error.
    """
    try:
        norm_cfg = NormalizeConfig(
            diogenes_endpoint=os.environ.get("DIOGENES_ENDPOINT", "http://localhost:8888/Diogenes.cgi"),
            heritage_base=os.environ.get("HERITAGE_BASE", "http://localhost:48080"),
            db_path=None,
            no_cache=True,
            output="pretty",
        )
        norm_path = normalization_db_path()
        norm_path.parent.mkdir(parents=True, exist_ok=True)
        use_memory = not norm_path.exists()
        if use_memory:
            with duckdb.connect(database=":memory:") as conn:
                service = _create_normalization_service(norm_cfg, conn, read_only=False)
                normalized = service.normalize(word, _parse_language(lang))
        else:
            with connect_duckdb(norm_path, read_only=True, lock=False) as conn:
                service = _create_normalization_service(norm_cfg, conn, read_only=True)
                normalized = service.normalize(word, _parse_language(lang))
        candidates = getattr(normalized.normalized, "candidates", []) or []
        if candidates and hasattr(candidates[0], "lemma"):
            best = candidates[0].lemma
            if isinstance(best, str) and best:
                return best
        orig = getattr(normalized.normalized, "original", None)
        if isinstance(orig, str) and orig:
            return orig
        return word
    except Exception:
        return word


def _parse_diogenes(lang: str, word: str, endpoint: str | None, normalize: bool) -> dict:
    base = endpoint or os.environ.get("DIOGENES_PARSE_ENDPOINT", "http://localhost:8888/Perseus.cgi")
    query_word = _normalize_word(lang, word) if normalize else word
    mapped_lang = "grk" if lang.lower() == "grc" else lang
    params = {"do": "parse", "lang": mapped_lang, "q": query_word}
    resp = requests.get(base, params=params)
    html = resp.text if resp.ok else ""
    parsed = _parse_diogenes_html(html)
    return {
        "tool": "diogenes",
        "endpoint": base,
        "url": resp.url,
        "status": resp.status_code,
        "lang": lang,
        "word": word,
        "content_length": len(html),
        "parsed": parsed,
    }


def _parse_whitakers(_lang: str, word: str, binary: str | None) -> dict:
    # Whitaker is language-aware internally; we accept lang for symmetry but do not pass it.
    candidates = [binary] if binary else []
    candidates.extend(
        [
            os.environ.get("WHITAKERS_BIN"),
            "whitakers-words",
            "words",
        ]
    )
    cmd = next((c for c in candidates if c), None)
    if not cmd:
        raise RuntimeError("No Whitaker binary found; set WHITAKERS_BIN or install whitakers-words.")

    proc = subprocess.run([cmd, word], check=False, capture_output=True, text=True)
    text = proc.stdout or ""
    parsed = _parse_whitaker_output(text)
    return {
        "tool": "whitakers",
        "binary": cmd,
        "status": proc.returncode,
        "word": word,
        "content_length": len(text),
        "parsed": parsed,
    }


def _parse_cltk(lang: str, word: str, normalize: bool) -> dict:
    client = get_cltk_fetch_client()
    query_word = _normalize_word(lang, word) if normalize else word
    effect = client.execute(
        call_id=f"cltk-{query_word}",
        endpoint=f"cltk://ipa/{lang}",
        params={"word": query_word, "language": lang},
    )
    raw_json = effect.body.decode("utf-8", errors="ignore")
    parsed = {}
    try:
        parsed = orjson.loads(effect.body)
    except Exception:
        parsed = {}
    return {
        "tool": "cltk",
        "endpoint": effect.endpoint,
        "status": effect.status_code,
        "word": word,
        "content_length": len(raw_json),
        "parsed": parsed,
    }


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("tool")
@click.argument("lang")
@click.argument("word")
@click.option(
    "--opt",
    default="",
    help="Optional arg: diogenes endpoint or Whitaker binary override",
    show_default=True,
)
@click.option(
    "--normalize/--no-normalize",
    default=False,
    help="Normalize input via normalizer and use best candidate for the tool query",
    show_default=True,
)
def cli(tool: str, lang: str, word: str, opt: str, normalize: bool) -> None:
    """Parse tool output with optional normalization."""
    tool_l = tool.lower()
    if tool_l in {"diogenes", "dio"}:
        out = _parse_diogenes(lang, word, opt or None, normalize)
    elif tool_l in {"whitakers", "whitaker", "ww"}:
        out = _parse_whitakers(lang, word, opt or None)
    elif tool_l == "cltk":
        out = _parse_cltk(lang, word, normalize)
    else:
        raise SystemExit(f"Unsupported tool '{args.tool}'. Use 'diogenes', 'whitakers', or 'cltk'.")
    sys.stdout.buffer.write(orjson.dumps(out, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    cli()
