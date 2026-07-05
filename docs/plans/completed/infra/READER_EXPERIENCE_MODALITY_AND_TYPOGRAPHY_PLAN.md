# Reader Experience Modality And Typography Plan

> **Purpose:** Define the experience target for Project Orion's reader UI so typography, discovery, apparatus, and provenance serve a new modality of classical reading rather than a basic lexicon.

## Experience Thesis

Project Orion should feel like a humanist memory theatre for classical texts:
serious, academic, poetic, source-grounded, and visually alive. The reader is
not merely a lookup tool. It is a keyed encounter with works, witnesses,
citations, forms, names, and traditions.

Useful reference points:

- Virgilian gravity: lucid, ordered, sonorous.
- Austenian precision: restrained wit, exact social/intellectual placement.
- Rabelais and `Pantagruel`: abundant learning, comic vitality, encyclopedic appetite.
- `Hypnerotomachia Poliphili`: visual-textual ceremony, architectural language, ornament as memory.
- Bruno's `ars memoriae`: keyed images, places, emblems, traversal, recall.
- Mary Carruthers: reading as memory craft, not passive consumption.
- Tufte: dense evidence, disciplined hierarchy, data ink over chrome.

## What We Have

- Manuscript and vespers themes with serious color direction.
- Noto Serif and Noto Serif Devanagari loading.
- A reader passage surface with citation gutter, token selection, transliteration, page navigation, source details, and apparatus tabs.
- Work dossiers, traditional structure, provenance chips, source-index, and Library watchlist integration.
- Quality discipline around source manifests, source-index provenance, and staged/imported status.

## What We Ought To Have

- A named typography policy for primary text, citation, apparatus, source witness, transliteration, and OCR-quality text.
- A stronger sense that every work is a keyed object: author, title, source witness, citation shape, and tradition are visible before lexical lookup.
- Discovery language that invites entering a library, consulting shelves, tracing phrases, and opening witnesses.
- Apparatus notes that feel scholarly rather than generic.
- Ornament and motion that help memory and delight without hiding evidence.
- Clear difference between:
  - imported readable works
  - staged/non-importable evidence
  - source-decision targets
  - watchlist/acquisition desire

## Tone Policy

Use language that is:

- academic but not sterile
- serious but not lifeless
- poetic but not vague
- source-grounded before interpretive
- classical in register without fake archaism

Preferred terms:

- `work`, `witness`, `passage`, `apparatus`, `source`, `division`, `citation`, `shelf`, `memory key`, `provenance`, `reader desk`

Avoid where possible:

- generic SaaS labels like `item`, `result`, `data card`, `content`, `resource`
- over-promising generated interpretation
- hiding uncertainty behind polished copy

## Typography Policy

Primary text:

- serif reader face
- narrow measure, roughly 58-66 characters
- generous leading for Greek, Sanskrit, and dense scholastic Latin
- visible but quiet citation gutter
- no paragraph-sized wall of UI chrome around the text

Citation and structure:

- small-caps or inscriptional labels
- enough contrast to scan, not enough to dominate
- stable citation strings over decorative titles

Apparatus:

- compact
- source-first
- clear distinction between source text, transliteration, generated notes, and provenance

OCR and uncertain sources:

- never present machine text as clean text without quality labels
- provenance and uncertainty belong in the visual hierarchy, not buried in raw IDs

## Ornament Design Rubric

The ornament system should be judged against a medieval draughtsman standard, not a generic icon standard.

Primary reference logic:

- Villard de Honnecourt: model-book geometry, visible construction, measured animals, architectural drafting, and practical diagram logic.
- French Arthurian manuscript illumination: lively marginal creatures, wildness at the edge of the page, heraldic and narrative clarity.
- Eusebian canon tables and frontispieces: proportional columns, arches, bounded architectural frames, tabular legibility.
- Inhabited initials: letters as constructed spaces where vines, heads, faces, beasts, or rubric points belong to the letter body.

Quality criteria:

- `construction`: the form has visible or recoverable axes, arcs, triangles, circles, or column grids.
- `silhouette`: the object reads at thumbnail size before color, animation, or explanatory copy helps it.
- `register`: linework feels like manuscript drawing or rubricated draft, not rounded SaaS illustration.
- `integration`: ornament grows from the letter/table/creature geometry rather than floating beside it.
- `boundedness`: the artboard is architecturally contained and never spills across unrelated UI.
- `delight`: the book pet may be cute, strange, or monster-like, but it must remain legible as an intentional creature.

Review process:

- Use `/ornament-zoo` as the review sheet, but measure screenshots against this rubric.
- Do not ask for screenshot feedback until the implementation has a stated target for each criterion.
- Treat screenshot feedback as evidence for which criterion failed, not as the design source itself.
- If an ornament reads as a rounded vector icon with manuscript decoration pasted onto it, stop incremental tweaking and reset the visual grammar: ink-first contour, subordinate construction lines, sparse wash, thinner detail strokes, and smaller bounded presentation.

## UI Changes In This Pass

