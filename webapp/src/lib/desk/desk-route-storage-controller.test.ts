import assert from 'node:assert/strict';

import { createDeskRouteStorageController } from './desk-route-storage-controller';
import type { DeskRouteStorageState } from './desk-route-storage-controller';
import { DESK_STATE_STORAGE_KEY } from './desk-route-workspace';
import type { EncounterResult, ToolId } from '../search-data';
import type { WordIndexItem } from '../word-index';

function fakeStorage(initial: Record<string, string> = {}) {
	const values = new Map(Object.entries(initial));

	return {
		values,
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

const localStorage = fakeStorage({ 'orion-theme': 'vespers' });
const sessionStorage = fakeStorage();
const documentThemes: string[] = [];
const state: DeskRouteStorageState = {
	language: 'grc',
	query: 'logos',
	backendMode: 'cli',
	translationMode: 'auto',
	theme: 'manuscript',
	lookupTools: ['diogenes', 'bailly'] as ToolId[],
	visibleTools: ['bailly'] as ToolId[],
	encounter,
	textLayers: { bucket: 'source' },
	expandedSections: { section: true },
	collapsedBranches: {},
	wordIndex: null,
	wordIndexSections: null,
	wordIndexEarmarks: [
		{ encounter: { language: 'grc', q: 'logos', dictionary: 'diogenes' } }
	] as WordIndexItem[],
	loading: true,
	enrichingTranslations: true,
	errorMessage: 'old error',
	enrichmentError: 'old enrichment'
};

const controller = createDeskRouteStorageController(state, {
	browser: true,
	localStorage,
	sessionStorage,
	setDocumentTheme: (theme) => documentThemes.push(theme)
});

controller.saveDeskState();
assert.ok(sessionStorage.getItem(DESK_STATE_STORAGE_KEY));

controller.saveWordIndexEarmarks();
assert.ok([...localStorage.values.keys()].some((key) => key.includes('word-index-earmarks')));

state.encounter = null;
state.query = '';
controller.saveDeskState();
assert.equal(sessionStorage.getItem(DESK_STATE_STORAGE_KEY), null);

state.query = 'logos';
state.encounter = encounter;
controller.saveDeskState();
state.encounter = null;
state.visibleTools = [];
state.loading = true;
state.enrichingTranslations = true;
state.errorMessage = 'stale';
state.enrichmentError = 'stale';

const restored = controller.restoreDeskState(new URLSearchParams('q=logos'));
const restoredEncounter = state.encounter as EncounterResult | null;
assert.equal(restored, true);
assert.equal(restoredEncounter?.query, 'logos');
assert.deepEqual(state.visibleTools, ['bailly']);
assert.equal(state.loading, false);
assert.equal(state.enrichingTranslations, false);
assert.equal(state.errorMessage, '');
assert.equal(state.enrichmentError, '');

controller.clearAppStorage();
assert.equal(localStorage.getItem('orion-theme'), null);
assert.equal(documentThemes.at(-1), 'manuscript');

console.log('desk route storage controller checks complete');
