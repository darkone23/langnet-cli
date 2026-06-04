import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const readerPageSource = readFileSync(
	new URL('./ReaderRouteController.svelte', import.meta.url),
	'utf8'
);
const readerPageViewSource = readFileSync(
	new URL('./ReaderRouteControllerView.svelte', import.meta.url),
	'utf8'
);
const readerApiSource = readFileSync(new URL('./reader-api.ts', import.meta.url), 'utf8');
const readerContentLoadersSource = readFileSync(
	new URL('./reader-route-content-loaders.ts', import.meta.url),
	'utf8'
);
const readerDiscoveryLoadersSource = readFileSync(
	new URL('./reader-route-discovery-loaders.ts', import.meta.url),
	'utf8'
);
const readerRouteWorkspaceSource = readFileSync(
	new URL('./reader-route-workspace.ts', import.meta.url),
	'utf8'
);
const readerCssSource = readFileSync(new URL('../../app.css', import.meta.url), 'utf8');
const apparatusSheetSource = readFileSync(
	new URL('./ReaderApparatusSheet.svelte', import.meta.url),
	'utf8'
);
const apparatusWordSource = readFileSync(
	new URL('./ReaderApparatusWordPanel.svelte', import.meta.url),
	'utf8'
);
const apparatusOracleSource = readFileSync(
	new URL('./ReaderApparatusOraclePanel.svelte', import.meta.url),
	'utf8'
);
const apparatusEvidenceSource = readFileSync(
	new URL('./ReaderApparatusEvidencePanel.svelte', import.meta.url),
	'utf8'
);
const apparatusStructureSource = readFileSync(
	new URL('./ReaderApparatusStructurePanel.svelte', import.meta.url),
	'utf8'
);
const readerShellSource = readFileSync(new URL('./ReaderShell.svelte', import.meta.url), 'utf8');
const readerSelectedWorkDeskSource = readFileSync(
	new URL('./ReaderSelectedWorkDesk.svelte', import.meta.url),
	'utf8'
);
const discoveryViewSource = readFileSync(
	new URL('./ReaderDiscoveryView.svelte', import.meta.url),
	'utf8'
);
const deskHeaderSource = readFileSync(
	new URL('./ReaderDeskHeader.svelte', import.meta.url),
	'utf8'
);
const readerContentsListSource = readFileSync(
	new URL('./ReaderContentsList.svelte', import.meta.url),
	'utf8'
);
const workDossierSource = readFileSync(
	new URL('./ReaderWorkDossier.svelte', import.meta.url),
	'utf8'
);
const currentDivisionSource = readFileSync(
	new URL('./ReaderCurrentDivision.svelte', import.meta.url),
	'utf8'
);
const pageNavSource = readFileSync(new URL('./ReaderPageNav.svelte', import.meta.url), 'utf8');
const readerPassageViewSource = readFileSync(
	new URL('./ReaderPassageView.svelte', import.meta.url),
	'utf8'
);
const readerLeafSource = readFileSync(new URL('./ReaderLeaf.svelte', import.meta.url), 'utf8');
const readerSourceDetailsSource = readFileSync(
	new URL('./ReaderSourceDetails.svelte', import.meta.url),
	'utf8'
);

function assertIncludes(source: string, tokens: string[], label: string) {
	for (const token of tokens) {
		assert.ok(source.includes(token), `${label} should expose token: ${token}`);
	}
}

function assertScoped(source: string, tokens: string[], label: string) {
	for (const token of tokens) {
		assert.ok(source.includes(token), `${label} should define scoped style: ${token}`);
		assert.ok(
			!readerCssSource.includes(`\n\t${token}`),
			`component-local ${label} selector should move out of app.css: ${token}`
		);
	}
}

assertIncludes(
	apparatusSheetSource,
	[
		'orion-reader-apparatus-sheet open',
		'<style>',
		'ReaderApparatusStructurePanel',
		'ReaderApparatusWordPanel',
		'ReaderApparatusOraclePanel',
		'ReaderApparatusEvidencePanel',
		'.orion-reader-apparatus-sheet-head'
	],
	'apparatus shell'
);
assertScoped(
	apparatusSheetSource,
	['.orion-reader-apparatus-sheet', '.orion-reader-apparatus-sheet-head'],
	'Apparatus Sheet component'
);
assertIncludes(
	apparatusWordSource,
	[
		'orion-reader-apparatus-word-panel',
		'<style>',
		'.orion-reader-apparatus-summary',
		'selectedWordBriefingBadge',
		'selectedWordHref'
	],
	'word apparatus panel'
);
assertIncludes(
	apparatusOracleSource,
	[
		'orion-reader-apparatus-oracle-panel',
		'<style>',
		'selectedWordBriefingCanGenerate',
		'onGenerateBriefing'
	],
	'oracle apparatus panel'
);
assertIncludes(
	apparatusEvidenceSource,
	[
		'orion-reader-apparatus-evidence-panel',
		'<style>',
		'.orion-reader-apparatus-evidence-list',
		'currentDivisionTrail.length',
		'selectedSegment.citation_path'
	],
	'evidence apparatus panel'
);
assert.ok(
	apparatusStructureSource.includes('ReaderCanonTable'),
	'structure apparatus panel should use the shared Canon Table component'
);
for (const token of [
	'.orion-reader-apparatus-word-panel',
	'.orion-reader-apparatus-oracle-panel',
	'.orion-reader-apparatus-evidence-panel',
	'.orion-reader-apparatus-summary',
	'.orion-reader-apparatus-evidence-list'
]) {
	assert.ok(
		`${apparatusWordSource}\n${apparatusOracleSource}\n${apparatusEvidenceSource}`.includes(token),
		`apparatus panel component should define scoped style: ${token}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${token}`),
		`component-local apparatus selector should move out of app.css: ${token}`
	);
}

