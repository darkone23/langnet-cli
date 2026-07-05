import assert from 'node:assert/strict';

import {
	allAvailableToolIds,
	liveVisibleToolsForLookupTools,
	nextLookupTools,
	nextVisibleTools
} from './desk-tool-filters';

const availableTools = [{ id: 'diogenes' }, { id: 'bailly' }, { id: 'strongs_greek' }] as const;

assert.deepEqual(allAvailableToolIds(availableTools), ['diogenes', 'bailly', 'strongs_greek']);
assert.deepEqual(nextLookupTools(['diogenes'], 'diogenes'), ['diogenes']);
assert.deepEqual(nextLookupTools(['diogenes', 'bailly'], 'bailly'), ['diogenes']);
assert.deepEqual(nextLookupTools(['diogenes'], 'bailly'), ['diogenes', 'bailly']);
assert.deepEqual(
	liveVisibleToolsForLookupTools(
		['diogenes', 'strongs_greek'],
		['diogenes', 'bailly', 'strongs_greek']
	),
	['diogenes', 'strongs_greek']
);
assert.deepEqual(nextVisibleTools(['bailly'], 'bailly'), ['bailly']);
assert.deepEqual(nextVisibleTools(['diogenes', 'bailly'], 'diogenes'), ['bailly']);
assert.deepEqual(nextVisibleTools(['diogenes'], 'bailly'), ['diogenes', 'bailly']);

console.log('desk tool filter checks complete');
