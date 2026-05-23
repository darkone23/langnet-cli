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
			concept_ids: ['case.genitive', 'number.singular', 'process.declension'],
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
			unresolved_reason: null,
			learning_overlay: {
				schema_version: 'langnet.learning_overlay.v1',
				status: 'mapped',
				concept_ids: ['case.genitive'],
				concepts: [
					{
						id: 'case.genitive',
						kind: 'case',
						foster_gateway: 'Possessing Function',
						plain_english: 'Marks belonging or relation.',
						traditional: {
							en: 'genitive',
							grc: 'γενική',
							lat: 'genetivus',
							san: 'ṣaṣṭhī vibhakti'
						},
						native_gateways: [
							{
								language: 'lat',
								label: 'Latin',
								term: 'genetivus',
								role: '',
								foster_gateway: 'Possessing Function',
								explanation:
									'Latin gateway: genetivus; LangNet uses Possessing Function as the learner gateway.'
							}
						],
						source_evidence: [
							{
								evidence_level: 'reader_segment',
								source_anchor_id: 'grammar.source.dionysius_thrax.ars_grammatica',
								work_id: 'langnet:reader:tlg:tlg0063.001',
								canonical_text_id: 'urn:ctsv2:grc:ars-grammatica-peri-grammatike-s',
								cts_work_urn: 'urn:cts:greekLit:tlg0063.tlg001',
								citation_path: '1.1.31.7',
								canonical_address: 'urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.31.7',
								label: 'Dionysius Thrax, Ars grammatica'
							}
						],
						foster_bridges: [
							{
								id: 'of-possession',
								status: 'promoted_match',
								foster_terms: ['of-possession'],
								concept_ids: ['case.genitive'],
								related_concept_ids: [],
								plain_english: 'Foster/Ossa possession or relation maps to the genitive concept.',
								learner_action: 'Ask what relation the form marks.',
								product_use: 'Show a possession/relation gateway beside genitive evidence.',
								morphology_predicates: ['case=genitive'],
								source_refs: ['page:69'],
								summary_refs: ['toc:1.6'],
								caveats: []
							}
						]
					}
				],
				missing_evidence: [],
				evidence_gaps: []
			}
		}
	],
	warnings: [],
	schema_version: 'langnet.paradigm_resolution.v1'
});

assert.equal(resolution?.schema_version, 'langnet.paradigm_resolution.v1');
assert.equal(resolution?.candidates[0]?.paradigm_request?.source, 'diogenes:inflect');
assert.deepEqual(resolution?.candidates[0]?.concept_ids, [
	'case.genitive',
	'number.singular',
	'process.declension'
]);
assert.deepEqual(resolution?.candidates[0]?.native_analyses[0]?.features, {
	case: 'genitive',
	number: 'singular'
});
assert.equal(
	resolution?.candidates[0]?.learning_overlay?.concepts[0]?.foster_gateway,
	'Possessing Function'
);
assert.equal(
	resolution?.candidates[0]?.learning_overlay?.concepts[0]?.foster_bridges[0]?.id,
	'of-possession'
);
assert.equal(
	resolution?.candidates[0]?.learning_overlay?.concepts[0]?.native_gateways[0]?.term,
	'genetivus'
);
assert.equal(
	resolution?.candidates[0]?.learning_overlay?.concepts[0]?.foster_bridges[0]?.learner_action,
	'Ask what relation the form marks.'
);

assert.equal(normalizeParadigmResolution(null), undefined);
assert.equal(normalizeParadigmResolution({ searched_form: 'x' })?.candidates.length, 0);
