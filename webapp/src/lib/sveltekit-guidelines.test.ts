import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const guidelinesSource = readFileSync(
	new URL('../../docs/SVELTEKIT_GUIDELINES.md', import.meta.url),
	'utf8'
);
const uiDocSource = readFileSync(new URL('../../docs/UI.md', import.meta.url), 'utf8');
const webappReadmeSource = readFileSync(new URL('../../README.md', import.meta.url), 'utf8');
const docsReadmeSource = readFileSync(new URL('../../../docs/README.md', import.meta.url), 'utf8');
const appCssSource = readFileSync(new URL('../app.css', import.meta.url), 'utf8');
const deskRouteSource = readFileSync(new URL('../routes/+page.svelte', import.meta.url), 'utf8');
const deskDirectoryUrl = new URL('./desk/', import.meta.url);
const readerRouteSource = readFileSync(
	new URL('../routes/reader/+page.svelte', import.meta.url),
	'utf8'
);
const readerDirectoryUrl = new URL('./reader/', import.meta.url);
const readerApiSource = readFileSync(new URL('./reader-api.ts', readerDirectoryUrl), 'utf8');
const deskEntryCssSource = readFileSync(new URL('./desk-entry.css', deskDirectoryUrl), 'utf8');
const deskEntrySource = readFileSync(new URL('./desk-entry.ts', deskDirectoryUrl), 'utf8');
const deskEndpointsSource = readFileSync(new URL('./desk-endpoints.ts', deskDirectoryUrl), 'utf8');
const deskLookupSource = readFileSync(new URL('./desk-lookup.ts', deskDirectoryUrl), 'utf8');
const deskMotdSource = readFileSync(new URL('./desk-motd.ts', deskDirectoryUrl), 'utf8');
const deskRouteHelperSource = readFileSync(new URL('./desk-route.ts', deskDirectoryUrl), 'utf8');
const deskSessionSource = readFileSync(new URL('./desk-session.ts', deskDirectoryUrl), 'utf8');
const deskStatusSource = readFileSync(new URL('./desk-status.ts', deskDirectoryUrl), 'utf8');
const wordIndexSource = readFileSync(new URL('./word-index.ts', import.meta.url), 'utf8');

const rootLibFileNames = readdirSync(new URL('./', import.meta.url), { withFileTypes: true })
	.filter((entry) => entry.isFile())
	.map((entry) => entry.name);

assert.deepEqual(
	rootLibFileNames.filter((name) => /^Desk|^desk-/.test(name)).sort(),
	[],
	'Word Desk files should be clustered under src/lib/desk instead of flat src/lib'
);

assert.ok(
	existsSync(new URL('./reader-api.ts', readerDirectoryUrl)) &&
		existsSync(new URL('./reader-api.test.ts', readerDirectoryUrl)) &&
		existsSync(new URL('./text.ts', readerDirectoryUrl)),
	'Reader-specific API and text helpers should live under src/lib/reader'
);

assert.deepEqual(
	rootLibFileNames
		.filter(
			(name) =>
				name === 'reader.ts' ||
				name === 'reader.test.ts' ||
				/^reader-(index|loading|page)-.*\.ts$/.test(name)
		)
		.sort(),
	[],
	'Reader domain helpers should be clustered under src/lib/reader instead of flat src/lib'
);

for (const readerGuardFile of ['page-loading.test.ts', 'reading-surface-guards.test.ts']) {
	const source = readFileSync(new URL(`./${readerGuardFile}`, readerDirectoryUrl), 'utf8');
	const lineCount = source.split('\n').length;
	assert.ok(
		lineCount < 1000,
		`Reader source guard ${readerGuardFile} should stay below 1000 lines; split by UI concern`
	);
}

{
	const source = readFileSync(new URL('./index.ts', readerDirectoryUrl), 'utf8');
	const lineCount = source.split('\n').length;
	assert.ok(
		lineCount < 1000,
		'Reader domain index should stay below 1000 lines; extract focused helper modules'
	);
}

for (const referenceUrl of [
	'https://svelte.dev/docs/kit/project-structure',
	'https://svelte.dev/docs/kit/routing',
	'https://svelte.dev/docs/kit/load',
	'https://svelte.dev/docs/kit/state-management',
	'https://svelte.dev/docs/svelte/svelte-files',
	'https://svelte.dev/docs/svelte/$props'
]) {
	assert.ok(
		guidelinesSource.includes(referenceUrl),
		`SvelteKit guidelines should cite official reference: ${referenceUrl}`
	);
}

