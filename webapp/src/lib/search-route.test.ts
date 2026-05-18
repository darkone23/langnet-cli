import assert from 'node:assert/strict';
import { shouldRetrySearchWithoutTranslation } from './search-route';

assert.equal(
	shouldRetrySearchWithoutTranslation(
		new Error(
			'Unable to use translation cache data/cache/langnet.duckdb: Bailly translation block 01:04:00 kept French dictionary prose'
		),
		'auto'
	),
	true
);

assert.equal(
	shouldRetrySearchWithoutTranslation(new Error('langnet-cli timed out after 120s'), 'auto'),
	false
);

assert.equal(
	shouldRetrySearchWithoutTranslation(
		new Error('Unable to use translation cache data/cache/langnet.duckdb'),
		'off'
	),
	false
);

console.log('search route helpers ok');
