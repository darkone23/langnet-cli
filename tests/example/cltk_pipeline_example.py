import time

# from packaging import version
# import contextlib
from cltk import NLP
from cltk.dependency.tree import DependencyTree
from cltk.languages.example_texts import get_example_text
from cltk.languages.pipelines import GreekPipeline, SanskritPipeline


class PipelineExample:
    """
    adapted from [demo pipelines notebook](https://github.com/cltk/cltk/blob/master/notebooks/Demo%20of%20Pipeline%20for%20all%20languages.ipynb)
    """

    @staticmethod
    def main():
        # print("CLTK pipelines currently not functional...")
        # print("try to visit https://centre-for-humanities-computing.github.io/odyCy/getting_started.html#")

        iso_to_pipeline = {
            # "akk": AkkadianPipeline,
            # "ang": OldEnglishPipeline,
            # "arb": ArabicPipeline,
            # "arc": AramaicPipeline,
            # "chu": OCSPipeline,
            # "cop": CopticPipeline,
            # "enm": MiddleEnglishPipeline,
            # "frm": MiddleFrenchPipeline,
            # "fro": OldFrenchPipeline,
            # "gmh": MiddleHighGermanPipeline,
            # "got": GothicPipeline,
            "grc": GreekPipeline,
            # "hin": HindiPipeline,
            # latin pipeline broken with latest torch defaults (stanza and weights_only)
            # https://github.com/cltk/cltk/issues/1274
            # "lat": LatinPipeline,  # this pipeline is currently quite slow
            # "lzh": ChinesePipeline,
            # "non": OldNorsePipeline,
            # "pan": PanjabiPipeline,
            # "pli": PaliPipeline,
            "san": SanskritPipeline,
        }
        for lang, pipeline in iso_to_pipeline.items():
            start = time.monotonic()
            print(f"{pipeline.language.name} ('{pipeline.language.iso_639_3_code}') ...")
            text = get_example_text(lang)
            print(f"Getting text took {time.monotonic() - start}s")
            start = time.monotonic()
            cltk_nlp = NLP(language=lang)
            cltk_doc = cltk_nlp.analyze(text=text)
            print(f"Running analyze took {time.monotonic() - start}s")
            start = time.monotonic()
            _x_strs = cltk_doc.sentences_strings
            word = cltk_doc.sentences[0][0]
            print("Example `Word`:", word)
            if all([w.features for w in cltk_doc.sentences[0]]):
                print("Printing dependency tree of first sentence ...")
                try:
                    a_tree = DependencyTree.to_tree(cltk_doc.sentences[0])  # type: ignore
                except Exception:
                    print(f"Dependency parsing Process not available for '{lang}'.")
                    print("")
                    continue
                a_tree.print_tree()
            print(f"Getting to tree took {time.monotonic() - start}s")
            print("")


if __name__ == "__main__":
    PipelineExample.main()
    # unittest.main()
