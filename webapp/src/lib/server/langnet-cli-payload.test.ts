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

const baillyTranslatedSourcePayload = structuredClone(payload);
(baillyTranslatedSourcePayload.buckets[0] as Record<string, unknown>).witnesses = [
	{
		sense_anchor: 'sense:lex:logos#source',
		source_tool: 'bailly',
		gloss: 'parole : la parole, en general',
		evidence: {
			source_tool: 'bailly',
			source_ref: 'bailly:bailly-p1450-c1-0024',
			source_lang: 'fr',
			display_gloss: 'parole : la parole, en general'
		}
	}
];

const baillyTranslatedSourceResult = mapCliPayload(
	baillyTranslatedSourcePayload,
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

assert.equal(
	baillyTranslatedSourceResult.buckets[0]?.translation?.source_text,
	'parole : la parole, en general'
);
assert.equal(baillyTranslatedSourceResult.buckets[0]?.translation?.target_text, 'word, speech:');

const hugeSourcePayload = structuredClone(payload);
hugeSourcePayload.display.meanings[0].evidence_gloss = 'short source summary';
(hugeSourcePayload.buckets[0] as Record<string, unknown>).witnesses = [
	{
		evidence: {
			source_entry: {
				source_text: 'long source text '.repeat(500)
			}
		}
	}
];

const hugeSourceResult = mapCliPayload(
	hugeSourcePayload,
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

assert.equal(hugeSourceResult.buckets[0]?.translation?.source_text, 'short source summary');

const gaffiotErrorResult = mapCliPayload(
	{
		query: 'edo',
		source_tools: ['gaffiot'],
		display: {
			analysis: [],
			meanings: [
				{
					bucket_id: 'bucket:edo',
					sources: ['gaffiot'],
					source_langs: ['fr'],
					display_gloss: 'manger',
					evidence_gloss: 'manger',
					entries: [
						{
							source_tool: 'gaffiot',
							source_ref: 'gaffiot:gaffiot_22738',
							source_lang: 'fr',
							dictionary: 'gaffiot',
							headword: 'edo',
							translation: {
								available: false,
								translation_id: 'tr:gaffiot:edo:error',
								model: 'openai:google/gemini-2.5-flash',
								source_lexicon: 'gaffiot',
								source_text_hash: 'gaffiot-source-hash',
								source_text_lang: 'fr',
								target_lang: 'en',
								derived_from_tool: 'gaffiot',
								status: 'error'
							},
							source_entry: {
								dict: 'gaffiot',
								entry_id: 'gaffiot_22738',
								headword_norm: 'edo',
								variant_num: 1
							}
						}
					]
				}
			]
		},
		buckets: [{ bucket_id: 'bucket:edo' }],
		ranking: [
			{
				bucket_id: 'bucket:edo',
				source_tools: ['gaffiot'],
				bucket_lemmas: ['edo'],
				has_english_translation: false,
				has_bilingual_source: true
			}
		],
		translation_cache: {
			mode: 'cache',
			model: 'openai:google/gemini-2.5-flash',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 1, hits: 0, missing: 0, errors: 1, empty: 0 },
			after: { total: 1, hits: 0, missing: 0, errors: 1, empty: 0 }
		},
		request: {
			translation_mode: 'cache',
			tool_filter: ['gaffiot'],
			reader_lang: 'en'
		}
	},
	{
		language: 'lat',
		query: 'edo',
		dictionaries: ['gaffiot'],
		translationMode: 'cache',
		maxBuckets: 1,
		maxGlossChars: 1200,
		timeoutMs: 300_000
	},
	'gaffiot'
);

assert.equal(gaffiotErrorResult.buckets[0]?.translation?.available, false);
assert.equal(gaffiotErrorResult.buckets[0]?.translation?.translation_id, 'tr:gaffiot:edo:error');
assert.equal(gaffiotErrorResult.buckets[0]?.translation?.source_lexicon, 'gaffiot');
assert.equal(gaffiotErrorResult.buckets[0]?.translation?.entry_id, 'gaffiot_22738');
assert.equal(gaffiotErrorResult.buckets[0]?.translation?.occurrence, 1);
assert.equal(gaffiotErrorResult.buckets[0]?.translation?.source_text_hash, 'gaffiot-source-hash');
assert.equal(gaffiotErrorResult.buckets[0]?.translation?.model, 'openai:google/gemini-2.5-flash');

const dicoTranslatedResult = mapCliPayload(
	{
		query: 'dharma',
		source_tools: ['dico', 'translation'],
		display: {
			analysis: [],
			meanings: [
				{
					bucket_id: 'bucket:dharma',
					sources: ['dico', 'translation'],
					source_refs: ['dico:34.html#dharma:0'],
					source_langs: ['en', 'fr'],
					display_gloss: 'law, condition, proper nature',
					evidence_gloss: 'law, condition, proper nature',
					entries: [
						{
							source_tool: 'translation',
							source_ref: 'dico:34.html#dharma:0',
							source_lang: 'en',
							dictionary: 'dico',
							headword: 'dharma',
							translation: {
								available: true,
								translation_id: 'tr:dico:dharma:123',
								source_lexicon: 'dico',
								source_text_hash: 'dico-source-hash',
								source_text_lang: 'fr',
								target_lang: 'en',
								derived_from_tool: 'dico',
								derived_from_sense: 'sense:lex:dharma#source'
							}
						},
						{
							source_tool: 'dico',
							source_ref: 'dico:34.html#dharma:0',
							source_lang: 'fr',
							dictionary: 'dico',
							headword: 'dharma',
							sense_anchor: 'sense:lex:dharma#source',
							source_detail_summary: {
								text: 'phil. le Devoir, le Droit et la Justice'
							},
							translation: { available: false }
						}
					]
				}
			]
		},
		buckets: [
			{
				bucket_id: 'bucket:dharma',
				witnesses: [
					{
						sense_anchor: 'sense:lex:dharma#source',
						source_tool: 'dico',
						gloss: 'dharma [ dharman ] m. n. loi, condition, nature propre',
						evidence: {
							source_tool: 'dico',
							source_ref: 'dico:34.html#dharma:0',
							source_lang: 'fr',
							display_gloss: 'dharma [ dharman ] m. n. loi, condition, nature propre'
						}
					}
				]
			}
		],
		ranking: [
			{
				bucket_id: 'bucket:dharma',
				source_tools: ['dico'],
				bucket_lemmas: ['dharma'],
				has_english_translation: true,
				has_bilingual_source: true
			}
		],
		translation_cache: {
			mode: 'cache',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 1, hits: 1, missing: 0, errors: 0 },
			after: { total: 1, hits: 1, missing: 0, errors: 0 }
		},
		request: {
			translation_mode: 'cache',
			tool_filter: ['dico'],
			reader_lang: 'en'
		}
	},
	{
		language: 'san',
		query: 'dharma',
		dictionaries: ['dico'],
		translationMode: 'cache',
		maxBuckets: 1,
		maxGlossChars: 1200,
		timeoutMs: 300_000
	},
	'dico'
);

