from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import orjson
from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery, ToolCallSpec, ToolPlan

from langnet.cli import _build_exec_clients
from langnet.databuild.bailly import apply_bailly_schema, insert_pdf_structural_entry


def test_build_exec_clients_wires_bailly_fetch_client() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p090-c1-0004",
                    "lemma": "ἀγελαῖος",
                    "lemma_norm": "agelaios",
                    "source": {"kind": "pdf", "page_start": 90, "page_end": 90},
                    "raw_text": "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau",
                    "blocks": [
                        {
                            "path": "00",
                            "marker": "head",
                            "text": "ἀγελαῖος, α, ον [ ᾰγ ]",
                        },
                        {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
                    ],
                },
            )
        with patch("langnet.databuild.bailly.default_bailly_path", return_value=db_path):
            clients = _build_bailly_clients()

            client = clients["fetch.bailly"]
            assert client.tool == "fetch.bailly"
            raw = client.execute(
                "bailly-fetch-1", "duckdb://bailly", params={"headword": "agelaios"}
            )
            body = orjson.loads(raw.body)
            assert len(body["entries"]) == 1
            assert body["entries"][0]["lemma_norm"] == "agelaios"


def _build_bailly_clients():
    plan = ToolPlan(
        plan_id="plan-bailly-1",
        plan_hash="hash-bailly-1",
        query=NormalizedQuery(
            original="agelaios",
            language=LanguageHint.LANGUAGE_HINT_GRC,
            candidates=[CanonicalCandidate(lemma="agelaios", encodings={}, sources=["test"])],
            normalizations=[],
        ),
        tool_calls=[
            ToolCallSpec(
                tool="fetch.bailly",
                call_id="bailly-fetch-1",
                endpoint="duckdb://bailly",
                params={"headword": "agelaios"},
            )
        ],
        dependencies=[],
    )
    return _build_exec_clients(plan, diogenes_endpoint="", use_stubs=False)
