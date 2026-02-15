# Backend Tool Capabilities (Claim/Witness Expectations)

This document defines what each backend is trusted for and what claims/witness fields we expect it to emit for the semantic distillation pipeline.

## Diogenes (Greek/Latin lexica)
- **Trusted for**: Lexicon senses (LSJ/L&S), CTS citations, entry markers/hierarchy.
- **Not trusted for**: High-fidelity morphology (use Whitaker’s/CLTK), consistent sense IDs (must synthesize `sense_ref`).
- **Expected claims/witnesses**:
  - `source_ref`: synthetic per sense/block (e.g., `lsj:00:02`).
  - Gloss/sense text per marker.
  - Citations: CTS URNs + display text.
  - POS if present in metadata; otherwise optional.

## Whitaker’s Words (Latin morphology)
- **Trusted for**: Morphology parsing; coarse POS and lemma.
- **Not trusted for**: Rich senses/gloss quality; citations.
- **Expected claims/witnesses**:
  - Morphology features (case/number/gender/tense/mood/voice/person).
  - Lemma, POS, foster codes if mapped.
  - `source_ref`: synthetic per analysis if available.

## Heritage Platform (Sanskrit)
- **Trusted for**: Morphology, canonicalization, dictionary senses from Heritage.
- **Not trusted for**: Stable sense IDs; occasional mangled SLP1.
- **Expected claims/witnesses**:
  - Morphology features, lemma/root.
  - Glosses per sense with `source_ref` synthetic if absent.
  - Citations: none (unless provided).

## CDSL (Monier-Williams/AP90 via Cologne)
- **Trusted for**: Dictionary senses with stable entry IDs (MW/AP90).
- **Not trusted for**: Clean glosses without citation noise; register/domain completeness.
- **Expected claims/witnesses**:
  - `source_ref`: stable (e.g., `mw:217497`).
  - Gloss/sense text; strip citation abbreviations.
  - POS/gender when available; domains/register if recoverable.

## CLTK (Latin/Greek morphology/dictionary)
- **Trusted for**: Morphology parsing; basic dictionary glosses (Latin).
- **Not trusted for**: Citation fidelity; rich senses.
- **Expected claims/witnesses**:
  - Morphology features, lemma, POS.
  - Gloss text when present; `source_ref` synthetic.

## Expectations for Claim Emission
- Every adapter should emit claims with:
  - `subject`: lemma or sense_ref.
  - `predicate`: POS, gloss, morphology feature, citation, etc.
  - `value`: predicate value (e.g., “noun”, “fire”, `{case: nom}`).
  - `provenance`: `source`, `source_ref`, timing if available.
  - `citations`: CTS URNs or dictionary refs when present.
- Sense IDs: synthesize stable `sense_ref` when upstream lacks them.
- Provenance is required for any claim shown to users or used in reduction.

## Indexing & Modes Expectations
- Claims/witnesses should be indexable by lemma, source_ref, and predicate to support cacheable lookups.
- Index builds should run via `just` tasks (planned) and avoid re-querying backends when data is unchanged.
- Zoom levels:
  - **research**: return all claims/witnesses/raw facts from the index.
  - **didactic**: return bucketed/curated facts (semantic reduction output) derived from indexed claims.
- Epistemic modes (merge strictness): **open** vs **skeptic** (aka open/closed) should be consistently named when exposed.

---

## Tool Fact Types

Each tool emits canonical fact types with tool-specific fields. These are defined in protobuf schemas under `vendor/langnet-spec/schema/tools/`. See `docs/technical/design/tool-fact-architecture.md` for the full architecture.

### Fact Types by Tool

| Tool | Fact Types | Tool-Specific Fields | Proto File |
|------|------------|---------------------|------------|
| **CDSL** | `CDSLSenseFact`, `CDSLEntryFact` | `sense_lines`, `grammar_refs` | `cdsl_spec.proto` |
| **Diogenes** | `DiogenesMorphFact`, `DiogenesDictFact`, `DiogenesCitationFact` | `reference_id`, `logeion_link`, `is_fuzzy_match`, `entry_id` | `diogenes_spec.proto` |
| **Heritage** | `HeritageMorphFact`, `HeritageDictFact`, `HeritageColorFact` | `color`, `color_meaning`, `compound_role`, `sandhi` | `heritage_spec.proto` |
| **Whitakers** | `WhitakersAnalysisFact`, `WhitakersTermFact` | `term_codes`, `term_facts` | `whitakers_spec.proto` |
| **CLTK** | `CLTKMorphFact`, `CLTKLewisFact` | `principal_parts`, `model_id` | `cltk_spec.proto` |

### Universal Predicates

Tool-specific facts are transformed to universal Claims with these predicates:

| Predicate | Source Facts | Value Fields |
|-----------|-------------|--------------|
| `has_gloss` | CDSLSenseFact, DiogenesDictFact, HeritageDictFact | gloss, domains, register |
| `has_morphology` | DiogenesMorphFact, HeritageMorphFact, WhitakersAnalysisFact, CLTKMorphFact | lemma, pos, features |
| `has_citation` | DiogenesCitationFact | cts_urn, text, author, work |
| `has_etymology` | CDSLEntryFact, HeritageDictFact | root, etymology |

### Provenance Requirements

Every fact must include a `provenance_id` linking to a `ProvenanceRecord` containing:

- `source`: Tool name (cdsl, diogenes, heritage, whitakers, cltk)
- `source_ref`: Tool-specific reference (mw:217497, dg:55038347)
- `request_url`: Full URL that produced the response
- `raw_ref`: Reference to stored raw response (for re-parsing)
- `extracted_at`: Extraction timestamp
- `tool_version`: Adapter version

### Related Documents

- `docs/technical/design/tool-fact-architecture.md` - Two-layer proto architecture
- `docs/technical/design/mermaid/tool-fact-flow.md` - Diagrams
- `docs/plans/active/tool-fact-indexing.md` - Implementation roadmap
