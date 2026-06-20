import assert from 'node:assert/strict';

import { createDeskMotdController } from './desk-motd-controller';
import type { DeskMotdState } from './desk-motd-controller';
import type { WordRecommendationResult } from '../search-data';

function motdPayload(query: string): WordRecommendationResult {
	return {
		schema_version: 'langnet.word_of_day.v1',
		generated_at: '2026-06-20T00:00:00Z',
		suggested_ttl_seconds: 3600,
		items: [
			{
				language: 'lat',
				query,
				key: `lat:${query}`,
				display: query,
				primary_lexeme: query,
				lexeme_anchors: [],
				summary: 'test gloss',
				learner_note: '',
				mnemonic: '',
				difficulty: 'beginner',
				confidence: 'source',
				ambiguity: { has_multiple_lexemes: false, lexeme_count: 0, note: '' },
				recommended_request: {
					language: 'lat',
					q: query,
					dictionary: 'all',
					translation: 'cache',
					backend: 'cli'
				},
				source_basis: [],
				display_forms: { native: query, roman: query, canonical: query, script: 'Latin' },
				ui: { href_query: '', badge: '', short_gloss: 'test gloss' }
			}
		],
		warnings: []
	};
}

const state: DeskMotdState = {
	motd: null,
	motdStale: false,
	motdLoading: false,
	motdRefreshing: false,
	motdError: ''
};
const requests: string[] = [];
const saved: WordRecommendationResult[] = [];

const controller = createDeskMotdController(
	state,
	{
		fetchPayload: async <T>(url: string) => {
			requests.push(url);
			return {
				response: { ok: true },
				data: motdPayload(`word-${requests.length}`) as T
			};
		},
		saveMotd: (result) => {
			saved.push(result);
		},
		recommendationsFailedMessage: 'Recommendations failed.'
	}
);

await controller.load(false);

assert.equal(state.motd?.items[0]?.query, 'word-1');
assert.equal(state.motdStale, false);
assert.equal(state.motdLoading, false);
assert.equal(state.motdRefreshing, false);
assert.equal(state.motdError, '');
assert.equal(saved.length, 1);
assert.match(requests[0]!, /\/api\/motd\?/);
assert.match(requests[0]!, /language=all/);
assert.doesNotMatch(requests[0]!, /refresh=1/);

state.motdStale = true;
await controller.load(true);

assert.equal(state.motd?.items[0]?.query, 'word-2');
assert.match(requests[1]!, /refresh=1/);
assert.match(requests[1]!, /avoid=lat%3Aword-1/);
assert.equal(saved.length, 2);

controller.reset();

assert.equal(state.motd, null);
assert.equal(state.motdStale, false);
assert.equal(state.motdLoading, false);
assert.equal(state.motdRefreshing, false);
assert.equal(state.motdError, '');

console.log('desk motd controller checks complete');
