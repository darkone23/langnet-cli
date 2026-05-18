import assert from 'node:assert/strict';
import { wordIndexCandidateQueries } from './word-index-fallbacks';
import type { EncounterResult } from './search-data';

const varnamalaEncounter = {
	query: 'varnamala',
	language: 'san',
	lexeme_anchors: ['lex:varramala'],
	buckets: [
		{
			bucket_lemmas: ['varramala', 'varṇamālā'],
			witnesses: [
				{
					headword: 'varṇamālā',
					lexeme_anchor: 'lex:varramala'
				}
			]
		}
	],
	word_index: {
		anchors: [
			{
				anchor_status: 'exact',
				canonical_key: 'vara',
				canonical_name: 'वर',
				source_name: 'vara',
				query: 'varṇa'
			},
			{
				anchor_status: 'exact',
				canonical_key: 'maalaa',
				canonical_name: 'माला',
				source_name: 'mAlA',
				query: 'mālā'
			}
		]
	}
} as EncounterResult;

assert.deepEqual(wordIndexCandidateQueries(varnamalaEncounter, 'varnamala').slice(0, 3), [
	'varnamala',
	'varramala',
	'varṇamālā'
]);

assert.equal(wordIndexCandidateQueries(varnamalaEncounter, 'varnamala').includes('vara'), true);
assert.ok(
	wordIndexCandidateQueries(varnamalaEncounter, 'varnamala').indexOf('vara') >
		wordIndexCandidateQueries(varnamalaEncounter, 'varnamala').indexOf('varṇamālā')
);

assert.deepEqual(wordIndexCandidateQueries(null, 'unfoundword'), ['unfoundword']);
