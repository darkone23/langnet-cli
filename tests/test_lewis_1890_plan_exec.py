from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import orjson
from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery, ToolCallSpec, ToolPlan

from langnet.cli import _build_exec_clients
from langnet.databuild.lewis_1890 import Lewis1890BuildConfig, Lewis1890Builder


def test_build_exec_clients_wires_lewis_1890_fetch_client() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "lewis.yaml"
        db_path = base / "lex_lewis_1890.duckdb"
        source.write_text('lupus: "lupus ī, m a wolf."\n', encoding="utf-8")
        result = Lewis1890Builder(
            Lewis1890BuildConfig(source_path=source, output_path=db_path)
        ).build()
        assert result.status.value == "success", result.message

        with patch("langnet.databuild.lewis_1890.default_lewis_1890_path", return_value=db_path):
            clients = _build_lewis_1890_clients()

            client = clients["fetch.lewis_1890"]
            assert client.tool == "fetch.lewis_1890"
            raw = client.execute(
                "lewis-1890-1", "duckdb://lewis_1890", params={"headword": "lupus"}
            )
            body = orjson.loads(raw.body)
            assert body["entries"][0]["headword_norm"] == "lupus"


def _build_lewis_1890_clients():
    plan = ToolPlan(
        plan_id="plan-lewis-1890-1",
        plan_hash="hash-lewis-1890-1",
        query=NormalizedQuery(
            original="lupus",
            language=LanguageHint.LANGUAGE_HINT_LAT,
            candidates=[CanonicalCandidate(lemma="lupus", encodings={}, sources=["test"])],
            normalizations=[],
        ),
        tool_calls=[
            ToolCallSpec(
                tool="fetch.lewis_1890",
                call_id="lewis-1890-1",
                endpoint="duckdb://lewis_1890",
                params={"headword": "lupus"},
            )
        ],
        dependencies=[],
    )
    return _build_exec_clients(plan, diogenes_endpoint="", use_stubs=False)
