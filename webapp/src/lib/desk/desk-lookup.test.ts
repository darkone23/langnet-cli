import assert from 'node:assert/strict';
import type { EncounterBucket, EncounterResult } from '../search-data';
import {
	deskEncounterViewState,
	fetchDeskEncounter,
	firstPassTranslationMode,
	manualDeskQueryChanged,
	retryDeskTranslation,
	shouldProgressivelyEnrichLookup,
	validateDeskLookupWord
} from './desk-lookup';
import { sectionExpansionKey } from './desk-entry';

function bucket(id: string, sourceRef: string): EncounterBucket {
	return {
		bucket_id: id,
		display_gloss: 'speech',
		normalized_gloss: 'speech',
		bucket_lemmas: ['logos'],
		source_tools: ['bailly'],
		source_refs: [sourceRef],
		reasons: [],
		witnesses: [{ tool: 'bailly', label: 'Bailly', detail: '', source_ref: sourceRef }],
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

function encounter(): EncounterResult {
	return {
		query: 'logos',
		language: 'grc',
		dictionaries: ['all'],
		source_tools: ['diogenes'],
		lexeme_anchors: [],
		analysis: [],
		components: [],
		buckets: [bucket('bucket:1', 'bailly:2'), bucket('bucket:2', 'diogenes:1')],
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
			translation_mode: 'cache',
			tool_filter: ['all'],
			reader_lang: 'en'
		},
		backend: 'cli'
	};
}

assert.deepEqual(validateDeskLookupWord(' logos '), { ok: true, word: 'logos' });
assert.deepEqual(validateDeskLookupWord(''), { ok: false, reason: 'empty' });
assert.deepEqual(validateDeskLookupWord('two words'), { ok: false, reason: 'multiword' });

assert.equal(shouldProgressivelyEnrichLookup('cli', 'auto'), true);
assert.equal(shouldProgressivelyEnrichLookup('cli', 'populate'), true);
assert.equal(shouldProgressivelyEnrichLookup('cli', 'do-it-all'), true);
assert.equal(shouldProgressivelyEnrichLookup('cli', 'cache'), false);
assert.equal(shouldProgressivelyEnrichLookup('sample', 'auto'), false);
assert.equal(firstPassTranslationMode('cli', 'auto'), 'cache');
assert.equal(firstPassTranslationMode('sample', 'auto'), 'auto');
assert.equal(manualDeskQueryChanged('logos', 'logos'), false);
assert.equal(manualDeskQueryChanged('logos', 'ratio'), true);
assert.equal(manualDeskQueryChanged('', 'ratio'), false);

const result = encounter();
const [firstBucket, secondBucket] = result.buckets;
const resetState = deskEncounterViewState({
	result,
	resetReaderState: true,
	previousVisibleTools: ['diogenes'],
	pendingVisibleTools: ['bailly'],
	pendingSourceLayers: [firstBucket.bucket_id],
	pendingExpandedSections: [sectionExpansionKey(firstBucket)],
	pendingCollapsedBranches: [sectionExpansionKey(secondBucket)]
});

assert.deepEqual(resetState.visibleTools, ['bailly']);
assert.deepEqual(resetState.textLayers, { [firstBucket.bucket_id]: 'source' });
assert.deepEqual(resetState.expandedSections, { [sectionExpansionKey(firstBucket)]: true });
assert.deepEqual(resetState.collapsedBranches, { [sectionExpansionKey(secondBucket)]: true });
assert.equal(resetState.shouldClearPendingRouteState, true);

const preservedState = deskEncounterViewState({
	result,
	resetReaderState: false,
	previousVisibleTools: ['diogenes'],
	pendingVisibleTools: ['bailly'],
	pendingSourceLayers: [firstBucket.bucket_id],
	pendingExpandedSections: [sectionExpansionKey(firstBucket)],
	pendingCollapsedBranches: [sectionExpansionKey(secondBucket)]
});

assert.deepEqual(preservedState.visibleTools, ['diogenes']);
assert.deepEqual(preservedState.textLayers, {});
assert.equal(preservedState.shouldClearPendingRouteState, false);

{
	let delayed = 0;
	let requestedUrl = '';
	const fetched = await fetchDeskEncounter({
		url: '/api/search?lang=grc&q=logos',
		delayMs: 12,
		delay: async (milliseconds) => {
			delayed = milliseconds;
		},
		fetchPayload: async <T = unknown>(input: RequestInfo | URL) => {
			requestedUrl = String(input);
			return { response: new Response(null, { status: 200 }), data: encounter() as T };
		},
		searchFailedMessage: 'search failed'
	});

	assert.equal(requestedUrl, '/api/search?lang=grc&q=logos');
	assert.equal(delayed, 12);
	assert.equal(fetched.query, 'logos');
}

await assert.rejects(
	() =>
		fetchDeskEncounter({
			url: '/api/search',
			delayMs: 0,
			delay: async () => undefined,
			fetchPayload: async <T = unknown>() => ({
				response: new Response(null, { status: 500 }),
				data: { ...encounter(), error: 'backend unavailable' } as T
			}),
			searchFailedMessage: 'search failed'
		}),
	/backend unavailable/
);

{
	let retryInput = '';
	let retryBody: Record<string, unknown> = {};
	await retryDeskTranslation({
		translation: {
			available: false,
			translation_id: 'translation:1',
			source_tool: 'bailly',
			source_lexicon: 'bailly',
			entry_id: 'logos',
			occurrence: 2,
			headword_norm: 'logos',
			source_text_hash: 'hash',
			source_lang: 'fr',
			source_label: 'Bailly',
			source_text: 'mot',
			target_lang: 'en',
			target_text: ''
		},
		fetchPayload: async <T = unknown>(input: RequestInfo | URL, init?: RequestInit) => {
			retryInput = String(input);
			retryBody = JSON.parse(String(init?.body));
			return { response: new Response(null, { status: 200 }), data: {} as T };
		},
		translationFailedMessage: 'translation failed'
	});

	assert.equal(retryInput, '/api/translation-cache');
	assert.deepEqual(retryBody, {
		translation_id: 'translation:1',
		source_lexicon: 'bailly',
		entry_id: 'logos',
		occurrence: 2,
		headword_norm: 'logos',
		source_text_hash: 'hash',
		max_retries: 3
	});
}

await assert.rejects(
	() =>
		retryDeskTranslation({
			translation: {
				available: false,
				source_tool: 'bailly',
				source_lang: 'fr',
				source_label: 'Bailly',
				source_text: 'mot',
				target_lang: 'en',
				target_text: ''
			},
			fetchPayload: async <T = unknown>() => ({
				response: new Response(null, { status: 429 }),
				data: { limit_reached: true } as T
			}),
			translationFailedMessage: 'translation failed'
		}),
	/translation has reached its retry limit/
);