for (const guidelineToken of [
	'Do not add Alpine.js or htmx',
	'SvelteKit routes should orchestrate. Components should render.',
	'Use Svelte 5 `$props` with typed props',
	'src/lib/<surface>/*',
	'The Lexicon Word Desk lives in',
	'Prefer SvelteKit `load`',
	'Do not put request-specific state in shared server modules',
	'visible waits should expose elapsed seconds',
	'After frontend changes, rebuild production and restart the process listening on'
]) {
	assert.ok(
		guidelinesSource.includes(guidelineToken),
		`SvelteKit guidelines should preserve project rule: ${guidelineToken}`
	);
}

for (const linkedDoc of [uiDocSource, webappReadmeSource, docsReadmeSource]) {
	assert.ok(
		linkedDoc.includes('SVELTEKIT_GUIDELINES.md'),
		'SvelteKit guidelines should be discoverable from UI, webapp, and main docs'
	);
}

for (const extractedComponent of [
	'OrionProvenanceChips.svelte',
	'DeskActivityLedger.svelte',
	'DeskComponentLedger.svelte',
	'DeskColophonPanel.svelte',
	'DeskDictionaryGroupCard.svelte',
	'DeskHeadwordBookplate.svelte',
	'DeskHeroSearch.svelte',
	'DeskLookupLoadingPanel.svelte',
	'DeskLookupResults.svelte',
	'DeskMotdFolio.svelte',
	'DeskMotdSkeletonList.svelte',
	'DeskPageShell.svelte',
	'DeskPageMarksPanel.svelte',
	'DeskParadigmPanel.svelte',
	'DeskPulseWidget.svelte',
	'DeskSearchReading.svelte',
	'DeskSidebar.svelte',
	'DeskSourceControls.svelte',
	'DeskToolChip.svelte',
	'DeskTopbar.svelte',
	'DeskWordIndexEarmarks.svelte',
	'DeskWordIndexRail.svelte',
	'DeskWordIndexRows.svelte',
	'DeskWordIndexSections.svelte',
	'OrionObjectCard.svelte',
	'ReaderActiveFilter.svelte',
	'ReaderAddressLookup.svelte',
	'ReaderAuthorDiscoveryView.svelte',
	'ReaderAuthorList.svelte',
	'ReaderAuthorSearchForm.svelte',
	'ReaderAuthorToc.svelte',
	'ReaderCanonTable.svelte',
	'ReaderContextSidebar.svelte',
	'ReaderContentsList.svelte',
	'ReaderCurrentDivision.svelte',
	'ReaderDeskChrome.svelte',
	'ReaderDeskEmpty.svelte',
	'ReaderDeskHeader.svelte',
	'ReaderDiscoveryChooser.svelte',
	'ReaderDiscoveryHeader.svelte',
	'ReaderDiscoveryPager.svelte',
	'ReaderDiscoverySummary.svelte',
	'ReaderDiscoveryShelves.svelte',
	'ReaderDiscoveryView.svelte',
	'ReaderErrorPanel.svelte',
	'ReaderLeaf.svelte',
	'ReaderLoadingRows.svelte',
	'ReaderLoadingStrip.svelte',
	'ReaderPageNav.svelte',
	'ReaderPassageView.svelte',
	'ReaderSelectedWorkDesk.svelte',
	'ReaderShelfWorkResults.svelte',
	'ReaderShelfWorkSearchForm.svelte',
	'ReaderShelfWorkView.svelte',
	'ReaderSelectedWordPanel.svelte',
	'ReaderSourceDetails.svelte',
	'ReaderTextSearchForm.svelte',
	'ReaderTextSearchResults.svelte',
	'ReaderTextSearchView.svelte',
	'ReaderWorkDossier.svelte',
	'ReaderApparatusSheet.svelte',
	'ReaderApparatusStructurePanel.svelte',
	'ReaderApparatusTabs.svelte',
	'ReaderApparatusWordPanel.svelte',
	'ReaderApparatusOraclePanel.svelte',
	'ReaderApparatusEvidencePanel.svelte'
]) {
	const componentUrl = extractedComponent.startsWith('Desk')
		? new URL(`./${extractedComponent}`, deskDirectoryUrl)
		: new URL(`./${extractedComponent}`, import.meta.url);
	assert.ok(existsSync(componentUrl), `${extractedComponent} should exist as a focused component`);
	const source = readFileSync(componentUrl, 'utf8');
	const lineCount = source.split('\n').length;
	assert.ok(
		lineCount < 500,
		`${extractedComponent} should stay below the preferred 500-line target`
	);
	assert.ok(source.includes('$props'), `${extractedComponent} should use Svelte 5 $props`);
}

