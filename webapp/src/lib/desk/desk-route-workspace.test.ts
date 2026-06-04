import assert from 'node:assert/strict';

import {
	clearDeskBrowserStorage,
	clearDeskMotdState,
	clearDeskStateStorage,
	clearDeskThemeStorage,
	clearDeskWordIndexState,
	readDeskMotdFromBrowserStorage,
	readDeskMotdFromStorage,
	readDeskStateFromBrowserStorage,
	readDeskWordIndexEarmarksFromBrowserStorage,
	readDeskStateFromStorage,
	readDeskWordIndexEarmarksFromStorage,
	restoreDeskStateFromStorage,
	writeDeskMotdToBrowserStorage,
	writeDeskMotdToStorage,
	writeDeskStateToBrowserStorage,
	writeDeskStateToStorage,
	writeDeskWordIndexEarmarksToBrowserStorage,
	writeDeskWordIndexEarmarksToStorage,
	WORD_INDEX_EARMARK_STORAGE_KEY
} from './desk-route-workspace';
import { saveStoredWordIndexEarmarks } from './desk-storage';
import type {
	EncounterResult,
	WordRecommendationItem,
	WordRecommendationResult
} from '../search-data';
import { type WordIndexItem } from '../word-index';

function fakeStorage(initial: Record<string, string> = {}) {
	const values = new Map(Object.entries(initial));

	return {
		get length() {
			return values.size;
		},
		getItem(key: string) {
			return values.get(key) ?? null;
		},
		setItem(key: string, value: string) {
			values.set(key, value);
		},
		removeItem(key: string) {
			values.delete(key);
		},
		key(index: number) {
			return [...values.keys()][index] ?? null;
		},
		clear() {
			values.clear();
		}
	};
}

const motdItem: WordRecommendationItem = {
	language: 'san',
	query: 'jyotis',
	key: 'san:jyotis',
	display: 'jyotis',
	primary_lexeme: 'jyotis',
	lexeme_anchors: ['jyotis'],
	summary: 'light',
	learner_note: '',
	mnemonic: '',
	difficulty: '',
	confidence: '',
	ambiguity: {
		has_multiple_lexemes: false,
		lexeme_count: 1,
		note: ''
	},
	recommended_request: {
		language: 'san',
		q: 'jyotis',
		dictionary: 'dico',
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
		badge: '',
		short_gloss: ''
	}
};

const motdResult: WordRecommendationResult = {
	schema_version: 'langnet.word_recommendation.v1',
	generated_at: 'fixture',
	suggested_ttl_seconds: 10,
	items: [motdItem],
	warnings: []
};

const encounter: EncounterResult = {
	query: 'logos',
	language: 'grc',
	dictionaries: ['diogenes', 'bailly'],
	source_tools: [],
	lexeme_anchors: [],
	buckets: [],
	analysis: [],
	components: [],
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
		tool_filter: ['diogenes', 'bailly'],
		reader_lang: 'en'
	},
	backend: 'cli'
};

{
	const storage = fakeStorage();
	writeDeskMotdToStorage(storage, motdResult);
	const read = readDeskMotdFromStorage(storage, (value) => value);
	assert.equal(read.result?.items[0]?.query, 'jyotis');
	assert.equal(read.stale, false);
}

{
	const storage = fakeStorage();
	const items = [
		{ encounter: { language: 'grc', q: 'logos', dictionary: 'diogenes' } },
		{ encounter: { language: 'grc', q: 'agni', dictionary: 'diogenes' } }
	] as WordIndexItem[];
	writeDeskWordIndexEarmarksToStorage(storage, items);
	assert.equal(readDeskWordIndexEarmarksFromStorage(storage).length, 2);
}

{
	type WorkspaceState = Parameters<typeof writeDeskStateToStorage>[1];
	const storage = fakeStorage();
	const state: WorkspaceState = {
		language: 'grc',
		query: 'logos',
		backendMode: 'cli',
		translationMode: 'auto',
		theme: 'manuscript',
		lookupTools: ['diogenes', 'bailly'],
		visibleTools: ['bailly'],
		encounter,
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {},
		wordIndex: null,
		wordIndexSections: null
	};
	writeDeskStateToStorage(storage, state);
	const restored = readDeskStateFromStorage(storage);
	assert.ok(restored);
	assert.equal(restored?.query, 'logos');
}

{
	const storage = fakeStorage();
	const stale = {
		version: 5,
		expiresAt: 1,
		routeKey: 'x',
		language: 'grc',
		query: 'logos',
		backendMode: 'cli',
		translationMode: 'auto',
		theme: 'manuscript',
		lookupTools: ['diogenes'],
		visibleTools: ['diogenes'],
		encounter: null,
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {}
	} as any;
	storage.setItem('orion-desk-state:v5', JSON.stringify(stale));
	assert.equal(readDeskStateFromStorage(storage), null);
}

