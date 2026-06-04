import { strict as assert } from 'node:assert';
import * as fixtures from './page-loading-fixtures';
const {
	readerPageSource,
	readerPageViewSource,
	readerApiSource,
	readerRouteWorkspaceSource,
	readerCssSource,
	apparatusSheetSource,
	apparatusWordSource,
	apparatusOracleSource,
	apparatusEvidenceSource,
	apparatusStructureSource,
	apparatusTabsSource,
	addressLookupSource,
	readerDeskChromeSource,
	readerShellSource,
	activeFilterSource,
	workDossierSource,
	currentDivisionSource,
	discoveryChooserSource,
	discoveryHeaderSource,
	discoveryViewSource,
	discoverySummarySource,
	discoveryPagerSource,
	discoveryShelvesSource,
	deskHeaderSource,
	deskEmptySource,
	pageNavSource,
	readerLeafSource,
	readerPassageViewSource,
	readerSourceDetailsSource,
	readerSelectedWordPanelSource,
	readerSelectedWorkDeskSource,
	readerLoadingTimersSource,
	readerIndexStatsSource,
	readerPageAuthorsSource,
	readerPageRoutingSource,
	readerPageNavigationSource,
	readerContextSidebarSource,
	readerErrorPanelSource,
	readerLoadingRowsSource,
	readerLoadingStripSource,
	shelfWorkSearchFormSource,
	shelfWorkResultsSource,
	shelfWorkViewSource,
	textSearchFormSource,
	textSearchResultsSource,
	textSearchViewSource,
	authorSearchFormSource,
	authorListSource,
	authorDiscoveryViewSource,
	authorTocSource,
	orionObjectCardSource,
	orionProvenanceChipsSource,
	readerCanonTableSource,
	readerContentsListSource
} = fixtures;

for (const primitiveSourceToken of [
	'ReaderSelectedWorkDesk',
	'ReaderContextSidebar',
	'ReaderShell',
	'ReaderLoadingStrip',
	'createReaderLoadingTimers',
	'buildReaderIndexStatsTargets',
	'readerSelectedWorkTitleLabel',
	'buildCurrentReaderRouteState',
	'readerCurrentReadingWorkRef',
	'readerLoadingElapsedSeconds'
]) {
	assert.ok(
		`${readerPageSource}\n${readerPageViewSource}\n${readerPassageViewSource}\n${readerRouteWorkspaceSource}`.includes(
			primitiveSourceToken
		),
		`reader page should expose Orion primitive source token: ${primitiveSourceToken}`
	);
}

for (const pageNavigationHelperToken of [
	'readerShelfIsActive',
	'readerSegmentIsActive',
	'readerCurrentReadingWorkRef',
	'readerSearchResultWorkRef'
]) {
	assert.ok(
		readerPageNavigationSource.includes(pageNavigationHelperToken),
		`Reader page navigation helper should expose token: ${pageNavigationHelperToken}`
	);
}

for (const indexStatsHelperToken of [
	'readerIndexStatsFromSections',
	'findReaderIndexStatsInList',
	'upsertReaderIndexStatsList',
	'defaultReaderCatalogForLanguage',
	'buildReaderIndexStatsTargets'
]) {
	assert.ok(
		readerIndexStatsSource.includes(indexStatsHelperToken),
		`Reader index stats helper should expose token: ${indexStatsHelperToken}`
	);
}

for (const pageRoutingHelperToken of [
	'buildCurrentReaderRouteState',
	'defaultReaderAddressForLanguage',
	'formatReaderAddress',
	'readerIsCanonicalRef',
	'readerWorkHasContributorMetadata'
]) {
	assert.ok(
		readerPageRoutingSource.includes(pageRoutingHelperToken),
		`Reader page routing helper should expose token: ${pageRoutingHelperToken}`
	);
}

for (const pageAuthorHelperToken of [
	'readerSyntheticAuthorFromWork',
	'readerSyntheticAuthorFromRoute',
	'upsertReaderAuthor',
	'readerFacetValueLabel',
	'readerSelectedWorkContributorLine'
]) {
	assert.ok(
		readerPageAuthorsSource.includes(pageAuthorHelperToken),
		`Reader page author helper should expose token: ${pageAuthorHelperToken}`
	);
}

for (const loadingTimerToken of [
	'ReaderLoadingKey',
	'createReaderLoadingTimers',
	'onElapsed(kind, 0)',
	'setInterval',
	'Math.floor',
	'stopAll'
]) {
	assert.ok(
		readerLoadingTimersSource.includes(loadingTimerToken),
		`Reader loading timer helper should expose token: ${loadingTimerToken}`
	);
}

