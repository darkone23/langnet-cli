import assert from 'node:assert/strict';
import {
	motdItemKeys,
	motdTtlMs,
	storedMotdIsFresh,
	storedMotdStatus,
	type StoredMotd
} from './motd-cache';

const now = Date.UTC(2026, 4, 9, 12);
const result = {
	schema_version: 'langnet.word_of_day.v1',
	generated_at: '2026-05-09T12:00:00Z',
	suggested_ttl_seconds: 86_400,
	items: [],
	warnings: []
};

assert.equal(motdTtlMs(0), 3_600_000);
assert.equal(motdTtlMs(30), 60_000);
assert.equal(motdTtlMs(200_000), 86_400_000);

const storedTwoHoursAgo = {
	version: 3,
	kind: 'current',
	savedAt: now - 2 * 60 * 60 * 1000,
	expiresAt: now + 22 * 60 * 60 * 1000,
	result
} satisfies StoredMotd;

assert.equal(storedMotdIsFresh(storedTwoHoursAgo, now), true);
assert.equal(storedMotdIsFresh({ ...storedTwoHoursAgo, expiresAt: now }, now), false);
assert.equal(storedMotdStatus({ ...storedTwoHoursAgo, expiresAt: now }, now), 'stale');
assert.equal(storedMotdStatus({ ...storedTwoHoursAgo, expiresAt: now - 60_000 }, now), 'stale');
assert.equal(
	storedMotdIsFresh({ ...storedTwoHoursAgo, version: 2 } as unknown as Partial<StoredMotd>, now),
	false
);
assert.equal(
	storedMotdStatus({ ...storedTwoHoursAgo, version: 2 } as unknown as Partial<StoredMotd>, now),
	'invalid'
);

assert.deepEqual(
	motdItemKeys({
		...result,
		items: [
			{ key: 'grc:logos', language: 'grc', query: 'logos' },
			{ key: '', language: 'lat', query: 'ratio' },
			{ key: 'grc:logos', language: 'grc', query: 'logos' }
		]
	}),
	['grc:logos', 'lat:ratio']
);