{
	const params = new URLSearchParams('q=logos');
	const restored = restoreDeskStateFromStorage({
		params,
		stored: {
			version: 5,
			expiresAt: Date.now() + 10_000,
			routeKey:
				'{"language":"grc","query":"logos","backendMode":"cli","translationMode":"auto","lookupTools":["bailly","diogenes"]}',
			language: 'grc',
			query: 'logos',
			backendMode: 'cli',
			translationMode: 'auto',
			theme: 'manuscript',
			lookupTools: ['diogenes', 'bailly'],
			visibleTools: ['bailly'],
			encounter,
			textLayers: { bucket1: 'source' },
			expandedSections: { a: true },
			collapsedBranches: {},
			wordIndex: null,
			wordIndexSections: null
		},
		language: 'grc',
		query: 'logos',
		backendMode: 'cli',
		translationMode: 'auto',
		lookupTools: ['diogenes', 'bailly']
	});

	assert.ok(restored);
	assert.equal(restored!.encounter?.query, 'logos');
	assert.equal(restored!.visibleTools[0], 'bailly');
	assert.equal(restored!.theme, 'manuscript');
}

{
	const storage = fakeStorage({
		a: '1',
		b: '2',
		'orion-motd-cache:v1': '1',
		'orion-motd-cache:v2': '2',
		'orion-motd-cache:v3': '3',
		'orion-motd-cache:v4': '4',
		'orion-desk-state:v1': '5',
		'orion-desk-state:v2': '6',
		'orion-desk-state:v3': '7',
		'orion-desk-state:v4': '8',
		'orion-word-index-earmarks:v1': '9',
		orion_theme_test: 'x'
	});
	clearDeskMotdState(storage);
	clearDeskStateStorage(storage);
	clearDeskWordIndexState(storage);
	clearDeskThemeStorage(storage);
	assert.equal(storage.getItem('orion-motd-cache:v4'), null);
	assert.equal(storage.getItem('orion-desk-state:v4'), null);
	assert.equal(storage.getItem(WORD_INDEX_EARMARK_STORAGE_KEY), null);
	assert.equal(storage.getItem('orion_theme_test'), 'x');
}

{
	const storage = fakeStorage();
	const item = {
		encounter: { language: 'grc', q: 'logos', dictionary: 'diogenes' }
	} as WordIndexItem;
	saveStoredWordIndexEarmarks(storage, WORD_INDEX_EARMARK_STORAGE_KEY, [item, item]);
	clearDeskWordIndexState(storage);
	assert.equal(storage.getItem(WORD_INDEX_EARMARK_STORAGE_KEY), null);
}

{
	assert.deepEqual(readDeskMotdFromBrowserStorage(undefined, (value) => value).result, null);
	assert.equal(readDeskMotdFromBrowserStorage(undefined, (value) => value).stale, false);
	assert.equal(readDeskWordIndexEarmarksFromBrowserStorage(undefined).length, 0);
	assert.equal(readDeskStateFromBrowserStorage(undefined), null);

	assert.doesNotThrow(() => {
		writeDeskMotdToBrowserStorage(undefined, motdResult);
		writeDeskWordIndexEarmarksToBrowserStorage(undefined, []);
		writeDeskStateToBrowserStorage(undefined, {
			language: 'grc',
			query: 'logos',
			backendMode: 'cli',
			translationMode: 'auto',
			theme: 'manuscript',
			lookupTools: ['diogenes'],
			visibleTools: ['diogenes'],
			encounter: null,
			textLayers: {},
			expandedSections: {},
			collapsedBranches: {},
			wordIndex: null,
			wordIndexSections: null
		});
	});
}

{
	const storage = fakeStorage({
		orion_theme_test: 'x',
		'orion-motd-cache:v1': '1',
		'orion-word-index-earmarks:v1': 'x'
	} as Record<string, string>) as Storage;

	storage.setItem('orion-desk-state:v5', '1');
	storage.setItem('orion-theme', 'vespers');

	clearDeskBrowserStorage({
		localStorage: storage,
		sessionStorage: storage
	});

	assert.equal(storage.getItem('orion-desk-state:v5'), null);
	assert.equal(storage.getItem(WORD_INDEX_EARMARK_STORAGE_KEY), null);
	assert.equal(storage.getItem('orion-theme'), null);
	assert.equal(storage.getItem('orion-motd-cache:v1'), null);
}
