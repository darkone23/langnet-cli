import { strict as assert } from 'node:assert';
import * as fixtures from './page-loading-fixtures';
const {
	readerPageSource,
	readerApiSource,
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
