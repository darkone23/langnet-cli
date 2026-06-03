import assert from 'node:assert/strict';
import {
	currentDeskRouteKey,
	deskRouteHydration,
	deskAppRouteUrl,
	deskMotdHref,
	deskWordIndexHref,
	deskWordIndexSectionHref,
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
import type { EncounterResult } from '../search-data';
import type { WordIndexItem, WordIndexSection } from '../word-index';

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
	deskAppRouteUrl({
		includeLoad: false,
		language: 'san',
		query: '',
		backendMode: 'cli',
		translationMode: 'auto',
		theme: 'manuscript',
		routePrefillOnly: false,
		lookupTools: ['cdsl', 'heritage'],
		defaultTools: ['cdsl', 'heritage'],
		allLookupSelected: true,
		encounterMatchesQuery: false,
		hasEncounter: false,
		visibleTools: [],
		returnedToolIds: [],
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {},
		pendingVisibleTools: [],
		pendingSourceLayers: [],
		pendingExpandedSections: [],
		pendingCollapsedBranches: []
	}),
	'/',
	'clear default desk state should collapse to the home route'
);
assert.equal(
	deskAppRouteUrl({
		includeLoad: true,
		language: 'grc',
		query: ' logos ',
		backendMode: 'cli',
		translationMode: 'cache',
		theme: 'vespers',
		routePrefillOnly: false,
		lookupTools: ['diogenes', 'bailly'],
		defaultTools: ['diogenes', 'bailly'],
		allLookupSelected: true,
		encounterMatchesQuery: true,
		hasEncounter: true,
		visibleTools: ['bailly'],
		returnedToolIds: ['diogenes', 'bailly'],
		textLayers: { bucket1: 'source', bucket2: 'reader' },
		expandedSections: {},
		collapsedBranches: {},
		pendingVisibleTools: [],
		pendingSourceLayers: [],
		pendingExpandedSections: [],
		pendingCollapsedBranches: []
	}),
	'/?lang=grc&q=logos&backend=cli&translation=cache&theme=vespers&load=yes&dictionary=all&visible=bailly&source=bucket1'
);
assert.equal(
	deskMotdHref(
		{
			language: 'san',
			query: 'agni',
			key: 'agni',
			display: 'agni',
			primary_lexeme: 'agni',
			lexeme_anchors: [],
			summary: '',
			learner_note: '',
			mnemonic: '',
			difficulty: '',
			confidence: '',
			ambiguity: { has_multiple_lexemes: false, lexeme_count: 1, note: '' },
			recommended_request: {
				language: 'san',
				q: 'agni',
				dictionary: 'dico',
				translation: 'cache',
				backend: 'cli'
			},
			source_basis: [],
			display_forms: { native: 'agni', roman: 'agni', canonical: 'agni', script: 'roman' },
			ui: { href_query: 'agni', badge: '', short_gloss: '' }
		},
		{ theme: 'vespers', motdLinksLoad: false }
	),
	'/?lang=san&q=agni&dictionary=dico&translation=cache&backend=cli&theme=vespers&load=no'
);

const wordIndexItem = {
	encounter: {
		language: 'grc',
		q: 'logos',
		dictionary: 'bailly'
	},
	language: 'grc',
	display: 'logos',
	key: 'logos',
	query: 'logos',
	source: 'bailly',
	dictionary: 'bailly'
} as unknown as WordIndexItem;

assert.equal(
	deskWordIndexHref(wordIndexItem, {
		translationMode: 'auto',
		theme: 'manuscript',
		includeLoad: true
	}),
	'/?lang=grc&q=logos&translation=auto&theme=manuscript&dictionary=bailly&load=yes'
);

const wordIndexSection = {
	label: 'lambda',
	available: true,
	transliteration: 'lambda',
	anchor: {
		language: 'grc',
		query: 'logos',
		source: 'bailly',
		dictionary: 'bailly',
		canonical_key: 'logos',
		source_order_key: 'logos',
		lexeme_id: 'logos',
		index_entry_id: 'logos',
		source_order_id: 'logos'
	}
} as WordIndexSection;

assert.equal(
	deskWordIndexSectionHref(wordIndexSection, {
		translationMode: 'cache',
		theme: 'vespers'
	}),
	'/?lang=grc&q=logos&translation=cache&theme=vespers&dictionary=bailly&load=yes'
);
{
	const hydration = deskRouteHydration({
		params: new URLSearchParams(
			'lang=grc&q=Logos&dictionary=all&visible=bailly&source=bucket1&theme=vespers&backend=sample&translation=cache&load=yes'
		),
		currentLanguage: 'grc',
		currentQuery: 'logos',
		encounter
	});

	assert.deepEqual(hydration, {
		nextLanguage: 'grc',
		nextQuery: 'Logos',
		validTools: ['diogenes', 'bailly', 'strongs_greek', 'cts_index', 'spacy', 'cltk'],
		requestedTools: ['diogenes', 'bailly', 'strongs_greek', 'cts_index', 'spacy', 'cltk'],
		requestedVisibleTools: ['bailly'],
		requestedTheme: 'vespers',
		requestedBackend: 'sample',
		requestedTranslation: 'cache',
		shouldPrefillOnly: false,
		routeLoadRequested: true,
		routeMatchesCurrentEncounter: true,
		shouldResetEncounter: false,
		shouldPreserveEncounter: true,
		routeVisibleTools: ['bailly'],
		routeSourceLayers: ['bucket1'],
		routeExpandedSections: [],
		routeCollapsedBranches: [],
		shouldRestoreFromSession: false
	});
}
{
	const hydration = deskRouteHydration({
		params: new URLSearchParams(
			'lang=xxx&q=two%20words&dictionary=bogus&theme=bad&backend=bad&translation=bad&prefill=1'
		),
		currentLanguage: 'san',
		currentQuery: '',
		encounter: null
	});

	assert.equal(hydration.nextLanguage, 'san');
	assert.equal(hydration.routeLoadRequested, false);
	assert.equal(hydration.shouldPrefillOnly, true);
	assert.deepEqual(hydration.requestedTools, null);
	assert.deepEqual(hydration.requestedVisibleTools, null);
	assert.equal(hydration.requestedTheme, null);
	assert.equal(hydration.requestedBackend, null);
	assert.equal(hydration.requestedTranslation, null);
	assert.equal(hydration.shouldRestoreFromSession, false);
}
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
