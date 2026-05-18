import assert from 'node:assert/strict';
import {
	routeMatchesEncounter,
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