assert.ok(
	deskRouteSource.includes("from '$lib/desk/desk-endpoints'") &&
		deskRouteSource.includes('searchEndpointUrl({') &&
		deskRouteSource.includes('wordIndexNearbyEndpointUrl({') &&
		deskEndpointsSource.includes('export function searchEndpointUrl') &&
		deskEndpointsSource.includes('export function wordIndexNearbyEndpointUrl'),
	'Word Desk route should delegate endpoint construction to focused helper functions'
);

assert.ok(
	deskEntrySource.includes('export function groupBuckets') &&
		deskEntrySource.includes('export function sectionSegments') &&
		deskEntrySource.includes('export function componentMeaningSegments') &&
		!deskRouteSource.includes('function groupBuckets') &&
		!deskRouteSource.includes('function sectionSegments') &&
		!deskRouteSource.includes('function componentMeaningSegments'),
	'Word Desk route should delegate entry grouping, section display, and component meaning helpers to desk-entry.ts'
);
assert.ok(
	deskRouteHelperSource.includes('export function deskAppRouteUrl') &&
		deskRouteHelperSource.includes('export function deskMotdHref') &&
		deskRouteHelperSource.includes('export function deskWordIndexHref') &&
		deskRouteSource.includes('deskAppRouteUrl({') &&
		deskRouteSource.includes('deskMotdHref(item') &&
		deskRouteSource.includes('deskWordIndexHref(item') &&
		!deskRouteSource.includes("params.append('visible'") &&
		!deskRouteSource.includes("params.append('source'") &&
		!deskRouteSource.includes("params.set('dictionary'"),
	'Word Desk route should delegate shareable URL construction to desk-route.ts'
);
assert.ok(
	deskRouteHelperSource.includes('export function deskRouteHydration') &&
		deskRouteSource.includes('deskRouteHydration({') &&
		!deskRouteSource.includes('readLanguageParam') &&
		!deskRouteSource.includes('readToolParams') &&
		!deskRouteSource.includes('routeShouldLoad') &&
		!deskRouteSource.includes('shouldLoadEncounterForRoute') &&
		!deskRouteSource.includes('shouldResetEncounterForRoute'),
	'Word Desk route should delegate URL hydration parsing and load/preserve decisions to desk-route.ts'
);
assert.ok(
	deskLookupSource.includes('export function validateDeskLookupWord') &&
		deskLookupSource.includes('export function firstPassTranslationMode') &&
		deskLookupSource.includes('export function deskEncounterViewState') &&
		deskRouteSource.includes('validateDeskLookupWord(query)') &&
		deskRouteSource.includes('deskEncounterViewState({') &&
		!deskRouteSource.includes("mode === 'auto' || mode === 'populate'") &&
		!deskRouteSource.includes('const nextReturnedTools = [') &&
		!deskRouteSource.includes('const routedVisibleTools ='),
	'Word Desk route should delegate lookup validation, enrichment policy, and encounter view-state derivation to desk-lookup.ts'
);
assert.ok(
	deskLookupSource.includes('export async function fetchDeskEncounter') &&
		deskLookupSource.includes('export async function retryDeskTranslation') &&
		deskRouteSource.includes('fetchDeskEncounter({') &&
		deskRouteSource.includes('retryDeskTranslation({') &&
		!deskRouteSource.includes('Promise.all([') &&
		!deskRouteSource.includes("'/api/translation-cache'") &&
		!deskRouteSource.includes('max_retries'),
	'Word Desk route should delegate encounter fetch delay mechanics and translation retry POST construction to desk-lookup.ts'
);

