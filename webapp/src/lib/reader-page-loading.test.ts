import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const readerPageSource = readFileSync(
	new URL('../routes/reader/+page.svelte', import.meta.url),
	'utf8'
);
const readerCssSource = readFileSync(new URL('../app.css', import.meta.url), 'utf8');
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
const apparatusTabsSource = readFileSync(
	new URL('./ReaderApparatusTabs.svelte', import.meta.url),
	'utf8'
);
const addressLookupSource = readFileSync(
	new URL('./ReaderAddressLookup.svelte', import.meta.url),
	'utf8'
);
const readerDeskChromeSource = readFileSync(
	new URL('./ReaderDeskChrome.svelte', import.meta.url),
	'utf8'
);
const readerShellSource = readFileSync(new URL('./ReaderShell.svelte', import.meta.url), 'utf8');
const activeFilterSource = readFileSync(
	new URL('./ReaderActiveFilter.svelte', import.meta.url),
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
const discoveryChooserSource = readFileSync(
	new URL('./ReaderDiscoveryChooser.svelte', import.meta.url),
	'utf8'
);
const discoveryHeaderSource = readFileSync(
	new URL('./ReaderDiscoveryHeader.svelte', import.meta.url),
	'utf8'
);
const discoveryViewSource = readFileSync(
	new URL('./ReaderDiscoveryView.svelte', import.meta.url),
	'utf8'
);
const discoverySummarySource = readFileSync(
	new URL('./ReaderDiscoverySummary.svelte', import.meta.url),
	'utf8'
);
const discoveryPagerSource = readFileSync(
	new URL('./ReaderDiscoveryPager.svelte', import.meta.url),
	'utf8'
);
const discoveryShelvesSource = readFileSync(
	new URL('./ReaderDiscoveryShelves.svelte', import.meta.url),
	'utf8'
);
const deskHeaderSource = readFileSync(
	new URL('./ReaderDeskHeader.svelte', import.meta.url),
	'utf8'
);
const deskEmptySource = readFileSync(new URL('./ReaderDeskEmpty.svelte', import.meta.url), 'utf8');
const pageNavSource = readFileSync(new URL('./ReaderPageNav.svelte', import.meta.url), 'utf8');
const readerLeafSource = readFileSync(new URL('./ReaderLeaf.svelte', import.meta.url), 'utf8');
const readerPassageViewSource = readFileSync(
	new URL('./ReaderPassageView.svelte', import.meta.url),
	'utf8'
);
const readerSourceDetailsSource = readFileSync(
	new URL('./ReaderSourceDetails.svelte', import.meta.url),
	'utf8'
);
const readerSelectedWordPanelSource = readFileSync(
	new URL('./ReaderSelectedWordPanel.svelte', import.meta.url),
	'utf8'
);
const readerSelectedWorkDeskSource = readFileSync(
	new URL('./ReaderSelectedWorkDesk.svelte', import.meta.url),
	'utf8'
);
const readerLoadingTimersSource = readFileSync(
	new URL('./reader-loading-timers.ts', import.meta.url),
	'utf8'
);
const readerIndexStatsSource = readFileSync(
	new URL('./reader-index-stats.ts', import.meta.url),
	'utf8'
);
const readerPageAuthorsSource = readFileSync(
	new URL('./reader-page-authors.ts', import.meta.url),
	'utf8'
);
const readerPageRoutingSource = readFileSync(
	new URL('./reader-page-routing.ts', import.meta.url),
	'utf8'
);
const readerPageNavigationSource = readFileSync(
	new URL('./reader-page-navigation.ts', import.meta.url),
	'utf8'
);
const readerContextSidebarSource = readFileSync(
	new URL('./ReaderContextSidebar.svelte', import.meta.url),
	'utf8'
);
const readerErrorPanelSource = readFileSync(
	new URL('./ReaderErrorPanel.svelte', import.meta.url),
	'utf8'
);
const readerLoadingRowsSource = readFileSync(
	new URL('./ReaderLoadingRows.svelte', import.meta.url),
	'utf8'
);
const readerLoadingStripSource = readFileSync(
	new URL('./ReaderLoadingStrip.svelte', import.meta.url),
	'utf8'
);
const shelfWorkSearchFormSource = readFileSync(
	new URL('./ReaderShelfWorkSearchForm.svelte', import.meta.url),
	'utf8'
);
const shelfWorkResultsSource = readFileSync(
	new URL('./ReaderShelfWorkResults.svelte', import.meta.url),
	'utf8'
);
const shelfWorkViewSource = readFileSync(
	new URL('./ReaderShelfWorkView.svelte', import.meta.url),
	'utf8'
);
const textSearchFormSource = readFileSync(
	new URL('./ReaderTextSearchForm.svelte', import.meta.url),
	'utf8'
);
const textSearchResultsSource = readFileSync(
	new URL('./ReaderTextSearchResults.svelte', import.meta.url),
	'utf8'
);
const textSearchViewSource = readFileSync(
	new URL('./ReaderTextSearchView.svelte', import.meta.url),
	'utf8'
);
const authorSearchFormSource = readFileSync(
	new URL('./ReaderAuthorSearchForm.svelte', import.meta.url),
	'utf8'
);
const authorListSource = readFileSync(
	new URL('./ReaderAuthorList.svelte', import.meta.url),
	'utf8'
);
const authorDiscoveryViewSource = readFileSync(
	new URL('./ReaderAuthorDiscoveryView.svelte', import.meta.url),
	'utf8'
);
const authorTocSource = readFileSync(new URL('./ReaderAuthorToc.svelte', import.meta.url), 'utf8');
const orionObjectCardSource = readFileSync(
	new URL('./OrionObjectCard.svelte', import.meta.url),
	'utf8'
);
const orionProvenanceChipsSource = readFileSync(
	new URL('./OrionProvenanceChips.svelte', import.meta.url),
	'utf8'
);
const readerCanonTableSource = readFileSync(
	new URL('./ReaderCanonTable.svelte', import.meta.url),
	'utf8'
);
const readerContentsListSource = readFileSync(
	new URL('./ReaderContentsList.svelte', import.meta.url),
	'utf8'
);

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
		readerPageSource.includes(primitiveSourceToken),
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
		readerPageSource.includes(workDeskSourceToken),
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

for (const selectedWordPanelToken of [
	'orion-reader-selected-word',
	'selectedWordRomanization',
	'selectedWordBriefingOutput',
	'selectedWordBriefingBadge',
	'selectedWordBriefingCanGenerate',
	'onGenerateBriefing',
	'encounterBriefingCompactText',
	'<style>'
]) {
	assert.ok(
		readerSelectedWordPanelSource.includes(selectedWordPanelToken),
		`Reader Selected Word Panel component should expose token: ${selectedWordPanelToken}`
	);
}

assert.ok(
	!readerCssSource.includes('\n\t.orion-reader-selected-word'),
	'component-local selected-word selector should move out of app.css'
);

for (const shelfWorkResultsComponentToken of [
	'ReaderActiveFilter',
	'orion-reader-work-list',
	'orion-reader-work-row',
	'orion-reader-work-meta',
	'selectedWorkId',
	'activeAuthorLabel',
	'onOpenWork',
	'onFilterByAuthor',
	'onClearAuthorFilter',
	'<style>'
]) {
	assert.ok(
		shelfWorkResultsSource.includes(shelfWorkResultsComponentToken),
		`Reader Shelf Work Results component should expose token: ${shelfWorkResultsComponentToken}`
	);
}

for (const shelfWorkViewComponentToken of [
	'ReaderDiscoveryShelves',
	'ReaderShelfWorkSearchForm',
	'ReaderShelfWorkResults',
	'ReaderDiscoveryPager',
	'ReaderDeskEmpty',
	'hasActiveDiscoveryQuery',
	'onRetryLibrary',
	'onSummaryElement',
	'onOpenPrevious',
	'<script lang="ts">'
]) {
	assert.ok(
		shelfWorkViewSource.includes(shelfWorkViewComponentToken),
		`Reader Shelf Work View component should expose token: ${shelfWorkViewComponentToken}`
	);
}

for (const textSearchViewComponentToken of [
	'ReaderTextSearchForm',
	'ReaderTextSearchResults',
	'ReaderDiscoveryPager',
	'ReaderLoadingRows',
	'ReaderDeskEmpty',
	'queryCandidates',
	'onRetrySearch',
	'onOpenPrevious',
	'<script lang="ts">'
]) {
	assert.ok(
		textSearchViewSource.includes(textSearchViewComponentToken),
		`Reader Text Search View component should expose token: ${textSearchViewComponentToken}`
	);
}

for (const textSearchResultsComponentToken of [
	'orion-reader-work-list',
	'orion-reader-work-row',
	'orion-reader-work-meta',
	'queryCandidates',
	'onOpenResult',
	'onOpenAuthor',
	'candidateLabel',
	'<style>'
]) {
	assert.ok(
		textSearchResultsSource.includes(textSearchResultsComponentToken),
		`Reader Text Search Results component should expose token: ${textSearchResultsComponentToken}`
	);
}

for (const activeFilterComponentToken of [
	'orion-reader-active-filter',
	'Clear author',
	'label',
	'onClear',
	'<style>'
]) {
	assert.ok(
		activeFilterSource.includes(activeFilterComponentToken),
		`Reader Active Filter component should expose token: ${activeFilterComponentToken}`
	);
}

for (const activeFilterCssToken of ['.orion-reader-active-filter']) {
	assert.ok(
		activeFilterSource.includes(activeFilterCssToken),
		`Reader Active Filter component should define scoped style: ${activeFilterCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${activeFilterCssToken}`),
		`component-local Reader Active Filter selector should move out of app.css: ${activeFilterCssToken}`
	);
}

