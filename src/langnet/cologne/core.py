from rich.pretty import pprint

# pprint("Loading indic transliteration")

# import pycdsl
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

from indic_transliteration.detect import detect

# pprint("Loading indic transliteration: OK")

from pydantic import BaseModel, Field


class SanskritDictionaryEntry(BaseModel):
    subid: str | None = Field(default=None)
    id: str
    meaning: str


class SanskritDictionaryLookup(BaseModel):
    term: str
    iast: str
    hk: str
    entries: list[SanskritDictionaryEntry]


class CologneSanskritQueryResult(BaseModel):
    mw: list[SanskritDictionaryLookup]
    ap90: list[SanskritDictionaryLookup]


class SanskritCologneLexicon:
    def __init__(self):
        # TODO:
        # this blows up if you don't have an internet connection or cologne is not online...

        # pprint("About to setup CDSL")
        # self.CDSL: pycdsl.CDSLCorpus = pycdsl.CDSLCorpus()
        # self.CDSL.setup()
        # pprint("Setup CDSL: sanskrit feature DISABLED (hangs on load when no route!)")

        # Sanskrit-English
        # self.mw: pycdsl.CDSLDict = self.CDSL["MW"]
        # self.ap90: pycdsl.CDSLDict = self.CDSL["AP90"]
        #
        # English-Sanskrit
        # self.mwe: pycdsl.CDSLDict = self.CDSL["MWE"]
        # self.ae: pycdsl.CDSLDict = self.CDSL["AE"]

        # print()

        # top_terms = self.mw.stats(top=1024 * 8)

        # for term in top_terms["top"]:
        #     (k, v) = term
        #     it = transliterate(k, sanscript.DEVANAGARI, sanscript.ITRANS)
        #     print(SCHEMES[sanscript.OPTITRANS].to_lay_indian(it))

        pass

    def transliterate(self, data):
        mode = detect(data)
        # print("using mode", mode)
        return transliterate(data, mode, sanscript.DEVANAGARI)

    # def serialize_results(self, results: list[pycdsl.lexicon.Entry]):
    #     # need to group results by ID
    #     # rule: if lexicon id contains a dot group on LHS
    #     xs = [
    #         dict(
    #             id=result.id,
    #             key=result.key,
    #             # iast=transliterate(result.key, sanscript.DEVANAGARI, sanscript.IAST),
    #             meaning=result.meaning(),
    #         )
    #         for result in results
    #     ]
    #     # xs.sort()
    #     xs = sorted(xs, key=lambda x: x["key"])
    #     results = dict()
    #     for x in xs:
    #         k = x["key"]
    #         existing = results.get(k, [])
    #         id = str(x["id"])
    #         subid = None
    #         id_parts = id.split(".")
    #         parts_len = len(id_parts)
    #         if parts_len == 1:
    #             pass
    #         elif parts_len == 2:
    #             id = id_parts[0]
    #             subid = id_parts[1]
    #         else:
    #             print("Unexpected CDSL id length:", x)
    #         del x["key"]
    #         x["id"] = id
    #         x["subid"] = subid
    #         existing.append(x)
    #         results[k] = existing
    #     result_xs = []
    #     for k, vs in results.items():
    #         r = dict(
    #             term=k,
    #             iast=transliterate(k, sanscript.DEVANAGARI, sanscript.IAST),
    #             hk=transliterate(k, sanscript.DEVANAGARI, sanscript.HK),
    #             entries=vs,
    #         )
    #         result_xs.append(r)
    #     return result_xs

    def lookup_ascii(self, data) -> CologneSanskritQueryResult:
        devengari = self.transliterate(data)
        placeholder = SanskritDictionaryLookup(
            term=data,
            iast=data,
            hk=data,
            entries=[
                SanskritDictionaryEntry(
                    id="placeholder",
                    meaning=f"CDSL integration pending - searched for: {devengari}",
                )
            ],
        )
        return CologneSanskritQueryResult(mw=[placeholder], ap90=[placeholder])
