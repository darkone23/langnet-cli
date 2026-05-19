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

console.log('langnet-cli payload mapping ok');
