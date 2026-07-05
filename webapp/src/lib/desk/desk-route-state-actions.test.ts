import assert from 'node:assert/strict';

import {
	clearDeskEncounterPatch,
	clearDeskSearchPatch,
	clearPendingDeskRouteStatePatch,
	resetDeskAppPatch,
	selectDeskLanguagePatch
} from './desk-route-state-actions';

assert.deepEqual(clearPendingDeskRouteStatePatch(), {
	pendingVisibleToolsFromRoute: null,
	pendingSourceLayersFromRoute: [],
	pendingExpandedSectionsFromRoute: [],
	pendingCollapsedBranchesFromRoute: [],
	pendingQueryFromRoute: ''
});

assert.deepEqual(clearDeskEncounterPatch(), {
	activeSearchIdDelta: 1,
	encounter: null,
	visibleTools: [],
	loading: false,
	enrichingTranslations: false,
	errorMessage: '',
	enrichmentError: '',
	textLayers: {},
	expandedSections: {},
	collapsedBranches: {}
});

assert.deepEqual(clearDeskSearchPatch(), {
	activeSearchIdDelta: 1,
	query: '',
	encounter: null,
	visibleTools: [],
	errorMessage: '',
	enrichmentError: '',
	enrichingTranslations: false,
	textLayers: {},
	expandedSections: {},
	collapsedBranches: {},
	...clearPendingDeskRouteStatePatch()
});

assert.deepEqual(resetDeskAppPatch(), {
	activeSearchIdDelta: 1,
	routeLoadRequested: false,
	routePrefillOnly: false,
	language: 'san',
	query: '',
	backendMode: 'cli',
	translationMode: 'auto',
	theme: 'manuscript',
	lookupTools: ['cdsl', 'heritage', 'dico'],
	wordIndexEarmarks: [],
	encounter: null,
	visibleTools: [],
	loading: false,
	enrichingTranslations: false,
	errorMessage: '',
	enrichmentError: '',
	textLayers: {},
	expandedSections: {},
	collapsedBranches: {},
	...clearPendingDeskRouteStatePatch()
});

assert.deepEqual(selectDeskLanguagePatch('lat'), {
	activeSearchIdDelta: 1,
	routeLoadRequested: false,
	routePrefillOnly: false,
	language: 'lat',
	query: '',
	lookupTools: ['diogenes', 'lewis_1890', 'gaffiot', 'georges_1913', 'whitakers', 'cltk'],
	visibleTools: [],
	encounter: null,
	errorMessage: '',
	enrichmentError: '',
	enrichingTranslations: false,
	textLayers: {},
	expandedSections: {},
	collapsedBranches: {},
	...clearPendingDeskRouteStatePatch()
});

console.log('desk route state action checks complete');