for (const authorListWorkCssToken of [
	'.orion-reader-work-list',
	'.orion-reader-work-row',
	'.orion-reader-work-row strong',
	'.orion-reader-work-row span'
]) {
	assert.ok(
		authorListSource.includes(authorListWorkCssToken),
		`Reader Author List should own expanded work-list style: ${authorListWorkCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${authorListWorkCssToken}`),
		`component-local work-list selector should move out of app.css: ${authorListWorkCssToken}`
	);
}

for (const discoveryChooserComponentToken of [
	'orion-reader-shelf-grid',
	'orion-reader-shelf-card',
	'Shelves',
	'Authors',
	'Text search',
	'onSelectView',
	'<style>'
]) {
	assert.ok(
		discoveryChooserSource.includes(discoveryChooserComponentToken),
		`Reader Discovery Chooser component should expose token: ${discoveryChooserComponentToken}`
	);
}

for (const discoveryChooserCssToken of ['.orion-reader-shelf-grid', '.orion-reader-shelf-card']) {
	assert.ok(
		discoveryChooserSource.includes(discoveryChooserCssToken),
		`Reader Discovery Chooser component should define scoped style: ${discoveryChooserCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${discoveryChooserCssToken}`),
		`component-local Reader Discovery Chooser selector should move out of app.css: ${discoveryChooserCssToken}`
	);
}

