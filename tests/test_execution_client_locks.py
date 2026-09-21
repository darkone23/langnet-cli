from __future__ import annotations

import threading
import unittest
from unittest import mock

from langnet.execution import clients


class _CountingStub:
    """Stand-in for the real client classes: counts constructions, raises on #2."""

    constructed = 0
    guard = threading.Lock()

    def __init__(self, *args: object, **kwargs: object) -> None:
        with _CountingStub.guard:
            _CountingStub.constructed += 1
            if _CountingStub.constructed > 1:
                raise AssertionError("client constructed more than once")


class TestClientSingletonLocks(unittest.TestCase):
    """Server worker threads race lazy singletons; init must be double-checked locked."""

    def setUp(self) -> None:
        clients._CLTK_CLIENT_SINGLETON = None  # noqa: SLF001
        clients._SPACY_CLIENT_SINGLETON = None  # noqa: SLF001
        _CountingStub.constructed = 0

    def tearDown(self) -> None:
        clients._CLTK_CLIENT_SINGLETON = None  # noqa: SLF001
        clients._SPACY_CLIENT_SINGLETON = None  # noqa: SLF001

    def _hammer(self, class_name: str, getter_name: str) -> list[Exception]:
        getter = getattr(clients, getter_name)
        barrier = threading.Barrier(8)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                barrier.wait()
                getter()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        with mock.patch.object(clients, class_name, _CountingStub):
            threads = [threading.Thread(target=worker) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        return errors

    def test_cltk_client_initialized_once_under_thread_race(self) -> None:
        errors = self._hammer("CLTKFetchClient", "get_cltk_fetch_client")

        for error in errors:
            raise AssertionError(f"worker thread failed: {error}") from error
        self.assertEqual(_CountingStub.constructed, 1)

    def test_spacy_client_initialized_once_under_thread_race(self) -> None:
        errors = self._hammer("SpacyFetchClient", "get_spacy_fetch_client")

        for error in errors:
            raise AssertionError(f"worker thread failed: {error}") from error
        self.assertEqual(_CountingStub.constructed, 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
