import type { ParadigmResolutionPayload } from './paradigm-resolution';

export type LanguageMode = 'san' | 'grc' | 'lat';
export type SearchBackend = 'sample' | 'cli';
export type TranslationMode = 'off' | 'cache' | 'populate' | 'auto' | 'do-it-all';

export type ToolId =
	| 'cdsl'
	| 'heritage'
	| 'dico'
	| 'diogenes'
	| 'bailly'
	| 'cts_index'
	| 'spacy'
	| 'cltk'
	| 'whitakers'
	| 'gaffiot'
	| 'lewis_1890';

export type ToolRequest = ToolId | 'all';

export type ToolMeta = {
	id: ToolId;
	language: LanguageMode;
	label: string;
	shortLabel: string;
	kind: string;
	description: string;
};

export type EncounterBucket = {
	bucket_id: string;
	display_gloss: string;
	normalized_gloss: string;
	bucket_lemmas: string[];
	source_tools: ToolId[];
	source_refs: string[];
	reasons: string[];
	witnesses: {
		tool: ToolId;
		label: string;
		detail: string;
		dictionary?: string;
		headword?: string;
		lexeme_anchor?: string;
		source_ref?: string;
	}[];
	witness_count: number;
	preferred_lemma_rank: number;
	effective_preferred_lemma_rank: number;
	learner_quality_order: number;
	has_english_translation: boolean;
	has_source_translation: boolean;
	source_langs: string[];
	reader_lang: 'en';
	evidence_note: string;
	translation_note: string;
	translation?: {
		available: boolean;
		translation_id?: string;
		source_tool?: ToolId;
		source_lexicon?: ToolId;
		entry_id?: string;
		occurrence?: number;
		headword_norm?: string;
		source_text_hash?: string;
		source_lang: string;
		source_label: string;
		source_text: string;
		target_lang: 'en';
		target_text: string;
		model?: string;
	};
};

export type EncounterAnalysis = {
	form: string;
	lemma: string;
	analysis: string;
	source: string;
	foster_display: string;
	display_text: string;
};

export type EncounterComponentMeaning = {
	bucket_id: string;
	display_gloss: string;
	source_tools: ToolId[];
	source_refs: string[];
	source_langs: string[];
	translation?: {
		available: boolean;
		translation_id?: string;
		source_tool?: ToolId;
		source_lexicon?: ToolId;
		entry_id?: string;
		occurrence?: number;
		headword_norm?: string;
		source_text_hash?: string;
		source_lang: string;
		source_label: string;
		source_text: string;
		target_lang: 'en';
		target_text: string;
		model?: string;
	};
};

export type EncounterComponent = {
	surface: string;
	lemma: string;
	display: string;
	role: string;
	analysis: string;
	source_tool: ToolId;
	lookup_terms: string[];
	evidence: {
		status: string;
		source: string;
		lookup_tool_filter: ToolRequest;
		meanings: EncounterComponentMeaning[];
		error: string;
	};
};

export type TranslationCache = {
	mode: TranslationMode;
	cache_db?: string;
	model?: string;
	cache_available: boolean;
	populate: boolean;
	written: number;
	before: {
		total: number;
		hits: number;
		missing: number;
		errors: number;
		empty?: number;
	};
	after: {
		total: number;
		hits: number;
		missing: number;
		errors: number;
		empty?: number;
	};
};

export type EncounterWordIndexAnchor = {
	language: LanguageMode;
	query: string;
	source: string;
	dictionary: string;
	anchor_status: string;
	lexeme_id: string;
	wheel_id: string;
	wheel_order_key: string;
	canonical_name: string;
	canonical_key: string;
	source_name: string;
	source_ref: string;
	index_entry_id: string;
	source_order_id: string;
	source_order_key: string;
};

export type EncounterWordIndexContext = {
	request: {
		language: LanguageMode;
		query: string;
		query_candidates: string[];
		source: string;
		radius: number;
	};
	anchors: EncounterWordIndexAnchor[];
	warnings: {
		source?: string;
		message: string;
	}[];
};

