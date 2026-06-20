import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const pageSource = readFileSync('src/routes/+page.svelte', 'utf8');
const pageControllerSource = readFileSync('src/lib/desk/DeskRouteController.svelte', 'utf8');
const fullPageSource = `${pageSource}\n${pageControllerSource}`;
const compactPageSource = fullPageSource.replace(/\s+/g, ' ');
const deskEndpointsSource = readFileSync('src/lib/desk/desk-endpoints.ts', 'utf8');
const deskWorkspaceSource = readFileSync('src/lib/desk/desk-route-workspace.ts', 'utf8');
const deskSessionSource = readFileSync('src/lib/desk/desk-session.ts', 'utf8');
const deskMotdControllerSource = readFileSync('src/lib/desk/desk-motd-controller.ts', 'utf8');
const componentLedgerSource = readFileSync('src/lib/desk/DeskComponentLedger.svelte', 'utf8');
const compactComponentLedgerSource = componentLedgerSource.replace(/\s+/g, ' ');
const dictionaryGroupCardSource = readFileSync(
	'src/lib/desk/DeskDictionaryGroupCard.svelte',
	'utf8'
);
const compactDictionaryGroupCardSource = dictionaryGroupCardSource.replace(/\s+/g, ' ');
const lookupResultsSource = readFileSync('src/lib/desk/DeskLookupResults.svelte', 'utf8');
const compactLookupResultsSource = lookupResultsSource.replace(/\s+/g, ' ');
const paradigmPanelSource = readFileSync('src/lib/desk/DeskParadigmPanel.svelte', 'utf8');
const deskParadigmSource = readFileSync('src/lib/desk/desk-paradigm.ts', 'utf8');
const learnPageSource = readFileSync('src/routes/learn/+page.svelte', 'utf8');
const uiCopySource = readFileSync('src/lib/ui-copy.ts', 'utf8');
const motdFolioSource = readFileSync('src/lib/desk/DeskMotdFolio.svelte', 'utf8');
const learnSource = readFileSync('src/lib/learn.ts', 'utf8');
const appCssSource = readFileSync('src/app.css', 'utf8');
const motdSource = readFileSync('src/routes/api/motd/+server.ts', 'utf8');
const wordIndexSource = readFileSync('src/routes/api/word-index/+server.ts', 'utf8');