assert.ok(
	deskStatusSource.includes('export function deskCacheSummary') &&
		deskStatusSource.includes('export function deskCurrentStatusLabel') &&
		deskStatusSource.includes('export function deskCurrentStatusDetail') &&
		deskStatusSource.includes('export function deskReaderLayerStatus') &&
		deskRouteSource.includes('deskCacheSummary(encounter)') &&
		deskRouteSource.includes('deskCurrentStatusLabel({') &&
		deskRouteSource.includes('deskCurrentStatusDetail({') &&
		deskRouteSource.includes('deskReaderLayerStatus({') &&
		!deskRouteSource.includes('function cacheSummary') &&
		!deskRouteSource.includes('function readerLayerStatus') &&
		!deskRouteSource.includes('uiCopy.status.cacheUnavailable') &&
		!deskRouteSource.includes('uiCopy.status.showingSections(') &&
		!deskRouteSource.includes('uiCopy.readerLayer.'),
	'Word Desk route should delegate status, reader-layer, and translation-cache display policy to desk-status.ts'
);

assert.ok(
	readerRouteSource.includes("from '$lib/reader/reader-api'") &&
		readerApiSource.includes('export function readerCatalogsUrl') &&
		readerApiSource.includes('export function readerEncounterBriefingUrl') &&
		readerApiSource.includes('export async function fetchReaderEncounterBriefing') &&
		readerApiSource.includes('export function readerWorksUrl') &&
		readerApiSource.includes('export function readerContentsUrl') &&
		readerRouteSource.includes('readerCatalogsUrl()') &&
		readerRouteSource.includes('fetchReaderEncounterBriefing({') &&
		readerRouteSource.includes('readerWorksUrl({') &&
		readerRouteSource.includes('readerContentsUrl({') &&
		!readerRouteSource.includes('new URLSearchParams({') &&
		!readerRouteSource.includes("'/api/reader?mode=catalogs'") &&
		!readerRouteSource.includes('/api/encounter-briefing?'),
	'Reader route should delegate API and encounter briefing URL construction to src/lib/reader/reader-api.ts'
);

for (const localEndpointFunction of [
	'function wordIndexEndpointUrl',
	'function wordIndexSectionsEndpointUrl',
	'function wordIndexBrowseEndpointUrl'
]) {
	assert.equal(
		deskRouteSource.includes(localEndpointFunction),
		false,
		`Word Desk route should not keep local endpoint builder ${localEndpointFunction}`
	);
}

assert.ok(
	deskRouteSource.includes('wordIndexMergedRowsFromResponse(currentWordIndex)') &&
		deskRouteSource.includes('wordIndexRowMatchedWithQuery(row') &&
		deskRouteSource.includes('wordIndexRowSourcesForLanguage(row, language') &&
		wordIndexSource.includes('export function wordIndexMergedRowsFromResponse') &&
		wordIndexSource.includes('export function wordIndexRowMatched'),
	'Word Desk route should keep pure endpoint and word-index row helpers outside route markup'
);

for (const localWordIndexFunction of [
	'function mergeWordIndexRows',
	'function mergedWordIndexRowsFromResponse',
	'function wordIndexMergeKey',
	'function wordIndexSortKey',
	'function wordIndexPrimaryItem',
	'function wordIndexDisplay(',
	'function wordIndexLookup(',
	'function wordIndexEntryCountLabel',
	'function encounterWordIndexMatchKeys',
	'function sourceToolFromWordIndex'
]) {
	assert.equal(
		deskRouteSource.includes(localWordIndexFunction),
		false,
		`Word Desk route should not keep local word-index helper ${localWordIndexFunction}`
	);
}

assert.ok(
	deskRouteSource.includes("from '$lib/desk/desk-motd'") &&
		deskRouteSource.includes('motdVisibleWarningsForResult(motd)') &&
		deskMotdSource.includes('export function normalizeMotdResult') &&
		deskMotdSource.includes('export function motdDisplayWord'),
	'Word Desk route should delegate MOTD normalization and display helpers to desk-motd.ts'
);

