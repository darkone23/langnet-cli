# CITATIONS

langnet-cli is a derived work that synthesizes classical language resources from multiple projects and digital libraries. This document acknowledges the scholars, projects, and institutions whose work makes this software possible.

## Lectori Benevolo

This project stands on the shoulders of giants. The tools and data it aggregates represent decades of scholarly work by academics, volunteers, and institutions committed to preserving and sharing access to classical texts.

We offer our sincere thanks to the maintainers, contributors, and institutions behind these resources.

## Software Tools

### Classical Language Toolkit (CLTK)

**Repository**: https://github.com/cltk/cltk

The CLTK is the foundation for computational work with pre-modern languages. It provides essential NLP tools for lemmatization, tokenization, and morphological analysis.

**License**: MIT

**Citation**:

> Johnson, Kyle P., Patrick J. Burns, John Stewart, Todd Cook, Clément Besnier, and William J. B. Mattingly. "The Classical Language Toolkit: An NLP Framework for Pre-Modern Languages." In *Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics and the 11th International Joint Conference on Natural Language Processing: System Demonstrations*, pp. 20-29. 2021. https://doi.org/10.18653/v1/2021.acl-demo.3

**BibTeX**:
```bibtex
@article{johnson-etal-2021-classical,
    title = "The {C}lassical {L}anguage {T}oolkit: {A}n {NLP} Framework for Pre-Modern Languages",
    author = "Johnson, Kyle P. and Burns, Patrick J. and Stewart, John and Cook, Todd and Besnier, Clément and Mattingly, William J. B.",
    booktitle = "Proceedings of the 59th Annual Meeting of the ACL and the 11th International Joint Conference on NLP: System Demonstrations",
    month = aug,
    year = "2021",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2021.acl-demo.3",
    doi = "10.18653/v1/2021.acl-demo.3",
    pages = "20--29",
}
```

### CLTK Model Credits

CLTK's effectiveness depends on models and resources contributed by research groups:

**Greek (OdyCy)**: Center for Humanities Computing Aarhus
- Model: https://huggingface.co/chcaa
- Citation: https://aclanthology.org/2023.latechclfl-1.14

**Latin (NLPL Word Vectors)**: NLPL Working Group, University of Oslo
- Model: http://vectors.nlpl.eu/
- Citation: https://aclanthology.org/W17-0237

### Diogenes

**Repository**: https://github.com/pjheslin/diogenes
**Website**: https://d.iogen.es/

Diogenes, maintained by Peter Heslin, provides programmatic access to the Perseus Digital Library's lexicon and morphology tools. It is a remarkable resource for classical scholars.

**License**: GPL v3

### Whitaker's Words

**Repository**: https://github.com/darkone23/whitakers-words
**Mirror**: https://github.com/mk270/whitakers-words
**Original**: https://web.archive.org/web/20170708174611/https://archives.nd.edu/words.htm#1 (archived from Notre Dame)

William A. Whitaker (1936-2010) created this Latin morphological analyzer while at the University of Notre Dame. His generous permission to use and distribute his work freely has enabled decades of scholarship.

**License**: Permissive (free for any and all use)

> "This is a free program, which means it is proper to copy it and pass it on to your friends... Permission is hereby freely given for any and all use of program and data." — William A. Whitaker

### spaCy

**Repository**: https://github.com/explosion/spaCy

Used within CLTK for Latin NLP pipelines.

**License**: MIT

## Lexical Resources

The dictionaries and lexica integrated into langnet represent centuries of scholarly effort:

### Perseus Digital Library (LSJ & Lewis & Short)

**Greek**: *A Greek-English Lexicon* (Liddell-Scott-Jones, 9th ed., 1940)
- Public domain in the United States
- Digitized by the Perseus Project under Gregory Crane's leadership

**Latin**: *A Latin Dictionary* (Lewis & Short, 1879)
- Public domain in the United States
- Digitized by the Perseus Project

These foundational reference works continue to serve scholars worldwide through digitization efforts.

### Cologne Digital Sanskrit Lexicon (CDSL)

**Provider**: Universität zu Köln  
**Website**: https://www.sanskrit-lexicon.uni-koeln.de/

Cologne University's digitization of Sanskrit dictionaries provides invaluable resources for Indic studies:

- **MW**: *A Sanskrit-English Dictionary* (Monier-Williams, 1899)
- **AP90**: *The Practical Sanskrit-English Dictionary* (Apte, 1957-1959)

### indic-transliteration

**Repository**: https://github.com/ketanmalik/indic-transliteration

Python library for Sanskrit transliteration schemes (HK, IAST, Devanagari, etc.).

**License**: MIT

## Data Sources Summary

| Source | Language | Content | Notes |
|--------|----------|---------|-------|
| CLTK models | Latin/Greek/Sanskrit | NLP models, lemmatizers | MIT license |
| OdyCy (chcaa) | Greek | spaCy pipeline model | CC BY-SA 4.0 |
| NLPL (Oslo) | Latin | Word embeddings | CC BY-SA 4.0 |
| Perseus/LSJ | Greek | Dictionary entries | Public domain |
| Perseus/L&S | Latin | Dictionary entries | Public domain |
| CDSL/MW | Sanskrit | Dictionary entries | Research use |
| CDSL/AP90 | Sanskrit | Dictionary entries | Research use |

## Academic Attribution

When publishing research that uses langnet, please cite:

1. **CLTK**: Johnson et al. 2021 (https://aclanthology.org/2021.acl-demo.3)
2. **Greek NLP**: OdyCy by CHC Aarhus (https://aclanthology.org/2023.latechclfl-1.14)
3. **Latin embeddings**: NLPL (University of Oslo) (https://aclanthology.org/W17-0237)
4. Specific lexical resources used (LSJ, Lewis & Short, Monier-Williams)

**Suggested text for lexicon attributions**:

> "Greek dictionary data from the Liddell-Scott-Jones lexicon, digitized by the Perseus Digital Library (https://www.perseus.tufts.edu)."

> "Latin dictionary data from Lewis and Short's A Latin Dictionary (1879), digitized by the Perseus Project."

> "Greek NLP pipeline by the Center for Humanities Computing Aarhus (https://huggingface.co/chcaa)."

> "Latin word embeddings from the NLPL Working Group, University of Oslo (http://vectors.nlpl.eu/)."

## Contributing to Upstream

If you find errors in the lexical data embedded in these resources, please consider contributing to the upstream projects:

- [Perseus/Logeion](https://github.com/PerseusDL/lexica) for dictionary corrections
- [CLTK](https://github.com/cltk/cltk) for NLP model improvements
- [Whitaker's Words](https://github.com/darkone23/whitakers-words) for Latin morphology updates

## A Note to the Reader

Classical studies thrive through collaboration and the generous sharing of knowledge across centuries. The digitization of ancient texts, the development of morphological analyzers, and the creation of NLP tools all represent immense labor by scholars committed to preserving our shared cultural heritage.

This project exists because others chose to share their work freely. May it contribute, in turn, to the ongoing conversation about classical languages and texts.
