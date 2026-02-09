from __future__ import annotations

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

    def adapt(self, data: dict, language: str, word: str):
        entries = []
        if "diogenes" in data:
            entries.extend(self.diogenes_adapter.adapt(data["diogenes"], language, word))
        if "spacy" in data:
            entries.extend(self.cltk_adapter.adapt(data["spacy"], language, word))
        if "cltk" in data:
            entries.extend(self.cltk_adapter.adapt(data["cltk"], language, word))
        return entries


class LatinAdapter:
    def __init__(self, diogenes_adapter, whitakers_adapter, cltk_adapter):
        self.diogenes_adapter = diogenes_adapter
        self.whitakers_adapter = whitakers_adapter
        self.cltk_adapter = cltk_adapter

    def adapt(self, data: dict, language: str, word: str):
        entries = []
        if "diogenes" in data:
            entries.extend(self.diogenes_adapter.adapt(data["diogenes"], language, word))
        if "whitakers" in data:
            entries.extend(self.whitakers_adapter.adapt(data["whitakers"], language, word))
        if "cltk" in data:
            entries.extend(self.cltk_adapter.adapt(data["cltk"], language, word))
        return entries


class SanskritAdapter:
    def __init__(self, heritage_adapter, cdsl_adapter, cltk_adapter):
        self.heritage_adapter = heritage_adapter
        self.cdsl_adapter = cdsl_adapter
        self.cltk_adapter = cltk_adapter

    def adapt(self, data: dict, language: str, word: str):
        entries = []
        if "heritage" in data:
            entries.extend(self.heritage_adapter.adapt(data["heritage"], language, word))
        if "cdsl" in data:
            entries.extend(self.cdsl_adapter.adapt(data["cdsl"], language, word))
        if "cltk" in data:
            entries.extend(self.cltk_adapter.adapt(data["cltk"], language, word))
        return entries