export type EncounterResult = {
	query: string;
	language: LanguageMode;
	dictionaries: ToolRequest[];
	source_tools: ToolId[];
	lexeme_anchors: string[];
	buckets: EncounterBucket[];
	analysis: EncounterAnalysis[];
	components: EncounterComponent[];
	paradigm_resolution?: ParadigmResolutionPayload;
	word_index?: EncounterWordIndexContext;
	translation_cache: TranslationCache;
	warnings: string[];
	request: {
		translation_mode: TranslationMode;
		tool_filter: ToolRequest[];
		reader_lang: 'en';
		cache_policy?: string;
		normalization_cache_writes?: boolean;
		translation_cache_writes?: boolean;
	};
	backend: SearchBackend;
	error?: string;
};

export type WordRecommendationItem = {
	language: LanguageMode;
	query: string;
	key: string;
	display: string;
	primary_lexeme: string;
	lexeme_anchors: string[];
	summary: string;
	learner_note: string;
	mnemonic: string;
	difficulty: string;
	confidence: string;
	ambiguity: {
		has_multiple_lexemes: boolean;
		lexeme_count: number;
		note: string;
	};
	recommended_request: {
		language: LanguageMode;
		q: string;
		dictionary: ToolRequest;
		translation: TranslationMode;
		backend: SearchBackend;
	};
	source_basis: {
		tool: string;
		source_ref: string;
		lexeme_anchor: string;
		evidence: string;
	}[];
	display_forms: {
		native: string;
		roman: string;
		canonical: string;
		script: string;
	};
	ui: {
		href_query: string;
		badge: string;
		short_gloss: string;
	};
	novelty?: {
		is_repeat: boolean;
		avoided_recent_count: number;
		fresh_requested: boolean;
		reason: string;
	};
};

export type WordRecommendationResult = {
	schema_version: string;
	generated_at: string;
	suggested_ttl_seconds: number;
	items: WordRecommendationItem[];
	exhaustion?: {
		fresh_requested: boolean;
		fresh_satisfied: boolean;
		reason: string | null;
	};
	warnings: {
		language?: LanguageMode;
		query?: string;
		message: string;
	}[];
	error?: string;
};

export const languageModes: { id: LanguageMode; label: string }[] = [
	{ id: 'san', label: 'Sanskrit' },
	{ id: 'grc', label: 'Greek' },
	{ id: 'lat', label: 'Latin' }
];

export const tools: ToolMeta[] = [
	{
		id: 'cdsl',
		language: 'san',
		label: 'CDSL Sanskrit dictionaries',
		shortLabel: 'CDSL',
		kind: 'dictionary',
		description: 'Long-form Sanskrit dictionary entries and source glosses.'
	},
	{
		id: 'heritage',
		language: 'san',
		label: 'Sanskrit Heritage',
		shortLabel: 'Heritage',
		kind: 'morphology',
		description: 'Sanskrit forms, lemmas, and morphology notes.'
	},
	{
		id: 'dico',
		language: 'san',
		label: 'DICO Sanskrit',
		shortLabel: 'DICO',
		kind: 'translation',
		description: 'Sanskrit source entries with reader English when available.'
	},
	{
		id: 'diogenes',
		language: 'grc',
		label: 'Diogenes / LSJ',
		shortLabel: 'Diogenes',
		kind: 'dictionary',
		description: 'Greek dictionary entries with morphology and citation context.'
	},
	{
		id: 'bailly',
		language: 'grc',
		label: 'Bailly',
		shortLabel: 'Bailly',
		kind: 'dictionary',
		description: 'Greek-French dictionary entries with reader English when available.'
	},
	{
		id: 'cts_index',
		language: 'grc',
		label: 'CTS index',
		shortLabel: 'CTS',
		kind: 'citation',
		description: 'Passage lookup and source references.'
	},
	{
		id: 'spacy',
		language: 'grc',
		label: 'spaCy Greek',
		shortLabel: 'spaCy',
		kind: 'morphology',
		description: 'Compact Greek token and morphology analysis.'
	},
	{
		id: 'cltk',
		language: 'grc',
		label: 'CLTK Greek',
		shortLabel: 'CLTK',
		kind: 'lexicon',
		description: 'Supplemental Greek lexicon, transliteration, and IPA support.'
	},
	{
		id: 'diogenes',
		language: 'lat',
		label: 'Diogenes / Lewis & Short',
		shortLabel: 'Diogenes',
		kind: 'dictionary',
		description: 'Lewis & Short Latin entries kept in source reading order.'
	},
	{
		id: 'lewis_1890',
		language: 'lat',
		label: 'Lewis 1890',
		shortLabel: 'Lewis 1890',
		kind: 'dictionary',
		description: 'Lewis smaller Latin-English entries from the standalone upstream source.'
	},
	{
		id: 'gaffiot',
		language: 'lat',
		label: 'Gaffiot',
		shortLabel: 'Gaffiot',
		kind: 'dictionary',
		description: 'French-Latin entries with reader English when available.'
	},
	{
		id: 'whitakers',
		language: 'lat',
		label: "Whitaker's Words",
		shortLabel: 'Words',
		kind: 'morphology',
		description: 'Latin forms, morphology, and compact lexical analysis.'
	},
	{
		id: 'cltk',
		language: 'lat',
		label: 'CLTK Latin',
		shortLabel: 'CLTK',
		kind: 'lexicon',
		description: 'Supplemental Latin lexicon and morphology support.'
	}
];

