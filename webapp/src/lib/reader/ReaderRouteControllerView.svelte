<script lang="ts">
	import { uiCopy } from '$lib/ui-copy';
	import ReaderApparatusSheet from '$lib/reader/ReaderApparatusSheet.svelte';
	import ReaderApparatusTabs from '$lib/reader/ReaderApparatusTabs.svelte';
	import ReaderContextSidebar from '$lib/reader/ReaderContextSidebar.svelte';
	import ReaderDeskChrome from '$lib/reader/ReaderDeskChrome.svelte';
	import ReaderDeskHeader from '$lib/reader/ReaderDeskHeader.svelte';
	import ReaderDiscoveryView from '$lib/reader/ReaderDiscoveryView.svelte';
	import ReaderPassageView from '$lib/reader/ReaderPassageView.svelte';
	import ReaderSelectedWorkDesk from '$lib/reader/ReaderSelectedWorkDesk.svelte';
	import ReaderShell from '$lib/reader/ReaderShell.svelte';
	import {
		readerAuthorSectionRomanHint,
		readerShelfMetaLabel,
		readerTextSearchCandidateLabel,
		readerVisibleTextSearchCandidates,
		readerWorkMetaLine
	} from '$lib/reader/page-formatting';
	import { readerFacetValueLabel } from '$lib/reader/page-authors';
	import { readerShelfIsActive } from '$lib/reader/page-navigation';

	const props = $props();

	const renderTextSearchCandidateLabel = readerTextSearchCandidateLabel;
	const renderTextSearchQueryCandidates = readerVisibleTextSearchCandidates;
</script>

<svelte:window onkeydown={props.onOpenWindowKeydown} />

