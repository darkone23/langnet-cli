import os
import sys
import orjson
import requests

from langnet.execution.handlers.diogenes import _parse_diogenes_html


def _parse_endpoint(default: str | None = None) -> str:
    return default or os.environ.get("DIOGENES_PARSE_ENDPOINT", "http://localhost:8888/Perseus.cgi")


def run(lang: str, word: str, endpoint: str | None) -> None:
    base = _parse_endpoint(endpoint)
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
    lang = sys.argv[1] if len(sys.argv) > 1 else "lat"
    word = sys.argv[2] if len(sys.argv) > 2 else "lupus"
    endpoint = sys.argv[3] if len(sys.argv) > 3 else None
    run(lang, word, endpoint)
