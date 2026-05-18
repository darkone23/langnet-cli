import assert from 'node:assert/strict';
import type { ParadigmPayload } from './paradigm';
import type { ParadigmResolutionCandidate } from './paradigm-resolution';
import {
	curateParadigmCandidates,
	paradigmPayloadHasForms,
	paradigmSlotGroups,
	sanskritParadigmLemmaFallbacks
} from './paradigm-ui';

function candidate(
	lemma: string,
	overrides: Partial<ParadigmResolutionCandidate> = {}
): ParadigmResolutionCandidate {
	return {
		lemma,
		entry_type: 'root',
		part_of_speech: 'noun',
		paradigm_kind: 'declension',
		native_analyses: [],
		functional_analyses: [],
		paradigm_request: null,
		confidence: 'low',
		provenance: ['test'],
		unresolved_reason: 'missing_gender_or_declension',
		...overrides
	};
}

const ashtangaCandidates = [
	candidate('aṅga_1', {
		confidence: 'high',
		unresolved_reason: null,
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'aṅga_1',
			kind: 'declension',
			options: { gender: 'Mas' }
		}
	}),
	candidate('aṣṭan'),
	candidate('aṅga_2'),
	candidate('aśtanga'),
	candidate('ashtanga'),
	candidate('aṣtanga')
];

const curatedAshtanga = curateParadigmCandidates(ashtangaCandidates);
assert.deepEqual(
	curatedAshtanga.visible.map((item) => item.lemma),
	['aṅga_1']
);
assert.equal(curatedAshtanga.hiddenCount, 5);

const unresolvedOnly = curateParadigmCandidates([
	candidate('unknown-a'),
	candidate('unknown-b', { confidence: 'medium' }),
	candidate('unknown-c')
]);
assert.deepEqual(
	unresolvedOnly.visible.map((item) => item.lemma),
	['unknown-b']
);
assert.equal(unresolvedOnly.hiddenCount, 2);

const emptyPayload = {
	schema_version: 'langnet.paradigm.v1',
	language: 'san',
	lemma: 'aṅga_1',
	kind: 'declension',
	source: 'heritage:sktdeclin',
	source_request: {},
	paradigms: [{ label: 'aṅga_1 declension', dimensions: ['case', 'number'], slots: [] }],
	warnings: ['heritage_declension_table_not_found']
} satisfies ParadigmPayload;

assert.equal(paradigmPayloadHasForms(emptyPayload), false);

const populatedPayload = {
	...emptyPayload,
	paradigms: [
		{
			label: 'ratio declension',
			dimensions: ['number', 'case'],
			slots: [
				{
					features: { number: 'singular', case: 'nominative' },
					forms: [{ text: 'ratio', normalized: 'ratio', source_key: 'ratio' }],
					source_label: '',
					is_ambiguous: false
				}
			]
		}
	]
} satisfies ParadigmPayload;

assert.equal(paradigmPayloadHasForms(populatedPayload), true);

const amoBlock = {
	label: 'amo conjugation',
	dimensions: ['tense', 'mood', 'voice', 'person', 'number'],
	slots: [
		{
			features: {
				tense: 'present',
				mood: 'indicative',
				voice: 'active',
				person: '1',
				number: 'singular'
			},
			forms: [{ text: 'amo', normalized: 'amo', source_key: 'amo' }],
			source_label: '',
			is_ambiguous: false
		},
		{
			features: {
				tense: 'present',
				mood: 'indicative',
				voice: 'passive',
				person: '1',
				number: 'singular'
			},
			forms: [{ text: 'amor', normalized: 'amor', source_key: 'amor' }],
			source_label: '',
			is_ambiguous: false
		}
	]
};

assert.deepEqual(
	paradigmSlotGroups(amoBlock).map((group) => group.label),
	['Indicative · present · active', 'Indicative · present · passive']
);

assert.deepEqual(sanskritParadigmLemmaFallbacks('aṅga_1'), ['aṅga_1', 'anga']);
assert.deepEqual(sanskritParadigmLemmaFallbacks('jala'), ['jala']);