for (const authorListComponentToken of [
	'orion-reader-author-list',
	'orion-reader-author-group',
	'orion-reader-author-heading',
	'orion-reader-author-button',
	'selectedAuthorId',
	'onOpenAuthor',
	'onOpenWork',
	'<style>'
]) {
	assert.ok(
		authorListSource.includes(authorListComponentToken),
		`Reader Author List component should expose token: ${authorListComponentToken}`
	);
}

for (const authorListCssToken of [
	'.orion-reader-author-list',
	'.orion-reader-author-group',
	'.orion-reader-author-heading',
	'.orion-reader-author-button'
]) {
	assert.ok(
		authorListSource.includes(authorListCssToken),
		`Reader Author List component should define scoped style: ${authorListCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${authorListCssToken}`),
		`component-local Reader Author List selector should move out of app.css: ${authorListCssToken}`
	);
}

for (const authorTocComponentToken of [
	'orion-reader-author-toc',
	'orion-reader-author-toc-grid',
	'orion-reader-author-section-native',
	'orion-reader-author-section-roman',
	'onJumpToSection',
	'onClearSection',
	'romanHintForSection',
	'<style>'
]) {
	assert.ok(
		authorTocSource.includes(authorTocComponentToken),
		`Reader Author TOC component should expose token: ${authorTocComponentToken}`
	);
}

for (const authorTocCssToken of ['.orion-reader-author-toc', '.orion-reader-author-toc-grid']) {
	assert.ok(
		authorTocSource.includes(authorTocCssToken),
		`Reader Author TOC component should define scoped style: ${authorTocCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${authorTocCssToken}`),
		`component-local Reader Author TOC selector should move out of app.css: ${authorTocCssToken}`
	);
}