for (const sharedPrimitiveToken of [
	'orion-object-card',
	'OrionProvenanceChips',
	'orion-reader-provenance-row',
	'orion-reader-provenance-chip',
	'orion-reader-canon-table',
	'orion-reader-division-card'
]) {
	const primitiveSources = [
		orionObjectCardSource,
		orionProvenanceChipsSource,
		readerCanonTableSource
	].join('\n');
	assert.ok(
		primitiveSources.includes(sharedPrimitiveToken),
		`shared Orion primitive components should expose token: ${sharedPrimitiveToken}`
	);
}

for (const componentStyleContract of [
	[orionObjectCardSource, '<style>', '.orion-object-card'],
	[orionProvenanceChipsSource, '<style>', '.orion-reader-provenance-row'],
	[readerCanonTableSource, '<style>', '.orion-reader-canon-table'],
	[readerCanonTableSource, '.orion-reader-division-card', '--division-depth']
]) {
	const [source, firstToken, secondToken] = componentStyleContract;
	assert.ok(
		source.includes(firstToken) && source.includes(secondToken),
		`shared Orion primitive styles should live with the component: ${secondToken}`
	);
}

for (const globalPrimitiveSelector of [
	'\n\t.orion-object-card {',
	'\n\t.orion-reader-provenance-row {',
	'\n\t.orion-reader-canon-table {',
	'\n\t.orion-reader-division-card {'
]) {
	assert.ok(
		!readerCssSource.includes(globalPrimitiveSelector),
		`component-local primitive selector should move out of app.css: ${globalPrimitiveSelector.trim()}`
	);
}

for (const workDeskSourceToken of [
	'ReaderDeskChrome',
	'ReaderContextSidebar',
	'ReaderDiscoveryView',
	'ReaderSelectedWorkDesk',
	'ReaderErrorPanel',
	'ReaderLoadingRows',
	'ReaderLoadingStrip',
	'ReaderDeskHeader',
	'ReaderPassageView',
	'ReaderApparatusTabs',
	'activeApparatusPanel = panel',
	'ReaderApparatusSheet',
	'selectedWordBriefingBadge',
	'selectedWordHref',
	'currentDivisionTrail'
]) {
	assert.ok(
		`${readerPageSource}\n${readerPageViewSource}\n${readerPassageViewSource}\n${readerContextSidebarSource}`.includes(
			workDeskSourceToken
		),
		`reader page should expose Work Desk apparatus token: ${workDeskSourceToken}`
	);
}

for (const selectedWorkDeskComponentToken of [
	'orion-reader-work-desk',
	'OrionObjectCard',
	'ReaderWorkDossier',
	'classificationConfidence',
	'workTitle',
	'workSubtitle',
	'onOpenDivision',
	'onRetry',
	'<script lang="ts">'
]) {
	assert.ok(
		readerSelectedWorkDeskSource.includes(selectedWorkDeskComponentToken),
		`Reader Selected Work Desk component should expose token: ${selectedWorkDeskComponentToken}`
	);
}

for (const readerDeskChromeComponentToken of [
	'ReaderAddressLookup',
	'orion-home-seal',
	'Unified reader',
	'Reader Desk',
	'languageModes',
	'catalogError',
	'onThemeSelect',
	'onLanguageSelect',
	'onOpenAddress',
	'<script lang="ts">'
]) {
	assert.ok(
		readerDeskChromeSource.includes(readerDeskChromeComponentToken),
		`Reader Desk Chrome component should expose token: ${readerDeskChromeComponentToken}`
	);
}

for (const readerShellComponentToken of [
	'orion-reader-shell',
	'orion-reader-sidebar-frame',
	'orion-reader-main',
	'Snippet',
	'@render sidebar',
	'<style>'
]) {
	assert.ok(
		readerShellSource.includes(readerShellComponentToken),
		`Reader Shell component should expose token: ${readerShellComponentToken}`
	);
}

for (const discoveryViewComponentToken of [
	'orion-reader-discovery',
	'ReaderDiscoveryHeader',
	'ReaderDiscoveryChooser',
	'ReaderTextSearchView',
	'ReaderShelfWorkView',
	'ReaderAuthorDiscoveryView',
	'activeDiscoveryTitle',
	'readerView ===',
	'onSelectView',
	'onOpenWork',
	'onOpenAuthor',
	'<script lang="ts">'
]) {
	assert.ok(
		discoveryViewSource.includes(discoveryViewComponentToken),
		`Reader Discovery View component should expose token: ${discoveryViewComponentToken}`
	);
}

