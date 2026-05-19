import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const pageSource = readFileSync('src/routes/+page.svelte', 'utf8');
const motdSource = readFileSync('src/routes/api/motd/+server.ts', 'utf8');
const wordIndexSource = readFileSync('src/routes/api/word-index/+server.ts', 'utf8');

assert.equal(
	pageSource.includes('if (!motdItems.length) void loadMotd(false);'),
	true,
	'initial page load should prepare the learner folio when no usable cached item exists'
);
assert.equal(
	pageSource.includes('uiCopy.margin.noWord'),
	false,
	'learner folio should not render an empty no-word content state'
);
assert.equal(
	pageSource.includes('throw new Error(data.error ?? uiCopy.errors.recommendationsFailed);'),
	true,
	'empty MOTD responses should be treated as errors instead of visible empty content'
);
assert.equal(
	pageSource.includes("const deskStorageKey = 'orion-desk-state:v3';") &&
		pageSource.includes('version: 3'),
	true,
	'desk session storage version should invalidate stale pre-translation state'
);
assert.equal(
	pageSource.includes('encounterNeedsFreshReaderLayer(stored.encounter)') &&
		pageSource.includes('hasMissingSourceReaderTranslations(result)'),
	true,
	'stored encounters with incomplete reader translations should not bypass a fresh lookup'
);
assert.equal(
	pageSource.includes('!query.trim() && !currentWordIndex && !wordIndexEarmarks.length'),
	false,
	'word-index sections are static and should not wait for a search before loading'
);
assert.equal(
	pageSource.includes('void loadWordIndexSections(language);'),
	true,
	'word-index sections should be requested as soon as route state is ready'
);
assert.equal(
	pageSource.includes('let motdPending = $derived(motdLoading && !motd && !motdError);'),
	true,
	'MOTD skeleton should reflect active loading, not an idle empty state'
);

assert.equal(
	motdSource.includes('Learner folio is not cached yet'),
	false,
	'auto MOTD requests should no longer return an empty cache-only placeholder'
);
assert.equal(
	motdSource.includes('wordRecommendationsFromCli') &&
		motdSource.includes('const generationCandidateSource = candidateSource'),
	true,
	'auto MOTD requests should be allowed to refresh through the CLI recommendation path'
);
assert.equal(
	motdSource.includes('Using the previous word of the day; replacement could not be prepared'),
	true,
	'MOTD refresh failures should serve the previous cached result when possible'
);

assert.equal(
	wordIndexSource.includes("if (mode === 'sections')"),
	true,
	'word-index sections should be handled before the CLI fallback'
);
assert.equal(
	wordIndexSource.indexOf("if (mode === 'sections')") <
		wordIndexSource.indexOf('return respond(await wordIndexFromCli(request))'),
	true,
	'word-index sections should avoid the Python CLI path'
);

console.log('initial-load performance policy ok');
