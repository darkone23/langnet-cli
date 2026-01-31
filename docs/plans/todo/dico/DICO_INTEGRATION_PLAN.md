# French DICO Dictionary Integration Plan

@architect "Design bilingual dictionary architecture"

## Overview

Integrate the French DICO dictionary as a secondary lexicon for Sanskrit, providing French definitions alongside Sanskrit headwords. This enables bilingual search and cross-lingual vocabulary building.

## Goals

1. **Extract DICO URLs from Heritage Platform**
   - Heritage's `sktsearch` returns links in Velthuis encoding (e.g., `agnii` for agnī)
   - Parse and decode these URLs to build a DICO reference index

2. **Build DICO Dictionary Backend**
   - Import or scrape DICO dictionary data
   - Create Sanskrit-to-French lookup capability
   - Wire to `LanguageEngine` alongside existing Heritage/CDSL backends

3. **Bilingual Search Enhancement**
   - Allow queries in French to find Sanskrit terms
   - Return French definitions in `SanskritQueryResult`
   - Support cross-lexicon etymology ("French 'feu' → Sanskrit 'agni'?")

## Technical Considerations

- DICO data format (XML, JSON, HTML scrape?)
- Velthuis decoding for URL parsing
- Schema design for bilingual entries
- Caching strategy for DICO lookups
- Integration with existing normalization pipeline

## Phases

1. **Phase 1: URL Extraction** - Parse DICO links from Heritage responses
2. **Phase 2: Data Import** - Ingest DICO dictionary into local storage
3. **Phase 3: API Integration** - Add DICO backend to `LanguageEngine`
4. **Phase 4: Bilingual UX** - French search and cross-language results