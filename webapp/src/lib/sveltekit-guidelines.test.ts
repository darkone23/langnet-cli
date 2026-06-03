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
	'DeskColophonPanel.svelte',
	'DeskHeroSearch.svelte',
	'DeskMotdFolio.svelte',
	'DeskMotdSkeletonList.svelte',
	'DeskPulseWidget.svelte',
	'DeskSearchReading.svelte',
	'DeskSourceControls.svelte',
	'DeskToolChip.svelte',
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
	['\n\t.orion-tool-chip', 'DeskToolChip.svelte'],
	['\n\t.orion-tool-icon', 'DeskToolChip.svelte'],
	['\n\t.orion-tool-check', 'DeskToolChip.svelte'],
	['\n\t.orion-pulse-widget', 'DeskPulseWidget.svelte'],
	['\n\t.orion-search-reading', 'DeskSearchReading.svelte'],
	['\n\t.orion-motd-folio', 'DeskMotdFolio.svelte'],
	['\n\t.orion-motd-link', 'DeskMotdFolio.svelte'],
	['\n\t.orion-motd-control-skeleton', 'DeskMotdFolio.svelte'],
	['\n\t.orion-motd-skeleton-card', 'DeskMotdFolio.svelte'],
	['@keyframes orion-pulse-ring', 'DeskPulseWidget.svelte'],
	['@keyframes orion-pulse-core', 'DeskPulseWidget.svelte'],
	['@keyframes orion-pulse-dot', 'DeskPulseWidget.svelte']
] as const) {
	assert.ok(
		!appCssSource.includes(globalChipSelector),
		`desk source selector ${globalChipSelector.trim()} should live in ${componentName}`
	);
}

{
	const deskRouteSource = readFileSync(new URL('../routes/+page.svelte', import.meta.url), 'utf8');

	assert.ok(
		deskRouteSource.includes('DeskSourceControls'),
		'desk route should compose source controls through DeskSourceControls'
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
		deskRouteSource.includes('DeskColophonPanel'),
		'desk route should compose encounter colophon through DeskColophonPanel'
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
