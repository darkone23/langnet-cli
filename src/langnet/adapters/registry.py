from __future__ import annotations

import time

from .cdsl import CDSLBackendAdapter
from .cltk import CLTKBackendAdapter
from .diogenes import DiogenesBackendAdapter
from .heritage import HeritageBackendAdapter
from .whitakers import WhitakersBackendAdapter


class CompositeAdapter:
    def __init__(self, adapters: list):
        self.adapters = [a for a in adapters if a is not None]

    def adapt(self, data: dict, language: str, word: str):
        results = []
        for adapter in self.adapters:
            results.extend(adapter.adapt(data, language, word))
        return results


class LanguageAdapterRegistry:
    """Registry mapping language codes to backend adapters."""

    def __init__(self):
        self._greek = DiogenesBackendAdapter()
        self._latin = DiogenesBackendAdapter()
        self._sanskrit = HeritageBackendAdapter()
        self._cltk = CLTKBackendAdapter()
        self._whitakers = WhitakersBackendAdapter()
        self._cdsl = CDSLBackendAdapter()

    def get_adapter(self, lang_code: str):
        if lang_code in {"grc", "grk"}:
            return GreekAdapter(self._greek, self._cltk)
        if lang_code == "lat":
            return LatinAdapter(self._latin, self._whitakers, self._cltk)
        if lang_code == "san":
            return SanskritAdapter(self._sanskrit, self._cdsl, self._cltk)
        raise ValueError(f"No adapter found for language: {lang_code}")


class GreekAdapter:
    def __init__(self, diogenes_adapter, cltk_adapter):
        self.diogenes_adapter = diogenes_adapter
        self.cltk_adapter = cltk_adapter

    @staticmethod
    def _call_adapter(adapter, data: dict, language: str, word: str, timings):
        try:
            return adapter.adapt(data, language, word, timings=timings)  # type: ignore[arg-type]
        except TypeError:
            return adapter.adapt(data, language, word)

    def _time(self, timings: dict[str, float] | None, name: str, func):
        if timings is None:
            return func()
        start = time.perf_counter()
        try:
            return func()
        finally:
            timings[name] = (time.perf_counter() - start) * 1000

    def adapt(self, data: dict, language: str, word: str, timings: dict[str, float] | None = None):
        entries = []
        if "diogenes" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_diogenes",
                    lambda: self._call_adapter(self.diogenes_adapter, data["diogenes"], language, word, timings),
                )
            )
        if "spacy" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_spacy",
                    lambda: self._call_adapter(self.cltk_adapter, data["spacy"], language, word, timings),
                )
            )
        if "cltk" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_cltk",
                    lambda: self._call_adapter(self.cltk_adapter, data["cltk"], language, word, timings),
                )
            )
        return entries


class LatinAdapter:
    def __init__(self, diogenes_adapter, whitakers_adapter, cltk_adapter):
        self.diogenes_adapter = diogenes_adapter
        self.whitakers_adapter = whitakers_adapter
        self.cltk_adapter = cltk_adapter

    @staticmethod
    def _call_adapter(adapter, data: dict, language: str, word: str, timings):
        try:
            return adapter.adapt(data, language, word, timings=timings)  # type: ignore[arg-type]
        except TypeError:
            return adapter.adapt(data, language, word)

    def _time(self, timings: dict[str, float] | None, name: str, func):
        if timings is None:
            return func()
        start = time.perf_counter()
        try:
            return func()
        finally:
            timings[name] = (time.perf_counter() - start) * 1000

    def adapt(self, data: dict, language: str, word: str, timings: dict[str, float] | None = None):
        entries = []
        if "whitakers" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_whitakers",
                    lambda: self._call_adapter(self.whitakers_adapter, data["whitakers"], language, word, timings),
                )
            )
        if "diogenes" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_diogenes",
                    lambda: self._call_adapter(self.diogenes_adapter, data["diogenes"], language, word, timings),
                )
            )
        if "cltk" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_cltk",
                    lambda: self._call_adapter(self.cltk_adapter, data["cltk"], language, word, timings),
                )
            )
        return entries


class SanskritAdapter:
    def __init__(self, heritage_adapter, cdsl_adapter, cltk_adapter):
        self.heritage_adapter = heritage_adapter
        self.cdsl_adapter = cdsl_adapter
        self.cltk_adapter = cltk_adapter

    @staticmethod
    def _call_adapter(adapter, data: dict, language: str, word: str, timings):
        try:
            return adapter.adapt(data, language, word, timings=timings)  # type: ignore[arg-type]
        except TypeError:
            return adapter.adapt(data, language, word)

    def _time(self, timings: dict[str, float] | None, name: str, func):
        if timings is None:
            return func()
        start = time.perf_counter()
        try:
            return func()
        finally:
            timings[name] = (time.perf_counter() - start) * 1000

    def adapt(self, data: dict, language: str, word: str, timings: dict[str, float] | None = None):
        entries = []
        if "heritage" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_heritage",
                    lambda: self._call_adapter(self.heritage_adapter, data["heritage"], language, word, timings),
                )
            )
        if "cdsl" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_cdsl",
                    lambda: self._call_adapter(self.cdsl_adapter, data["cdsl"], language, word, timings),
                )
            )
        if "cltk" in data:
            entries.extend(
                self._time(
                    timings,
                    "adapt_cltk",
                    lambda: self._call_adapter(self.cltk_adapter, data["cltk"], language, word, timings),
                )
            )
        return entries
