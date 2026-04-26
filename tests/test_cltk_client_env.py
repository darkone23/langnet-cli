from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from langnet.execution.clients import _ensure_cltk_data_dir


def test_ensure_cltk_data_dir_uses_project_cache_when_home_missing() -> None:
    old_cltk_data = os.environ.pop("CLTK_DATA", None)
    try:
        with (
            tempfile.TemporaryDirectory() as temp_home,
            patch.object(Path, "home", return_value=Path(temp_home)),
        ):
            _ensure_cltk_data_dir()

        cltk_data = Path("data/cache/cltk_data").resolve()
        assert cltk_data.is_dir()
        assert os.environ["CLTK_DATA"] == str(cltk_data)
    finally:
        if old_cltk_data is not None:
            os.environ["CLTK_DATA"] = old_cltk_data
        else:
            os.environ.pop("CLTK_DATA", None)


def test_ensure_cltk_data_dir_prefers_existing_home_models() -> None:
    old_cltk_data = os.environ.pop("CLTK_DATA", None)
    try:
        with tempfile.TemporaryDirectory() as temp_home:
            home_path = Path(temp_home)
            home_cltk_data = home_path / "cltk_data"
            home_cltk_data.mkdir()

            with patch.object(Path, "home", return_value=home_path):
                _ensure_cltk_data_dir()

        assert "CLTK_DATA" not in os.environ
    finally:
        if old_cltk_data is not None:
            os.environ["CLTK_DATA"] = old_cltk_data
        else:
            os.environ.pop("CLTK_DATA", None)