for (const localMotdFunction of [
	'function normalizeMotdResult',
	'function normalizeMotdItem',
	'function motdDisplayWord',
	'function stripLatinMotdTags',
	'function stripGreekMotdEncoding',
	'function motdWordClass',
	'function motdWordLang',
	'function motdDisplayLookup',
	'function greekMotdRomanLookup',
	'function transliterateGreekMotd',
	'function stripSanskritMotdEncoding',
	'function motdDisplayGloss',
	'function motdDisplayNote',
	'function shouldShowMotdWarning',
	'function isRecoverableMotdWarning'
]) {
	assert.equal(
		deskRouteSource.includes(localMotdFunction),
		false,
		`Word Desk route should not keep local MOTD helper ${localMotdFunction}`
	);
}

assert.ok(
	deskRouteSource.includes("from '$lib/desk/desk-session'") &&
		deskRouteSource.includes('encounterMatchesStoredRoute(stored.encounter, language, query)') &&
		deskSessionSource.includes('export function encounterNeedsFreshReaderLayer') &&
		deskSessionSource.includes('export function validStoredTools'),
	'Word Desk route should delegate pure session/freshness helpers to desk-session.ts'
);

for (const localSessionFunction of [
	'function encounterNeedsFreshReaderLayer',
	'function hasStaleTranslatedSourceLayer',
	'function sourceLayerLooksLikeReaderEnglish',
	'function encounterMatchesStoredRoute',
	'function validStoredTools',
	'function returnedToolsForEncounter',
	'function hasMissingSourceReaderTranslations',
	'function isTranslatedSourceTool'
]) {
	assert.equal(
		deskRouteSource.includes(localSessionFunction),
		false,
		`Word Desk route should not keep local session helper ${localSessionFunction}`
	);
}

for (const [globalChipSelector, componentName] of [
	['\n\t.orion-source-grid', 'DeskSourceControls.svelte'],
	['\n\t.orion-page {', 'DeskPageShell.svelte'],
	['\n\t.orion-page-shell', 'DeskPageShell.svelte'],
	['\n\t.orion-sidebar', 'DeskSidebar.svelte'],
	['\n\t.orion-home-seal', 'DeskTopbar.svelte'],
	['\n\t.orion-topbar-control', 'DeskTopbar.svelte'],
	['\n\t.orion-tool-chip', 'DeskToolChip.svelte'],
	['\n\t.orion-tool-icon', 'DeskToolChip.svelte'],
	['\n\t.orion-tool-check', 'DeskToolChip.svelte'],
	['\n\t.orion-pulse-widget', 'DeskPulseWidget.svelte'],
	['\n\t.orion-search-reading', 'DeskSearchReading.svelte'],
	['\n\t.orion-motd-folio', 'DeskMotdFolio.svelte'],
	['\n\t.orion-motd-link', 'DeskMotdFolio.svelte'],
	['\n\t.orion-motd-control-skeleton', 'DeskMotdFolio.svelte'],
	['\n\t.orion-motd-skeleton-card', 'DeskMotdFolio.svelte'],
	['\n\t.orion-endpoint-code', 'DeskPageMarksPanel.svelte'],
	['\n\t.orion-earmarks', 'DeskWordIndexEarmarks.svelte'],
	['\n\t.orion-index-section-rail', 'DeskWordIndexRail.svelte'],
	['\n\t.orion-index-skeleton', 'DeskWordIndexRail.svelte'],
	['\n\t.orion-index-busy', 'DeskWordIndexRail.svelte'],
	['\n\t.orion-index-groups', 'DeskWordIndexRail.svelte'],
	['\n\t.orion-index-row', 'DeskWordIndexRail.svelte'],
	['\n\t.orion-index-earmark', 'DeskWordIndexRail.svelte'],
	['\n\t.orion-component-ledger', 'DeskComponentLedger.svelte'],
	['\n\t.orion-component-count', 'DeskComponentLedger.svelte'],
	['\n\t.orion-component-list', 'DeskComponentLedger.svelte'],
	['\n\t.orion-component-source', 'DeskComponentLedger.svelte'],
	['\n\t.orion-component-empty', 'DeskComponentLedger.svelte'],
	['\n\t.orion-component-meaning', 'DeskComponentLedger.svelte'],
	['\n\t.orion-activity-ledger', 'DeskActivityLedger.svelte'],
	['\n\t.orion-paradigm-panel', 'DeskParadigmPanel.svelte'],
	['\n\t.orion-learning-strip', 'DeskParadigmPanel.svelte'],
	['\n\t.orion-table-learning', 'DeskParadigmPanel.svelte'],
	['\n\t.orion-entry-bookplate', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-illuminated-title', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-plain-title', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-devanagari-title', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-headword-forms', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-entry-lead', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-entry-source-line', 'DeskHeadwordBookplate.svelte'],
	['\n\t.orion-result-group', 'desk-entry.css'],
	['\n\t.orion-entry-reader', 'desk-entry.css'],
	['\n\t.orion-reader-sections', 'desk-entry.css'],
	['\n\t.orion-reader-section', 'desk-entry.css'],
	['\n\t.orion-reader-marker', 'desk-entry.css'],
	['\n\t.orion-branch-toggle', 'desk-entry.css'],
	['\n\t.orion-section-detail-toggle', 'desk-entry.css'],
	['\n\t.orion-entry-source-strip', 'desk-entry.css'],
	['\n\t.orion-entry-chrome', 'desk-entry.css'],
	['\n\t.orion-translator-sigil', 'desk-entry.css'],
	['\n\t.orion-layer-switch', 'desk-entry.css'],
	['@keyframes orion-pulse-ring', 'DeskPulseWidget.svelte'],
	['@keyframes orion-pulse-core', 'DeskPulseWidget.svelte'],
	['@keyframes orion-pulse-dot', 'DeskPulseWidget.svelte'],
	['@keyframes orion-translator-dot', 'desk-entry.css'],
	['@keyframes orion-translation-leaf', 'desk-entry.css'],
	['@keyframes orion-translation-ink', 'desk-entry.css'],
	['@keyframes orion-translation-gild', 'desk-entry.css']
] as const) {
	assert.ok(
		!appCssSource.includes(globalChipSelector),
		`desk source selector ${globalChipSelector.trim()} should live in ${componentName}`
	);
}

