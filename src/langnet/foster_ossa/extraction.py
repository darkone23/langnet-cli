from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import orjson

from langnet.foster_ossa.models import FosterOssaPage

PdfTextRunner = Callable[[list[str]], str]


def run_pdftotext(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def iter_page_rows_from_pdftotext(
    text: str,
    *,
    source_path: Path,
) -> Iterator[FosterOssaPage]:
    raw_pages = text.split("\f")
    if raw_pages and not raw_pages[0].strip():
        raw_pages = raw_pages[1:]
    if raw_pages and not raw_pages[-1].strip():
        raw_pages = raw_pages[:-1]

    for page_number, page_text in enumerate(raw_pages, start=1):
        warning = ""
        if not page_text.strip():
            warning = "empty_page"
        if not page_text and not warning:
            continue
        yield FosterOssaPage.from_text(
            page_number=page_number,
            source_path=str(source_path),
            extraction_tool="pdftotext",
            text=page_text,
            warning=warning,
        )


def extract_pdf_pages(
    source_path: Path,
    *,
    runner: PdfTextRunner = run_pdftotext,
) -> Iterator[FosterOssaPage]:
    expanded = source_path.expanduser()
    output = runner(["pdftotext", "-layout", str(expanded), "-"])
    yield from iter_page_rows_from_pdftotext(output, source_path=expanded)


def write_page_rows_jsonl(
    pages: Iterable[FosterOssaPage],
    output_path: Path,
) -> int:
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("wb") as output:
        for page in pages:
            output.write(orjson.dumps(page.as_dict()))
            output.write(b"\n")
            count += 1
    return count
