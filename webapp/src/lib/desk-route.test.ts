import assert from 'node:assert/strict';
import {
	currentDeskRouteKey,
	isClearDeskRouteState,
	readLanguageParam,
	readRouteList,
	readToolParams,
	routeMatchesEncounter,
	routePrefillOnlyRequested,
	routeShouldLoad,
	shouldLoadEncounterForRoute,
	shouldPersistDeskRouteListParam,
	shouldResetEncounterForRoute
} from './desk-route';
import type { EncounterResult } from './search-data';

const encounter = {
	query: 'Logos',
	language: 'grc',
	dictionaries: ['bailly'],
	buckets: [],
	source_tools: [],
	lexeme_anchors: [],
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
		tool_filter: ['bailly'],
		reader_lang: 'en'
	},
	backend: 'cli'
} as EncounterResult;

assert.equal(routeMatchesEncounter(encounter, 'grc', 'logos'), true);
assert.equal(routeMatchesEncounter(encounter, 'grc', ' logos '), true);
assert.equal(routeMatchesEncounter(encounter, 'lat', 'logos'), false);
assert.equal(routeMatchesEncounter(encounter, 'grc', 'ratio'), false);

assert.equal(
	shouldResetEncounterForRoute({
		currentLanguage: 'grc',
		currentQuery: 'logos',
		nextLanguage: 'grc',
		nextQuery: 'logos'
	}),
	false
);
assert.equal(
	shouldResetEncounterForRoute({
		currentLanguage: 'grc',
		currentQuery: 'logos',
		nextLanguage: 'grc',
		nextQuery: 'ratio'
	}),
	true
);

assert.equal(
	shouldLoadEncounterForRoute({
		routeWantsLoad: true,
		routeExplicitlyRequestsLoad: false,
		hasLoadableQuery: true,
		routeMatchesCurrentEncounter: true
	}),
	false
);

assert.equal(shouldPersistDeskRouteListParam('visible'), true);
assert.equal(shouldPersistDeskRouteListParam('source'), true);
assert.equal(shouldPersistDeskRouteListParam('expand'), false);
assert.equal(shouldPersistDeskRouteListParam('collapse'), false);
{
	const params = new URLSearchParams(
		'language=grc&q=logos&dictionary=diogenes,bailly&dictionary=all&visible=bailly&source=a&source=b'
	);
	assert.equal(readLanguageParam(params), 'grc');
	assert.deepEqual(readRouteList(params, 'source'), ['a', 'b']);
	assert.deepEqual(readToolParams(params, 'visible', ['diogenes', 'bailly']), ['bailly']);
	assert.deepEqual(readToolParams(params, 'dictionary', ['diogenes', 'bailly']), [
		'diogenes',
		'bailly'
	]);
}

assert.equal(routePrefillOnlyRequested(new URLSearchParams('load=no')), true);
assert.equal(routePrefillOnlyRequested(new URLSearchParams('prefill=true')), true);
assert.equal(routeShouldLoad(new URLSearchParams('q=logos')), true);
assert.equal(routeShouldLoad(new URLSearchParams('q=logos&load=false')), false);
assert.equal(routeShouldLoad(new URLSearchParams('q=logos&prefill=1')), false);
assert.equal(routeShouldLoad(new URLSearchParams('load=true')), true);
assert.equal(
	currentDeskRouteKey({
		language: 'san',
		query: ' Jyotis ',
		backendMode: 'cli',
		translationMode: 'auto',
		lookupTools: ['dico', 'cdsl']
	}),
	'{"language":"san","query":"jyotis","backendMode":"cli","translationMode":"auto","lookupTools":["cdsl","dico"]}'
);
assert.equal(
	isClearDeskRouteState({
		includeLoad: false,
		language: 'san',
		query: '',
		backendMode: 'cli',
		translationMode: 'auto',
		theme: 'manuscript',
		lookupTools: ['cdsl', 'heritage'],
		defaultTools: ['cdsl', 'heritage'],
		hasEncounter: false,
		visibleTools: [],
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {},
		pendingVisibleTools: [],
		pendingSourceLayers: [],
		pendingExpandedSections: [],
		pendingCollapsedBranches: []
	}),
	true
);
assert.equal(
	shouldLoadEncounterForRoute({
		routeWantsLoad: true,
		routeExplicitlyRequestsLoad: true,
		hasLoadableQuery: true,
		routeMatchesCurrentEncounter: true
	}),
	true
);
assert.equal(
	shouldLoadEncounterForRoute({
		routeWantsLoad: true,
		routeExplicitlyRequestsLoad: false,
		hasLoadableQuery: true,
		routeMatchesCurrentEncounter: false
	}),
	true
);
assert.equal(
	shouldLoadEncounterForRoute({
		routeWantsLoad: true,
		routeExplicitlyRequestsLoad: false,
		hasLoadableQuery: false,
		routeMatchesCurrentEncounter: false
	}),
	false
);
