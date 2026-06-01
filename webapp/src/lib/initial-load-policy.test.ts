import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const pageSource = readFileSync('src/routes/+page.svelte', 'utf8');
const compactPageSource = pageSource.replace(/\s+/g, ' ');
const learnPageSource = readFileSync('src/routes/learn/+page.svelte', 'utf8');
const learnSource = readFileSync('src/lib/learn.ts', 'utf8');
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
	pageSource.includes("const deskStorageKey = 'orion-desk-state:v5';") &&
		pageSource.includes('version: 5') &&
		pageSource.includes("sessionStorage.removeItem('orion-desk-state:v4');") &&
		pageSource.includes("sessionStorage.removeItem('orion-desk-state:v3');"),
	true,
	'desk session storage version should invalidate stale pre-translation/source-layer state'
);
assert.equal(
	pageSource.includes('encounterNeedsFreshReaderLayer(stored.encounter)') &&
		pageSource.includes('hasMissingSourceReaderTranslations(result)') &&
		pageSource.includes('hasStaleTranslatedSourceLayer(result)'),
	true,
	'stored encounters with incomplete reader translations should not bypass a fresh lookup'
);
assert.equal(
	pageSource.includes("params.set('source_layer_version', '3');"),
	true,
	'CLI search requests should bust server response cache after translated source-layer contract changes'
);
assert.equal(
	compactPageSource.includes('sectionSegments(bucket, textLayers') &&
		compactPageSource.includes('groupLayerIsSource(group, textLayers)') &&
		compactPageSource.includes('readerEntryLabel(group, textLayers)') &&
		compactPageSource.includes('componentMeaningSegments( meaning, textLayers') &&
		compactPageSource.includes('componentLayerIsSource(component, textLayers)'),
	true,
	'reader source/English layer toggles should expose textLayers as a direct Svelte template dependency'
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
	pageSource.includes('let motdLoading = $state(false);'),
	true,
	'MOTD loading should not start true before the initial API request is actually scheduled'
);
assert.equal(
	pageSource.includes('if (motdStale && motdItems.length) void loadMotd(false);'),
	true,
	'stale local MOTD should remain visible while a refresh starts in the background'
);
assert.equal(
	pageSource.includes('uiCopy.margin.refreshingPrevious'),
	true,
	'MOTD should display a stale/refreshing indicator while old cards stay visible'
);
assert.equal(
	pageSource.includes("candidate_source: 'pool'") &&
		pageSource.includes("timeout_ms: '3000'") &&
		pageSource.includes("language: 'all'"),
	true,
	'MOTD page requests should use all-language precomputed pool recommendations with a tight timeout'
);

assert.equal(
	motdSource.includes('Learner folio is not cached yet'),
	false,
	'auto MOTD requests should no longer return an empty cache-only placeholder'
);
assert.equal(
	motdSource.includes('wordRecommendationsFromMotdPool') &&
		motdSource.includes('const requestedCandidateSource = url.searchParams.get') &&
		motdSource.includes("candidateSource === 'pool'") &&
		motdSource.includes('samplePoolMotd') &&
		motdSource.includes('motdDictionary(language)') &&
		motdSource.includes('Precomputed learner pool returned no cards'),
	true,
	'normal MOTD requests should sample the precomputed learner pool instead of running live LLM work'
);
assert.equal(
	motdSource.includes('Using the previous word of the day; replacement could not be prepared'),
	true,
	'MOTD refresh failures should serve the previous cached result when possible'
);
assert.equal(
	motdSource.includes('serveStaleWhileRefreshing') &&
		motdSource.includes('void refreshMotdCacheInBackground'),
	true,
	'expired server MOTD cache should be returned immediately while refresh continues'
);
assert.equal(
	motdSource.includes('web-motd-cache.json') &&
		motdSource.includes('hydrateMotdDiskCache') &&
		motdSource.includes('persistMotdDiskCache'),
	true,
	'MOTD should persist successful server results outside process memory'
);
assert.equal(
	motdSource.includes("readInteger(url.searchParams.get('timeout_ms'), 3_000"),
	true,
	'MOTD API default timeout should be tight because normal requests are local pool samples'
);
assert.equal(
	pageSource.includes('gateway.language !== targetLanguage') &&
		pageSource.includes('candidateLearningLanguage(candidate)'),
	true,
	'learning overlay native grammar terms should be scoped to the active lookup language'
);
assert.equal(
	pageSource.includes('learnerDisplayForm') &&
		pageSource.includes('learningGatewayTitle(learning)') &&
		pageSource.includes('href="/learn"'),
	true,
	'dictionary form cards should be a small learning preview with a path into the Learn workflow'
);
assert.equal(
	pageSource.includes('learningEvidenceGapLabels') ||
		pageSource.includes('candidate.provenance.join'),
	false,
	'beginner-facing form cards should not expose raw evidence gaps or source provenance'
);
assert.equal(
	learnPageSource.includes('Start here') &&
		learnPageSource.includes('How Ancient Forms Work') &&
		learnPageSource.includes('selectedScriptGuide') &&
		learnPageSource.includes('Learn Forms') &&
		learnPageSource.includes('Reader question') &&
		learnPageSource.includes('Try A Source Word') &&
		learnPageSource.includes('Source Tradition') &&
		learnPageSource.includes('sourceReferenceHref'),
	true,
	'standalone Learn workflow should expose concept study, reader questions, source references, and source practice'
);
assert.equal(
	learnSource.includes('Receiving Function') &&
		learnSource.includes('learnStartCards') &&
		learnSource.includes('learnScriptGuides') &&
		learnSource.includes('What is a form?') &&
		learnSource.includes('Devanagari and transliteration') &&
		learnSource.includes('dvitīyā vibhakti') &&
		learnSource.includes('genikē ptōsis') &&
		learnSource.includes('accusativus') &&
		learnSource.includes('langnet:reader:sanskrit_dcs:dcs_413') &&
		learnSource.includes('551190'),
	true,
	'Learn workflow should map Foster gateways into Sanskrit, Greek, and Latin terms with source anchors'
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
