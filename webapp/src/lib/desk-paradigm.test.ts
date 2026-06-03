import { strict as assert } from 'node:assert';

import {
	candidateLearningLanguage,
	learningFosterBridges,
	learningGatewayTitle,
	learningNativeGateways,
	learningPrimarySummary,
	paradigmCandidateKey,
	paradigmCandidateSubtitle,
	paradigmCandidateTitle,
	paradigmFeatureEntries,
	paradigmSlotFeatureSummary,
	paradigmTableAxisNotes,
	paradigmTableLearningSummary,
	paradigmTableLearningTitle
} from './desk-paradigm';
import type { ParadigmResolutionCandidate } from './paradigm-resolution';

const candidate: ParadigmResolutionCandidate = {
	lemma: 'jyotis',
	entry_type: 'noun',
	part_of_speech: 'substantive',
	paradigm_kind: 'declension',
	observed_form: 'jyotin',
	slot_features: { case: 'locative', number: 'singular' },
	foster_display: 'in light',
	display_summary: 'locative singular',
	ranking_reasons: ['case-number-gender'],
	concept_ids: ['locative'],
	native_analyses: [
		{
			language: 'san',
			features: { case: 'locative', number: 'singular', gender: 'neuter' },
			source: 'fixture'
		}
	],
	functional_analyses: [{ relation: 'location_relation', native_feature: {}, confidence: 'high' }],
	paradigm_request: {
		source: 'heritage',
		language: 'san',
		lemma: 'jyotis',
		kind: 'declension',
		options: {}
	},
	confidence: 'high',
	provenance: ['fixture'],
	unresolved_reason: null,
	learning_overlay: {
		schema_version: 'langnet.learning_overlay.v1',
		status: 'fixture',
		concept_ids: ['locative'],
		missing_evidence: [],
		evidence_gaps: [],
		concepts: [
			{
				id: 'locative',
				kind: 'case',
				foster_gateway: 'where',
				plain_english: 'marks where something is situated',
				traditional: { san: 'saptamī', san_role: 'location' },
				native_gateways: [],
				source_evidence: [],
				foster_bridges: [
					{
						id: 'bridge-locative',
						status: 'reviewed',
						foster_terms: [],
						concept_ids: ['locative'],
						related_concept_ids: [],
						plain_english: 'ask where the word is located',
						learner_action: 'try a where-question',
						product_use: '',
						morphology_predicates: [],
						source_refs: [],
						summary_refs: [],
						caveats: []
					}
				]
			}
		]
	}
};

assert.equal(paradigmCandidateKey(candidate), 'san:declension:heritage:jyotis:{}');
assert.equal(paradigmCandidateTitle(candidate, 'fallback'), 'jyotis declension');
assert.ok(paradigmCandidateSubtitle(candidate).includes('form jyotin'));
assert.deepEqual(paradigmFeatureEntries(candidate).slice(0, 2), [
	{ key: 'case', value: 'locative' },
	{ key: 'number', value: 'singular' }
]);
assert.equal(learningGatewayTitle(candidate.learning_overlay?.concepts ?? []), 'where');
assert.equal(learningPrimarySummary(candidate), 'locative singular');
assert.equal(candidateLearningLanguage(candidate, 'grc'), 'san');
assert.deepEqual(
	learningNativeGateways(candidate.learning_overlay?.concepts ?? [], 'san').map((gateway) => [
		gateway.term,
		gateway.role
	]),
	[['saptamī', 'location']]
);
assert.equal(
	learningFosterBridges(candidate.learning_overlay?.concepts ?? [])[0]?.id,
	'bridge-locative'
);

const block = {
	label: 'Declension',
	dimensions: ['case', 'number'],
	slots: []
};

assert.equal(
	paradigmSlotFeatureSummary({ case: 'locative', number: 'singular' }),
	'case locative · number singular'
);
assert.equal(paradigmTableLearningTitle(candidate), 'Reading a declension table');
assert.ok(paradigmTableLearningSummary(candidate, block).includes('noun-form jobs'));
assert.deepEqual(paradigmTableAxisNotes(block), [
	{ label: 'case', note: 'job in the expression' },
	{ label: 'number', note: 'one, two, or many' }
]);
