> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Reader Discovery Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace freeform reader classifier categories/scopes with strict discovery groups and controlled discovery tags that support global popularity and one clear peer-relative popularity score.

**Architecture:** The generated classifier will output one primary `classification_discovery_group_id` and zero or more strict `classification_discovery_tags`. Existing `classification_category`, `classification_scope`, `classification_popularity_score`, and `classification_scope_popularity_score` remain compatibility fields derived from the new model until callers migrate.

**Tech Stack:** Python dataclasses, DuckDB catalog tables, CSV import/export, Click CLI, JSON model prompts, pytest through `just`.

---

## User Contract

The reader metadata should optimize for discoverability, not taxonomy theory. Users should be able to ask for "popular ayurvedic texts", "popular Greek medical texts", "Latin grammar by popularity", or "famous works overall" without choosing between genre/domain/tradition/form fields.

The catalog therefore exposes:

- `classification_discovery_group_id`: one required peer bucket used for group-relative popularity.
- `classification_discovery_tags`: strict pipe-delimited tag IDs used for faceted discovery.
- `classification_global_popularity_score`: 0-100 popularity within the language corpus.
- `classification_global_popularity_tier`: one of `canonical`, `major`, `common`, `specialist`, `obscure`.
- `classification_group_popularity_score`: 0-100 popularity within `classification_discovery_group_id`.
- `classification_group_popularity_tier`: one of `canonical`, `major`, `common`, `specialist`, `obscure`.

The CSV stores tags as pipe-delimited snake-case IDs, such as:

```csv
classification_discovery_group_id,classification_discovery_tags
medicine,medicine|ayurveda|technical
epic,epic|itihasa|mahabharata
rhetoric,rhetoric|speech|oratory
```

The model exchange may use JSON arrays for tags, but generated CSV and DuckDB storage use the pipe-delimited form.

## Taxonomy Principles

- Use plain English discovery denominators: `medicine`, `ethics`, `law`, `grammar`, `rhetoric`, `philosophy`, `astronomy`, `mathematics`, `epic`, `drama`.
- Use tradition tags for precision: `ayurveda`, `dharmashastra`, `vyakarana`, `patristics`, `roman_law`, `hippocratic_galenic_medicine`.
- Keep only one peer bucket for popularity: `classification_discovery_group_id`.
- Treat `classification_discovery_tags` as strict controlled IDs, never freeform generated labels.
- Do not create hyper-specific tags unless they split a recurring and useful discovery set.
- Keep legacy fields as derived compatibility output while the CLI and catalog UI migrate.

## Controlled Discovery Groups

Each work receives exactly one group. This is the group used by `classification_group_popularity_score`.

| ID | Description |
| --- | --- |
| `epic` | Epic and large-scale heroic narrative traditions. |
| `drama` | Performed or performable dramatic works, including tragedy and comedy. |
| `poetry` | Verse works whose primary discovery identity is poetic rather than epic, drama, or hymn. |
| `hymn` | Hymnic, praise, devotional, or liturgical verse. |
| `narrative` | Prose or mixed narrative works such as novels, tales, romances, and story collections. |
| `history` | Historical narrative, chronography, antiquarian history, and related historical prose. |
| `biography` | Lives, memoir-like works, hagiography, and biographical collections. |
| `rhetoric` | Speeches, oratory, rhetorical handbooks, declamation, and rhetorical education. |
| `grammar` | Grammar, linguistic analysis, philology, and language instruction. |
| `lexicography` | Dictionaries, glossaries, word lists, synonymics, and lexical reference works. |
| `philosophy` | Philosophical works whose primary discovery identity is metaphysics, logic, epistemology, cosmology, or system-building. |
| `ethics` | Works about conduct, duty, moral order, discipline, virtue, social obligation, or how one ought to live. |
| `law` | Juridical works whose primary discovery identity is law, courts, codes, legal procedure, or legal interpretation. |
| `medicine` | Medical, surgical, pharmacological, diagnostic, and health-related works. |
| `religion` | Theology, scripture, exegesis, devotional doctrine, and religious instruction not better grouped as hymn, ritual, philosophy, or ethics. |
| `ritual` | Works whose primary identity is ritual procedure, liturgy, sacrifice, rite, or ceremonial practice. |
| `poetics` | Literary theory, metrics, aesthetics, dramaturgy, and criticism. |
| `astronomy` | Astronomy, calendrics, celestial computation, and astronomical theory. |
| `astrology` | Astrology, horoscopy, and astral divination. |
| `mathematics` | Mathematics, geometry, arithmetic, and mathematical exposition not primarily astronomical. |
| `science` | Natural history, mechanics, optics, geography, agriculture, and technical science not covered by medicine, astronomy, or mathematics. |
| `technical` | Manuals and technical treatises whose field is known but not one of the more specific groups. |
| `commentary` | Commentaries and scholia whose primary discovery identity is their commentary function rather than a subject field. |
| `letter` | Letters and epistolary collections. |
| `inscription` | Inscriptions and epigraphic texts. |
| `fragmentary` | Fragmentary or excerpted works whose recoverable peer group is not known. |
| `anthology` | Anthologies, miscellanies, collections, and compendia whose contents cross groups. |
| `other` | Use only when no clearer controlled group applies. |
| `uncertain` | Use when the row has insufficient evidence for a reliable group. |

