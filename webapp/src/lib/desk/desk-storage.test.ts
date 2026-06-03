import assert from 'node:assert/strict';

import {
	clearStorageKeys,
	readStoredDeskState,
	readStoredMotd,
	readStoredWordIndexEarmarks,
	saveStoredDeskState,
	saveStoredMotd,
	saveStoredWordIndexEarmarks,
	type StoredDeskState
} from './desk-storage';
import type { WordRecommendationResult } from '../search-data';
import type { WordIndexItem } from '../word-index';

function fakeStorage(initial: Record<string, string> = {}): Storage {
	const values = new Map(Object.entries(initial));
	return {
		get length() {
			return values.size;
		},
		clear() {
			values.clear();
		},
		getItem(key: string) {
			return values.get(key) ?? null;
		},
		key(index: number) {
			return [...values.keys()][index] ?? null;
		},
		removeItem(key: string) {
			values.delete(key);
		},
		setItem(key: string, value: string) {
			values.set(key, value);
		}
	};
}

const motdKey = 'motd';
const motdResult = {
	schema_version: 'langnet.word_recommendation.v1',
	items: [
		{
			language: 'san',
			query: 'jyotis',
			key: 'san:jyotis',
			display: 'jyotis',
			primary_lexeme: 'jyotis',
			lexeme_anchors: ['jyotis'],
			summary: 'light',
			learner_note: '',
			mnemonic: '',
			difficulty: 'easy',
			confidence: 'high',
			ambiguity: {
				has_multiple_lexemes: false,
				lexeme_count: 1,
				note: ''
			},
			recommended_request: {
				language: 'san',
				q: 'jyotis',
				dictionary: 'all',
				translation: 'cache',
				backend: 'cli'
			},
			source_basis: [],
			display_forms: {
				native: 'jyotis',
				roman: 'jyotis',
				canonical: 'jyotis',
				script: ''
			},
			ui: {
				href_query: 'jyotis',
				badge: 'Sanskrit',
				short_gloss: 'light'
			}
		}
	],
	warnings: [],
	error: '',
	generated_at: 'fixture',
	suggested_ttl_seconds: 60
} satisfies WordRecommendationResult;

{
	const storage = fakeStorage();
	saveStoredMotd(storage, motdKey, motdResult, 1_000);
	const stored = readStoredMotd(storage, motdKey, (result) => result, 30_000);
	assert.equal(stored.result?.items[0]?.display, 'jyotis');
	assert.equal(stored.stale, false);
}

{
	const storage = fakeStorage();
	saveStoredMotd(storage, motdKey, motdResult, 1_000);
	const stored = readStoredMotd(storage, motdKey, (result) => result, 90_000);
	assert.equal(stored.result?.items[0]?.display, 'jyotis');
	assert.equal(stored.stale, true);
}

{
	const storage = fakeStorage({ motd: '{' });
	assert.deepEqual(
		readStoredMotd(storage, motdKey, (result) => result),
		{
			result: null,
			stale: false
		}
	);
	assert.equal(storage.getItem(motdKey), null);
}

{
	const item = { encounter: { q: 'logos' } } as WordIndexItem;
	const storage = fakeStorage();
	saveStoredWordIndexEarmarks(storage, 'earmarks', [item, {} as WordIndexItem]);
	assert.deepEqual(readStoredWordIndexEarmarks(storage, 'earmarks'), [item]);
}

{
	const storage = fakeStorage();
	const state = {
		version: 5,
		expiresAt: 5_000,
		routeKey: 'route',
		language: 'grc',
		query: 'logos',
		backendMode: 'cli',
		translationMode: 'cache',
		theme: 'manuscript',
		lookupTools: ['diogenes'],
		visibleTools: ['diogenes'],
		encounter: null,
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {}
	} satisfies StoredDeskState;

	saveStoredDeskState(storage, 'desk', state);
	assert.equal(readStoredDeskState(storage, 'desk', 4_000)?.query, 'logos');
	assert.equal(readStoredDeskState(storage, 'desk', 5_001), null);
	assert.equal(storage.getItem('desk'), null);
}

{
	const storage = fakeStorage({ a: '1', b: '2' });
	clearStorageKeys(storage, ['a', 'b']);
	assert.equal(storage.length, 0);
}
