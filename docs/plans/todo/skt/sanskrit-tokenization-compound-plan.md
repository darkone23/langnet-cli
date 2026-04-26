# Sanskrit Tokenization and Compound Plan

**Status:** ⏳ TODO  
**Feature Area:** skt  
**Owner Roles:** @architect for sequencing, @coder for implementation, @auditor for fixture review

## Goal

Improve Sanskrit tokenization and compound handling without bypassing the claim/evidence pipeline.

## Current Position

Sanskrit lookup uses Heritage and CDSL. Word-level claims are now the foundation. Tokenization and compounds should feed that same path.

## Scope

1. Normalize Sanskrit input consistently.
2. Detect likely compounds.
3. Produce candidate component queries.
4. Run components through normal lookup/claim flow.
5. Present component evidence and a cautious compound explanation.

## Out of Scope

- Passage-level syntax.
- Generated explanations without source evidence.
- Broad sandhi search before fixture tests exist.

## First Task

Add a fixture-only tokenizer test for one compound. Expected output should include candidate components and the query forms that would be sent to Heritage/CDSL.
