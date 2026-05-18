import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const readerPageSource = readFileSync(
	new URL('../routes/reader/+page.svelte', import.meta.url),
	'utf8'
);

const loadAuthorSectionsMatch = readerPageSource.match(
	/async function loadAuthorSections[\s\S]*?\n\t}\n\n\tasync function loadAuthors/
);

assert.ok(
	loadAuthorSectionsMatch,
	'reader page should define loadAuthorSections before loadAuthors'
);

const loadAuthorSectionsSource = loadAuthorSectionsMatch[0];
const loadingIndex = loadAuthorSectionsSource.indexOf('authorsLoading = true');
const fetchSectionsIndex = loadAuthorSectionsSource.indexOf('await fetchReaderAuthorSections');
const parallelAuthorsIndex = loadAuthorSectionsSource.indexOf('const authorsPromise =');

assert.ok(
	loadingIndex !== -1 && loadingIndex < fetchSectionsIndex,
	'author loading should begin before fetching author sections'
);

assert.ok(
	parallelAuthorsIndex !== -1 && parallelAuthorsIndex < fetchSectionsIndex,
	'top-author loading should begin before author sections finish'
);

const restoreReaderIndexStateMatch = readerPageSource.match(
	/function restoreReaderIndexState\(\)[\s\S]*?\n\t}\n\n\tfunction saveReaderIndexState/
);
assert.ok(restoreReaderIndexStateMatch, 'reader page should define restoreReaderIndexState');
const restoreReaderIndexStateSource = restoreReaderIndexStateMatch[0];

for (const stalePayloadAssignment of [
	'catalogs = stored.catalogs',
	'readerIndexStats =',
	'facets = stored.facets',
	'discoveryShelves = stored.discoveryShelves',
	'authorSections = stored.authorSections',
	'authors = stored.authors',
	'works = stored.works',
	'textSearchResults ='
]) {
	assert.equal(
		restoreReaderIndexStateSource.includes(stalePayloadAssignment),
		false,
		`reader state restore should not replay cached API payloads: ${stalePayloadAssignment}`
	);
}

const saveReaderIndexStateMatch = readerPageSource.match(
	/function saveReaderIndexState\(\)[\s\S]*?\n\t}\n<\/script>/
);
assert.ok(saveReaderIndexStateMatch, 'reader page should define saveReaderIndexState');
const saveReaderIndexStateSource = saveReaderIndexStateMatch[0];

for (const stalePayloadField of [
	'catalogs,',
	'readerIndexStats,',
	'facets,',
	'discoveryShelves,',
	'authorSections,',
	'authors,',
	'works,',
	'textSearchResults,'
]) {
	assert.equal(
		saveReaderIndexStateSource.includes(stalePayloadField),
		false,
		`reader state persistence should not store API payloads: ${stalePayloadField}`
	);
}

const selectLanguageMatch = readerPageSource.match(
	/function selectLanguage[\s\S]*?\n\t}\n\n\tasync function fetchReaderAuthorSections/
);
assert.ok(
	selectLanguageMatch,
	'reader page should define selectLanguage before reader fetch helpers'
);
assert.ok(
	!selectLanguageMatch[0].includes('loadAllReaderIndexStats'),
	'language changes should not refetch stats for every language'
);

const loadReaderIndexStatsForMatch = readerPageSource.match(
	/async function loadReaderIndexStatsFor[\s\S]*?\n\t}\n\n\tasync function loadAllReaderIndexStats/
);
assert.ok(
	loadReaderIndexStatsForMatch,
	'reader page should define loadReaderIndexStatsFor before loadAllReaderIndexStats'
);
assert.ok(
	loadReaderIndexStatsForMatch[0].includes('readerHasIndexStats') &&
		loadReaderIndexStatsForMatch[0].includes('readerIndexStatsInFlight'),
	'reader stats requests should skip cached and in-flight targets'
);
