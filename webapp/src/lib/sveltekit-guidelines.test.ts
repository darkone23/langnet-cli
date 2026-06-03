import { existsSync, readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const guidelinesSource = readFileSync(
	new URL('../../docs/SVELTEKIT_GUIDELINES.md', import.meta.url),
	'utf8'
);
const uiDocSource = readFileSync(new URL('../../docs/UI.md', import.meta.url), 'utf8');
const webappReadmeSource = readFileSync(new URL('../../README.md', import.meta.url), 'utf8');
const docsReadmeSource = readFileSync(new URL('../../../docs/README.md', import.meta.url), 'utf8');
const appCssSource = readFileSync(new URL('../app.css', import.meta.url), 'utf8');
const deskEntryCssSource = readFileSync(new URL('./desk-entry.css', import.meta.url), 'utf8');

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
	const componentUrl = new URL(`./${extractedComponent}`, import.meta.url);
	assert.ok(existsSync(componentUrl), `${extractedComponent} should exist as a focused component`);
	const source = readFileSync(componentUrl, 'utf8');
	const lineCount = source.split('\n').length;
	assert.ok(
		lineCount < 500,
		`${extractedComponent} should stay below the preferred 500-line target`
	);
	assert.ok(source.includes('$props'), `${extractedComponent} should use Svelte 5 $props`);
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
	const source = readFileSync(new URL(`./${entryFrameComponent}`, import.meta.url), 'utf8');
	assert.ok(
		source.includes("import '$lib/desk-entry.css';"),
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
		new URL('./DeskLookupResults.svelte', import.meta.url),
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
		new URL('./DeskHeroSearch.svelte', import.meta.url),
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
		new URL('./DeskWordIndexRail.svelte', import.meta.url),
		'utf8'
	);
	assert.ok(
		wordIndexRailSource.includes('DeskWordIndexEarmarks') &&
			wordIndexRailSource.includes('DeskWordIndexSections') &&
			wordIndexRailSource.includes('DeskWordIndexRows'),
		'DeskWordIndexRail should compose saved earmarks, section navigation, and row rendering'
	);
	const sidebarSource = readFileSync(new URL('./DeskSidebar.svelte', import.meta.url), 'utf8');
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
		new URL('./DeskComponentLedger.svelte', import.meta.url),
		'utf8'
	);
	const dictionaryGroupCardSource = readFileSync(
		new URL('./DeskDictionaryGroupCard.svelte', import.meta.url),
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