for (const [source, token] of [
	[readerShellSource, '.orion-reader-shell'],
	[readerShellSource, '.orion-reader-sidebar-frame'],
	[readerSelectedWorkDeskSource, '.orion-reader-work-desk'],
	[readerSelectedWorkDeskSource, '.orion-reader-work-desk :global(.orion-object-card)'],
	[discoveryViewSource, '.orion-reader-discovery'],
	[deskHeaderSource, '.orion-reader-desk-kicker'],
	[readerContentsListSource, '.orion-reader-page-segments summary']
] as const) {
	assert.ok(source.includes(token), `reader layout selector should live with owner: ${token}`);
}
for (const token of [
	'\n\t.orion-reader-shell',
	'\n\t.orion-reader-sidebar',
	'\n\t.orion-reader-work-desk',
	'\n\t.orion-reader-desk-passage',
	'\n\t.orion-reader-desk-kicker',
	'\n\t.orion-reader-page-segments',
	'\n\t.orion-reader-discovery'
]) {
	assert.ok(
		!readerCssSource.includes(token),
		`reader layout selector should move out of app.css: ${token.trim()}`
	);
}

assertIncludes(
	`${readerPageSource}\n${readerPageViewSource}\n${readerApiSource}\n${readerContentLoadersSource}`,
	[
		'let structure = $state<ReaderStructureNode[]>([])',
		'readerStructureUrl({ catalogId: stateBag.catalogId, language: stateBag.language, work })',
		'await loadStructure(readerWorkRef(work))',
		'ReaderContextSidebar',
		'ReaderApparatusTabs',
		"readerLoadingElapsedSeconds('structure')"
	],
	'reader page structure UI'
);
assertIncludes(readerPageSource, ['ReaderRouteControllerView'], 'reader page orchestration');
assertIncludes(
	`${readerPageSource}\n${readerPageViewSource}\n${readerApiSource}\n${readerContentLoadersSource}`,
	[
		'let workDossier = $state<ReaderWorkDossierResponse | null>(null)',
		'loadWorkDossier',
		'readerWorkDossierUrl({ catalogId: stateBag.catalogId, language: stateBag.language, work })',
		'ReaderSelectedWorkDesk',
		'readerLoadingStatus(uiCopy.workDossier.loading,'
	],
	'reader page Work Dossier'
);
assertIncludes(
	workDossierSource,
	[
		'orion-reader-work-dossier',
		'<style>',
		'uiCopy.workDossier.title',
		'dossierStatItems',
		'orion-reader-work-dossier-stats',
		'dossier.division_bios.slice(0, 3)',
		'onRetry',
		'onOpenDivision'
	],
	'Work Dossier component'
);
assertScoped(
	workDossierSource,
	['.orion-reader-work-dossier', '.orion-reader-work-dossier-note'],
	'Work Dossier component'
);

assertIncludes(
	`${readerPageSource}\n${readerPageViewSource}`,
	['currentDivisionTrail', 'currentDivisionNode', 'ReaderPassageView', 'ReaderApparatusSheet'],
	'reader page current division marginalium'
);
assertIncludes(
	currentDivisionSource,
	[
		'orion-reader-current-division',
		'orion-reader-current-division-trail',
		'<style>',
		'OrionProvenanceChips',
		'uiCopy.readerStructure.current',
		'onOpenDivision'
	],
	'Current Division component'
);
assertScoped(
	currentDivisionSource,
	['.orion-reader-current-division', '.orion-reader-current-division-trail'],
	'Current Division component'
);

assertIncludes(
	`${readerPageSource}\n${readerPageViewSource}`,
	['ReaderPassageView', 'pagePrevCursor', 'pageNextCursor', 'pageRangeLabel'],
	'reader page navigation'
);
assertIncludes(
	pageNavSource,
	[
		'orion-reader-page-nav',
		'orion-reader-page-nav-bottom',
		'orion-reader-page-work-label',
		'<style>',
		'onOpenPage'
	],
	'Reader Page Nav component'
);
assertScoped(
	pageNavSource,
	['.orion-reader-page-nav', '.orion-reader-page-work-label'],
	'Reader Page Nav component'
);

