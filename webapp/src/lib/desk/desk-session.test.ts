import assert from 'node:assert/strict';

import {
	encounterMatchesStoredRoute,
	encounterNeedsFreshReaderLayer,
	hasMissingSourceReaderTranslations,
	hasStaleTranslatedSourceLayer,
	isTranslatedSourceTool,
	returnedToolsForEncounter,
	sourceLayerLooksLikeReaderEnglish,
	validStoredTools
} from './desk-session';
import type { EncounterResult } from '../search-data';

function encounter(overrides: Partial<EncounterResult> = {}): EncounterResult {
	return {
		query: 'logos',
		language: 'grc',
		dictionaries: ['all'],
		source_tools: ['diogenes'],
		lexeme_anchors: ['lex:logos'],
		analysis: [],
		components: [],
		buckets: [],
		translation_cache: {
			mode: 'cache',
			cache_db: '',
			model: '',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 0, hits: 0, missing: 0, errors: 0, empty: 0 },
			after: { total: 0, hits: 0, missing: 0, errors: 0, empty: 0 }
		},
		warnings: [],
		request: {
			translation_mode: 'cache',
			tool_filter: ['diogenes'],
			reader_lang: 'en'
		},
		backend: 'cli',
		...overrides
	};
}

assert.equal(encounterMatchesStoredRoute(encounter(), 'grc', ' logos '), true);
assert.equal(encounterMatchesStoredRoute(encounter(), 'lat', 'logos'), false);
assert.equal(encounterMatchesStoredRoute(null, 'grc', 'logos'), false);

assert.equal(sourceLayerLooksLikeReaderEnglish('same prose', 'same prose'), true);
assert.equal(sourceLayerLooksLikeReaderEnglish('', 'reader'), true);
assert.equal(sourceLayerLooksLikeReaderEnglish('texte francais', 'reader English'), false);

const staleSourceLayer = encounter({
	buckets: [
		{
			bucket_id: 'bucket:logos',
			display_gloss: 'speech',
			normalized_gloss: 'speech',
			bucket_lemmas: ['logos'],
			source_tools: ['bailly'],
			source_refs: [],
			reasons: [],
			witnesses: [],
			witness_count: 1,
			preferred_lemma_rank: 0,
			effective_preferred_lemma_rank: 0,
			learner_quality_order: 0,
			has_english_translation: true,
			has_source_translation: true,
			source_langs: ['fr'],
			reader_lang: 'en',
			evidence_note: '',
			translation_note: '',
			translation: {
				available: true,
				source_tool: 'bailly',
				source_lang: 'fr',
				source_label: 'Bailly',
				source_text: 'This text is accidentally English and very long. '.repeat(4),
				target_lang: 'en',
				target_text: 'This text is accidentally English and very long. '.repeat(4)
			}
		}
	]
});

assert.equal(hasStaleTranslatedSourceLayer(staleSourceLayer), true);
assert.equal(encounterNeedsFreshReaderLayer(staleSourceLayer), true);

const missingTranslation = encounter({
	buckets: [
		{
			...staleSourceLayer.buckets[0]!,
			translation: {
				available: false,
				source_tool: 'bailly',
				source_lang: 'fr',
				source_label: 'Bailly',
				source_text: 'logos',
				target_lang: 'en',
				target_text: ''
			}
		}
	],
	components: [
		{
			surface: 'logos',
			lemma: 'logos',
			display: 'logos',
			role: 'root',
			analysis: '',
			source_tool: 'diogenes',
			lookup_terms: ['logos'],
			evidence: {
				status: 'ok',
				source: 'bailly',
				lookup_tool_filter: 'bailly',
				error: '',
				meanings: [
					{
						bucket_id: 'component:logos',
						display_gloss: 'word',
						source_tools: ['bailly'],
						source_refs: [],
						source_langs: ['fr'],
						translation: {
							available: false,
							source_tool: 'bailly',
							source_lang: 'fr',
							source_label: 'Bailly',
							source_text: 'mot',
							target_lang: 'en',
							target_text: ''
						}
					}
				]
			}
		}
	]
});

assert.equal(hasMissingSourceReaderTranslations(missingTranslation), true);
assert.equal(encounterNeedsFreshReaderLayer(missingTranslation), true);

assert.deepEqual(validStoredTools(['diogenes', 'cdsl', 'bailly'], 'grc'), ['diogenes', 'bailly']);
assert.equal(validStoredTools(['cdsl'], 'grc'), null);
assert.deepEqual(returnedToolsForEncounter(staleSourceLayer), ['diogenes', 'bailly']);
assert.equal(isTranslatedSourceTool('bailly'), true);
assert.equal(isTranslatedSourceTool('diogenes'), false);
