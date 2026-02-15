"""
Ad-hoc benchmark for the Diogenes backend without restarting the server.

Measures HTTP fetch vs HTML parsing time for a single word.
"""

from __future__ import annotations

import argparse
import time
from statistics import mean

import requests
from bs4 import BeautifulSoup

from langnet.diogenes.core import DiogenesScraper


def make_url(base_url: str, word: str, language: str) -> str:
    if not base_url.endswith("/"):
        base_url += "/"
    return f"{base_url}Perseus.cgi?do=parse&lang={language}&q={word}"


def fetch_raw(url: str) -> tuple[requests.Response, float]:
    start = time.perf_counter()
    resp = requests.get(url)
    return resp, (time.perf_counter() - start) * 1000


def parse_response(scraper: DiogenesScraper, text: str) -> dict[str, object]:
    metrics: dict[str, object] = {}
    result: dict[str, object] = {"chunks": [], "dg_parsed": True}

    split_start = time.perf_counter()
    documents = text.split("<hr />")
    metrics["doc_split_ms"] = (time.perf_counter() - split_start) * 1000
    metrics["doc_count"] = len(documents)

    chunk_times: list[float] = []
    parse_start = time.perf_counter()
    for doc in documents:
        t0 = time.perf_counter()
        soup = scraper._make_soup(doc)  # noqa: SLF001
        chunk = scraper.get_next_chunk(result, soup)
        scraper.process_chunk(result, chunk)
        chunk_times.append((time.perf_counter() - t0) * 1000)
    metrics["parse_total_ms"] = (time.perf_counter() - parse_start) * 1000
    metrics["chunk_ms_avg"] = mean(chunk_times) if chunk_times else 0.0
    metrics["chunk_ms_max"] = max(chunk_times) if chunk_times else 0.0
    metrics["chunk_ms_min"] = min(chunk_times) if chunk_times else 0.0

    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("word")
    parser.add_argument("--language", default="grc")
    parser.add_argument("--base-url", default="http://localhost:8888/")
    args = parser.parse_args()

    url = make_url(args.base_url, args.word, args.language)
    scraper = DiogenesScraper(base_url=args.base_url)

    resp, http_ms = fetch_raw(url)
    print(f"HTTP status={resp.status_code} http_ms={http_ms:.2f} content_len={len(resp.text)}")
    if resp.status_code != 200:
        return

    metrics = parse_response(scraper, resp.text)
    print(
        "doc_split_ms={doc_split_ms:.2f} doc_count={doc_count} "
        "parse_total_ms={parse_total_ms:.2f} "
        "chunk_ms_avg={chunk_ms_avg:.2f} chunk_ms_min={chunk_ms_min:.2f} chunk_ms_max={chunk_ms_max:.2f}".format(
            **metrics
        )
    )


if __name__ == "__main__":
    main()
