import assert from 'node:assert/strict';

import {
	createDeskWordIndexController,
	type DeskWordIndexState
} from './desk-word-index';
import type { WordIndexResponse, WordIndexSectionsResponse, WordIndexItem } from '../word-index';

type FetchPayload = (
	input: RequestInfo | URL,
	init?: RequestInit
) => Promise<{ response: Response; data: WordIndexResponse | WordIndexSectionsResponse }>;

function response<T>(data: T, ok = true) {
	return {
		response: new Response('{}', {
			status: ok ? 200 : 500
		}),
		data
	};
}

function indexResponse(language: 'grc' | 'san', hasRows = true): WordIndexResponse {
	return {
		schema_version: '1',
		request: {
			mode: 'nearby',
			language,
			source: 'all',
			query: 'logos'
		},
		sources: [],
		items: hasRows ? [mockItem(`${language}:logos`)] : [],
		neighborhood: hasRows
			? {
				groups: [
					{
						language,
						source: 'w',
						dictionary: 'd',
						before: [],
						after: [],
						radius: 1,
						neighborhood_kind: 'exact',
						anchor_status: 'found',
						window: {
							policy: 'all',
							contiguous: false,
							collapsed: false,
							before_count: 0,
							after_count: 0,
							source_entry_count: 0
						}
					}
				],
				window: {
					policy: 'all',
					contiguous: false,
					collapsed: false,
					before_count: 0,
					after_count: 0,
					source_group_count: 1,
					lexeme_count: 1
				}
			}
			: {
				groups: []
			},
		pagination: { next_cursor: null, prev_cursor: null },
		warnings: []
	};
}

function sectionsResponse(language: 'grc' | 'san'): WordIndexSectionsResponse {
	return {
		schema_version: '1',
		request: {
			language,
			source: 'all'
		},
		sections: [],
		warnings: []
	};
}

function mockItem(key: string): WordIndexItem {
	return {
		ids: {
			lexeme: key,
			wheel: key,
			index_entry: key,
			source_order: '0',
			source_ref: key
		},
		lexeme_id: key,
		wheel_id: key,
		wheel_order_key: key,
		index_entry_id: key,
		source_order_id: key,
		language: 'grc',
		source: 'bailly',
		dictionary: 'bailly',
		kind: 'word',
		canonical_name: key,
		canonical_key: key,
		source_name: 'Bailly',
		lookup: key,
		display: {
			primary: key,
			transliteration: key,
			source_key: key
		},
		sort_key: key,
		source_order_key: key,
		source_ref: key,
		source_entries: [],
		metadata: {},
		encounter: {
			language: 'grc',
			q: 'logos',
			dictionary: 'bailly'
		}
	} as WordIndexItem;
}

function createController(fetchPayload: FetchPayload, language: 'grc' | 'san' = 'grc') {
	const state: DeskWordIndexState = {
		language,
		wordIndex: null,
		wordIndexSections: null,
		wordIndexLoading: false,
		wordIndexSectionsLoading: false,
		wordIndexError: '',
		wordIndexSectionsError: '',
		wordIndexRequestId: 0,
		wordIndexEarmarks: []
	};

	const typedFetchPayload = ((input: RequestInfo | URL, init?: RequestInit) =>
		fetchPayload(input, init)) as <T>(
		input: RequestInfo | URL,
		init?: RequestInit
	) => Promise<{ response: Response; data: T }>;

	return {
		state,
		controller: createDeskWordIndexController(state, {
			fetchPayload: typedFetchPayload,
			errors: {
				indexFailed: 'index failed'
			}
		},
			{ wordIndexRadius: 5 }
		)
	};
}

{
	const { state, controller } = createController(async (input: RequestInfo | URL) => {
		assert.equal(String(input).includes('/api/word-index?mode=sections&language=grc'), true);
		return response(sectionsResponse('grc'));
	});

	await controller.loadSections('grc');
	assert.equal(state.wordIndexSections?.request.language, 'grc');
	assert.equal(state.wordIndexSectionsLoading, false);
}

{
	const calls: string[] = [];
	const { state, controller } = createController(async (input: RequestInfo | URL) => {
		const target = String(input);
		calls.push(target);

		if (target.includes('language=grc')) {
			return response(indexResponse('grc'), true);
		}

		return response(indexResponse('san'), true);
	});

	await controller.loadSections('san');
	await controller.loadSections('grc');
	assert.equal(state.wordIndexSections?.request.language, 'grc');
	assert.equal(calls.length, 2);
}

{
	let call = 0;
	const { state, controller } = createController(async (input: RequestInfo | URL) => {
		const target = String(input);
		if (!target.includes('mode=nearby')) return response(indexResponse('grc'));
		if (call === 0) {
			call += 1;
			return response(indexResponse('grc', false));
		}
		return response(indexResponse('grc', true));
	});

	await controller.loadNearbyWordIndex('logos', 'grc', ['logos', 'λόγος']);
	assert.equal(state.wordIndex?.request.language, 'grc');
	assert.equal(state.wordIndexError, '');
	assert.equal(state.wordIndexLoading, false);
}

{
	const { state, controller } = createController(async () => response(sectionsResponse('grc')));
	const before = state.wordIndexRequestId;
	await controller.loadBrowseWordIndex('logos');
	assert.equal(state.wordIndexLoading, false);
	assert.equal(state.wordIndexRequestId, before + 1);
	assert.equal(state.wordIndex !== null, true);
}

{
	const { state, controller } = createController(async () => response(sectionsResponse('grc')));
	const first = mockItem('first');
	const second = mockItem('second');

	controller.toggleEarmark(first);
	assert.equal(state.wordIndexEarmarks.length, 1);
	assert.equal(controller.isEarmarked(first), true);
	controller.toggleEarmark(first);
	assert.equal(state.wordIndexEarmarks.length, 0);

	controller.toggleEarmark(first);
	controller.toggleEarmark(second);
	assert.equal(state.wordIndexEarmarks.length, 2);
	controller.clearEarmarks();
	assert.equal(state.wordIndexEarmarks.length, 0);
}

{
	const { state, controller } = createController(async () => response(sectionsResponse('grc')));
	state.wordIndexLoading = true;
	state.wordIndex = indexResponse('grc');
	state.wordIndexRequestId = 3;
	state.wordIndexError = 'old';
	controller.clearSearchState();
	assert.equal(state.wordIndexLoading, false);
	assert.equal(state.wordIndex, null);
	assert.equal(state.wordIndexError, '');
	assert.equal(state.wordIndexRequestId, 4);
}
