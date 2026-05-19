import assert from 'node:assert/strict';
import { TimedResponseCache, canCacheSearchResponse, searchCacheKey } from './search-cache';

const left = new URL(
	'http://example.test/api/search?language=grc&q=logos&dictionary=all&translation=cache'
);
const right = new URL(
	'http://example.test/api/search?translation=cache&dictionary=all&q=logos&language=grc'
);

assert.equal(searchCacheKey(left), searchCacheKey(right));

const cache = new TimedResponseCache<{ ok: true }>({ ttlMs: 10, maxEntries: 2 });
cache.set('a', { ok: true }, 100);
assert.deepEqual(cache.get('a', 105), { ok: true });
assert.equal(cache.get('a', 111), undefined);

cache.set('a', { ok: true }, 200);
cache.set('b', { ok: true }, 200);
cache.set('c', { ok: true }, 200);
assert.equal(cache.size, 2);
assert.equal(cache.get('a', 201), undefined);
assert.deepEqual(cache.get('b', 201), { ok: true });
assert.deepEqual(cache.get('c', 201), { ok: true });

assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'cache',
		payload: { buckets: [] }
	}),
	true
);
assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'auto',
		payload: { buckets: [] }
	}),
	false
);
assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'cache',
		payload: { error: 'failed' }
	}),
	false
);
assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'cache',
		payload: {
			buckets: [],
			translation_cache: {
				after: { total: 1, hits: 0, missing: 0, errors: 1, empty: 0 }
			}
		}
	}),
	false
);
assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'cache',
		payload: {
			buckets: [],
			translation_cache: {
				after: { total: 1, hits: 0, missing: 1, errors: 0, empty: 0 }
			}
		}
	}),
	false
);
assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'cache',
		payload: {
			buckets: [],
			translation_cache: {
				after: { total: 1, hits: 0, missing: 0, errors: 0, empty: 1 }
			}
		}
	}),
	false
);
assert.equal(
	canCacheSearchResponse({
		backend: 'cli',
		word: 'logos',
		translationMode: 'cache',
		payload: {
			buckets: [],
			translation_cache: {
				after: { total: 1, hits: 1, missing: 0, errors: 0, empty: 0 }
			}
		}
	}),
	true
);

console.log('search response cache helpers ok');
