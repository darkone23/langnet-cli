# Learning UI North Star

This document is the product design anchor for wiring LangNet's grammar
learning overlay into the SvelteKit web app. It narrows the broader pedagogy
docs into the first usable browser experience.

## North Star

The web UI should help a learner answer one question first:

> What is this form doing here?

The answer should start from the word in front of the reader, then bridge into
traditional grammar and source evidence:

1. observed form and source-backed morphology;
2. Foster functional gateway;
3. traditional Greek, Latin, and Sanskrit terms;
4. short learner action;
5. source/evidence links and caveats.

The UI should not become a grammar dashboard. The dictionary entry remains the
center of the page. Learning material sits near the existing Forms panel and
explains the current encounter.

## Primary User Flow

1. A learner searches one word or arrives from the Reader Desk with a selected
   passage word.
2. The encounter results load dictionary evidence and form readings.
3. The Forms area shows the best source-backed readings.
4. A compact "Learn this form" layer explains the selected or first visible
   reading.
5. Loaded form tables begin with a small table-reading gateway before the slots.
6. The learner can expand into source-backed details, load a form table, or jump
   to source references.

This keeps the learning experience local to the encounter instead of sending
the learner to a separate textbook page.

## First Slice

Add a compact learning layer inside the existing Forms panel.

For each visible paradigm candidate, show:

- observed form;
- lemma;
- source/provenance;
- part of speech and paradigm kind;
- native morphology features;
- Foster gateway label;
- native gateway rows from mapped concepts, linking Greek, Latin, and Sanskrit
  terms back to the Foster gateway;
- one learner action when a Foster bridge exists;
- evidence gap note when a concept is work-backed but not segment-backed.

The panel should prefer the current `encounter --include-learning` payload when
available. It should not synthesize learning copy from raw feature labels in the
browser.

When a full morphology table is loaded, add a "Reading a declension table" or
"Reading a conjugation table" gateway before the slot grid. This gateway should
explain the table dimensions in learner terms: case as the word's job in the
expression, number as count, gender as agreement class, person as speaker /
addressee / other, tense as time or verbal frame, mood as mode of statement, and
voice as action relation.

## Display Model

Use three visual tiers:

- **Reading line:** short, always visible. Example: `λόγου -> λόγος, genitive
singular, Possessing Function`.
- **Learning chips:** compact terms and functions. Example: `genitive`,
  `γενική`, `genetivus`, `ṣaṣṭhī vibhakti`, `of-possession`.
- **Details:** expandable source-backed explanation, learner action, source
  refs, and caveats.

The default view should be quiet and scan-friendly. Expanded details are for
learners who ask for more.

## Copy Rules

- Lead with the form's job, not the internal concept ID.
- Keep traditional terms visible beside Foster labels.
- Say "may be" or preserve alternates when the backend returns ambiguity.
- Show aggregate Foster bundles as related bundles, not promoted facts.
- Use caveats for missing evidence instead of smoothing over gaps.
- Avoid explaining the whole grammar system inside each result card.

## Source And Evidence Behavior

Every learning claim should come from one of these sources:

- source-backed morphology in the encounter candidate;
- a stable grammar concept from `learn concept`;
- a reviewed Foster bridge from `learn foster-bridge`;
- an explicit caveat from `learn doctor` or encounter `evidence_gaps`.

Foster `page:*` and `toc:*` references are currently actionable but not embedded
snippets. In the first UI slice, render them as quiet source links/actions. Do
not present them as quoted proof until the server can resolve them into local
snippets.

## Backend Contract

The SvelteKit adapter should request learning overlays from the CLI:

```txt
langnet-cli encounter <language> <query> <tool-filter> \
  --include-paradigm-resolution \
  --include-learning \
  --output json
```

The UI should consume:

- `paradigm_resolution.candidates[]`;
- candidate `learning_overlay.concepts[]`;
- concept `foster_gateway`;
- concept `traditional`;
- concept `native_gateways`;
- concept `foster_bridges[]`;
- bridge `learner_action`, `morphology_predicates`, `summary_refs`, and
  `caveats`;
- concept `source_evidence`;
- candidate `evidence_gaps`;
- compact bridge records from `learn foster-bridge --view compact` when a
  separate bridge lookup becomes useful.

Current implementation status: `src/lib/server/langnet-cli.ts` requests both
`--include-paradigm-resolution` and `--include-learning`, and the web payload
types preserve candidate `learning_overlay` data for the Forms panel.

Before UI work, `learn doctor --output json` should be the readiness check. The
expected current state is `ok: true` with warnings for:

- `process.declension` lacking exact segment evidence;
- Foster source refs being actionable but not embedded snippets.

These warnings are not blockers, but the UI must display them honestly when they
affect the current form.

## Layout Placement

Place learning content in the main result column:

1. search form;
2. loading/error state;
3. Forms panel with "Learn this form";
4. component entries when present;
5. dictionary result groups;
6. word-index/sidebar context.

Do not move the learning layer into the sidebar. The learner should see grammar
while looking at the word and dictionary evidence.

## Interaction States

The first UI slice should cover:

- no morphology: hide the learning layer and keep dictionary results primary;
- one clear reading: show the learning layer expanded enough to be useful;
- multiple readings: show one compact learning row per visible candidate;
- additional or unresolved readings: keep them quiet behind the first visible
  slice, matching current Forms behavior;
- missing evidence: show a short caveat such as `Needs exact source passage`;
- aggregate bridge: show `related Foster bundle`, not a single case claim.

## Non-Goals For The First Slice

- Passage-level sentence annotation.
- Practice drills or writing prompts.
- Full grammar-source reader embedded in the result card.
- Generated explanations not backed by current CLI payloads.
- A separate grammar dashboard route.

## Later Slices

After the first Forms integration:

1. Resolve Foster `page:*` and `toc:*` refs into local snippets/actions.
2. Add a grammar-source drawer that opens exact reader segments when available.
3. Add sentence-mode annotations in the Reader Desk for selected passages.
4. Add small practice prompts from the same concept IDs.
5. Add dictionary-entry parsing as another source of morphology and process
   evidence.

## Immediate Build Queue

1. Improve the first "Learn this form" and table-reading blocks after live
   visual review.
2. Add browser-level regression tests for a visible candidate with
   `case.genitive`, native gateways, and the `of-possession` Foster bridge.
3. Add browser-level regression tests for a visible candidate with
   an aggregate Foster bridge such as `by-with-from-in`.
4. Add a source-reference endpoint for Foster `page:*` and `toc:*` actions.
5. Resolve bridge/source examples into snippets when the server has a source
   reference endpoint.
6. Run `cd webapp && just verify` after each UI slice.

## Acceptance Checks

- `λόγου`, `puellae`, and `putrāṇām` can show a Foster gateway plus traditional
  grammar names when the backend supplies morphology.
- Ambiguous forms preserve multiple readings instead of forcing one explanation.
- Ambiguous Heritage analysis strings such as `m. sg. voc. | n. sg. voc.`
  remain separate readings and should be displayed as ambiguous, not as one
  high-confidence collapsed form.
- The web adapter includes `--include-learning` when asking for encounters.
- Learning rows use the same concept IDs exposed by CLI JSON.
- Aggregate candidates such as `by-with-from-in` are displayed as related
  bundles.
- `learn doctor --output json` remains the UI-readiness gate before changing
  the learning surface.