for (const entrySelector of [
	'.orion-result-group',
	'.orion-entry-reader',
	'.orion-reader-sections',
	'.orion-section-detail-toggle',
	'.orion-entry-chrome',
	'.orion-translator-sigil',
	'@keyframes orion-translator-dot'
]) {
	assert.ok(
		deskEntryCssSource.includes(entrySelector),
		`desk-entry.css should keep shared entry frame selector: ${entrySelector}`
	);
}

for (const entryFrameComponent of [
	'DeskDictionaryGroupCard.svelte',
	'DeskComponentLedger.svelte'
] as const) {
	const source = readFileSync(new URL(`./${entryFrameComponent}`, deskDirectoryUrl), 'utf8');
	assert.ok(
		source.includes("import '$lib/desk/desk-entry.css';"),
		`${entryFrameComponent} should import the shared entry frame stylesheet`
	);
}

{
	const deskRouteSource = readFileSync(new URL('../routes/+page.svelte', import.meta.url), 'utf8');

	assert.ok(
		deskRouteSource.includes('DeskPageShell'),
		'desk route should compose page layout through DeskPageShell'
	);
	assert.ok(
		!deskRouteSource.includes('<main class="orion-page') &&
			!deskRouteSource.includes('orion-page-shell'),
		'desk route should not keep local page shell markup'
	);
	assert.ok(
		deskRouteSource.includes('DeskSidebar'),
		'desk route should compose sidebar instruments through DeskSidebar'
	);
	assert.ok(
		!deskRouteSource.includes('<aside') && !deskRouteSource.includes('orion-sidebar'),
		'desk route should not keep local sidebar chrome markup'
	);
	assert.ok(
		deskRouteSource.includes('DeskTopbar'),
		'desk route should compose navigation and status through DeskTopbar'
	);
	assert.ok(
		!deskRouteSource.includes('orion-home-seal') &&
			!deskRouteSource.includes('orion-topbar-control'),
		'desk route should not keep local topbar chrome markup'
	);
	assert.ok(
		!deskRouteSource.includes('orion-source-grid'),
		'desk route should not keep local source grid markup'
	);
	assert.ok(
		!deskRouteSource.includes('orion-search-reading'),
		'desk route should not keep local romanized search reading markup'
	);
	assert.ok(
		!deskRouteSource.includes('uiCopy.colophon'),
		'desk route should not keep local encounter colophon markup'
	);
	assert.ok(
		deskRouteSource.includes('DeskHeroSearch'),
		'desk route should compose hero search through DeskHeroSearch'
	);
	assert.ok(
		!deskRouteSource.includes('uiCopy.hero'),
		'desk route should not keep local hero search markup'
	);
	assert.ok(
		deskRouteSource.includes('DeskActivityLedger'),
		'desk route should compose async status through DeskActivityLedger'
	);
	assert.ok(
		deskRouteSource.includes('DeskLookupResults'),
		'desk route should compose lookup result surfaces through DeskLookupResults'
	);
	assert.ok(
		!deskRouteSource.includes('uiCopy.search.loadingTitle') &&
			!deskRouteSource.includes('uiCopy.search.coldSources'),
		'desk route should not keep local lookup loading panel copy'
	);
	assert.ok(
		!deskRouteSource.includes('orion-paradigm-panel') &&
			!deskRouteSource.includes('orion-learning-strip'),
		'desk route should not keep local paradigm panel markup'
	);
	assert.ok(
		!deskRouteSource.includes('orion-dictionary-witnesses') &&
			!deskRouteSource.includes('uiCopy.results.noFilterMatch') &&
			!deskRouteSource.includes('uiCopy.translator.alert'),
		'desk route should not keep local lookup result/witness markup'
	);

	const lookupResultsSource = readFileSync(
		new URL('./DeskLookupResults.svelte', deskDirectoryUrl),
		'utf8'
	);
	assert.ok(
		lookupResultsSource.includes('DeskLookupLoadingPanel'),
		'DeskLookupResults should compose the lookup waiting panel through DeskLookupLoadingPanel'
	);
	assert.ok(
		lookupResultsSource.includes('DeskParadigmPanel'),
		'DeskLookupResults should compose form tables through DeskParadigmPanel'
	);
	assert.ok(
		lookupResultsSource.includes('DeskComponentLedger'),
		'DeskLookupResults should compose compound members through DeskComponentLedger'
	);
	assert.ok(
		lookupResultsSource.includes('DeskDictionaryGroupCard'),
		'DeskLookupResults should compose dictionary source groups through DeskDictionaryGroupCard'
	);

	const heroSearchSource = readFileSync(
		new URL('./DeskHeroSearch.svelte', deskDirectoryUrl),
		'utf8'
	);
	assert.ok(
		heroSearchSource.includes('DeskSearchReading'),
		'DeskHeroSearch should compose romanized search readings through DeskSearchReading'
	);
	assert.ok(
		deskRouteSource.includes('DeskMotdFolio'),
		'desk route should compose margin recommendations through DeskMotdFolio'
	);
	assert.ok(
		!deskRouteSource.includes('uiCopy.margin'),
		'desk route should not keep local margin folio markup'
	);
	assert.ok(
		!deskRouteSource.includes('uiCopy.pageMarks'),
		'desk route should not keep local page marks markup'
	);
	assert.ok(
		!deskRouteSource.includes('orion-earmarks'),
		'desk route should not keep local word-index earmark markup'
	);
	assert.ok(
		!deskRouteSource.includes('orion-index-section-rail') &&
			!deskRouteSource.includes('orion-index-row'),
		'desk route should not keep local word-index rail markup'
	);

	const wordIndexRailSource = readFileSync(
		new URL('./DeskWordIndexRail.svelte', deskDirectoryUrl),
		'utf8'
	);
	assert.ok(
		wordIndexRailSource.includes('DeskWordIndexEarmarks') &&
			wordIndexRailSource.includes('DeskWordIndexSections') &&
			wordIndexRailSource.includes('DeskWordIndexRows'),
		'DeskWordIndexRail should compose saved earmarks, section navigation, and row rendering'
	);
	const sidebarSource = readFileSync(new URL('./DeskSidebar.svelte', deskDirectoryUrl), 'utf8');
	assert.ok(
		sidebarSource.includes('DeskWordIndexRail') &&
			sidebarSource.includes('DeskSourceControls') &&
			sidebarSource.includes('DeskColophonPanel') &&
			sidebarSource.includes('DeskPageMarksPanel'),
		'DeskSidebar should compose word-index, source controls, colophon, and page marks'
	);
	assert.ok(
		!deskRouteSource.includes('orion-component-ledger') &&
			!deskRouteSource.includes('orion-component-list'),
		'desk route should not keep local compound member ledger markup'
	);
	assert.ok(
		!deskRouteSource.includes('orion-entry-bookplate') &&
			!deskRouteSource.includes('orion-headword-forms'),
		'desk route should not keep local illuminated headword bookplate markup'
	);
	assert.ok(
		!deskRouteSource.includes('visibleGroupBuckets(group) as bucket') &&
			!deskRouteSource.includes('orion-entry-reader'),
		'desk route should not keep local dictionary source-group card markup'
	);

	const componentLedgerSource = readFileSync(
		new URL('./DeskComponentLedger.svelte', deskDirectoryUrl),
		'utf8'
	);
	const dictionaryGroupCardSource = readFileSync(
		new URL('./DeskDictionaryGroupCard.svelte', deskDirectoryUrl),
		'utf8'
	);
	assert.ok(
		dictionaryGroupCardSource.includes('DeskHeadwordBookplate'),
		'DeskDictionaryGroupCard should compose dictionary headword bookplates through DeskHeadwordBookplate'
	);
	assert.ok(
		componentLedgerSource.includes('DeskHeadwordBookplate'),
		'DeskComponentLedger should reuse DeskHeadwordBookplate for member objects'
	);
	assert.ok(
		!componentLedgerSource.includes('orion-entry-bookplate') &&
			!componentLedgerSource.includes('orion-headword-forms'),
		'DeskComponentLedger should not keep local illuminated headword bookplate markup'
	);
}

