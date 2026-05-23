import assert from 'node:assert/strict';
import { mapCliPayload } from './langnet-cli';

const payload = {
	query: 'logos',
	source_tools: ['translation'],
	display: {
		analysis: [],
		meanings: [
			{
				bucket_id: 'bucket:logos',
				sources: ['translation'],
				source_langs: ['en'],
				display_gloss: 'word, speech:',
				evidence_gloss: 'word, speech:',
				entries: [
					{
						source_tool: 'translation',
						source_ref: 'bailly:bailly-p1450-c1-0024',
						source_lang: 'en',
						dictionary: 'bailly',
						headword: 'logos',
						translation: {
							available: true,
							translation_id: 'tr:bailly:logos:123',
							model: 'openai:google/gemini-2.5-flash',
							source_lexicon: 'bailly',
							source_text_hash: 'source-hash',
							source_text_lang: 'fr',
							target_lang: 'en',
							derived_from_tool: 'bailly'
						}
					}
				]
			}
		]
	},
	buckets: [{ bucket_id: 'bucket:logos' }],
	ranking: [
		{
			bucket_id: 'bucket:logos',
			source_tools: ['bailly'],
			bucket_lemmas: ['logos'],
			has_english_translation: true,
			has_bilingual_source: true
		}
	],
	translation_cache: {
		mode: 'cache',
		model: 'openai:google/gemini-2.5-flash',
		cache_available: true,
		populate: false,
		written: 0,
		before: { total: 1, hits: 1, missing: 0, errors: 0, empty: 0 },
		after: { total: 1, hits: 1, missing: 0, errors: 0, empty: 0 }
	},
	request: {
		translation_mode: 'cache',
		tool_filter: ['bailly'],
		reader_lang: 'en'
	}
};

const result = mapCliPayload(
	payload,
	{
		language: 'grc',
		query: 'logos',
		dictionaries: ['bailly'],
		translationMode: 'cache',
		maxBuckets: 1,
		maxGlossChars: 1200,
		timeoutMs: 300_000
	},
	'bailly'
);

assert.equal(result.buckets[0]?.translation?.model, 'openai:google/gemini-2.5-flash');
assert.equal(result.buckets[0]?.translation?.translation_id, 'tr:bailly:logos:123');
assert.equal(result.buckets[0]?.translation?.source_lexicon, 'bailly');
assert.equal(result.buckets[0]?.translation?.source_text_hash, 'source-hash');
assert.equal(result.buckets[0]?.translation?.entry_id, 'bailly-p1450-c1-0024');

const learningResult = mapCliPayload(
	{
		query: 'puellae',
		source_tools: ['whitakers'],
		display: { analysis: [], meanings: [] },
		buckets: [],
		ranking: [],
		translation_cache: {
			mode: 'cache',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 0, hits: 0, missing: 0, errors: 0 },
			after: { total: 0, hits: 0, missing: 0, errors: 0 }
		},
		paradigm_resolution: {
			searched_form: 'puellae',
			normalized_form: 'puellae',
			language: 'lat',
			candidates: [
				{
					lemma: 'puella',
					entry_type: 'variant',
					part_of_speech: 'noun',
					paradigm_kind: 'declension',
					observed_form: 'puellae',
					slot_features: { case: 'genitive', number: 'singular' },
					foster_display: 'Possessing Function; Single',
					display_summary: 'puellae: genitive singular',
					ranking_reasons: [],
					concept_ids: ['case.genitive', 'number.singular', 'process.declension'],
					native_analyses: [],
					functional_analyses: [],
					paradigm_request: null,
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
									lat: 'genetivus',
									grc: 'γενική',
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
								source_evidence: [],
								foster_bridges: [
									{
										id: 'of-possession',
										status: 'promoted_match',
										foster_terms: ['of-possession'],
										concept_ids: ['case.genitive'],
										related_concept_ids: [],
										plain_english:
											'Foster/Ossa possession or relation maps to the genitive concept.',
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
		},
		request: {
			translation_mode: 'cache',
			tool_filter: ['whitakers'],
			reader_lang: 'en'
		}
	},
	{
		language: 'lat',
		query: 'puellae',
		dictionaries: ['whitakers'],
		translationMode: 'cache',
		maxBuckets: 1,
		maxGlossChars: 1200,
		timeoutMs: 300_000
	},
	'whitakers'
);

assert.equal(
	learningResult.paradigm_resolution?.candidates[0]?.learning_overlay?.concepts[0]?.foster_gateway,
	'Possessing Function'
);
assert.equal(
	learningResult.paradigm_resolution?.candidates[0]?.learning_overlay?.concepts[0]
		?.foster_bridges[0]?.id,
	'of-possession'
);
assert.equal(
	learningResult.paradigm_resolution?.candidates[0]?.learning_overlay?.concepts[0]
		?.native_gateways[0]?.term,
	'genetivus'
);
assert.equal(
	learningResult.paradigm_resolution?.candidates[0]?.learning_overlay?.concepts[0]
		?.foster_bridges[0]?.learner_action,
	'Ask what relation the form marks.'
);

console.log('langnet-cli payload mapping ok');