for (const shelfWorkSearchFormComponentToken of [
	'orion-reader-discovery-search',
	'Search titles or authors',
	'discoveryGroup',
	'discoveryTag',
	'discoverySort',
	'onApplyFilters',
	'<style>'
]) {
	assert.ok(
		shelfWorkSearchFormSource.includes(shelfWorkSearchFormComponentToken),
		`Reader Shelf Work Search Form component should expose token: ${shelfWorkSearchFormComponentToken}`
	);
}

for (const authorSearchFormComponentToken of [
	'orion-reader-discovery-search',
	'Search authors',
	'authorAgentKind',
	'authorHistoricity',
	'onApplyFilters',
	'onSubmitSearch',
	'<style>'
]) {
	assert.ok(
		authorSearchFormSource.includes(authorSearchFormComponentToken),
		`Reader Author Search Form component should expose token: ${authorSearchFormComponentToken}`
	);
}

for (const textSearchFormComponentToken of [
	'orion-reader-discovery-search',
	'Search inside texts',
	'textSearchMode',
	'onTextQueryInput',
	'onTextSearchModeChange',
	'onSubmitSearch',
	'onClearSearch',
	'<style>'
]) {
	assert.ok(
		textSearchFormSource.includes(textSearchFormComponentToken),
		`Reader Text Search Form component should expose token: ${textSearchFormComponentToken}`
	);
}

for (const textSearchFormCssToken of ['.orion-reader-discovery-search']) {
	assert.ok(
		textSearchFormSource.includes(textSearchFormCssToken),
		`Reader Text Search Form component should define scoped style: ${textSearchFormCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${textSearchFormCssToken}`),
		`component-local Reader Text Search Form selector should move out of app.css: ${textSearchFormCssToken}`
	);
}

for (const discoveryHeaderComponentToken of [
	'orion-reader-discovery-topline',
	'Library discovery',
	'Shelves',
	'Top authors',
	'Text search',
	'onSelectView',
	'<style>'
]) {
	assert.ok(
		discoveryHeaderSource.includes(discoveryHeaderComponentToken),
		`Reader Discovery Header component should expose token: ${discoveryHeaderComponentToken}`
	);
}

for (const discoveryHeaderCssToken of ['.orion-reader-discovery-topline']) {
	assert.ok(
		discoveryHeaderSource.includes(discoveryHeaderCssToken),
		`Reader Discovery Header component should define scoped style: ${discoveryHeaderCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${discoveryHeaderCssToken}`),
		`component-local Reader Discovery Header selector should move out of app.css: ${discoveryHeaderCssToken}`
	);
}

for (const discoverySummaryComponentToken of [
	'orion-reader-discovery-summary',
	'primary',
	'secondary',
	'onSummaryElement',
	'<style>'
]) {
	assert.ok(
		discoverySummarySource.includes(discoverySummaryComponentToken),
		`Reader Discovery Summary component should expose token: ${discoverySummaryComponentToken}`
	);
}

for (const discoverySummaryCssToken of ['.orion-reader-discovery-summary']) {
	assert.ok(
		discoverySummarySource.includes(discoverySummaryCssToken),
		`Reader Discovery Summary component should define scoped style: ${discoverySummaryCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${discoverySummaryCssToken}`),
		`component-local Reader Discovery Summary selector should move out of app.css: ${discoverySummaryCssToken}`
	);
}

for (const discoveryPagerComponentToken of [
	'orion-reader-discovery-pager',
	'previousLabel',
	'nextLabel',
	'onOpenPrevious',
	'onOpenNext',
	'<style>'
]) {
	assert.ok(
		discoveryPagerSource.includes(discoveryPagerComponentToken),
		`Reader Discovery Pager component should expose token: ${discoveryPagerComponentToken}`
	);
}

for (const discoveryPagerCssToken of ['.orion-reader-discovery-pager']) {
	assert.ok(
		discoveryPagerSource.includes(discoveryPagerCssToken),
		`Reader Discovery Pager component should define scoped style: ${discoveryPagerCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${discoveryPagerCssToken}`),
		`component-local Reader Discovery Pager selector should move out of app.css: ${discoveryPagerCssToken}`
	);
}

for (const discoveryShelvesComponentToken of [
	'orion-reader-shelf-grid',
	'orion-reader-shelf-card',
	'shelfIsActive',
	'shelfMetaLabel',
	'onSelectShelf',
	'<style>'
]) {
	assert.ok(
		discoveryShelvesSource.includes(discoveryShelvesComponentToken),
		`Reader Discovery Shelves component should expose token: ${discoveryShelvesComponentToken}`
	);
}