## Controlled Discovery Tags

Tags are optional, strict, and may include both broad and tradition-specific facets. The implementation should start with these IDs and add more only when a recurring catalog need is observed.

| ID | Description |
| --- | --- |
| `ayurveda` | Sanskrit medical tradition. |
| `dharmashastra` | Sanskrit dharma, conduct, duty, penance, social order, and related juridical material. |
| `dharmasutra` | Dharmasutra literature. |
| `arthashastra` | Statecraft, polity, administration, economics, and political power. |
| `kamashastra` | Erotics, pleasure, and the science of kāma. |
| `rasashastra` | Alchemy, iatrochemistry, mineral and metallurgical medicine. |
| `ratnashastra` | Gemological and jewel-science literature. |
| `vyakarana` | Sanskrit grammatical tradition. |
| `paniniya` | Paninian grammatical tradition. |
| `nirukta` | Vedic etymology and semantic explanation. |
| `kosha` | Sanskrit lexicon, thesaurus, glossary, or word-list tradition. |
| `nighantu` | Nighantu lexical or medicinal glossary tradition. |
| `kavya` | Sanskrit ornate/literary poetry and prose. |
| `katha` | Sanskrit story, tale, and narrative-prose tradition. |
| `natya` | Sanskrit drama, dramaturgy, and performance theory. |
| `alamkarashastra` | Sanskrit poetics and figures-of-speech tradition. |
| `sahityashastra` | Sanskrit literary theory tradition. |
| `itihasa` | Sanskrit epic/historical narrative tradition, especially Mahābhārata and Rāmāyaṇa materials. |
| `mahabharata` | Mahābhārata or directly related works. |
| `ramayana` | Rāmāyaṇa or directly related works. |
| `purana` | Purāṇic literature. |
| `vedic` | Vedic period or Vedic-tradition material. |
| `veda` | Vedic texts and Vedic textual traditions. |
| `rgveda` | Rigvedic texts and directly related materials. |
| `yajurveda` | Yajurvedic texts and directly related materials. |
| `samaveda` | Samavedic texts and directly related materials. |
| `atharvaveda` | Atharvavedic texts and directly related materials. |
| `brahmana` | Brāhmaṇa literature. |
| `aranyaka` | Āraṇyaka literature. |
| `upanishad` | Upaniṣadic literature. |
| `kalpa` | Vedic ritual and procedural literature. |
| `grhyasutra` | Domestic ritual sutra literature. |
| `shrautasutra` | Public sacrificial ritual sutra literature. |
| `samhita` | Saṃhitā textual collections. |
| `smriti` | Remembered tradition and smṛti literature. |
| `sutra` | Sutra-form technical or scholastic literature. |
| `bhashya` | Bhāṣya commentary literature. |
| `vedanta` | Vedānta tradition. |
| `nyaya` | Nyāya logic and epistemology tradition. |
| `samkhya` | Sāṃkhya tradition. |
| `yoga` | Yoga tradition. |
| `mimamsa` | Mīmāṃsā tradition. |
| `vaisheshika` | Vaiśeṣika tradition. |
| `buddhist` | Buddhist literature or tradition. |
| `buddhist_sutra` | Buddhist sūtra/scriptural literature. |
| `buddhist_abhidharma` | Abhidharma and related scholastic Buddhist literature. |
| `buddhist_tantra` | Buddhist tantric literature. |
| `jain` | Jain literature or tradition. |
| `tantra` | Tantric literature broadly. |
| `shaiva` | Śaiva literature or tradition. |
| `bhakti` | Devotional literature and bhakti traditions. |
| `stotra` | Praise hymns and devotional stotra literature. |
| `patristics` | Christian patristic literature. |
| `roman_law` | Roman legal tradition. |
| `hippocratic_galenic_medicine` | Hippocratic, Galenic, or closely related Greek/Roman medical tradition. |
| `oratory` | Oratory and speech performance. |
| `speech` | Individual speeches or speech collections. |
| `tragedy` | Tragic drama. |
| `comedy` | Comic drama. |
| `satire` | Satire as a recurring literary discovery bucket. |
| `elegy` | Elegiac poetry. |
| `lyric` | Lyric poetry. |
| `epigram` | Epigrammatic poetry. |
| `didactic` | Didactic or instructional poetry. |
| `pastoral` | Pastoral/bucolic poetry. |
| `hagiography` | Saints' lives and holy biographies. |
| `homily` | Homilies and sermons. |
| `apology` | Apologetic works. |
| `commentary` | Commentary, explanation, or exegetical works. |
| `scholia` | Scholia and scholastic notes. |
| `fragmentary` | Fragmentary, excerpted, or unrecoverably partial texts. |
| `inscription` | Epigraphic material. |
| `technical` | Technical or manual-like works. |
| `ethics` | Conduct, duty, virtue, discipline, and moral instruction. |
| `law` | Legal procedure, codes, courts, jurisprudence, or legal interpretation. |
| `medicine` | Medical and health-related material. |
| `grammar` | Grammar and linguistic analysis. |
| `lexicography` | Lexical reference material. |
| `rhetoric` | Rhetoric and rhetorical education. |
| `philosophy` | Philosophical argument or tradition. |
| `religion` | Religious doctrine, theology, or scripture. |
| `ritual` | Ritual practice or ceremonial procedure. |
| `poetics` | Poetics, metrics, aesthetics, or criticism. |
| `astronomy` | Astronomy and calendrics. |
| `astrology` | Astrology, horoscopy, and astral divination. |
| `jyotisha` | Sanskrit astral science, astronomy, astrology, and calendrics. |
| `mathematics` | Mathematics and geometry. |
| `science` | Natural or technical science outside more specific groups. |
| `history` | Historical narrative or chronography. |
| `biography` | Biography and lives. |
| `letter` | Epistolary works. |
| `anthology` | Anthologies and miscellanies. |

