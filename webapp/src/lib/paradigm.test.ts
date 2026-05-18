import assert from 'node:assert/strict';
import { normalizeParadigmPayload, paradigmRequestKey } from './paradigm';
import type { ParadigmRequest } from './paradigm-resolution';

const request = {
	source: 'diogenes:inflect',
	language: 'lat',
	lemma: 'puella',
	kind: 'declension',
	options: {}
} satisfies ParadigmRequest;

const payload = normalizeParadigmPayload({
	schema_version: 'langnet.paradigm.v1',
	language: 'lat',
	lemma: 'puella',
	kind: 'declension',
	source: 'diogenes:inflect',
	source_request: { params: { q: 'puella' } },
	paradigms: [
		{
			label: 'puella declension',
			dimensions: ['number', 'case'],
			slots: [
				{
					features: { number: 'singular', case: 'nominative' },
					forms: [{ text: 'puella', normalized: 'puella', source_key: 'puella' }],
					source_label: '(fem nom sg)',
					is_ambiguous: false
				}
			]
		}
	],
	warnings: []
});

assert.equal(payload?.schema_version, 'langnet.paradigm.v1');
assert.equal(payload?.paradigms[0]?.slots[0]?.forms[0]?.text, 'puella');
assert.deepEqual(payload?.paradigms[0]?.slots[0]?.features, {
	number: 'singular',
	case: 'nominative'
});
assert.equal(normalizeParadigmPayload(null), undefined);
assert.equal(paradigmRequestKey(request), 'lat:declension:diogenes:inflect:puella:{}');
