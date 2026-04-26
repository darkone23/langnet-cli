import os
import sys

import click
import orjson
import requests

from langnet.execution.handlers.diogenes import _parse_diogenes_html


def _parse_endpoint(default: str | None = None) -> str:
    return default or os.environ.get("DIOGENES_PARSE_ENDPOINT", "http://localhost:8888/Perseus.cgi")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("lang", default="lat")
@click.argument("word", default="lupus")
@click.argument("endpoint", default="", required=False)
def cli(lang: str, word: str, endpoint: str) -> None:
    """Parse Diogenes HTML and dump the raw parsed JSON.

    Arguments:
      LANG      Diogenes language code, e.g. lat or grk (default: lat)
      WORD      Word to parse (default: lupus)
      ENDPOINT  Optional parse endpoint override
    """
    endpoint_val = endpoint if endpoint else None
    base = _parse_endpoint(endpoint_val)
    params = {"do": "parse", "lang": lang, "q": word}
    resp = requests.get(base, params=params)
    html = resp.text if resp.ok else ""
    parsed = _parse_diogenes_html(html)
    out = {
        "endpoint": base,
        "url": resp.url,
        "status": resp.status_code,
        "lang": lang,
        "word": word,
        "content_length": len(html),
        "parsed": parsed,
    }
    sys.stdout.buffer.write(orjson.dumps(out, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    cli()
