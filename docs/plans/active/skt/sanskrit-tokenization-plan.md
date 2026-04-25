# Sanskrit Tokenization Plan

## Goal
Create a tokenizer that properly handles compound words for classical language study tools.

## Input Example
"dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"

## Processing Steps
1. Split on whitespace
2. Detect hyphenated compounds
3. Split compounds into components
4. Prepare for dictionary lookup

## Components to Build
- CompoundSplitter: Handles hyphenated terms
- SanskritTokenizer: Main processing class
- Data models: Token, TokenComponent, TokenizedPassage

## Implementation Phases
1. Basic tokenization and compound splitting
2. Integration with Heritage Platform
3. Educational features and CLI

## Success Criteria
- Process example in <100ms
- 100% compound splitting accuracy
- Component-level lookup capability