for (const discoveryShelvesCssToken of ['.orion-reader-shelf-grid', '.orion-reader-shelf-card']) {
	assert.ok(
		discoveryShelvesSource.includes(discoveryShelvesCssToken),
		`Reader Discovery Shelves component should define scoped style: ${discoveryShelvesCssToken}`
	);
}

for (const addressLookupComponentToken of [
	'orion-reader-address-lookup',
	'Open reference',
	'onAddressInput',
	'onOpenAddress',
	'onShowLookup',
	'<style>'
]) {
	assert.ok(
		addressLookupSource.includes(addressLookupComponentToken),
		`Reader Address Lookup component should expose token: ${addressLookupComponentToken}`
	);
}

for (const addressLookupCssToken of ['.orion-reader-address-lookup']) {
	assert.ok(
		addressLookupSource.includes(addressLookupCssToken),
		`Reader Address Lookup component should define scoped style: ${addressLookupCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${addressLookupCssToken}`),
		`component-local Reader Address Lookup selector should move out of app.css: ${addressLookupCssToken}`
	);
}

for (const deskHeaderComponentToken of [
	'orion-reader-desk-head',
	'orion-reader-desk-actions',
	'orion-reader-desk-citation',
	'orion-reader-work-heading',
	'Transliteration',
	'onToggleTransliteration',
	'onShowLibrary',
	'<style>'
]) {
	assert.ok(
		deskHeaderSource.includes(deskHeaderComponentToken),
		`Reader Desk Header component should expose token: ${deskHeaderComponentToken}`
	);
}

for (const deskHeaderCssToken of [
	'.orion-reader-desk-head',
	'.orion-reader-desk-actions',
	'.orion-reader-desk-citation',
	'.orion-reader-desk-author',
	'.orion-reader-work-heading'
]) {
	assert.ok(
		deskHeaderSource.includes(deskHeaderCssToken),
		`Reader Desk Header component should define scoped style: ${deskHeaderCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${deskHeaderCssToken}`),
		`component-local Reader Desk Header selector should move out of app.css: ${deskHeaderCssToken}`
	);
}

for (const apparatusShellToken of [
	'orion-reader-apparatus-sheet open',
	'<style>',
	'ReaderApparatusStructurePanel',
	'ReaderApparatusWordPanel',
	'ReaderApparatusOraclePanel',
	'ReaderApparatusEvidencePanel',
	'.orion-reader-apparatus-sheet-head'
]) {
	assert.ok(
		apparatusSheetSource.includes(apparatusShellToken),
		`apparatus shell should expose panel routing token: ${apparatusShellToken}`
	);
}

for (const apparatusPanelToken of [
	'orion-reader-apparatus-word-panel',
	'<style>',
	'.orion-reader-apparatus-summary',
	'selectedWordBriefingBadge',
	'selectedWordHref'
]) {
	assert.ok(
		apparatusWordSource.includes(apparatusPanelToken),
		`word apparatus panel should expose token: ${apparatusPanelToken}`
	);
}

for (const apparatusPanelToken of [
	'orion-reader-apparatus-oracle-panel',
	'<style>',
	'selectedWordBriefingCanGenerate',
	'onGenerateBriefing'
]) {
	assert.ok(
		apparatusOracleSource.includes(apparatusPanelToken),
		`oracle apparatus panel should expose token: ${apparatusPanelToken}`
	);
}

for (const apparatusPanelToken of [
	'orion-reader-apparatus-evidence-panel',
	'<style>',
	'.orion-reader-apparatus-evidence-list',
	'currentDivisionTrail.length',
	'selectedSegment.citation_path'
]) {
	assert.ok(
		apparatusEvidenceSource.includes(apparatusPanelToken),
		`evidence apparatus panel should expose token: ${apparatusPanelToken}`
	);
}

assert.ok(
	apparatusStructureSource.includes('ReaderCanonTable'),
	'structure apparatus panel should use the shared Canon Table component'
);