const encounters: EncounterResult[] = [
	{
		query: 'dharma',
		language: 'san',
		dictionaries: ['all'],
		source_tools: ['cdsl', 'heritage', 'dico'],
		lexeme_anchors: ['lex:darma', 'lex:darmah', 'lex:dharma', 'lex:dharman'],
		buckets: [
			{
				bucket_id: 'bucket:san-dharma-main',
				display_gloss:
					'dharma [dharman] m. n. law, condition, inherent nature | duty, right conduct, virtue | religious or civic obligation | the teaching or order that sustains a way of life',
				normalized_gloss:
					'dharma dharman law condition inherent nature duty right conduct virtue religious civic obligation',
				bucket_lemmas: ['dharma', 'dharman', 'dharmaḥ'],
				source_tools: ['cdsl', 'heritage', 'dico'],
				source_refs: ['cdsl:mw:dharma', 'heritage:dharma', 'dico:dharma'],
				reasons: [
					'matches preferred morphology/reduction lemma',
					'ordered by source entry position',
					'sources: cdsl, heritage, dico'
				],
				witnesses: [
					{
						tool: 'cdsl',
						label: 'Monier-Williams style entry',
						detail: 'Long-form lexical entry groups law, duty, virtue, and sustaining order.'
					},
					{
						tool: 'heritage',
						label: 'Lemma reduction',
						detail:
							'Entered form is anchored to dharma / dharman rather than a compound-only match.'
					},
					{
						tool: 'dico',
						label: 'Translated entry layer',
						detail: 'Provides a source text layer that can be read beside the English rendering.'
					}
				],
				witness_count: 4,
				preferred_lemma_rank: 0,
				effective_preferred_lemma_rank: 0,
				learner_quality_order: 0,
				has_english_translation: true,
				has_source_translation: true,
				source_langs: ['en', 'fr', 'sa'],
				reader_lang: 'en',
				evidence_note: 'Best first stop: dictionary evidence and lemma reduction agree.',
				translation_note:
					'English reader gloss is available; DICO can supply translated entry text.',
				translation: {
					available: true,
					source_tool: 'dico',
					source_lang: 'fr',
					source_label: 'DICO FR',
					source_text:
						'dharma: loi, devoir, vertu; ordre qui soutient la conduite et la vie religieuse',
					target_lang: 'en',
					target_text:
						'dharma [dharman] m. n. law, condition, inherent nature | duty, right conduct, virtue | religious or civic obligation | the teaching or order that sustains a way of life'
				}
			},
			{
				bucket_id: 'bucket:san-dharma-compounds',
				display_gloss:
					'dharma as compound base: dharmakṣetra, dharmarāja, dharmaśāstra | law-field, king of justice, legal or ethical treatise',
				normalized_gloss:
					'dharma compound base dharmaksetra dharmaraja dharmasastra legal ethical treatise',
				bucket_lemmas: ['dharmakṣetra', 'dharmarāja', 'dharmaśāstra'],
				source_tools: ['cdsl'],
				source_refs: ['cdsl:mw:dharmaksetra', 'cdsl:mw:dharmaraja', 'cdsl:mw:dharmasastra'],
				reasons: ['fallback expansion from dictionary compounds', 'source: cdsl'],
				witnesses: [
					{
						tool: 'cdsl',
						label: 'Compound expansion',
						detail: 'Useful after the headword sense, but not the primary reader path.'
					}
				],
				witness_count: 1,
				preferred_lemma_rank: 2,
				effective_preferred_lemma_rank: 2,
				learner_quality_order: 2,
				has_english_translation: false,
				has_source_translation: false,
				source_langs: ['en'],
				reader_lang: 'en',
				evidence_note:
					'Secondary material: compound evidence is helpful once the headword is understood.',
				translation_note:
					'Source gloss is already readable, but no separate translated entry is attached.'
			},
			{
				bucket_id: 'bucket:san-dharma-form',
				display_gloss:
					'dharmaḥ: nominative singular masculine form | morphology witness points back to dharma',
				normalized_gloss: 'dharmah nominative singular masculine form morphology witness dharma',
				bucket_lemmas: ['dharmaḥ', 'dharma'],
				source_tools: ['heritage'],
				source_refs: ['heritage:dharmaH'],
				reasons: ['morphology-only evidence', 'source: heritage'],
				witnesses: [
					{
						tool: 'heritage',
						label: 'Inflected-form analysis',
						detail: 'Explains how a surface form should be routed to the lexical headword.'
					}
				],
				witness_count: 1,
				preferred_lemma_rank: 1,
				effective_preferred_lemma_rank: 1,
				learner_quality_order: 1,
				has_english_translation: false,
				has_source_translation: false,
				source_langs: ['sa'],
				reader_lang: 'en',
				evidence_note:
					'Form evidence: useful for routing, not a replacement for dictionary glosses.',
				translation_note: 'Morphology evidence only; no translated dictionary entry is attached.'
			}
		],
		analysis: [],
		components: [],
		translation_cache: {
			mode: 'auto',
			cache_available: true,
			populate: true,
			written: 0,
			before: { total: 3, hits: 3, missing: 0, errors: 0 },
			after: { total: 3, hits: 3, missing: 0, errors: 0 }
		},
		warnings: [],
		request: {
			translation_mode: 'auto',
			tool_filter: ['all'],
			reader_lang: 'en'
		},
		backend: 'sample'
	},
	{
		query: 'logos',
		language: 'grc',
		dictionaries: ['all'],
		source_tools: ['diogenes', 'cts_index', 'spacy', 'cltk'],
		lexeme_anchors: ['lex:logos', 'lex:λόγος', 'lex:logou'],
		buckets: [
			{
				bucket_id: 'bucket:grc-logos-speech',
				display_gloss:
					'λόγος, logos: word, speech, statement | account, narrative, explanation | reasoned argument | plea, proposal, public address | inward thought or reckoning when the context turns philosophical',
				normalized_gloss:
					'logos word speech statement account narrative explanation reasoned argument',
				bucket_lemmas: ['λόγος', 'logos'],
				source_tools: ['diogenes', 'cts_index', 'cltk'],
				source_refs: [
					'diogenes:lsj:logos',
					'cts_index:tlg0012.tlg001:1.5',
					'cts_index:tlg0012.tlg001:2.212',
					'cts_index:tlg0059.tlg030:17a',
					'cts_index:tlg0086.tlg010:1253a',
					'cts_index:tlg0007.tlg047:4.1',
					'cts_index:tlg0011.tlg003:904',
					'cts_index:tlg0527.tlg001:john.1.1',
					'cts_index:tlg0557.tlg001:12',
					'cltk:lemma:logos'
				],
				reasons: [
					'dictionary lemma match',
					'citation index available',
					'sources: diogenes, cts_index, cltk'
				],
				witnesses: [
					{
						tool: 'diogenes',
						label: 'LSJ-style dictionary entry',
						detail:
							'Long entry begins with word, speech, statement, and account before later abstractions.'
					},
					{
						tool: 'cts_index',
						label: 'Citation index',
						detail:
							'Represents the kind of long citation list that should stay collapsed until the reader asks for evidence.'
					},
					{
						tool: 'cltk',
						label: 'Lexicon support',
						detail: 'Supplies transliteration and compact lexical confirmation for the same lemma.'
					}
				],
				witness_count: 4,
				preferred_lemma_rank: 0,
				effective_preferred_lemma_rank: 0,
				learner_quality_order: 0,
				has_english_translation: true,
				has_source_translation: false,
				source_langs: ['en', 'grc'],
				reader_lang: 'en',
				evidence_note: 'Best first stop: dictionary meaning plus citation affordance.',
				translation_note: 'Reader-ready English gloss from LSJ-style dictionary evidence.'
			},
			{
				bucket_id: 'bucket:grc-logos-form',
				display_gloss:
					'λογου / logou: genitive singular analysis for λόγος; useful when a reader enters an inflected form',
				normalized_gloss: 'logou genitive singular analysis logos inflected form',
				bucket_lemmas: ['λόγου', 'logou', 'logos'],
				source_tools: ['spacy', 'cltk'],
				source_refs: ['spacy:grc:logou', 'cltk:morph:logos'],
				reasons: ['supplemental morphology match', 'sources: spacy, cltk'],
				witnesses: [
					{
						tool: 'spacy',
						label: 'Token analysis',
						detail: 'Treats the entered surface as an inflected form rather than a headword.'
					},
					{
						tool: 'cltk',
						label: 'Morphology confirmation',
						detail: 'Routes genitive singular evidence back to λόγος.'
					}
				],
				witness_count: 2,
				preferred_lemma_rank: 1,
				effective_preferred_lemma_rank: 1,
				learner_quality_order: 1,
				has_english_translation: false,
				has_source_translation: false,
				source_langs: ['grc'],
				reader_lang: 'en',
				evidence_note: 'Form evidence: useful when the entered word is inflected.',
				translation_note: 'Morphology evidence only; no reader translation attached.'
			},
			{
				bucket_id: 'bucket:grc-logos-account',
				display_gloss:
					'λόγος as account or reckoning | proportion, relation, measure | reasoned explanation in philosophical prose',
				normalized_gloss:
					'logos account reckoning proportion relation measure reasoned explanation philosophy',
				bucket_lemmas: ['λόγος', 'logos'],
				source_tools: ['diogenes'],
				source_refs: ['diogenes:lsj:logos:extended'],
				reasons: ['secondary dictionary sense cluster', 'source: diogenes'],
				witnesses: [
					{
						tool: 'diogenes',
						label: 'Extended dictionary senses',
						detail: 'A later sense cluster that is valuable but less immediate than speech/word.'
					}
				],
				witness_count: 1,
				preferred_lemma_rank: 0,
				effective_preferred_lemma_rank: 0,
				learner_quality_order: 2,
				has_english_translation: true,
				has_source_translation: false,
				source_langs: ['en', 'grc'],
				reader_lang: 'en',
				evidence_note: 'Deeper dictionary material: useful after the primary gloss is inspected.',
				translation_note: 'Reader-ready English gloss from Diogenes dictionary evidence.'
			}
		],
		analysis: [],
		components: [],
		translation_cache: {
			mode: 'auto',
			cache_available: true,
			populate: true,
			written: 1,
			before: { total: 3, hits: 2, missing: 1, errors: 0 },
			after: { total: 3, hits: 3, missing: 0, errors: 0 }
		},
		warnings: [],
		request: {
			translation_mode: 'auto',
			tool_filter: ['all'],
			reader_lang: 'en'
		},
		backend: 'sample'
	},
	{
		query: 'nexus',
		language: 'lat',
		dictionaries: ['all'],
		source_tools: ['diogenes', 'gaffiot', 'whitakers', 'cltk'],
		lexeme_anchors: ['lex:nexus', 'lex:necto'],
		buckets: [
			{
				bucket_id: 'bucket:lat-nexus-binding',
				display_gloss:
					'nexus: a binding, tying, fastening | legal obligation | connection or interlacing',
				normalized_gloss: 'nexus binding tying fastening legal obligation connection interlacing',
				bucket_lemmas: ['nexus', 'necto'],
				source_tools: ['diogenes', 'gaffiot', 'whitakers', 'cltk'],
				source_refs: ['diogenes:lat:nexus', 'gaffiot:nexus', 'whitakers:nexus', 'cltk:lat:nexus'],
				reasons: [
					'lemma match',
					'dictionary and morphology agree',
					'sources: diogenes, gaffiot, whitakers, cltk'
				],
				witnesses: [
					{
						tool: 'gaffiot',
						label: 'Gaffiot dictionary source',
						detail:
							'French entry text is available and can be translated for the English reader layer.'
					},
					{
						tool: 'diogenes',
						label: 'Latin dictionary witness',
						detail: 'Confirms the headword bucket around binding, connection, and legal obligation.'
					},
					{
						tool: 'whitakers',
						label: "Whitaker's morphology",
						detail: 'Confirms noun analysis and relation to necto / nexus.'
					},
					{
						tool: 'cltk',
						label: 'Supplemental lexicon',
						detail: 'Provides compact Latin lexical support for the same bucket.'
					}
				],
				witness_count: 3,
				preferred_lemma_rank: 0,
				effective_preferred_lemma_rank: 0,
				learner_quality_order: 0,
				has_english_translation: true,
				has_source_translation: true,
				source_langs: ['en', 'fr', 'lat'],
				reader_lang: 'en',
				evidence_note:
					'Best first stop: dictionary evidence agrees, and the French source can be toggled.',
				translation_note:
					'Gaffiot contributes French entry text with an English reader translation available.',
				translation: {
					available: true,
					source_tool: 'gaffiot',
					source_lang: 'fr',
					source_label: 'Gaffiot FR',
					source_text:
						'nexus: action de lier, enlacement, entrelacement | obligation juridique contractée par le débiteur | lien ou rapport entre des choses | enchaînement, connexion, réunion de parties | par extension, dépendance ou attache',
					target_lang: 'en',
					target_text:
						'nexus: a binding, tying, fastening | legal obligation contracted by a debtor | connection or relation between things | chain, connection, joining of parts | by extension, dependence or attachment'
				}
			},
			{
				bucket_id: 'bucket:lat-nexus-legal',
				display_gloss:
					'nexus as legal condition: obligation between creditor and debtor | one reduced to quasi-slavery for debt',
				normalized_gloss: 'nexus legal condition obligation creditor debtor quasi slavery debt',
				bucket_lemmas: ['nexus#noun'],
				source_tools: ['whitakers', 'diogenes'],
				source_refs: ['whitakers:nexus:noun', 'diogenes:lat:nexus:legal'],
				reasons: ['matches preferred morphology/reduction lemma', 'sources: whitakers, diogenes'],
				witnesses: [
					{
						tool: 'whitakers',
						label: 'Legal noun analysis',
						detail: 'Keeps the legal condition sense distinct from the broader connection gloss.'
					},
					{
						tool: 'diogenes',
						label: 'Dictionary sense support',
						detail: 'Provides the debt/obligation sense cluster as a secondary bucket.'
					}
				],
				witness_count: 2,
				preferred_lemma_rank: 0,
				effective_preferred_lemma_rank: 0,
				learner_quality_order: 0,
				has_english_translation: false,
				has_source_translation: false,
				source_langs: ['en', 'lat'],
				reader_lang: 'en',
				evidence_note: 'Secondary legal sense: relevant, but narrower than the main reader bucket.',
				translation_note:
					'Dictionary and morphology agree, but no separate translated source entry is attached.'
			},
			{
				bucket_id: 'bucket:lat-necto-form',
				display_gloss:
					'necto / nectere: to bind, tie, fasten | morphology relation explains why nexus is grouped with a verbal root',
				normalized_gloss: 'necto nectere bind tie fasten morphology relation nexus verbal root',
				bucket_lemmas: ['necto', 'nectere', 'nexus'],
				source_tools: ['whitakers', 'cltk'],
				source_refs: ['whitakers:necto', 'cltk:lat:necto'],
				reasons: ['related lemma expansion', 'sources: whitakers, cltk'],
				witnesses: [
					{
						tool: 'whitakers',
						label: 'Related verbal lemma',
						detail: 'Shows the verbal root that helps explain the nominal form.'
					},
					{
						tool: 'cltk',
						label: 'Lexicon relation',
						detail: 'Keeps the relation visible without merging it into the main noun bucket.'
					}
				],
				witness_count: 2,
				preferred_lemma_rank: 1,
				effective_preferred_lemma_rank: 1,
				learner_quality_order: 1,
				has_english_translation: true,
				has_source_translation: false,
				source_langs: ['en', 'lat'],
				reader_lang: 'en',
				evidence_note: 'Related lemma evidence: useful when moving from noun gloss to derivation.',
				translation_note:
					'Reader-ready English gloss; no separate translated source text is attached.'
			}
		],
		analysis: [],
		components: [],
		translation_cache: {
			mode: 'auto',
			cache_available: true,
			populate: true,
			written: 0,
			before: { total: 3, hits: 2, missing: 1, errors: 0 },
			after: { total: 3, hits: 3, missing: 0, errors: 0 }
		},
		warnings: [
			'Gaffiot source text may begin in French; Reader EN shows cached translation when available.'
		],
		request: {
			translation_mode: 'auto',
			tool_filter: ['all'],
			reader_lang: 'en'
		},
		backend: 'sample'
	}
];