assert.equal(
	fullPageSource.includes('if (!motdItems.length) void motdController.load(false);'),
	true,
	'initial page load should prepare the learner folio when no usable cached item exists'
);
assert.equal(
	fullPageSource.includes('uiCopy.margin.noWord'),
	false,
	'learner folio should not render an empty no-word content state'
);
assert.equal(
	deskMotdControllerSource.includes(
		'throw new Error(data.error ?? deps.recommendationsFailedMessage);'
	),
	true,
	'empty MOTD responses should be treated as errors instead of visible empty content'
);
assert.equal(
	fullPageSource.includes("from '$lib/desk/desk-route-workspace'") &&
		deskWorkspaceSource.includes('const legacyDeskStorageKeys = [') &&
		deskWorkspaceSource.includes('version: 5') &&
		deskWorkspaceSource.includes('orion-desk-state:v4') &&
		deskWorkspaceSource.includes("orion-desk-state:v3'"),
	true,
	'desk session storage version should invalidate stale pre-translation/source-layer state'
);
assert.equal(
	fullPageSource.includes('restoreDeskStateFromStorage(') &&
		fullPageSource.includes("from '$lib/desk/desk-session'") &&
		deskWorkspaceSource.includes('encounterNeedsFreshReaderLayer(stored.encounter') &&
		deskSessionSource.includes('hasMissingSourceReaderTranslations(result)') &&
		deskSessionSource.includes('hasStaleTranslatedSourceLayer(result)'),
	true,
	'stored encounters with incomplete reader translations should not bypass a fresh lookup'
);
assert.equal(
	deskEndpointsSource.includes("params.set('source_layer_version', '3');") &&
		fullPageSource.includes('searchEndpointUrl({'),
	true,
	'CLI search requests should bust server response cache after translated source-layer contract changes'
);
assert.equal(
	compactPageSource.includes('<DeskLookupResults') &&
		compactPageSource.includes('{textLayers}') &&
		compactLookupResultsSource.includes('<DeskDictionaryGroupCard') &&
		compactLookupResultsSource.includes('{textLayers}') &&
		compactDictionaryGroupCardSource.includes('helpers.sectionSegments(bucket, textLayers') &&
		compactDictionaryGroupCardSource.includes('helpers.groupLayerIsSource(group, textLayers)') &&
		compactDictionaryGroupCardSource.includes('helpers.readerEntryLabel(group, textLayers)') &&
		compactLookupResultsSource.includes('<DeskComponentLedger') &&
		compactLookupResultsSource.includes('{textLayers}') &&
		compactComponentLedgerSource.includes(
			'helpers.componentMeaningSegments( meaning, textLayers'
		) &&
		compactComponentLedgerSource.includes('helpers.componentLayerIsSource(component, textLayers)'),
	true,
	'reader source/English layer toggles should expose textLayers through the result Svelte template dependency chain'
);
assert.equal(
	fullPageSource.includes('!query.trim() && !currentWordIndex && !wordIndexEarmarks.length'),
	false,
	'word-index sections are static and should not wait for a search before loading'
);
assert.equal(
	fullPageSource.includes('void wordIndexController.loadSections(language);'),
	true,
	'word-index sections should be requested as soon as route state is ready'
);
assert.equal(
	fullPageSource.includes('let motdPending = $derived(motdLoading && !motd && !motdError);'),
	true,
	'MOTD skeleton should reflect active loading, not an idle empty state'
);
assert.equal(
	fullPageSource.includes('let motdLoading = $state(false);'),
	true,
	'MOTD loading should not start true before the initial API request is actually scheduled'
);
assert.equal(
	fullPageSource.includes('if (motdStale && motdItems.length) void motdController.load(false);'),
	true,
	'stale local MOTD should remain visible while a refresh starts in the background'
);
assert.equal(
	motdFolioSource.includes('uiCopy.margin.refreshingPrevious'),
	true,
	'MOTD should display a stale/refreshing indicator while old cards stay visible'
);
assert.equal(
	deskMotdControllerSource.includes("candidate_source: 'pool'") &&
		deskMotdControllerSource.includes("timeout_ms: '3000'") &&
		deskMotdControllerSource.includes("language: 'all'"),
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
	deskParadigmSource.includes('gateway.language !== targetLanguage') &&
		paradigmPanelSource.includes('candidateLearningLanguage(candidate, fallbackLanguage)'),
	true,
	'learning overlay native grammar terms should be scoped to the active lookup language'
);
assert.equal(
	paradigmPanelSource.includes('learnerDisplayForm') &&
		paradigmPanelSource.includes('learningGatewayTitle(learning)') &&
		paradigmPanelSource.includes('href="/learn"'),
	true,
	'dictionary form cards should be a small learning preview with a path into the Learn workflow'
);
assert.equal(
	paradigmPanelSource.includes('learningEvidenceGapLabels') ||
		paradigmPanelSource.includes('candidate.provenance.join'),
	false,
	'beginner-facing form cards should not expose raw evidence gaps or source provenance'
);
assert.equal(
	learnPageSource.includes('uiCopy.publicSite.learn') &&
		learnPageSource.includes('selectedScriptGuide') &&
		learnPageSource.includes('sourceReferenceHref') &&
		uiCopySource.includes('Start here') &&
		uiCopySource.includes('How Ancient Forms Work') &&
		uiCopySource.includes('Learn Forms') &&
		uiCopySource.includes('Reader question') &&
		uiCopySource.includes('Try A Source Word') &&
		uiCopySource.includes('Source Tradition'),
	true,
	'standalone Learn workflow should expose copy-system-backed concept study, reader questions, source references, and source practice'
);
assert.equal(
	learnPageSource.includes('<style>') && learnPageSource.includes('.orion-learn-page'),
	true,
	'Learn page should own its page-specific scoped styles'
);
assert.equal(
	appCssSource.includes('\n\t.orion-learn-'),
	false,
	'Learn page selectors should move out of app.css'
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

assert.equal(
	fullPageSource.includes("result.language !== 'lat'"),
	false,
	'word-index sidebar match keys should use encounter anchors for Greek and Sanskrit, not only Latin'
);

console.log('initial-load performance policy ok');
