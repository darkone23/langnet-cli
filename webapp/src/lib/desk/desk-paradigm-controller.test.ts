import assert from 'node:assert/strict';

import { createDeskParadigmController } from './desk-paradigm-controller';
import type { ParadigmPayload } from '../paradigm';
import type { ParadigmResolutionCandidate } from '../paradigm-resolution';

const candidate: ParadigmResolutionCandidate = {
	lemma: 'ratio',
	entry_type: 'noun',
	part_of_speech: 'substantive',
	paradigm_kind: 'declension',
	observed_form: 'ratio',
	slot_features: {},
	foster_display: '',
	display_summary: '',
	ranking_reasons: [],
	concept_ids: [],
	native_analyses: [],
	functional_analyses: [],
	paradigm_request: {
		source: 'fixture',
		language: 'lat',
		lemma: 'ratio',
		kind: 'declension',
		options: { gender: 'feminine' }
	},
	confidence: 'high',
	provenance: [],
	unresolved_reason: null,
	learning_overlay: null
};

const payload: ParadigmPayload = {
	schema_version: 'langnet.paradigm.v1',
	language: 'lat',
	lemma: 'ratio',
	kind: 'declension',
	source: 'fixture',
	source_request: {},
	paradigms: [
		{
			label: 'ratio declension',
			dimensions: ['number', 'case'],
			slots: [
				{
					features: { number: 'singular', case: 'nominative' },
					forms: [{ text: 'ratio', normalized: 'ratio', source_key: 'fixture:ratio' }],
					source_label: 'fixture',
					is_ambiguous: false
				}
			]
		}
	],
	warnings: []
};

const state = {
	paradigmPayloads: {} as Record<string, ParadigmPayload>,
	paradigmLoading: {} as Record<string, boolean>,
	paradigmErrors: {} as Record<string, string>
};
const requests: string[] = [];

const controller = createDeskParadigmController(state, {
	fetchPayload: async <T>(url: string) => {
		requests.push(url);
		return { response: { ok: true }, data: payload as T };
	},
	indexFailedMessage: 'Index failed.'
});

await controller.load(candidate);

const key = 'lat:declension:fixture:ratio:{"gender":"feminine"}';
assert.equal(state.paradigmPayloads[key]?.lemma, 'ratio');
assert.equal(state.paradigmLoading[key], false);
assert.equal(state.paradigmErrors[key], '');
assert.match(requests[0]!, /\/api\/paradigm\?/);
assert.match(requests[0]!, /language=lat/);
assert.match(requests[0]!, /lemma=ratio/);
assert.match(requests[0]!, /gender=feminine/);

await controller.load(candidate);
assert.equal(requests.length, 1, 'cached paradigm payload should not be fetched again');

controller.clear();
assert.deepEqual(state.paradigmPayloads, {});
assert.deepEqual(state.paradigmLoading, {});
assert.deepEqual(state.paradigmErrors, {});

console.log('desk paradigm controller checks complete');
