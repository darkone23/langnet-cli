from pathlib import Path

import re

from rich.pretty import pprint
pprint("Loading the CLTK module...")


import cltk.data.fetch as cltk_fetch
import cltk.lexicon.lat as cltk_latlex
import cltk.alphabet.lat as cltk_latchars
import cltk.phonology.lat.transcription as cltk_latscript
import cltk.lemmatize.lat as cltk_latlem

from cltk.languages.utils import get_lang, Language

from pydantic import BaseModel, Field

from typing import List



pprint("Loading the CLTK module[latin]...")
LATIN: Language = get_lang("lat")
pprint("Loading the CLTK module[grc]...")
GREEK: Language = get_lang("grc")
pprint("Loading the CLTK module[san]...")
SANSKRIT: Language = get_lang("san")

pprint("Loading the CLTK modules: OK")

class LatinQueryResult(BaseModel):
    headword: str
    ipa: str
    lewis_1890_lines: List[str]


class ClassicsToolkit:

    # https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes

    LATIN: Language = LATIN
    GREEK: Language = GREEK
    SANSKRIT: Language = SANSKRIT

    def __init__(self):

        self.lat_corpus = cltk_fetch.FetchCorpus(self.LATIN.iso_639_3_code)

        self.required_models = [
            "lat_models_cltk",
        ]
        for model in self.required_models:
            model_dir = Path.home() / Path("cltk_data/lat/model") / model
            if not model_dir.exists():
                self.lat_corpus.import_corpus("lat_models_cltk")

        self.latdict = cltk_latlex.LatinLewisLexicon()
        self.jvsub = cltk_latchars.JVReplacer()
        self.latxform = cltk_latscript.Transcriber("Classical", "Allen")
        self.latlemma = cltk_latlem.LatinBackoffLemmatizer()

    def latin_query(self, word) -> LatinQueryResult:
        (query, stem) = self.latlemma.lemmatize([word])[0]
        results = self.latdict.lookup(
            # always better to look up a headword in the dictionary
            word
        )  # Charlton T. Lewis's *An Elementary Latin Dic
        transcription = ""
        try:
            transcription = self.latxform.transcribe(word)
        except Exception as e:
            print(e)
        if not results:
            results = self.latdict.lookup(stem)
        if not transcription:
            try:
                transcription = self.latxform.transcribe(stem)
            except Exception as e:
                # print(e)
                pprint("Error in transcribe:")
                pprint(e)
                pass
        if transcription:
            transcription = transcription[1:-1]

        merged_lines = " ".join(results.splitlines(keepends=False))
        parts = re.sub(r'\s+', ' ', merged_lines)
        l_lines = []
        if parts:
            l_lines = [ parts ]
        
        return LatinQueryResult(
            headword=stem,
            ipa=transcription,
            lewis_1890_lines=l_lines,
        )