for (const primitiveConsumer of [
	'./ReaderCurrentDivision.svelte',
	'./ReaderWorkDossier.svelte',
	'./ReaderApparatusEvidencePanel.svelte'
]) {
	const source = readFileSync(new URL(primitiveConsumer, import.meta.url), 'utf8');

	assert.ok(
		source.includes('OrionProvenanceChips'),
		`${primitiveConsumer} should use the shared provenance chip component`
	);
	assert.ok(
		!source.includes('{#snippet provenanceChips'),
		`${primitiveConsumer} should not keep a local provenance chip snippet`
	);
}

for (const composedConsumer of [
	['../routes/reader/+page.svelte', 'ReaderPassageView', ''],
	['../routes/reader/+page.svelte', 'ReaderDiscoveryView', ''],
	['../routes/reader/+page.svelte', 'ReaderSelectedWorkDesk', ''],
	['./ReaderSelectedWorkDesk.svelte', 'OrionObjectCard', 'ReaderWorkDossier'],
	['./ReaderDiscoveryView.svelte', 'ReaderTextSearchView', 'ReaderShelfWorkView'],
	['./ReaderPassageView.svelte', 'ReaderCurrentDivision', 'ReaderLeaf'],
	['./ReaderContextSidebar.svelte', 'ReaderCanonTable', 'ReaderContentsList'],
	['./ReaderApparatusWordPanel.svelte', 'OrionObjectCard', ''],
	['./ReaderApparatusStructurePanel.svelte', 'ReaderCanonTable', '']
]) {
	const [path, firstComponent, secondComponent] = composedConsumer;
	const source = readFileSync(new URL(path, import.meta.url), 'utf8');

	assert.ok(source.includes(firstComponent), `${path} should use ${firstComponent}`);
	if (secondComponent) {
		assert.ok(source.includes(secondComponent), `${path} should use ${secondComponent}`);
	}
	assert.ok(
		!source.includes('{#snippet objectCard') && !source.includes('{#snippet canonTable'),
		`${path} should not keep local Object Card or Canon Table snippets`
	);
}

for (const routePath of [
	'webapp/src/routes/+page.svelte',
	'webapp/src/routes/reader/+page.svelte'
]) {
	const relativeToLib =
		routePath === 'webapp/src/routes/+page.svelte'
			? '../routes/+page.svelte'
			: '../routes/reader/+page.svelte';
	const source = readFileSync(new URL(relativeToLib, import.meta.url), 'utf8');
	const lineCount = source.split('\n').length;

	if (lineCount > 2000) {
		assert.ok(
			guidelinesSource.includes(routePath),
			`${routePath} is oversized and must remain listed as an active cleanup target`
		);
	}
}
