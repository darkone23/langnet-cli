import assert from 'node:assert/strict';
import type { ParadigmPayload } from './paradigm';
import type { ParadigmResolutionCandidate } from './paradigm-resolution';
import {
	curateParadigmCandidates,
	learnerDisplayForm,
	paradigmPayloadHasForms,
	paradigmSlotMatchesCandidate,
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
		observed_form: null,
		slot_features: {},
		foster_display: '',
		display_summary: null,
		ranking_reasons: [],
		concept_ids: [],
		learning_overlay: null,
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

const fosterCandidates = [
	candidate('noise', {
		confidence: 'high',
		unresolved_reason: null,
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'noise',
			kind: 'declension',
			options: { gender: 'Mas' }
		}
	}),
	candidate('putra', {
		confidence: 'high',
		unresolved_reason: null,
		observed_form: 'putrāṇām',
		slot_features: { case: 'genitive', number: 'plural', gender: 'masculine' },
		foster_display: 'Possessing Function; Group; Male',
		ranking_reasons: ['observed-form', 'lemma', 'case-number-gender'],
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'putra',
			kind: 'declension',
			options: { gender: 'Mas' }
		}
	})
];

assert.equal(curateParadigmCandidates(fosterCandidates).visible[0].lemma, 'putra');

const sambuddhiCandidates = [
	candidate('sambuddhan', {
		confidence: 'high',
		observed_form: 'sambuddhan',
		slot_features: { case: 'accusative', number: 'singular', gender: 'neuter' },
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'sambuddhan',
			kind: 'declension',
			options: { gender: 'Neu' }
		},
		unresolved_reason: null
	}),
	candidate('sambuddhi', {
		confidence: 'high',
		observed_form: 'sambuddhi',
		slot_features: { case: 'accusative', number: 'singular', gender: 'neuter' },
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'sambuddhi',
			kind: 'declension',
			options: { gender: 'Neu' }
		},
		unresolved_reason: null
	})
];

assert.equal(
	curateParadigmCandidates(sambuddhiCandidates, 'sambuddhi').visible[0].lemma,
	'sambuddhi'
);

const gamCandidates = [
	candidate('ga_2', {
		confidence: 'medium',
		observed_form: 'ga_2',
		slot_features: { case: 'accusative', number: 'singular', gender: 'neuter' },
		ranking_reasons: ['observed-form', 'ambiguous-analysis', 'case-number-gender'],
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'ga_2',
			kind: 'declension',
			options: { gender: 'Neu' }
		},
		unresolved_reason: null
	}),
	candidate('gan', {
		confidence: 'high',
		observed_form: 'gan',
		slot_features: { case: 'accusative', number: 'singular', gender: 'masculine' },
		ranking_reasons: ['observed-form', 'case-number-gender'],
		paradigm_request: {
			source: 'heritage:sktdeclin',
			language: 'san',
			lemma: 'gan',
			kind: 'declension',
			options: { gender: 'Mas' }
		},
		unresolved_reason: null
	})
];

assert.equal(curateParadigmCandidates(gamCandidates, 'ga_2').visible[0].lemma, 'gan');
assert.equal(learnerDisplayForm('ga_2'), 'ga');
assert.equal(learnerDisplayForm('ga_2: accusative singular'), 'ga: accusative singular');

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

assert.equal(
	paradigmSlotMatchesCandidate(
		{
			features: { case: 'genitive', number: 'singular' },
			forms: [{ text: 'λόγου', normalized: 'λόγου', source_key: 'lo/gou' }],
			source_label: '',
			is_ambiguous: false
		},
		candidate('λόγος', {
			observed_form: 'λόγου',
			slot_features: { case: 'genitive', number: 'singular' }
		}),
		'λόγου'
	),
	true
);

assert.deepEqual(sanskritParadigmLemmaFallbacks('aṅga_1'), ['aṅga_1', 'anga']);
assert.deepEqual(sanskritParadigmLemmaFallbacks('jala'), ['jala']);
