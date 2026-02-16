from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BASE_DIR / "vendor" / "langnet-spec" / "generated" / "python"
sys.path.insert(0, str(SCHEMA_PATH))

from langnet.clients import CLTKService  # noqa: E402


def test_cltk_service_warmup_uses_single_instance() -> None:
    calls: list[str] = []

    def _loader(lang: str) -> str:
        calls.append(lang)
        return f"pipeline-{lang}"

    service = CLTKService(loader=_loader)

    assert service.get_pipeline("lat") == "pipeline-lat"
    # Second access should reuse cached pipeline.
    assert service.get_pipeline("lat") == "pipeline-lat"
    service.warm_up(["lat", "grc"])

    assert calls.count("lat") == 1
    assert calls.count("grc") == 1
