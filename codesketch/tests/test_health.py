import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

import langnet.health as langnet_health
from langnet.config import LangnetSettings
from langnet.health import (
    ComponentStatus,
    check_cdsl,
    check_diogenes,
    check_heritage,
    overall_status,
    run_health_checks,
)


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "ok"):
        self.status_code = status_code
        self.text = text


class HealthCheckTests(unittest.TestCase):
    def test_check_diogenes_healthy_on_200(self):
        result = check_diogenes(
            "http://example.com",
            timeout=1,
            requester=lambda *args, **kwargs: FakeResponse(status_code=200),
        )
        self.assertEqual(result.status, "healthy")
        self.assertIsNotNone(result.details)
        assert result.details is not None
        self.assertEqual(result.details["status_code"], 200)

    def test_check_diogenes_degraded_on_404(self):
        result = check_diogenes(
            "http://example.com",
            timeout=1,
            requester=lambda *args, **kwargs: FakeResponse(status_code=404),
        )
        self.assertEqual(result.status, "degraded")
        self.assertIn("404", result.message or "")

    def test_check_cdsl_missing_indexes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir)
            result = check_cdsl(db_dir)
            self.assertEqual(result.status, "missing")
            self.assertIn("Missing CDSL indexes", result.message or "")

    def test_check_heritage_fallback_path(self):
        responses = iter([FakeResponse(status_code=404), FakeResponse(status_code=200)])

        def requester(url, timeout):
            return next(responses)

        result = check_heritage("http://example.com", timeout=1, requester=requester)
        self.assertEqual(result.status, "healthy")

    def test_run_health_checks_can_be_stubbed(self):
        settings = LangnetSettings.from_env(
            {
                "LANGNET_ENV": "test",
                "HTTP_TIMEOUT": "1",
                "DIOGENES_URL": "http://example.com",
                "HERITAGE_URL": "http://example.com",
                "CDSL_DB_DIR": "/tmp",
                "CDSL_DICT_DIR": "/tmp",
            }
        )

        with (
            mock.patch("langnet.health.check_diogenes", return_value=ComponentStatus("healthy")),
            mock.patch("langnet.health.check_cltk", return_value=ComponentStatus("healthy")),
            mock.patch("langnet.health.check_spacy", return_value=ComponentStatus("healthy")),
            mock.patch("langnet.health.check_whitakers", return_value=ComponentStatus("healthy")),
            mock.patch("langnet.health.check_cdsl", return_value=ComponentStatus("healthy")),
            mock.patch("langnet.health.check_heritage", return_value=ComponentStatus("healthy")),
            mock.patch("langnet.health.check_cache", return_value=ComponentStatus("healthy")),
        ):
            health = run_health_checks(settings)

        self.assertIsInstance(health, dict)
        self.assertEqual(health["status"], "healthy")
        components_obj = health.get("components")
        self.assertIsInstance(components_obj, dict)
        components = cast(dict[str, dict[str, object]], components_obj)
        component_values = components.values()
        self.assertTrue(
            all(
                isinstance(comp, dict) and comp.get("status") == "healthy"
                for comp in component_values
            )
        )

    def test_overall_status_degraded_when_component_unhealthy(self):
        components = {
            "a": ComponentStatus("healthy"),
            "b": ComponentStatus("missing"),
        }
        self.assertEqual(overall_status(components), "degraded")

    def test_cache_not_configured_marks_degraded(self):
        cache_status = langnet_health.check_cache()
        self.assertEqual(cache_status.status, "not_configured")
        components = {
            "a": ComponentStatus("healthy"),
            "cache": cache_status,
        }
        self.assertEqual(overall_status(components), "degraded")


if __name__ == "__main__":
    unittest.main()