assertIncludes(
	`${readerPageSource}\n${readerPageViewSource}`,
	['ReaderPassageView', 'pageSegments', 'segmentParts', 'selectToken', 'showSelectedWorkSegment'],
	'reader page Reader Leaf composition'
);
assertIncludes(
	readerPassageViewSource,
	[
		'ReaderErrorPanel',
		'ReaderLoadingRows',
		'ReaderLoadingStrip',
		'ReaderPageNav',
		'ReaderCurrentDivision',
		'ReaderLeaf',
		'ReaderSourceDetails',
		'Passage failed to load',
		'openingStatusLabel',
		'updatingStatusLabel',
		'onRetrySegment',
		'onOpenPage',
		'onOpenDivision',
		'onSelectToken',
		'<script lang="ts">'
	],
	'Reader Passage View component'
);
assertIncludes(
	readerLeafSource,
	[
		'orion-reader-leaf',
		'orion-reader-leaf-line',
		'orion-reader-token',
		'orion-reader-token-translit',
		'<style>',
		'onSelectToken',
		'onOpenSegment'
	],
	'Reader Leaf component'
);
assertScoped(
	readerLeafSource,
	['.orion-reader-leaf', '.orion-reader-leaf-line', '.orion-reader-token'],
	'Reader Leaf component'
);
assertIncludes(
	readerPassageViewSource,
	['ReaderSourceDetails', 'selectedSegment.source_text', 'selectedSegment.transliteration'],
	'Reader Passage View source details'
);
assertIncludes(
	readerSourceDetailsSource,
	[
		'orion-reader-desk-source',
		'Source / transliteration',
		'sourceText',
		'transliteration',
		'<style>'
	],
	'Reader Source Details component'
);
assertScoped(
	readerSourceDetailsSource,
	['.orion-reader-desk-source'],
	'Reader Source Details component'
);

const loadAuthorSectionsMatch = readerDiscoveryLoadersSource.match(
	/async function loadAuthorSections[\s\S]*?\n\t}\n\n\tasync function loadAuthors/
);
assert.ok(
	loadAuthorSectionsMatch,
	'reader page should define loadAuthorSections before loadAuthors'
);
const loadAuthorSectionsSource = loadAuthorSectionsMatch[0];
assert.ok(
	loadAuthorSectionsSource.indexOf('stateBag.authorsLoading = true') !== -1 &&
		loadAuthorSectionsSource.indexOf('stateBag.authorsLoading = true') <
			loadAuthorSectionsSource.indexOf('readerAuthorSectionsUrl'),
	'author loading should begin before fetching author sections'
);
assert.ok(
	loadAuthorSectionsSource.indexOf('const authorsPromise =') !== -1 &&
		loadAuthorSectionsSource.indexOf('const authorsPromise =') <
			loadAuthorSectionsSource.indexOf('readerAuthorSectionsUrl'),
	'top-author loading should begin before author sections finish'
);

const restoreReaderIndexStateMatch = readerRouteWorkspaceSource.match(
	/function restoreReaderIndexState\(\)[\s\S]*?\n\t}\n\n\tfunction saveReaderIndexState/
);
assert.ok(restoreReaderIndexStateMatch, 'reader page should define restoreReaderIndexState');
for (const token of [
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
		restoreReaderIndexStateMatch[0].includes(token),
		false,
		`reader state restore should not replay cached API payloads: ${token}`
	);
}

const saveReaderIndexStateMatch = readerRouteWorkspaceSource.match(
	/function saveReaderIndexState\(\)[\s\S]*?\n\t}\n\n\treturn/
);
assert.ok(saveReaderIndexStateMatch, 'reader page should define saveReaderIndexState');
for (const token of [
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
		saveReaderIndexStateMatch[0].includes(token),
		false,
		`reader state persistence should not store API payloads: ${token}`
	);
}

const selectLanguageMatch = readerPageSource.match(
	/function selectLanguage[\s\S]*?\n\t}\n\n\tasync function fetchEncounterBriefing/
);
assert.ok(selectLanguageMatch, 'reader page should define selectLanguage before fetch helpers');
assert.ok(
	!selectLanguageMatch[0].includes('loadAllReaderIndexStats'),
	'language changes should not refetch stats for every language'
);
const loadReaderIndexStatsForMatch = readerPageSource.match(
	/async function loadReaderIndexStatsFor[\s\S]*?\n\t}\n\n\tasync function loadAllReaderIndexStats/
);
assert.ok(loadReaderIndexStatsForMatch, 'reader page should define loadReaderIndexStatsFor');
assert.ok(
	loadReaderIndexStatsForMatch[0].includes('readerHasIndexStats') &&
		loadReaderIndexStatsForMatch[0].includes('readerIndexStatsInFlight'),
	'reader stats requests should skip cached and in-flight targets'
);
