import assert from 'node:assert/strict';
import { wordIndexSectionLookupTarget } from './word-index';
import { wordIndexSectionsResponse } from './word-index-sections';

const sanskrit = wordIndexSectionsResponse('san', 'all');

assert.equal(sanskrit.schema_version, 'langnet.word_index.sections.v1');
assert.equal(sanskrit.sections.length, 52);
assert.deepEqual(
	sanskrit.sections
		.slice(0, 4)
		.map((section) => [section.label, section.transliteration, section.anchor?.query]),
	[
		['अ', 'a', 'a'],
		['आ', 'ā', 'A'],
		['इ', 'i', 'i'],
		['ई', 'ī', 'I']
	]
);

const ksha = sanskrit.sections.find((section) => section.label === 'क्ष');
assert.equal(ksha?.anchor?.query, 'kz');
assert.deepEqual(ksha && wordIndexSectionLookupTarget(ksha), {
	language: 'san',
	query: 'kṣa',
	dictionary: 'all'
});

const greek = wordIndexSectionsResponse('grc', 'diogenes');
assert.equal(greek.sections.length, 24);
assert.deepEqual(
	greek.sections
		.filter((section) => ['Θ', 'Ξ', 'Ω'].includes(section.label))
		.map((section) => [section.label, section.anchor?.query, section.transliteration]),
	[
		['Θ', 'q', 'th'],
		['Ξ', 'c', 'x'],
		['Ω', 'ō', 'w']
	]
);

const theta = greek.sections.find((section) => section.label === 'Θ');
assert.deepEqual(theta && wordIndexSectionLookupTarget(theta), {
	language: 'grc',
	query: 'q',
	dictionary: 'diogenes'
});

const latin = wordIndexSectionsResponse('lat', 'all');
assert.equal(latin.sections.length, 26);
assert.equal(latin.sections[0]?.label, 'A');
assert.equal(latin.sections[25]?.anchor?.query, 'z');

console.log('word-index static sections ok');
