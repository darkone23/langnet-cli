import { readFileSync } from 'node:fs';

export const readerPageSource = readFileSync(
	new URL('./ReaderRouteController.svelte', import.meta.url),
	'utf8'
);
export const readerPageViewSource = readFileSync(
	new URL('./ReaderRouteControllerView.svelte', import.meta.url),
	'utf8'
);
export const readerApiSource = readFileSync(new URL('./reader-api.ts', import.meta.url), 'utf8');
export const readerRouteWorkspaceSource = readFileSync(
	new URL('./reader-route-workspace.ts', import.meta.url),
	'utf8'
);
export const readerCssSource = readFileSync(new URL('../../app.css', import.meta.url), 'utf8');
export const apparatusSheetSource = readFileSync(
	new URL('./ReaderApparatusSheet.svelte', import.meta.url),
	'utf8'
);
export const apparatusWordSource = readFileSync(
	new URL('./ReaderApparatusWordPanel.svelte', import.meta.url),
	'utf8'
);
export const apparatusOracleSource = readFileSync(
	new URL('./ReaderApparatusOraclePanel.svelte', import.meta.url),
	'utf8'
);
export const apparatusEvidenceSource = readFileSync(
	new URL('./ReaderApparatusEvidencePanel.svelte', import.meta.url),
	'utf8'
);
export const apparatusStructureSource = readFileSync(
	new URL('./ReaderApparatusStructurePanel.svelte', import.meta.url),
	'utf8'
);
export const apparatusTabsSource = readFileSync(
	new URL('./ReaderApparatusTabs.svelte', import.meta.url),
	'utf8'
);
export const addressLookupSource = readFileSync(
	new URL('./ReaderAddressLookup.svelte', import.meta.url),
	'utf8'
);
export const readerDeskChromeSource = readFileSync(
	new URL('./ReaderDeskChrome.svelte', import.meta.url),
	'utf8'
);
export const readerShellSource = readFileSync(
	new URL('./ReaderShell.svelte', import.meta.url),
	'utf8'
);
export const activeFilterSource = readFileSync(
	new URL('./ReaderActiveFilter.svelte', import.meta.url),
	'utf8'
);
export const workDossierSource = readFileSync(
	new URL('./ReaderWorkDossier.svelte', import.meta.url),
	'utf8'
);
export const currentDivisionSource = readFileSync(
	new URL('./ReaderCurrentDivision.svelte', import.meta.url),
	'utf8'
);
export const discoveryChooserSource = readFileSync(
	new URL('./ReaderDiscoveryChooser.svelte', import.meta.url),
	'utf8'
);
export const discoveryHeaderSource = readFileSync(
	new URL('./ReaderDiscoveryHeader.svelte', import.meta.url),
	'utf8'
);
export const discoveryViewSource = readFileSync(
	new URL('./ReaderDiscoveryView.svelte', import.meta.url),
	'utf8'
);
export const discoverySummarySource = readFileSync(
	new URL('./ReaderDiscoverySummary.svelte', import.meta.url),
	'utf8'
);
export const discoveryPagerSource = readFileSync(
	new URL('./ReaderDiscoveryPager.svelte', import.meta.url),
	'utf8'
);
export const discoveryShelvesSource = readFileSync(
	new URL('./ReaderDiscoveryShelves.svelte', import.meta.url),
	'utf8'
);
export const deskHeaderSource = readFileSync(
	new URL('./ReaderDeskHeader.svelte', import.meta.url),
	'utf8'
);
export const deskEmptySource = readFileSync(
	new URL('./ReaderDeskEmpty.svelte', import.meta.url),
	'utf8'
);
export const pageNavSource = readFileSync(
	new URL('./ReaderPageNav.svelte', import.meta.url),
	'utf8'
);
export const readerLeafSource = readFileSync(
	new URL('./ReaderLeaf.svelte', import.meta.url),
	'utf8'
);
export const readerPassageViewSource = readFileSync(
	new URL('./ReaderPassageView.svelte', import.meta.url),
	'utf8'
);
export const readerSourceDetailsSource = readFileSync(
	new URL('./ReaderSourceDetails.svelte', import.meta.url),
	'utf8'
);
export const readerSelectedWordPanelSource = readFileSync(
	new URL('./ReaderSelectedWordPanel.svelte', import.meta.url),
	'utf8'
);
export const readerSelectedWorkDeskSource = readFileSync(
	new URL('./ReaderSelectedWorkDesk.svelte', import.meta.url),
	'utf8'
);
export const readerLoadingTimersSource = readFileSync(
	new URL('./loading-timers.ts', import.meta.url),
	'utf8'
);
export const readerIndexStatsSource = readFileSync(
	new URL('./index-stats.ts', import.meta.url),
	'utf8'
);
export const readerPageAuthorsSource = readFileSync(
	new URL('./page-authors.ts', import.meta.url),
	'utf8'
);
export const readerPageRoutingSource = readFileSync(
	new URL('./page-routing.ts', import.meta.url),
	'utf8'
);
export const readerPageNavigationSource = readFileSync(
	new URL('./page-navigation.ts', import.meta.url),
	'utf8'
);
export const readerContextSidebarSource = readFileSync(
	new URL('./ReaderContextSidebar.svelte', import.meta.url),
	'utf8'
);
export const readerErrorPanelSource = readFileSync(
	new URL('./ReaderErrorPanel.svelte', import.meta.url),
	'utf8'
);
export const readerLoadingRowsSource = readFileSync(
	new URL('./ReaderLoadingRows.svelte', import.meta.url),
	'utf8'
);
export const readerLoadingStripSource = readFileSync(
	new URL('./ReaderLoadingStrip.svelte', import.meta.url),
	'utf8'
);
export const shelfWorkSearchFormSource = readFileSync(
	new URL('./ReaderShelfWorkSearchForm.svelte', import.meta.url),
	'utf8'
);
export const shelfWorkResultsSource = readFileSync(
	new URL('./ReaderShelfWorkResults.svelte', import.meta.url),
	'utf8'
);
export const shelfWorkViewSource = readFileSync(
	new URL('./ReaderShelfWorkView.svelte', import.meta.url),
	'utf8'
);
export const textSearchFormSource = readFileSync(
	new URL('./ReaderTextSearchForm.svelte', import.meta.url),
	'utf8'
);
export const textSearchResultsSource = readFileSync(
	new URL('./ReaderTextSearchResults.svelte', import.meta.url),
	'utf8'
);
export const textSearchViewSource = readFileSync(
	new URL('./ReaderTextSearchView.svelte', import.meta.url),
	'utf8'
);
export const authorSearchFormSource = readFileSync(
	new URL('./ReaderAuthorSearchForm.svelte', import.meta.url),
	'utf8'
);
export const authorListSource = readFileSync(
	new URL('./ReaderAuthorList.svelte', import.meta.url),
	'utf8'
);
export const authorDiscoveryViewSource = readFileSync(
	new URL('./ReaderAuthorDiscoveryView.svelte', import.meta.url),
	'utf8'
);
export const authorTocSource = readFileSync(
	new URL('./ReaderAuthorToc.svelte', import.meta.url),
	'utf8'
);
export const orionObjectCardSource = readFileSync(
	new URL('../OrionObjectCard.svelte', import.meta.url),
	'utf8'
);
export const orionProvenanceChipsSource = readFileSync(
	new URL('../OrionProvenanceChips.svelte', import.meta.url),
	'utf8'
);
export const readerCanonTableSource = readFileSync(
	new URL('./ReaderCanonTable.svelte', import.meta.url),
	'utf8'
);
export const readerContentsListSource = readFileSync(
	new URL('./ReaderContentsList.svelte', import.meta.url),
	'utf8'
);
export const libraryWorkPortalSource = readFileSync(
	new URL('../../routes/library/work/[work]/+page.svelte', import.meta.url),
	'utf8'
);
export const libraryAuthorPortalSource = readFileSync(
	new URL('../../routes/library/author/[author]/+page.svelte', import.meta.url),
	'utf8'
);
