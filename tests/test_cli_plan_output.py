from __future__ import annotations

import json

from click.testing import CliRunner

from langnet.cli import main


def test_plan_json_output_serializes_protobuf_maps() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["plan", "lat", "lupus", "--no-cache", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tool_calls"]
    assert isinstance(payload["tool_calls"][0]["params"], dict)
