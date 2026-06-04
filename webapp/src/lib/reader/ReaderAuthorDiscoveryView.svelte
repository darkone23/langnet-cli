<script lang="ts">
	import ReaderAuthorList from './ReaderAuthorList.svelte';
	import ReaderAuthorSearchForm from './ReaderAuthorSearchForm.svelte';
	import ReaderAuthorToc from './ReaderAuthorToc.svelte';
	import ReaderDeskEmpty from './ReaderDeskEmpty.svelte';
	import ReaderDiscoveryPager from './ReaderDiscoveryPager.svelte';
	import ReaderDiscoverySummary from './ReaderDiscoverySummary.svelte';
	import ReaderErrorPanel from './ReaderErrorPanel.svelte';
	import ReaderLoadingRows from './ReaderLoadingRows.svelte';
	import ReaderLoadingStrip from './ReaderLoadingStrip.svelte';
	import type {
		ReaderAuthor,
		ReaderAuthorSection,
		ReaderFacetValue,
		ReaderWork
	} from '$lib/reader';

	type Props = {
		workQuery: string;
		authorAgentKind: string;
		authorHistoricity: string;
		authorAgentKinds: ReaderFacetValue[];
		authorHistoricityStatuses: ReaderFacetValue[];
		authorsLoading: boolean;
		canSearch: boolean;
		authorsError: string;
		libraryError: string;
		authors: ReaderAuthor[];
		works: ReaderWork[];
		selectedAuthorId?: string | null;
		selectedWorkId?: string | null;
		libraryLoading: boolean;
		authorSections: ReaderAuthorSection[];
		activeAuthorSection: string;
		languageLabel: string;
		indexSummaryLabel: string;
		previousCursor: string | null;
		nextCursor: string | null;
		searchingAuthorsStatusLabel: string;
		searchingAuthorsElapsedLabel: string | number;
		updatingAuthorsStatusLabel: string;
		updatingAuthorsElapsedLabel: string | number;
		loadingAuthorWorksStatusLabel: string;
		loadingAuthorWorksElapsedLabel: string | number;
		romanHintForSection: (sectionKey: string) => string;
		workListLabel: (work: ReaderWork) => string;
		workListDiscriminator: (work: ReaderWork) => string;
		workMetaLine: (work: ReaderWork) => string;
		onWorkQueryInput: (value: string) => void;
		onAuthorAgentKindChange: (value: string) => void;
		onAuthorHistoricityChange: (value: string) => void;
		onApplyFilters: () => void;
		onSubmitSearch: () => void;
		onJumpToSection: (sectionKey: string) => void;
		onClearSection: () => void;
		onRetryAuthors: () => void;
		onRetryLibrary: () => void;
		onOpenAuthor: (author: ReaderAuthor) => void;
		onOpenWork: (work: ReaderWork) => void;
		onOpenPrevious: (cursor: string) => void;
		onOpenNext: (cursor: string) => void;
	};

	let {
		workQuery,
		authorAgentKind,
		authorHistoricity,
		authorAgentKinds,
		authorHistoricityStatuses,
		authorsLoading,
		canSearch,
		authorsError,
		libraryError,
		authors,
		works,
		selectedAuthorId = null,
		selectedWorkId = null,
		libraryLoading,
		authorSections,
		activeAuthorSection,
		languageLabel,
		indexSummaryLabel,
		previousCursor,
		nextCursor,
		searchingAuthorsStatusLabel,
		searchingAuthorsElapsedLabel,
		updatingAuthorsStatusLabel,
		updatingAuthorsElapsedLabel,
		loadingAuthorWorksStatusLabel,
		loadingAuthorWorksElapsedLabel,
		romanHintForSection,
		workListLabel,
		workListDiscriminator,
		workMetaLine,
		onWorkQueryInput,
		onAuthorAgentKindChange,
		onAuthorHistoricityChange,
		onApplyFilters,
		onSubmitSearch,
		onJumpToSection,
		onClearSection,
		onRetryAuthors,
		onRetryLibrary,
		onOpenAuthor,
		onOpenWork,
		onOpenPrevious,
		onOpenNext
	}: Props = $props();
</script>

<ReaderAuthorSearchForm
	{workQuery}
	{authorAgentKind}
	{authorHistoricity}
	{authorAgentKinds}
	{authorHistoricityStatuses}
	loading={authorsLoading}
	{canSearch}
	{onWorkQueryInput}
	{onAuthorAgentKindChange}
	{onAuthorHistoricityChange}
	{onApplyFilters}
	{onSubmitSearch}
/>

<ReaderAuthorToc
	{languageLabel}
	sections={authorSections}
	{activeAuthorSection}
	{romanHintForSection}
	{onJumpToSection}
	{onClearSection}
/>

{#if authorsError || libraryError}
	<ReaderErrorPanel
		title={authorsError ? 'Authors failed to load' : 'Author works failed to load'}
		message={authorsError || libraryError}
		retryLabel={authorsError ? 'Search authors again' : 'Load works again'}
		onRetry={authorsError ? onRetryAuthors : onRetryLibrary}
	/>
{:else if authorsLoading && !authors.length}
	<ReaderLoadingRows
		statusLabel={searchingAuthorsStatusLabel}
		elapsedLabel={searchingAuthorsElapsedLabel}
		variant="author"
		count={5}
	/>
{:else if authors.length}
	{#if authorsLoading}
		<ReaderLoadingStrip
			statusLabel={updatingAuthorsStatusLabel}
			elapsedLabel={updatingAuthorsElapsedLabel}
		/>
	{/if}
	<ReaderDiscoverySummary primary={`${authors.length} authors`} secondary={indexSummaryLabel} />
	<ReaderAuthorList
		{authors}
		{works}
		{selectedAuthorId}
		{selectedWorkId}
		{libraryLoading}
		{workListLabel}
		{workListDiscriminator}
		{workMetaLine}
		{onOpenAuthor}
		{onOpenWork}
	>
		{#snippet loadingAuthorWorks()}
			<ReaderLoadingRows
				statusLabel={loadingAuthorWorksStatusLabel}
				elapsedLabel={loadingAuthorWorksElapsedLabel}
				variant="work"
				count={3}
			/>
		{/snippet}
	</ReaderAuthorList>
	<ReaderDiscoveryPager
		{previousCursor}
		{nextCursor}
		previousLabel="Previous authors"
		nextLabel="Next authors"
		loading={authorsLoading}
		{onOpenPrevious}
		{onOpenNext}
	/>
{:else}
	<ReaderDeskEmpty
		icon="feather"
		message={activeAuthorSection
			? `No authors found in section ${activeAuthorSection}.`
			: 'No authors found for this selection.'}
	/>
{/if}