## Intended CLI Interactions

```bash
langnet-cli reader works --language san --group medicine --sort group-popularity
langnet-cli reader works --language san --tag ayurveda --sort group-popularity
langnet-cli reader works --language grc --tag tragedy --sort global-popularity
langnet-cli reader works --language lat --group grammar --sort group-popularity
langnet-cli reader popular --language san --tag ayurveda
langnet-cli reader groups --language san
langnet-cli reader tags --language san
```

Compatibility aliases stay available during migration:

```bash
langnet-cli reader works --language san --scope medicine --sort popularity
langnet-cli reader popular --language lat --scope grammar
```

## Implementation Tasks

### Task 1: Taxonomy Constants And Validation

**Files:**
- Create: `src/langnet/reader/discovery_taxonomy.py`
- Test: `tests/test_reader_discovery_taxonomy.py`

- [x] Add `DiscoveryTaxonomyEntry` with `id`, `label`, and `description`.
- [x] Add `DISCOVERY_GROUPS` and `DISCOVERY_TAGS` dictionaries.
- [x] Add `normalize_discovery_tags(value: object) -> tuple[str, ...]` that accepts pipe-delimited strings, lists, tuples, or sets.
- [x] Add `validate_discovery_group_id(value: str) -> str` and `validate_discovery_tags(values: Iterable[str]) -> tuple[str, ...]`.
- [x] Verify IDs are snake-case, unique, non-empty, and contain no pipe characters.

### Task 2: CSV Loader And Generated Output

**Files:**
- Modify: `src/langnet/reader/models.py`
- Modify: `src/langnet/reader/classification.py`
- Modify: `src/langnet/reader/bulk_classification.py`
- Test: `tests/test_reader_classification.py`
- Test: `tests/test_reader_bulk_classification.py`

- [x] Add discovery fields to `ReaderWorkClassification`.
- [x] Load new CSV fields when present.
- [x] Derive legacy fields from new fields when old fields are blank.
- [x] Normalize JSON-array tags from model responses into pipe-delimited CSV.
- [x] Update prompt allowed values with group/tag IDs plus descriptions.
- [x] Keep old generated fields in output for compatibility.

### Task 3: DuckDB Storage And Filtering

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/reader/service.py`
- Test: `tests/test_reader_storage.py`

- [x] Add discovery columns to `work_classifications`.
- [x] Add `work_classification_tags(work_id, tag_id)` for reliable tag filtering.
- [x] Populate normalized tags when classifications are registered.
- [x] Join discovery fields into `list_works`.
- [x] Add filters for `classification_discovery_group_id` and `classification_discovery_tag`.
- [x] Sort `global-popularity` by global score and `group-popularity` by group score.

### Task 4: CLI Discovery Commands

**Files:**
- Modify: `src/langnet/cli.py`
- Modify: `src/langnet/reader/service.py`
- Test: `tests/test_reader_cli.py`

- [x] Add `reader works --group`, `reader works --tag`, and `--sort global-popularity|group-popularity`.
- [x] Keep `--scope` as compatibility alias for `--group`/legacy scope matching.
- [x] Add `reader popular --group` and `reader popular --tag`.
- [x] Add `reader groups` and `reader tags` commands that emit IDs, labels, and descriptions.

### Task 5: Docs And Full Verification

**Files:**
- Modify: `docs/READER_WEB_CONTRACT.md`
- Modify: `docs/READER_CLI_HANDOFF.md`

- [x] Document CSV fields, pipe-delimited tags, and generated-data trust model.
- [x] Document CLI discovery workflows.
- [x] Run `just ruff-check`.
- [x] Run focused reader classification/storage/CLI tests.
- [x] Run `just test-fast` if focused verification is green.

## Self-Review

- Spec coverage: strict taxonomy, CSV shape, global/group popularity, CLI discovery, compatibility aliases, and validation are represented in tasks.
- Placeholder scan: no open-ended taxonomy values; implementation tasks identify exact modules and expected behavior.
- Type consistency: uses `classification_discovery_group_id`, `classification_discovery_tags`, `classification_global_popularity_score`, `classification_global_popularity_tier`, `classification_group_popularity_score`, and `classification_group_popularity_tier` consistently.