assert.equal(
	dicoTranslatedResult.buckets[0]?.translation?.source_text,
	'dharma [ dharman ] m. n. loi, condition, nature propre'
);
assert.equal(
	dicoTranslatedResult.buckets[0]?.translation?.target_text,
	'law, condition, proper nature'
);

const gaffiotTranslatedResult = mapCliPayload(
	{
		query: 'amo',
		source_tools: ['gaffiot', 'translation'],
		display: {
			analysis: [],
			meanings: [
				{
					bucket_id: 'bucket:amo',
					sources: ['gaffiot', 'translation'],
					source_refs: ['gaffiot:gaffiot_3731'],
					source_langs: ['en', 'fr'],
					display_gloss: 'to love, to have affection for',
					evidence_gloss: 'to love, to have affection for',
					source_detail_summary: {
						text: 'source refs: cf.; examples: Cic. Fam. 9, 7, 1'
					},
					entries: [
						{
							source_tool: 'translation',
							source_ref: 'gaffiot:gaffiot_3731',
							source_lang: 'en',
							dictionary: 'gaffiot',
							headword: 'amo',
							source_detail_summary: {
								text: 'source refs: cf.; examples: Cic. Fam. 9, 7, 1'
							},
							translation: {
								available: true,
								translation_id: 'tr:gaffiot:amo:123',
								source_lexicon: 'gaffiot',
								source_text_hash: 'gaffiot-source-hash',
								source_text_lang: 'fr',
								target_lang: 'en',
								derived_from_tool: 'gaffiot',
								derived_from_sense: 'sense:lex:amo#source'
							}
						},
						{
							source_tool: 'gaffiot',
							source_ref: 'gaffiot:gaffiot_3731',
							source_lang: 'fr',
							dictionary: 'gaffiot',
							headword: 'amo',
							sense_anchor: 'sense:lex:amo#source',
							source_detail_summary: {
								text: 'source refs: cf.; examples: Cic. Fam. 9, 7, 1'
							},
							source_entry: {
								dict: 'gaffiot',
								entry_id: 'gaffiot_3731',
								headword_norm: 'amo',
								source_text_chars: 3302,
								has_source_text: true
							},
							translation: { available: false }
						}
					]
				}
			]
		},
		buckets: [
			{
				bucket_id: 'bucket:amo',
				display_gloss: 'to love, to have affection for',
				witnesses: [
					{
						sense_anchor: 'sense:lex:amo#tr',
						source_tool: 'translation',
						gloss: 'to love, to have affection for',
						evidence: {
							source_tool: 'translation',
							derived_from_sense: 'sense:lex:amo#source'
						}
					},
					{
						sense_anchor: 'sense:lex:amo#source',
						source_tool: 'gaffiot',
						gloss: "āvī, ātum, āre, tr., 1 aimer, avoir de l'affection pour",
						evidence: {
							source_tool: 'gaffiot',
							source_lang: 'fr',
							display_gloss: "āvī, ātum, āre, tr., 1 aimer, avoir de l'affection pour"
						}
					}
				]
			}
		],
		ranking: [
			{
				bucket_id: 'bucket:amo',
				source_tools: ['gaffiot'],
				bucket_lemmas: ['amo'],
				has_english_translation: true,
				has_bilingual_source: true
			}
		],
		translation_cache: {
			mode: 'cache',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 1, hits: 1, missing: 0, errors: 0 },
			after: { total: 1, hits: 1, missing: 0, errors: 0 }
		},
		request: {
			translation_mode: 'cache',
			tool_filter: ['gaffiot'],
			reader_lang: 'en'
		}
	},
	{
		language: 'lat',
		query: 'amo',
		dictionaries: ['gaffiot'],
		translationMode: 'cache',
		maxBuckets: 1,
		maxGlossChars: 1200,
		timeoutMs: 300_000
	},
	'gaffiot'
);

assert.equal(
	gaffiotTranslatedResult.buckets[0]?.translation?.source_text,
	"āvī, ātum, āre, tr., 1 aimer, avoir de l'affection pour"
);
assert.notEqual(
	gaffiotTranslatedResult.buckets[0]?.translation?.source_text,
	'source refs: cf.; examples: Cic. Fam. 9, 7, 1'
);
assert.equal(
	gaffiotTranslatedResult.buckets[0]?.translation?.target_text,
	'to love, to have affection for'
);

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
