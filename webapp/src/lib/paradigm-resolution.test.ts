import assert from 'node:assert/strict';
import { normalizeParadigmResolution } from './paradigm-resolution';

const resolution = normalizeParadigmResolution({
	searched_form: 'puellae',
	normalized_form: 'puellae',
	language: 'lat',
	candidates: [
		{
			lemma: 'puella',
			entry_type: 'variant',
			part_of_speech: 'noun',
			paradigm_kind: 'declension',
			native_analyses: [
				{
					language: 'lat',
					features: { case: 'genitive', number: 'singular' },
					source: 'whitakers'
				}
			],
			functional_analyses: [
				{
					relation: 'possession_or_association',
					native_feature: { case: 'genitive', number: 'singular' },
					confidence: 'medium'
				}
			],
			paradigm_request: {
				source: 'diogenes:inflect',
				language: 'lat',
				lemma: 'puella',
				kind: 'declension',
				options: {}
			},
			confidence: 'medium',
			provenance: ['whitakers'],
			unresolved_reason: null
		}
	],
	warnings: [],
	schema_version: 'langnet.paradigm_resolution.v1'
});

assert.equal(resolution?.schema_version, 'langnet.paradigm_resolution.v1');
assert.equal(resolution?.candidates[0]?.paradigm_request?.source, 'diogenes:inflect');
assert.deepEqual(resolution?.candidates[0]?.native_analyses[0]?.features, {
	case: 'genitive',
	number: 'singular'
});

assert.equal(normalizeParadigmResolution(null), undefined);
assert.equal(normalizeParadigmResolution({ searched_form: 'x' })?.candidates.length, 0);