export function toolsForLanguage(language: LanguageMode) {
	return tools.filter((tool) => tool.language === language);
}

export function isSingleWord(query: string) {
	return /^\S+$/.test(query.trim());
}

export function resolveToolRequests(
	language: LanguageMode,
	requestedTools: ToolRequest[] = ['all']
) {
	return requestedTools.includes('all')
		? toolsForLanguage(language).map(({ id }) => id)
		: requestedTools.filter((tool): tool is ToolId => tool !== 'all');
}

function sourceRefBelongsToTool(sourceRef: string, tool: ToolId) {
	return sourceRef === tool || sourceRef.startsWith(`${tool}:`);
}

function projectBucketToTools(bucket: EncounterBucket, activeTools: Set<ToolId>) {
	const sourceTools = bucket.source_tools.filter((tool) => activeTools.has(tool));
	const witnesses = bucket.witnesses.filter((witness) => activeTools.has(witness.tool));
	const sourceRefs = bucket.source_refs.filter((sourceRef) =>
		sourceTools.some((tool) => sourceRefBelongsToTool(sourceRef, tool))
	);

	return {
		...bucket,
		source_tools: sourceTools,
		source_refs: sourceRefs,
		reasons: [
			...bucket.reasons.filter((reason) => !reason.startsWith('sources:')),
			`sources: ${sourceTools.join(', ')}`
		],
		witnesses,
		witness_count: witnesses.length || sourceTools.length
	};
}