- Add reader modality design plan.
- Add global reader typography tokens for measure, leading, citation gutter, and ornament colors.
- Improve reader leaf typography and language-sensitive rhythm.
- Add a restrained animated book-pet ornament as a mnemonic/illuminated-manuscript cue.
- Reframe source/transliteration as apparatus.
- Tune discovery choices toward shelves, authors, and phrase tracing as library acts.
- Tune work list rows toward keyed works: witness-ready title, author, tradition chips, and provenance-minded affordance.
- Add a work-opening threshold card so selected works are entered through witness, citation, and tradition before lookup.
- Add visible source/work quality badges in the reader desk header.
- Reframe selected-word lookup as marginalia so lexical study stays subordinate to the passage.
- Add Library work and author entries as threshold pages: readers inspect canonical keys, witnesses, divisions, and author shelves before entering the reader desk.
- Retarget Library row navigation toward localized `Work entry` and `Author entry` labels, with direct reading preserved as a secondary action.
- Keep user-facing navigation copy in `uiCopy`; avoid route/internal terms such as `portal` in visible product language.
- Hide deprecated CTS-style work refs, raw source IDs, and trash internal IDs from primary labels. Surface deterministic reader keys plus current canonical public IDs where available; retain raw IDs only as backend/provenance implementation details.
- Replace the local CSS-only book pet with a reusable inline-SVG illuminated sprite system.
- Add three manuscript ornament motifs:
  - `beast`: intelligible illuminated marginal creature for reader leaves and empty reader states.
  - `canonArch`: Eusebian canon-table arcade for work-entry thresholds.
  - `vineInitial`: memory-key initial with Villard sketch-line energy for author entries and work-entry cards.
- Remove the external animation-runtime path from the webapp and keep manuscript ornamentation repo-native.
- Treat `IlluminatedSprite.svelte` as the first-class DIY ornament engine.
- Borrow maintainability lessons from Lottie and Snap without adopting their runtime dependency model:
  - use small named artboards and semantic variants (`beast`, `canonArch`, `vineInitial`);
  - animate named layers with scoped keyframes rather than anonymous decorative loops;
  - prefer SVG path drawing, transform-origin choreography, and palette variables over canvas-only rendering;
  - keep every ornament inspectable, diffable, source-controlled, and easy to tune with ordinary Svelte/CSS;
  - respect `prefers-reduced-motion` so ornament remains subordinate to reading.
- Apply platform-backed SVG animation practices:
  - use CSS/SVG `transform-origin` with explicit transform boxes for reliable layer pivots;
  - use `stroke-dasharray`/`stroke-dashoffset` path reveals for rubric, script, vine, and arcade tracing;
  - encode animation contracts as named classes/layers so future art changes remain testable in source;
  - keep reduced-motion behavior in CSS, not in a runtime wrapper.
- The visible custom motifs now carry the intended influence directly:
  - Illuminated marginal beast with readable head, snout, ear, body, legs, paws, tail, eye, ornament, and gentle spirit-like motion.
  - Eusebian canon-table arcade with columns, arches, tabular rubric lines, and gold tracing.
  - Villard/Hypnerotomachia-style vine initial with sketch-line leaves, rubric endpoints, and memory-key function.
- Ornament quality bar:
  - show visible model-book construction logic inspired by Villard de Honnecourt: axes, arcs, triangles, measured bowls, and architectural scaffolds;
  - preserve cute book-pet readability without collapsing into generic rounded iconography;
  - make every ornament pass at thumbnail size before judging large presentation;
  - keep canon-table forms architectural and bounded rather than decorative overlays;
  - integrate leaves, rubric marks, and inhabited details into the letter or creature geometry rather than pasting them on afterward.
- The current DIY pass adds parchment flecks, marginal threadwork, canon-script strokes, initial highlights, staggered layer timelines, and explicit artboard metadata.
- This DIY direction avoids depending on opaque binary animation assets for the core reader experience.
- Reader performance close-out note: a stale `lang=grc` URL can open a Latin work and force the reader through a slow mismatched route. Work metadata now canonicalizes the active language, structure/dossier loads no longer block passage loading, and the immediate passage window is smaller by default. Remaining performance work should focus on the server-side `contents` retrieval path.

## Future Concrete Changes

- Add an explicit reader typography settings panel: measure, size, leading, theme, and transliteration mode.
- Add source-quality badges directly in the reader header for imported/staged/OCR/uncertain witness status.
- Add memory-key cards for named persons, works, places, and terms, backed by Suda/reference or source-index rows.
- Add marginalia mode: selected word plus local passage, morphology, and source witness in a stable side note.
- Add work-opening ceremony: title, author, tradition, citation shape, source witness, then passage.
- Extend work and author entry pages with cast-of-characters coverage so figures named in the UI resolve to imported reader works, reference entries, or acquisition watchlist targets.
- Run a thorough localization pass over reader/library copy so headings, labels, empty states, error states, and action text are all sourced from the localization layer and reviewed for academic, concise, source-grounded tone.
- Add visual distinction for machine OCR text versus reviewed electronic text.
- Add route-aware ornament semantics: different shelves, traditions, or cast-of-characters figures can eventually select different manuscript pets, initials, or canon-table emblems.

## Non-Goals

- Do not add decorative motion that obscures text or slows reading.
- Do not make the reader depend on a canvas/SVG library until a concrete interaction needs it.
- Do not let the UI imply acquisition or source certainty that the manifest does not support.
