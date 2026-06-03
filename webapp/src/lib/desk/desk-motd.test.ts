import assert from 'node:assert/strict';

import {
	isPresentableMotdItem,
	motdDisplayGloss,
	motdDisplayLookup,
	motdDisplayNote,
	motdDisplayWord,
	motdVisibleWarnings,
	motdWordClass,
	motdWordLang,
	normalizeMotdResult,
	shouldShowMotdWarning
} from './desk-motd';
import type { WordRecommendationItem, WordRecommendationResult } from '../search-data';

const normalized = normalizeMotdResult({
	schema_version: '',
	generated_at: '',
	suggested_ttl_seconds: 0,
	items: [
		{
			language: 'grc',
			query: 'logos',
			primary_lexeme: 'lo_gos_1',
			display_forms: {
				greek: 'λόγος_1',
				roman: 'lo-gos',
				script: 'Greek'
			},
			ui: { short_gloss: 'speech' },
			mnemonic: 'Query `logos` is backed by source evidence for LSJ. remember speech'
		},
		{
			language: 'san',
			query: 'jyotis',
			forms: {
				devanagari: 'ज्योतिस्',
				iast: 'jyotis',
				script: 'Devanagari'
			},
			summary: 'light'
		},
		{
			language: 'lat',
			query: 'ratio#noun',
			display: 'ratio#noun',
			summary: 'reason'
		},
		{
			language: 'lat',
			query: '',
			display: '',
			summary: '',
			learner_note: '',
			mnemonic: ''
		}
	],
	warnings: [{ message: 'Precomputed learner pool returned no cards' }, { message: 'hard error' }]
} as unknown as WordRecommendationResult);

assert.equal(normalized.schema_version, 'langnet.word_of_day.v1');
assert.equal(normalized.suggested_ttl_seconds, 3600);
assert.equal(normalized.items.length, 4);

const greek = normalized.items[0]!;
assert.equal(greek.key, 'grc:logos');
assert.equal(greek.recommended_request.dictionary, 'all');
assert.equal(motdDisplayWord(greek), 'λόγος');
assert.equal(motdDisplayLookup(greek), 'logos');
assert.equal(motdDisplayGloss(greek), 'speech');
assert.equal(motdDisplayNote(greek), 'remember speech');
assert.equal(motdWordClass(greek), 'orion-motd-word orion-motd-word-grc');
assert.equal(motdWordLang(greek), 'grc');

const sanskrit = normalized.items[1]!;
assert.equal(motdDisplayWord(sanskrit), 'ज्योतिस्');
assert.equal(motdDisplayLookup(sanskrit), 'jyotis');
assert.equal(motdWordClass(sanskrit), 'orion-motd-word orion-motd-word-san');
assert.equal(motdWordLang(sanskrit), 'sa-Deva');

const latin = normalized.items[2]!;
assert.equal(motdDisplayWord(latin), 'ratio');
assert.equal(motdDisplayLookup(latin), '');
assert.equal(motdWordClass(latin), 'orion-motd-word');
assert.equal(motdWordLang(latin), 'la');

assert.equal(
	isPresentableMotdItem({
		...latin,
		display: '',
		query: '',
		primary_lexeme: '',
		summary: '',
		learner_note: '',
		mnemonic: '',
		ui: { ...latin.ui, short_gloss: '' }
	}),
	false
);
assert.equal(shouldShowMotdWarning('Precomputed learner pool returned no cards', false), true);
assert.equal(shouldShowMotdWarning('Precomputed learner pool returned no cards', true), false);
assert.deepEqual(
	motdVisibleWarnings(normalized).map((warning) => warning.message),
	['hard error']
);

const emptyFallback = normalizeMotdResult({
	schema_version: 'custom',
	generated_at: '2026-06-03T00:00:00Z',
	suggested_ttl_seconds: 120,
	items: [
		{
			language: 'lat',
			query: 'amo',
			key: 'lat:amo',
			display: 'amo',
			primary_lexeme: 'amo',
			lexeme_anchors: [],
			summary: '',
			learner_note: '',
			mnemonic: '',
			difficulty: 'beginner',
			confidence: 'source',
			ambiguity: { has_multiple_lexemes: false, lexeme_count: 0, note: '' },
			recommended_request: {
				language: 'lat',
				q: 'amo',
				dictionary: 'whitakers',
				translation: 'auto',
				backend: 'cli'
			},
			source_basis: [],
			display_forms: { native: 'amo', roman: 'amo', canonical: 'amo', script: 'Latin' },
			ui: { href_query: '', badge: '', short_gloss: '' }
		} satisfies WordRecommendationItem
	],
	warnings: []
});

assert.equal(emptyFallback.schema_version, 'custom');
assert.equal(motdDisplayGloss(emptyFallback.items[0]!), 'Learner word.');
