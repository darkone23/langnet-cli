# TODO

## Roadmap: Future Work

### Dictionary Entry Parsers

Improve parsing of dictionary entries across all data sources into structured, searchable formats:

- **Lewis Latin Parser**: Parse CLTK's `LatinLewisLexicon.lookup()` raw text into structured `LewisEntry` dataclass
  - [ ] Analyze Lewis entry format: headword, part of speech, etymology, definitions, word family, citations
  - [ ] Create `LewisEntry` model with robust handling of edge cases
  - [ ] Wire parsed output to `LatinQueryResult`
  - [ ] Add comprehensive test coverage

- **CDSL Entry Enhancements**: Improve Sanskrit dictionary entry parsing
  - [ ] Parse granular sense structures from MW/AP90 entries
  - [ ] Extract citation references (Ṛgveda, etc.) as linked data
  - [ ] Handle variant readings and alternate etymologies
  - [ ] Improve Devanagari/IAST/HK transliteration consistency

- **Diogenes Greek Parser**: Improve Greek lexicon entry structuring
  - [ ] Parse morphological annotations into structured morphology data
  - [ ] Extract semantic relationships between senses
  - [ ] Handle cross-references and citations
  
- **Diogenes Latin Parser**: Improve Greek lexicon entry structuring
  - [ ] Parse morphological annotations into structured morphology data
  - [ ] Extract semantic relationships between senses
  - [ ] Handle cross-references and citations

### CLTK Enhancement

Expand and enhance CLTK integration for Sanskrit and Latin:

- **Sanskrit CLTK**:
  - [ ] Integrate Sanskrit word segmentation (sandhi splitter)
  - [ ] Add Sanskrit morphological analyzer integration (if available in CLTK)
  - [ ] Support for Vedic Sanskrit variants
  - [ ] Enhance IAST transliteration handling

- **Latin CLTK**:
  - [ ] Integrate Latin stemmer/lemmatizer for faster lookups
  - [ ] Add prosody data support (syllable quantities)
  - [ ] Improve Old Latin variant handling
  - [ ] Cross-reference Lewis with other Latin lexica

- **Greek CLTK**:
  - [ ] Evaluate Ancient Greek morphological models beyond spacy
  - [ ] Add Greek prosody and meter information
  - [ ] Support for Homeric Greek specific forms

### CDSL ETL Performance

Optimize Sanskrit dictionary indexing pipeline:

- [ ] **Sharded Database Build**: Implement divide-and-conquer indexing with parallel workers
  - Partition data by alphabet range or hash bucket
  - Build independent shard databases
  - Merge shards with DuckDB ATTACH/COPY

- [ ] **Bulk Loading**: Use DuckDB COPY for faster imports
  - Export parsed data to Parquet format
  - Bulk load via `COPY INTO table FROM file`

- [ ] **Transaction Batching**: Split bulk inserts into smaller commits

### Local Data Storage Layer

Build local knowledge base for derived lexicon data:

- [ ] **Schema Design**: language neutral grammar representation
  - `words`: term, language, headword, IPA, part_of_speech
  - `senses`: word_id, definition, citations, source_lemma
  - `morphology`: word_id, tags, stems, endings
  - `cognates`: word_id, related_word_id, relationship_type, related word language
  - should keep support for language specific grammar terms
- [ ] **Phonetics**: searching and indexing by 'sounds-like'
- [ ] **Fuzzy-finding**: include 'near matches' on miss
  - [ ] Properly integrate diogenes fuzzy logic (currently some dg_matched flag for direct or fuzzy matches)
- [ ] **Precomputed Indexes**: IPA, lemmas, morphological tags for fast search
- [ ] **Cross-lexicon Queries**: Enable etymology research ("find Latin words with Greek cognates")

### Performance & Observability

- [ ] **Async Backends**: Parallel lexicon queries across data sources
- [ ] **Distributed Tracing**: Add correlation IDs for request tracing
- [ ] **Query Profiling**: Track latency breakdown by backend

### Additional Backend

- [ ] Basics of adding sanskrit heritage platform backend
