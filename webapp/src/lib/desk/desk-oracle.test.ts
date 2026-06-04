import { strict as assert } from 'node:assert';

import { buildDeskOracleTrace } from './desk-oracle';
import type { EncounterResult } from '../search-data';

const encounter: EncounterResult = {
	query: 'logos',
	language: 'grc',
	source_tools: ['dico', 'diogenes'],
	dictionaries: ['all'],
	lexeme_anchors: [],
	buckets: [
		{
			bucket_id: 'dico::logos',
			source_tools: ['dico'],
			bucket_lemmas: ['logos'],
			source_refs: ['lsj:logos'],
			reasons: [],
			witnesses: [],
			witness_count: 1,
			preferred_lemma_rank: 1,
			effective_preferred_lemma_rank: 1,
			learner_quality_order: 1,
			has_english_translation: false,
			has_source_translation: false,
			source_langs: ['grc'],
			reader_lang: 'en',
			evidence_note: 'evidence',
			translation_note: 'note',
			display_gloss: 'word',
			normalized_gloss: 'word',
			translation: undefined
		}
	],
	analysis: [],
	components: [],
	translation_cache: {
		mode: 'cache',
		cache_db: 'default',
		cache_available: true,
		populate: true,
		written: 1,
		before: { total: 1, hits: 1, missing: 0, errors: 0 },
		after: { total: 1, hits: 1, missing: 0, errors: 0 }
	},
	warnings: ['seed warning'],
	request: {
		translation_mode: 'cache',
		tool_filter: ['dico'],
		reader_lang: 'en',
		normalization_cache_writes: true,
		translation_cache_writes: false,
		cache_policy: 'warm'
	},
	backend: 'cli',
	word_index: {
		request: {
			language: 'grc',
			query: 'logos',
			query_candidates: ['logos', 'λόγος'],
			source: 'lexicon',
			radius: 5
		},
		anchors: [
			{
				language: 'grc',
				query: 'logos',
				source: 'lsj',
				dictionary: 'dico',
				anchor_status: 'ok',
				lexeme_id: 'lsj-1',
				wheel_id: 'w',
				wheel_order_key: '1',
				canonical_name: 'logos',
				canonical_key: 'logos',
				source_name: 'lsj',
				source_ref: 'lsj:logos',
				index_entry_id: 'ie',
				source_order_id: 'so',
				source_order_key: 'sk'
			}
		],
		warnings: [
			{ source: 'index', message: 'index warning' },
			{ source: 'search', message: 'search warning' }
		]
	}
};

const trace = buildDeskOracleTrace(encounter);
assert.equal(trace.requestWord, 'logos');
assert.deepEqual(trace.normalizedCandidates, ['logos', 'λόγος']);
assert.equal(trace.sourceTools.join(','), 'dico,diogenes');
assert.equal(trace.bucketCount, 1);
assert.equal(trace.indexAnchorCount, 1);
assert.equal(trace.warnings[0], 'seed warning');
assert.equal(trace.provenanceChips.includes('backend=cli'), true);
assert.equal(trace.bucketSources[0], 'dico::logos');

const fallbackTrace = buildDeskOracleTrace(null, 'dory');
assert.equal(fallbackTrace.requestWord, 'dory');
assert.deepEqual(fallbackTrace.sourceTools, []);
assert.deepEqual(fallbackTrace.provenanceChips, []);