for (const readerLayoutCssContract of [
	[readerShellSource, '.orion-reader-shell'],
	[readerShellSource, '.orion-reader-sidebar-frame'],
	[readerSelectedWorkDeskSource, '.orion-reader-work-desk'],
	[readerSelectedWorkDeskSource, '.orion-reader-work-desk :global(.orion-object-card)'],
	[discoveryViewSource, '.orion-reader-discovery'],
	[deskHeaderSource, '.orion-reader-desk-kicker'],
	[readerContentsListSource, '.orion-reader-page-segments summary']
]) {
	const [source, token] = readerLayoutCssContract;
	assert.ok(
		source.includes(token),
		`reader layout selector should live with owning component: ${token}`
	);
}

for (const readerGlobalLayoutToken of [
	'\n\t.orion-reader-shell',
	'\n\t.orion-reader-sidebar',
	'\n\t.orion-reader-work-desk',
	'\n\t.orion-reader-desk-passage',
	'\n\t.orion-reader-desk-kicker',
	'\n\t.orion-reader-page-segments',
	'\n\t.orion-reader-discovery'
]) {
	assert.ok(
		!readerCssSource.includes(readerGlobalLayoutToken),
		`reader layout selector should move out of app.css: ${readerGlobalLayoutToken.trim()}`
	);
}

for (const apparatusCssToken of [
	'.orion-reader-apparatus-word-panel',
	'.orion-reader-apparatus-oracle-panel',
	'.orion-reader-apparatus-evidence-panel',
	'.orion-reader-apparatus-summary',
	'.orion-reader-apparatus-evidence-list'
]) {
	const apparatusSources = [
		apparatusWordSource,
		apparatusOracleSource,
		apparatusEvidenceSource
	].join('\n');
	assert.ok(
		apparatusSources.includes(apparatusCssToken),
		`apparatus panel component should define scoped style: ${apparatusCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${apparatusCssToken}`),
		`component-local apparatus selector should move out of app.css: ${apparatusCssToken}`
	);
}

for (const structureSourceToken of [
	'let structure = $state<ReaderStructureNode[]>([])',
	"mode: 'structure'",
	'await loadStructure(readerWorkRef(selectedWork))',
	'ReaderContextSidebar',
	"readerLoadingElapsed('structure')"
]) {
	assert.ok(
		readerPageSource.includes(structureSourceToken),
		`reader page should expose structure UI token: ${structureSourceToken}`
	);
}

for (const apparatusSheetCssToken of [
	'.orion-reader-apparatus-sheet',
	'.orion-reader-apparatus-sheet-head'
]) {
	assert.ok(
		apparatusSheetSource.includes(apparatusSheetCssToken),
		`Apparatus Sheet component should define scoped shell style: ${apparatusSheetCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${apparatusSheetCssToken}`),
		`component-local apparatus sheet selector should move out of app.css: ${apparatusSheetCssToken}`
	);
}

for (const dossierSourceToken of [
	'let workDossier = $state<ReaderWorkDossierResponse | null>(null)',
	'loadWorkDossier',
	"mode: 'about'",
	'ReaderSelectedWorkDesk',
	'readerLoadingStatus(uiCopy.workDossier.loading,'
]) {
	assert.ok(
		readerPageSource.includes(dossierSourceToken),
		`reader page should expose Work Dossier token: ${dossierSourceToken}`
	);
}

for (const dossierComponentToken of [
	'orion-reader-work-dossier',
	'<style>',
	'uiCopy.workDossier.title',
	'dossierStatItems',
	'orion-reader-work-dossier-stats',
	'dossier.division_bios.slice(0, 3)',
	'onRetry',
	'onOpenDivision'
]) {
	assert.ok(
		workDossierSource.includes(dossierComponentToken),
		`Work Dossier component should expose token: ${dossierComponentToken}`
	);
}

for (const dossierCssToken of ['.orion-reader-work-dossier', '.orion-reader-work-dossier-note']) {
	assert.ok(
		workDossierSource.includes(dossierCssToken),
		`Work Dossier component should define its own scoped style: ${dossierCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${dossierCssToken} {`),
		`component-local Work Dossier selector should move out of app.css: ${dossierCssToken}`
	);
}

for (const currentDivisionSourceToken of [
	'currentDivisionTrail',
	'currentDivisionNode',
	'ReaderPassageView'
]) {
	assert.ok(
		readerPageSource.includes(currentDivisionSourceToken),
		`reader page should expose current division marginalium token: ${currentDivisionSourceToken}`
	);
}

