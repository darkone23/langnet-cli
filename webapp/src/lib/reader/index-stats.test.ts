import { strict as assert } from 'node:assert';

import type { ReaderAuthorSection, ReaderCatalog, ReaderIndexStats } from './index';
import {
	buildReaderIndexStatsTargets,
	defaultReaderCatalogForLanguage,
	findReaderIndexStatsInList,
	readerIndexStatsFromSections,
	upsertReaderIndexStatsList
} from './index-stats';

const sections: ReaderAuthorSection[] = [
	{ key: 'A', label: 'A', native_label: 'A', sort_key: 'A', author_count: 2, work_count: 5 },
	{ key: 'B', label: 'B', native_label: 'B', sort_key: 'B', author_count: 3, work_count: 7 }
];

assert.deepEqual(readerIndexStatsFromSections('grc', 'perseus', sections), {
	language: 'grc',
	catalogId: 'perseus',
	workCount: 12,
	authorCount: 5
});

const stats: ReaderIndexStats[] = [
	{ language: 'grc', catalogId: 'perseus', workCount: 1, authorCount: 1 },
	{ language: 'lat', catalogId: 'latin', workCount: 2, authorCount: 2 }
];
const updated: ReaderIndexStats = {
	language: 'grc',
	catalogId: 'perseus',
	workCount: 12,
	authorCount: 5
};
assert.deepEqual(upsertReaderIndexStatsList(stats, updated), [stats[1], updated]);
assert.deepEqual(findReaderIndexStatsInList([stats[1], updated], 'grc', 'perseus'), updated);

const catalogs: ReaderCatalog[] = [
	{
		id: 'perseus',
		label: 'Perseus',
		path: 'perseus.yaml',
		languages: ['grc'],
		readiness: 'ready',
		available: true,
		description: ''
	},
	{
		id: 'latin',
		label: 'Latin',
		path: 'latin.yaml',
		languages: ['lat'],
		readiness: 'ready',
		available: true,
		description: ''
	},
	{
		id: 'offline',
		label: 'Offline',
		path: 'offline.yaml',
		languages: ['san'],
		readiness: 'missing',
		available: false,
		description: ''
	}
];

assert.equal(defaultReaderCatalogForLanguage(catalogs, { grc: 'perseus' }, 'grc'), 'perseus');
assert.equal(defaultReaderCatalogForLanguage(catalogs, {}, 'lat'), 'latin');
assert.equal(defaultReaderCatalogForLanguage(catalogs, {}, 'san'), '');

assert.deepEqual(
	buildReaderIndexStatsTargets({
		catalogs,
		catalogDefaults: { grc: 'perseus' },
		languageModes: [{ id: 'grc' }, { id: 'lat' }, { id: 'san' }],
		activeLanguage: 'grc',
		activeCatalogId: 'perseus'
	}),
	[
		{ language: 'grc', catalogId: 'perseus' },
		{ language: 'lat', catalogId: 'latin' }
	]
);
