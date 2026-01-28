import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

import langnet.logging  # noqa: F401 - ensures logging is configured before use

logger = structlog.get_logger(__name__)


@dataclass
class LatinQueryResult:
    headword: str
    ipa: str
    lewis_1890_lines: list[str]


@dataclass
class GreekMorphologyResult:
    text: str
    lemma: str
    pos: str
    morphological_features: dict


@dataclass
class SanskritMorphologyResult:
    lemma: str
    pos: str
    morphological_features: dict


class ClassicsToolkit:
    LATIN = "lat"
    GREEK = "grc"
    SANSKRIT = "san"

    _singleton_instance: "ClassicsToolkit | None" = None
    _initialized: bool = False

    _cltk_available: bool = False
    _spacy_available: bool = False
    _lat_corpus: Any | None = None
    _latdict: Any | None = None
    _latlemma: Any | None = None
    _latxform: Any | None = None
    _grc_spacy_model: Any | None = None
    _san_cltk_nlp: Any | None = None

    def __new__(cls):
        if cls._singleton_instance is None:
            cls._singleton_instance = super().__new__(cls)
        return cls._singleton_instance

    def __init__(self):
        if not ClassicsToolkit._initialized:
            self._try_import_cltk()
            self._try_import_spacy()
            self._try_import_sanskrit_cltk()
            ClassicsToolkit._initialized = True

    def _try_import_sanskrit_cltk(self):
        try:
            from cltk import NLP  # noqa: PLC0415

            self._san_cltk_nlp = NLP(language="san", suppress_banner=True)
            logger.info("sanskrit_cltk_loaded")
        except ImportError as e:
            logger.warning("sanskrit_cltk_unavailable", error=str(e))
            self._san_cltk_nlp = None
        except Exception as e:
            logger.warning("sanskrit_cltk_init_failed", error=str(e))
            self._san_cltk_nlp = None

    def _try_import_cltk(self):
        try:
            import cltk.alphabet.lat as cltk_latchars  # noqa: PLC0415
            import cltk.data.fetch as cltk_fetch  # noqa: PLC0415
            import cltk.lemmatize.lat as cltk_latlem  # noqa: PLC0415
            import cltk.lexicon.lat as cltk_latlex  # noqa: PLC0415
            import cltk.phonology.lat.transcription as cltk_latscript  # noqa: PLC0415
            from cltk.languages.utils import get_lang  # noqa: PLC0415

            self._LATIN = get_lang(self.LATIN)

            self._lat_corpus = cltk_fetch.FetchCorpus(self.LATIN)

            required_models = ["lat_models_cltk"]
            for model in required_models:
                model_dir = Path.home() / "cltk_data/lat/model" / model
                if not model_dir.exists():
                    assert self._lat_corpus is not None
                    self._lat_corpus.import_corpus("lat_models_cltk")

            self._latdict = cltk_latlex.LatinLewisLexicon()
            self._jvsub = cltk_latchars.JVReplacer()
            self._latxform = cltk_latscript.Transcriber("Classical", "Allen")
            self._latlemma = cltk_latlem.LatinBackoffLemmatizer()

            self._cltk_available = True
        except ImportError as e:
            logger.warning("cltk_unavailable", error=str(e))
            self._cltk_available = False

    def _try_import_spacy(self):
        model_name = "grc_odycy_joint_sm"
        try:
            import spacy  # noqa: PLC0415

            self._spacy_imported = True
            self._grc_spacy_model = spacy.load(model_name)
            self._spacy_available = True
            logger.info("spacy_model_loaded", model=model_name)
        except OSError as e:
            logger.warning("spacy_model_missing", model=model_name, error=str(e))
            self._spacy_available = False
        except ImportError as e:
            logger.warning("spacy_unavailable", error=str(e))
            self._spacy_imported = False
            self._spacy_available = False

    def is_available(self) -> bool:
        return self._cltk_available

    def spacy_is_available(self) -> bool:
        return self._spacy_available

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
            assert self._latlemma is not None
            assert self._latdict is not None
            assert self._latxform is not None
            (query, stem) = self._latlemma.lemmatize([word])[0]
            results = self._latdict.lookup(word)
            transcription = ""
            try:
                transcription = self._latxform.transcribe(word)
            except Exception as e:
                logger.debug("transcription_failed", word=word, error=str(e))
            if not results:
                results = self._latdict.lookup(stem)
            if not transcription:
                try:
                    transcription = self._latxform.transcribe(stem)
                except Exception as e:
                    logger.debug("stem_transcription_failed", stem=stem, error=str(e))
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
            logger.error("latin_query_failed", word=word, error=str(e))
            return LatinQueryResult(
                headword="error",
                ipa="",
                lewis_1890_lines=[f"Error: {str(e)}"],
            )

    def greek_morphology_query(self, word) -> GreekMorphologyResult:
        if not getattr(self, "_spacy_imported", False):
            return GreekMorphologyResult(
                text=word,
                lemma="spacy_unavailable",
                pos="",
                morphological_features={"error": "Spacy module not installed"},
            )

        if self._grc_spacy_model is None:
            return GreekMorphologyResult(
                text=word,
                lemma="spacy_unavailable",
                pos="",
                morphological_features={"error": "Spacy model not available"},
            )

        try:
            doc = self._grc_spacy_model(word)

            if len(doc) > 0:
                token = doc[0]
                morphological_features = {}
                if token.morph:
                    for key, value in token.morph.to_dict().items():
                        morphological_features[key] = value

                return GreekMorphologyResult(
                    text=word,
                    lemma=token.lemma_ if token.lemma_ else word,
                    pos=token.pos_ if token.pos_ else "",
                    morphological_features=morphological_features,
                )
            else:
                return GreekMorphologyResult(
                    text=word,
                    lemma=word,
                    pos="",
                    morphological_features={},
                )
        except Exception as e:
            logger.error("greek_morphology_query_failed", word=word, error=str(e))
            return GreekMorphologyResult(
                text=word,
                lemma="error",
                pos="",
                morphological_features={"error": str(e)},
            )

    def sanskrit_morphology_query(self, word: str) -> SanskritMorphologyResult:
        if self._san_cltk_nlp is None:
            return SanskritMorphologyResult(
                lemma="cltk_unavailable",
                pos="",
                morphological_features={"error": "CLTK Sanskrit model not available"},
            )

        try:
            cltk_doc = self._san_cltk_nlp.analyze(text=word)

            if cltk_doc.sentences and cltk_doc.sentences[0] and len(cltk_doc.sentences[0]) > 0:
                token = cltk_doc.sentences[0][0]
                morphological_features = {}
                if hasattr(token, "morphology") and token.morphology:
                    for key in dir(token.morphology):
                        if not key.startswith("_"):
                            value = getattr(token.morphology, key, None)
                            if value is not None:
                                morphological_features[key] = value

                lemma = getattr(token, "lemma", word) or word
                pos = getattr(token, "upos", "") or ""

                return SanskritMorphologyResult(
                    lemma=lemma,
                    pos=pos,
                    morphological_features=morphological_features,
                )
            else:
                return SanskritMorphologyResult(
                    lemma=word,
                    pos="",
                    morphological_features={},
                )
        except Exception as e:
            logger.error("sanskrit_morphology_query_failed", word=word, error=str(e))
            return SanskritMorphologyResult(
                lemma="error",
                pos="",
                morphological_features={"error": str(e)},
            )
