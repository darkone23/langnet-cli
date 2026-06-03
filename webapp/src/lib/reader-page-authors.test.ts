import { strict as assert } from 'node:assert';

import type { ReaderAuthor, ReaderFacetValue, ReaderWork } from './reader';
import {
	readerFacetValueLabel,
	readerFacetValues,
	readerSelectedWorkAuthorLabel,
	readerSelectedWorkContributorLine,
	readerSelectedWorkDiscriminator,
	readerSelectedWorkTitleLabel,
	readerSyntheticAuthorFromRoute,
	readerSyntheticAuthorFromWork,
	upsertReaderAuthor
} from './reader-page-authors';

const plato: ReaderAuthor = {
	author_id: 'plato',
	source_author_id: 'tlg0059',
	canonical_author_id: 'urn:cts:greekLit:tlg0059',
	display_name: 'Plato',
	author: 'Plato',
	index_name: 'Plato',
	native_name: 'Πλάτων',
	section_key: 'Π',
	language: 'grc',
	work_count: 12,
	alternate_names: ['Platon'],
	sort_key: 'plato'
};

const updatedPlato = { ...plato, display_name: 'Plato the Athenian', work_count: 13 };
const aristotle = {
	...plato,
	author_id: 'aristotle',
	source_author_id: 'tlg0086',
	canonical_author_id: 'urn:cts:greekLit:tlg0086'
};

assert.deepEqual(upsertReaderAuthor([plato], updatedPlato), [updatedPlato]);
assert.deepEqual(upsertReaderAuthor([plato], aristotle), [aristotle, plato]);

const republic: ReaderWork = {
	work_id: 'rep',
	collection_id: 'fixture',
	language: 'grc',
	title: 'Republic',
	author: 'Plato',
	author_id: 'plato',
	source_id: 'plato.rep',
	cts_work_urn: 'urn:cts:greekLit:tlg0059.tlg030',
	source_author: 'Platon',
	canonical_author_name: 'Plato',
	traditional_author_names: ['Plato'],
	translator_names: ['Paul Shorey'],
	classification_category: 'philosophy'
};

const syntheticFromWork = readerSyntheticAuthorFromWork(republic, 'plato');
assert.equal(syntheticFromWork.author_id, 'plato');
assert.equal(syntheticFromWork.display_name, 'Plato');
assert.deepEqual(syntheticFromWork.alternate_names, ['Platon']);

const syntheticFromRoute = readerSyntheticAuthorFromRoute('vyasa', 'Vyāsa', 'san');
assert.equal(syntheticFromRoute.language, 'san');
assert.equal(syntheticFromRoute.display_name, 'Vyāsa');

const facets = [
	{
		id: 'sorts',
		label: 'Sorts',
		description: '',
		values: [
			{ id: 'global-popularity', label: 'Global popularity', description: '', work_count: 10 }
		]
	}
];
const sortValues = readerFacetValues(facets, 'sorts') as ReaderFacetValue[];
assert.equal(sortValues.length, 1);
assert.equal(readerFacetValueLabel(sortValues, 'global-popularity'), 'Global popularity');
assert.equal(readerFacetValueLabel(sortValues, 'source_period'), 'Source Period');

assert.equal(readerSelectedWorkTitleLabel(republic, [republic]), 'Republic');
assert.equal(readerSelectedWorkDiscriminator(republic, [republic]), '');
assert.equal(
	readerSelectedWorkContributorLine(republic),
	'Paul Shorey, translator · Plato, traditional author'
);
assert.equal(readerSelectedWorkAuthorLabel(republic), 'Plato');
assert.equal(readerSelectedWorkTitleLabel(null, [republic]), '');