<svelte:head>
	<title>Reader Desk | {uiCopy.app.name}</title>
	<meta
		name="description"
		content="A didactic reader for Sanskrit, Greek, and Latin: search, read, and follow words through the sources."
	/>
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen" data-theme={props.theme}>
	<ReaderDeskChrome
	{...props}
		onThemeSelect={props.onThemeSelect}
		onLanguageSelect={props.onLanguageSelect}
		onAddressInput={props.onAddressInput}
		onOpenAddress={props.onOpenAddress}
		onCloseLookup={props.onCloseLookup}
		onShowLookup={props.onShowLookup}
	/>

	<ReaderShell>
		{#if props.selectedWork}
			<ReaderSelectedWorkDesk
				workTitle={props.selectedWorkLabels.title}
				workSubtitle={props.selectedWorkLabels.contributorLine || props.selectedWorkLabels.discriminator}
				classificationConfidence={props.selectedWork.classification_confidence}
				dossier={props.topSection}
				dossierLoading={props.dossierLoading}
				dossierLoadingLabel={props.dossierLoadingLabel}
				dossierError={props.dossierError}
				currentDivisionNode={props.currentDivisionNode}
				onOpenDivision={props.onOpenWorkDivision}
				onRetry={props.onRetrySelectedWork}
			/>
		{/if}

		<article class="orion-reader-desk-passage orion-manuscript-panel">
			<ReaderDeskHeader
				languageLabel={props.headerLanguageLabel}
				workAuthorLabel={props.selectedWork ? props.selectedWorkLabels.author : null}
				workTitle={props.selectedWork ? props.selectedWorkLabels.title : null}
				workDiscriminator={props.selectedWorkLabels.discriminator}
				workContributorLine={props.selectedWorkLabels.contributorLine}
				canOpenAuthor={Boolean(props.canOpenWorkAuthor)}
				segmentWorkId={props.selectedSegment?.work_id}
				hasSelectedSegment={Boolean(props.selectedSegment)}
				showTransliteration={props.showTransliteration}
				pageRangeLabel={props.pageRangeLabel}
				onOpenAuthor={props.onOpenWorkAuthor}
				onToggleTransliteration={props.onToggleTransliteration}
				onShowLibrary={props.onShowLibrary}
			/>

			{#if props.segmentError || props.segmentLoading || props.selectedSegment}
				<ReaderPassageView
					segmentError={props.segmentError}
					segmentLoading={props.segmentLoading}
					selectedSegment={props.selectedSegment}
					pagePrevCursor={props.pagePrevCursor}
					pageNextCursor={props.pageNextCursor}
					contentsLoading={props.contentsLoading}
					pageRangeLabel={props.pageRangeLabel}
					currentDivisionTrail={props.currentDivisionTrail}
					currentDivisionNode={props.currentDivisionNode}
					pageSegments={props.pageSegments}
					language={props.language}
					selectedWord={props.selectedWord}
					showTransliteration={props.showTransliteration}
					selectedWorkLabel={props.selectedWork ? props.selectedWorkLabels.title : 'reader page'}
					selectedWorkDetail={props.selectedWorkLabels.discriminator}
					openingStatusLabel={props.openingStatusLabel}
					openingElapsedLabel={props.openingElapsedLabel}
					updatingStatusLabel={props.updatingStatusLabel}
					updatingElapsedLabel={props.updatingElapsedLabel}
					segmentParts={props.segmentParts}
					onRetrySegment={props.onRetrySegment}
					onOpenPage={props.onOpenPage}
					onOpenDivision={props.onOpenDivisionFromPassage}
					onOpenSegment={props.onOpenSegment}
					onSelectToken={props.onSelectToken}
				/>
			{:else}
				<ReaderDiscoveryView
					activeDiscoveryTitle={props.activeDiscoveryTitle}
					readerView={props.readerView}
					languageLabel={props.headerLanguageLabel}
					catalogReady={props.catalogReady}
					textQuery={props.textQuery}
					textSearchMode={props.textSearchMode}
					textSearchLoading={props.textSearchLoading}
					textSearchError={props.textSearchError}
					textSearchResults={props.textSearchResults}
					textSearchQueryCandidates={renderTextSearchQueryCandidates(props.textSearchQueryCandidates)}
					textSearchCandidateLabel={renderTextSearchCandidateLabel}
					textSearchPrevCursor={props.textSearchPrevCursor}
					textSearchNextCursor={props.textSearchNextCursor}
					textSearchingStatusLabel={props.textSearchingStatusLabel}
					textSearchingElapsedLabel={props.textSearchingElapsedLabel}
					textUpdatingStatusLabel={props.textUpdatingStatusLabel}
					textUpdatingElapsedLabel={props.textUpdatingElapsedLabel}
					discoveryShelves={props.discoveryShelves}
					shelvesLoading={props.shelvesLoading}
					workQuery={props.workQuery}
					discoveryGroup={props.discoveryGroup}
					discoveryTag={props.discoveryTag}
					discoveryAuthorId={props.discoveryAuthorId}
					discoveryAuthorLabel={props.discoveryAuthorLabel}
					discoverySort={props.discoverySort}
					discoveryGroups={props.discoveryGroups}
					discoveryTags={props.discoveryTags}
					discoverySorts={props.discoverySorts}
					libraryLoading={props.libraryLoading}
					libraryError={props.libraryError}
					hasActiveDiscoveryQuery={props.hasActiveDiscoveryQuery}
					works={props.works}
					selectedWorkId={props.selectedWorkId}
					worksPrevCursor={props.worksPrevCursor}
					worksNextCursor={props.worksNextCursor}
					shelvesStatusLabel={props.shelvesStatusLabel}
					shelvesElapsedLabel={props.shelvesElapsedLabel}
					loadingWorksStatusLabel={props.loadingWorksStatusLabel}
					loadingWorksElapsedLabel={props.loadingWorksElapsedLabel}
					updatingWorksStatusLabel={props.updatingWorksStatusLabel}
					updatingWorksElapsedLabel={props.updatingWorksElapsedLabel}
					authorAgentKind={props.authorAgentKind}
					authorHistoricity={props.authorHistoricity}
					authorAgentKinds={props.authorAgentKinds}
							authorHistoricityStatuses={props.authorHistoricityStatuses}
							authorsLoading={props.authorsLoading}
					authorsError={props.authorsError}
					authors={props.authors}
					selectedAuthorId={props.selectedAuthorId}
					authorSections={props.authorSections}
					activeAuthorSection={props.activeAuthorSection}
					indexSummaryLabel={props.indexSummaryLabel}
					authorsPrevCursor={props.authorsPrevCursor}
					authorsNextCursor={props.authorsNextCursor}
					searchingAuthorsStatusLabel={props.searchingAuthorsStatusLabel}
					searchingAuthorsElapsedLabel={props.searchingAuthorsElapsedLabel}
					updatingAuthorsStatusLabel={props.updatingAuthorsStatusLabel}
					updatingAuthorsElapsedLabel={props.updatingAuthorsElapsedLabel}
					loadingAuthorWorksStatusLabel={props.loadingAuthorWorksStatusLabel}
					loadingAuthorWorksElapsedLabel={props.loadingAuthorWorksElapsedLabel}
					facetValueLabel={readerFacetValueLabel}
					workListLabel={props.discoveryWorkListLabel}
					workListDiscriminator={props.discoveryWorkListDiscriminator}
					workMetaLine={readerWorkMetaLine}
					shelfIsActive={(shelf) =>
						readerShelfIsActive(shelf, {
							discoveryGroup: props.discoveryGroup,
							discoveryTag: props.discoveryTag
						})
					}
					shelfMetaLabel={readerShelfMetaLabel}
						onSelectView={props.onSelectView}
					onTextQueryInput={props.onTextQueryInput}
					onTextSearchModeChange={props.onTextSearchModeChange}
					onSubmitTextSearch={props.onSubmitTextSearch}
					onClearTextSearch={props.onClearTextSearch}
					onRetryTextSearch={props.onRetryTextSearch}
					onOpenTextResult={props.onOpenTextResult}
					onOpenTextAuthor={props.onOpenTextAuthor}
					onOpenPreviousText={props.onOpenPreviousText}
					onOpenNextText={props.onOpenNextText}
					onSelectShelf={props.onSelectShelf}
					onWorkQueryInput={props.onWorkQueryInput}
					onDiscoveryGroupChange={props.onDiscoveryGroupChange}
					onDiscoveryTagChange={props.onDiscoveryTagChange}
					onDiscoverySortChange={props.onDiscoverySortChange}
					onApplyDiscoveryFilters={props.onApplyDiscoveryFilters}
					onSubmitDiscoverySearch={props.onSubmitDiscoverySearch}
					onClearDiscoveryFilters={props.onClearDiscoveryFilters}
					onRetryLibrary={props.onRetryLibrary}
					onSummaryElement={props.onSummaryElement}
					onOpenWork={props.onOpenWork}
					onFilterByAuthor={props.onFilterByAuthor}
					onClearAuthorFilter={props.onClearDiscoveryAuthor}
					onOpenPreviousWorks={props.onOpenPreviousWorks}
					onOpenNextWorks={props.onOpenNextWorks}
					onAuthorAgentKindChange={props.onAuthorAgentKindChange}
					onAuthorHistoricityChange={props.onAuthorHistoricityChange}
					onApplyAuthorFilters={props.onApplyAuthorFilters}
					onSubmitAuthorSearch={props.onSubmitAuthorSearch}
					onJumpToAuthorSection={props.onJumpToAuthorSection}
						onClearAuthorSection={props.onClearAuthorSection}
					onRetryAuthors={props.onRetryAuthors}
					onOpenAuthor={props.onOpenAuthor}
					onOpenAuthorWork={props.onOpenAuthorWork}
					onOpenPreviousAuthors={props.onOpenPreviousAuthors}
						onOpenNextAuthors={props.onOpenNextAuthors}
						romanHintForSection={(sectionKey) =>
							readerAuthorSectionRomanHint(props.language, sectionKey)
						}
					/>
			{/if}
		</article>

		{#snippet sidebar()}
			<ReaderContextSidebar
				structure={props.sidebarStructure}
				structureLoading={props.sidebarStructureLoading}
				structureError={props.sidebarStructureError}
				structureStatusLabel={props.sidebarStructureStatusLabel}
				structureElapsedLabel={props.sidebarStructureElapsedLabel}
				hasSelectedWork={Boolean(props.selectedWork)}
				contents={props.sidebarContents}
				contentsLoading={props.sidebarContentsLoading}
				contentsError={props.sidebarContentsError}
				contentsStatusLabel={props.sidebarContentsStatusLabel}
				contentsElapsedLabel={props.sidebarContentsElapsedLabel}
				selectedWord={props.selectedWord}
				selectedWordRomanization={props.selectedWordRomanization}
				selectedWordHref={props.selectedWordHref}
				selectedWordBriefingOutput={props.selectedWordBriefingOutput}
				selectedWordBriefingBadge={props.selectedWordBriefingBadge}
				selectedWordBriefingCanGenerate={props.selectedWordBriefingCanGenerate}
				selectedWordBriefingLoading={props.selectedWordBriefingLoading}
				selectedWordBriefingGenerating={props.selectedWordBriefingGenerating}
				selectedWordBriefingError={props.selectedWordBriefingError}
				segmentIsActive={props.segmentIsActive}
				onRetryStructure={props.onRetryStructure}
				onRetryContents={props.onRetryContents}
				onOpenDivision={props.onOpenDivision}
				onOpenSegment={props.onOpenSegment}
				onGenerateBriefing={props.onGenerateBriefing}
			/>
		{/snippet}
	</ReaderShell>

	<ReaderApparatusTabs
		showing={Boolean(props.selectedWork || props.selectedSegment || props.selectedWord)}
		onOpenPanel={props.onOpenPanel}
	/>

	<ReaderApparatusSheet
		activePanel={props.activeApparatusPanel}
		structure={props.sidebarStructure}
		selectedWord={props.selectedWord}
		selectedWordRomanization={props.selectedWordRomanization}
		selectedWordHref={props.selectedWordHref}
		selectedWordBriefingOutput={props.selectedWordBriefingOutput}
		selectedWordBriefingBadge={props.selectedWordBriefingBadge}
		selectedWordBriefingCanGenerate={props.selectedWordBriefingCanGenerate}
		selectedWordBriefingLoading={props.selectedWordBriefingLoading}
		selectedWordBriefingGenerating={props.selectedWordBriefingGenerating}
		selectedWordBriefingError={props.selectedWordBriefingError}
		currentDivisionTrail={props.currentDivisionTrail}
		currentDivisionNode={props.currentDivisionNode}
		selectedSegment={props.selectedSegment}
		selectedWorkTitle={props.selectedWork ? props.selectedWorkLabels.title : ''}
		selectedWorkAddress={props.selectedWork?.canonical_address || ''}
		onClose={props.onCloseApparatus}
		onOpenDivision={props.onOpenDivisionFromSheet}
		onGenerateBriefing={props.onGenerateBriefingFromSheet}
	/>

</main>
