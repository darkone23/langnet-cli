import assert from 'node:assert/strict';
import type { EncounterBucket, EncounterResult } from '../search-data';
import { refreshDeskSearchTranslations, retryDeskGroupTranslation } from './desk-workflows';

type FetchPayload = <T>(
	input: RequestInfo | URL,
	init?: RequestInit
) => Promise<{ response: Response; data: T }>;

function bucket(id: string): EncounterBucket {
	return {
		bucket_id: id,
		display_gloss: 'plain gloss',
		normalized_gloss: 'plain gloss',
		bucket_lemmas: ['logos'],
		source_tools: ['dico'],
		source_refs: ['dico:1'],
		reasons: [],
		witnesses: [],
		witness_count: 1,
		preferred_lemma_rank: 0,
		effective_preferred_lemma_rank: 0,
		learner_quality_order: 0,
		has_english_translation: false,
		has_source_translation: false,
		source_langs: ['fr'],
		reader_lang: 'en',
		evidence_note: '',
		translation_note: ''
	};
}

function encounter(override?: Partial<EncounterResult>): EncounterResult {
	return {
		query: 'logos',
		language: 'grc',
		dictionaries: ['all'],
		source_tools: ['dico'],
		lexeme_anchors: [],
		analysis: [],
		components: [],
		buckets: [bucket('bucket:1')],
		translation_cache: {
			mode: 'cache',
			cache_db: '',
			model: '',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 0, hits: 0, missing: 0, errors: 0, empty: 0 },
			after: { total: 0, hits: 0, missing: 0, errors: 0, empty: 0 }
		},
		warnings: [],
		request: {
			translation_mode: 'auto',
			tool_filter: ['dico'],
			reader_lang: 'en'
		},
		backend: 'cli',
		...override
	};
}

{
	const data = encounter();
	let enriched = false;
	let arrivalTriggered = 0;
	let enrichment = true;
	let enrichmentError = 'seed';

	await refreshDeskSearchTranslations({
		searchId: 1,
		isSearchCurrent: (value) => value === 1,
		fetchEncounter: async () => data,
		applyEncounter: () => {
			enriched = true;
		},
		setEnrichingTranslations: (value) => {
			enrichment = value;
		},
		setEnrichmentError: (message) => {
			enrichmentError = message;
		},
		tick: async () => undefined,
		triggerTranslationArrival: () => {
			arrivalTriggered += 1;
		},
		translationFailedMessage: 'translation failed',
		enrichmentMode: 'auto'
	});

	assert.equal(enriched, true);
	assert.equal(enrichment, false);
	assert.equal(enrichmentError, '');
	assert.equal(arrivalTriggered, 1);
}

{
	let enrichment = false;
	let enriched = false;

	await refreshDeskSearchTranslations({
		searchId: 1,
		isSearchCurrent: () => false,
		fetchEncounter: async () => encounter(),
		applyEncounter: () => {
			enriched = true;
		},
		setEnrichingTranslations: (value) => {
			enrichment = value;
		},
		setEnrichmentError: () => {
			throw new Error('should not change errors for stale search');
		},
		tick: async () => undefined,
		triggerTranslationArrival: () => {
			throw new Error('should not trigger arrival for stale search');
		},
		translationFailedMessage: 'translation failed',
		enrichmentMode: 'auto'
	});

	assert.equal(enriched, false);
	assert.equal(enrichment, true);
}

{
	let retrying = false;
	let applied = 0;
	let arrived = 0;
	let enrichmentError = 'seed';

	await retryDeskGroupTranslation({
		searchId: 1,
		isSearchCurrent: (value) => value === 1,
		translation: {
			available: false,
			source_tool: 'dico',
			source_lang: 'fr',
			source_label: 'DICO',
			source_text: 'd',
			source_text_hash: 'hash',
			translation_id: 't1',
			entry_id: 'logos',
			target_lang: 'en',
			target_text: 'x',
			occurrence: 1,
			headword_norm: 'logos'
		},
		retryKey: 'g1',
		setTranslationRetrying: (key, value) => {
			retrying = key === 'g1' && value;
		},
		setEnrichmentError: (message) => {
			enrichmentError = message;
		},
		tick: async () => undefined,
		fetchEncounter: async () => encounter(),
		applyEncounter: () => {
			applied += 1;
		},
		triggerTranslationArrival: () => {
			arrived += 1;
		},
		fetchPayload: (async (_input: RequestInfo | URL, _init?: RequestInit) => ({
			response: new Response('{}'),
			data: {} as unknown
		})) as FetchPayload,
		retryDeskTranslation: async () => ({}),
		translationFailedMessage: 'translation failed'
	});

	assert.equal(retrying, false);
	assert.equal(applied, 1);
	assert.equal(arrived, 1);
	assert.equal(enrichmentError, '');
}