export function encounterWord(
	query: string,
	language: LanguageMode,
	requestedTools: ToolRequest[] = ['all']
): EncounterResult {
	const normalizedQuery = query.trim().toLowerCase();
	const activeTools = new Set(resolveToolRequests(language, requestedTools));
	const fallback = encounters.find((encounter) => encounter.language === language) ?? encounters[0];
	const encounter =
		encounters.find(
			(candidate) =>
				candidate.language === language && candidate.query.toLowerCase() === normalizedQuery
		) ?? fallback;

	if (!normalizedQuery || !isSingleWord(query)) {
		return {
			...encounter,
			query,
			dictionaries: requestedTools,
			source_tools: [...activeTools],
			buckets: [],
			request: {
				...encounter.request,
				tool_filter: requestedTools
			}
		};
	}

	const buckets = encounter.buckets
		.filter((bucket) => bucket.source_tools.some((tool) => activeTools.has(tool)))
		.map((bucket) => projectBucketToTools(bucket, activeTools))
		.filter((bucket) => {
			const searchable = [
				encounter.query,
				bucket.display_gloss,
				bucket.normalized_gloss,
				bucket.evidence_note,
				bucket.translation_note,
				...bucket.bucket_lemmas,
				...bucket.reasons,
				...bucket.source_tools,
				...bucket.source_refs,
				...bucket.witnesses.flatMap((witness) => [witness.label, witness.detail])
			];

			return searchable.some((value) => value.toLowerCase().includes(normalizedQuery));
		});

	return {
		...encounter,
		query,
		dictionaries: requestedTools,
		source_tools: [...activeTools],
		buckets,
		request: {
			...encounter.request,
			tool_filter: requestedTools
		}
	};
}