for (const currentDivisionComponentToken of [
	'orion-reader-current-division',
	'orion-reader-current-division-trail',
	'<style>',
	'OrionProvenanceChips',
	'uiCopy.readerStructure.current',
	'onOpenDivision'
]) {
	assert.ok(
		currentDivisionSource.includes(currentDivisionComponentToken),
		`Current Division component should expose token: ${currentDivisionComponentToken}`
	);
}

for (const currentDivisionCssToken of [
	'.orion-reader-current-division',
	'.orion-reader-current-division-trail'
]) {
	assert.ok(
		currentDivisionSource.includes(currentDivisionCssToken),
		`Current Division component should define scoped style: ${currentDivisionCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${currentDivisionCssToken}`),
		`component-local current division selector should move out of app.css: ${currentDivisionCssToken}`
	);
}

for (const pageNavSourceToken of [
	'ReaderPassageView',
	'pagePrevCursor',
	'pageNextCursor',
	'pageRangeLabel'
]) {
	assert.ok(
		readerPageSource.includes(pageNavSourceToken),
		`reader page should compose page navigation token: ${pageNavSourceToken}`
	);
}

for (const pageNavComponentToken of [
	'orion-reader-page-nav',
	'orion-reader-page-nav-bottom',
	'orion-reader-page-work-label',
	'<style>',
	'onOpenPage'
]) {
	assert.ok(
		pageNavSource.includes(pageNavComponentToken),
		`Reader Page Nav component should expose token: ${pageNavComponentToken}`
	);
}

for (const pageNavCssToken of ['.orion-reader-page-nav', '.orion-reader-page-work-label']) {
	assert.ok(
		pageNavSource.includes(pageNavCssToken),
		`Reader Page Nav component should define scoped style: ${pageNavCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${pageNavCssToken}`),
		`component-local page nav selector should move out of app.css: ${pageNavCssToken}`
	);
}

for (const readerLeafSourceToken of [
	'ReaderPassageView',
	'pageSegments',
	'segmentParts',
	'selectToken',
	'showSelectedWorkSegment'
]) {
	assert.ok(
		readerPageSource.includes(readerLeafSourceToken),
		`reader page should compose Reader Leaf token: ${readerLeafSourceToken}`
	);
}

for (const passageViewComponentToken of [
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
]) {
	assert.ok(
		readerPassageViewSource.includes(passageViewComponentToken),
		`Reader Passage View component should expose token: ${passageViewComponentToken}`
	);
}

for (const readerLeafComponentToken of [
	'orion-reader-leaf',
	'orion-reader-leaf-line',
	'orion-reader-token',
	'orion-reader-token-translit',
	'<style>',
	'onSelectToken',
	'onOpenSegment'
]) {
	assert.ok(
		readerLeafSource.includes(readerLeafComponentToken),
		`Reader Leaf component should expose token: ${readerLeafComponentToken}`
	);
}

for (const readerLeafCssToken of [
	'.orion-reader-leaf',
	'.orion-reader-leaf-line',
	'.orion-reader-token'
]) {
	assert.ok(
		readerLeafSource.includes(readerLeafCssToken),
		`Reader Leaf component should define scoped style: ${readerLeafCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${readerLeafCssToken}`),
		`component-local Reader Leaf selector should move out of app.css: ${readerLeafCssToken}`
	);
}

for (const readerSourceDetailsToken of [
	'ReaderSourceDetails',
	'selectedSegment.source_text',
	'selectedSegment.transliteration'
]) {
	assert.ok(
		readerPassageViewSource.includes(readerSourceDetailsToken),
		`Reader Passage View should compose Reader Source Details token: ${readerSourceDetailsToken}`
	);
}

for (const readerSourceDetailsComponentToken of [
	'orion-reader-desk-source',
	'Source / transliteration',
	'sourceText',
	'transliteration',
	'<style>'
]) {
	assert.ok(
		readerSourceDetailsSource.includes(readerSourceDetailsComponentToken),
		`Reader Source Details component should expose token: ${readerSourceDetailsComponentToken}`
	);
}

for (const readerSourceDetailsCssToken of ['.orion-reader-desk-source']) {
	assert.ok(
		readerSourceDetailsSource.includes(readerSourceDetailsCssToken),
		`Reader Source Details component should define scoped style: ${readerSourceDetailsCssToken}`
	);
	assert.ok(
		!readerCssSource.includes(`\n\t${readerSourceDetailsCssToken}`),
		`component-local Reader Source Details selector should move out of app.css: ${readerSourceDetailsCssToken}`
	);
}

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