for (const contextSidebarComponentToken of [
	'orion-reader-sidebar',
	'ReaderCanonTable',
	'ReaderContentsList',
	'ReaderSelectedWordPanel',
	'ReaderLoadingRows',
	'ReaderLoadingStrip',
	'ReaderErrorPanel',
	'Structure failed to load',
	'Contents failed to load',
	'No book selected',
	'onOpenDivision',
	'onGenerateBriefing',
	'<script lang="ts">'
]) {
	assert.ok(
		readerContextSidebarSource.includes(contextSidebarComponentToken),
		`Reader Context Sidebar component should expose token: ${contextSidebarComponentToken}`
	);
}

for (const authorDiscoveryViewComponentToken of [
	'ReaderAuthorSearchForm',
	'ReaderAuthorToc',
	'ReaderAuthorList',
	'ReaderDiscoveryPager',
	'ReaderDeskEmpty',
	'loadingAuthorWorks',
	'activeAuthorSection',
	'onRetryAuthors',
	'onOpenPrevious',
	'<script lang="ts">'
]) {
	assert.ok(
		authorDiscoveryViewSource.includes(authorDiscoveryViewComponentToken),
		`Reader Author Discovery View component should expose token: ${authorDiscoveryViewComponentToken}`
	);
}

for (const deskEmptyComponentToken of [
	'orion-reader-desk-empty',
	'FileSearch',
	'Telescope',
	'Feather',
	'message',
	'<style>'
]) {
	assert.ok(
		deskEmptySource.includes(deskEmptyComponentToken),
		`Reader Desk Empty component should expose token: ${deskEmptyComponentToken}`
	);
}

assert.ok(
	!readerCssSource.includes('\n\t.orion-reader-desk-empty'),
	'component-local desk-empty selector should move out of app.css'
);

for (const apparatusTabsComponentToken of [
	'orion-reader-apparatus-tabs',
	'ScrollText',
	'BookOpen',
	'Sparkles',
	'Database',
	'onOpenPanel',
	'uiCopy.apparatus.structure',
	'<style>'
]) {
	assert.ok(
		apparatusTabsSource.includes(apparatusTabsComponentToken),
		`Reader Apparatus Tabs component should expose token: ${apparatusTabsComponentToken}`
	);
}

assert.ok(
	!readerCssSource.includes('\n\t.orion-reader-apparatus-tabs'),
	'component-local apparatus-tabs selector should move out of app.css'
);

for (const asyncComponentToken of [
	'orion-reader-loading-region',
	'orion-reader-loading-status',
	'orion-reader-skeleton-row',
	'statusLabel',
	'elapsedLabel',
	'<style>'
]) {
	assert.ok(
		readerLoadingRowsSource.includes(asyncComponentToken),
		`Reader Loading Rows component should expose token: ${asyncComponentToken}`
	);
}

for (const asyncComponentToken of [
	'orion-reader-loading-strip',
	'statusLabel',
	'elapsedLabel',
	'<style>'
]) {
	assert.ok(
		readerLoadingStripSource.includes(asyncComponentToken),
		`Reader Loading Strip component should expose token: ${asyncComponentToken}`
	);
}

for (const errorPanelComponentToken of [
	'orion-reader-state-panel',
	'orion-reader-state-error',
	'onRetry',
	'retryLabel',
	'<style>'
]) {
	assert.ok(
		readerErrorPanelSource.includes(errorPanelComponentToken),
		`Reader Error Panel component should expose token: ${errorPanelComponentToken}`
	);
}

for (const routeSnippetToken of [
	'{#snippet readerSkeletonRows',
	'{#snippet readerLoadingStrip',
	'{#snippet readerErrorPanel'
]) {
	assert.ok(
		!readerPageSource.includes(routeSnippetToken),
		`reader route should not keep async UI snippet: ${routeSnippetToken}`
	);
}

for (const asyncGlobalCssToken of [
	'.orion-reader-loading-region',
	'.orion-reader-loading-status',
	'.orion-reader-loading-strip',
	'.orion-reader-state-panel',
	'.orion-reader-state-error',
	'.orion-reader-skeleton-list',
	'.orion-reader-skeleton-row',
	'.orion-reader-skeleton-block'
]) {
	assert.ok(
		!readerCssSource.includes(`\n\t${asyncGlobalCssToken}`),
		`component-local async selector should move out of app.css: ${asyncGlobalCssToken}`
	);
}

for (const contentsListComponentToken of [
	'orion-reader-contents-list',
	'Page segments',
	'segmentIsActive',
	'onOpenSegment',
	'readerSegmentDisplayText',
	'<style>'
]) {
	assert.ok(
		readerContentsListSource.includes(contentsListComponentToken),
		`Reader Contents List component should expose token: ${contentsListComponentToken}`
	);
}

assert.ok(
	!readerCssSource.includes('\n\t.orion-reader-contents-list'),
	'component-local contents-list selector should move out of app.css'
);
