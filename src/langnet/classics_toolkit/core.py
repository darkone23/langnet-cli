from pathlib import Path
import re
from typing import List, Optional

from pydantic import BaseModel, Field


class LatinQueryResult(BaseModel):
    headword: str
    ipa: str
    lewis_1890_lines: List[str]


class ClassicsToolkit:
    LATIN = "lat"
    GREEK = "grc"
    SANSKRIT = "san"

    _cltk_available: bool = False
    _lat_corpus: Optional[object] = None
    _latdict: Optional[object] = None
    _latlemma: Optional[object] = None
    _latxform: Optional[object] = None

    def __init__(self):
        self._try_import_cltk()

    def _try_import_cltk(self):
        try:
            import cltk.data.fetch as cltk_fetch
            import cltk.lexicon.lat as cltk_latlex
            import cltk.alphabet.lat as cltk_latchars
            import cltk.phonology.lat.transcription as cltk_latscript
            import cltk.lemmatize.lat as cltk_latlem
            from cltk.languages.utils import get_lang

            self._LATIN = get_lang(self.LATIN)

            self._lat_corpus = cltk_fetch.FetchCorpus(self.LATIN)

            required_models = ["lat_models_cltk"]
            for model in required_models:
                model_dir = Path.home() / "cltk_data/lat/model" / model
                if not model_dir.exists():
                    self._lat_corpus.import_corpus("lat_models_cltk")

            self._latdict = cltk_latlex.LatinLewisLexicon()
            self._jvsub = cltk_latchars.JVReplacer()
            self._latxform = cltk_latscript.Transcriber("Classical", "Allen")
            self._latlemma = cltk_latlem.LatinBackoffLemmatizer()

            self._cltk_available = True
        except ImportError as e:
            print(f"CLTK not available: {e}")
            self._cltk_available = False

    def is_available(self) -> bool:
        return self._cltk_available

    @property
    def latdict(self):
        return self._latdict

    @property
    def latlemma(self):
        return self._latlemma

    @property
    def latxform(self):
        return self._latxform

    @property
    def jvsub(self):
        return self._jvsub

    def latin_query(self, word) -> LatinQueryResult:
        if not self._cltk_available:
            return LatinQueryResult(
                headword="cltk_unavailable",
                ipa="",
                lewis_1890_lines=["CLTK module not available"],
            )

        try:
            (query, stem) = self._latlemma.lemmatize([word])[0]
            results = self._latdict.lookup(word)
            transcription = ""
            try:
                transcription = self._latxform.transcribe(word)
            except Exception as e:
                print(e)
            if not results:
                results = self._latdict.lookup(stem)
            if not transcription:
                try:
                    transcription = self._latxform.transcribe(stem)
                except Exception as e:
                    print(f"Error in transcribe: {e}")
                    pass
            if transcription:
                transcription = transcription[1:-1]

            merged_lines = " ".join(results.splitlines(keepends=False))
            parts = re.sub(r"\s+", " ", merged_lines)
            l_lines = []
            if parts:
                l_lines = [parts]

            return LatinQueryResult(
                headword=stem,
                ipa=transcription,
                lewis_1890_lines=l_lines,
            )
        except Exception as e:
            print(f"Error in latin_query: {e}")
            return LatinQueryResult(
                headword="error",
                ipa="",
                lewis_1890_lines=[f"Error: {str(e)}"],
            )
