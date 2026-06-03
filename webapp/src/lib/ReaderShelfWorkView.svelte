<script lang="ts">
	import ReaderDeskEmpty from './ReaderDeskEmpty.svelte';
	import ReaderDiscoveryPager from './ReaderDiscoveryPager.svelte';
	import ReaderDiscoveryShelves from './ReaderDiscoveryShelves.svelte';
	import ReaderDiscoverySummary from './ReaderDiscoverySummary.svelte';
	import ReaderErrorPanel from './ReaderErrorPanel.svelte';
	import ReaderLoadingRows from './ReaderLoadingRows.svelte';
	import ReaderLoadingStrip from './ReaderLoadingStrip.svelte';
	import ReaderShelfWorkResults from './ReaderShelfWorkResults.svelte';
	import ReaderShelfWorkSearchForm from './ReaderShelfWorkSearchForm.svelte';
	import type {
		ReaderDiscoveryShelf,
		ReaderFacetValue,
		ReaderRouteState,
		ReaderWork
	} from './reader';

	type DiscoverySort = NonNullable<ReaderRouteState['discoverySort']>;

	type Props = {
		discoveryShelves: ReaderDiscoveryShelf[];
		shelvesLoading: boolean;
		workQuery: string;
		discoveryGroup: string;
		discoveryTag: string;
		discoverySort: DiscoverySort;
		discoveryGroups: ReaderFacetValue[];
		discoveryTags: ReaderFacetValue[];
		discoverySorts: ReaderFacetValue[];
		libraryLoading: boolean;
		canSearch: boolean;
		canClear: boolean;
		libraryError: string;
		hasActiveDiscoveryQuery: boolean;
		works: ReaderWork[];
		selectedWorkId?: string | null;
		activeAuthorLabel?: string;
		previousCursor: string | null;
		nextCursor: string | null;
		shelvesStatusLabel: string;
		shelvesElapsedLabel: string | number;
		loadingWorksStatusLabel: string;
		loadingWorksElapsedLabel: string | number;
		updatingWorksStatusLabel: string;
		updatingWorksElapsedLabel: string | number;
		facetValueLabel: (values: ReaderFacetValue[], id: string) => string;
		workListLabel: (work: ReaderWork) => string;
		workListDiscriminator: (work: ReaderWork) => string;
		workMetaLine: (work: ReaderWork) => string;
		shelfIsActive: (shelf: ReaderDiscoveryShelf) => boolean;
		shelfMetaLabel: (shelf: ReaderDiscoveryShelf) => string;
		onSelectShelf: (shelf: ReaderDiscoveryShelf) => void;
		onWorkQueryInput: (value: string) => void;
		onDiscoveryGroupChange: (value: string) => void;
		onDiscoveryTagChange: (value: string) => void;
		onDiscoverySortChange: (value: DiscoverySort) => void;
		onApplyFilters: () => void;
		onSubmitSearch: () => void;
		onClearFilters: () => void;
		onRetryLibrary: () => void;
		onSummaryElement: (element: HTMLElement | null) => void;
		onOpenWork: (work: ReaderWork) => void | Promise<void>;
		onFilterByAuthor: (work: ReaderWork) => void;
		onClearAuthorFilter: () => void;
		onOpenPrevious: (cursor: string) => void;
		onOpenNext: (cursor: string) => void;
	};

	let {
		discoveryShelves,
		shelvesLoading,
		workQuery,
		discoveryGroup,
		discoveryTag,
		discoverySort,
		discoveryGroups,
		discoveryTags,
		discoverySorts,
		libraryLoading,
		canSearch,
		canClear,
		libraryError,
		hasActiveDiscoveryQuery,
		works,
		selectedWorkId = null,
		activeAuthorLabel = '',
		previousCursor,
		nextCursor,
		shelvesStatusLabel,
		shelvesElapsedLabel,
		loadingWorksStatusLabel,
		loadingWorksElapsedLabel,
		updatingWorksStatusLabel,
		updatingWorksElapsedLabel,
		facetValueLabel,
		workListLabel,
		workListDiscriminator,
		workMetaLine,
		shelfIsActive,
		shelfMetaLabel,
		onSelectShelf,
		onWorkQueryInput,
		onDiscoveryGroupChange,
		onDiscoveryTagChange,
		onDiscoverySortChange,
		onApplyFilters,
		onSubmitSearch,
		onClearFilters,
		onRetryLibrary,
		onSummaryElement,
		onOpenWork,
		onFilterByAuthor,
		onClearAuthorFilter,
		onOpenPrevious,
		onOpenNext
	}: Props = $props();
</script>

{#if discoveryShelves.length}
	<ReaderDiscoveryShelves
		shelves={discoveryShelves}
		{shelfIsActive}
		{shelfMetaLabel}
		{onSelectShelf}
	/>
{:else if shelvesLoading}
	<ReaderLoadingRows
		statusLabel={shelvesStatusLabel}
		elapsedLabel={shelvesElapsedLabel}
		variant="work"
		count={4}
	/>
{/if}

<ReaderShelfWorkSearchForm
	{workQuery}
	{discoveryGroup}
	{discoveryTag}
	{discoverySort}
	{discoveryGroups}
	{discoveryTags}
	{discoverySorts}
	loading={libraryLoading}
	{canSearch}
	{canClear}
	{onWorkQueryInput}
	{onDiscoveryGroupChange}
	{onDiscoveryTagChange}
	{onDiscoverySortChange}
	{onApplyFilters}
	{onSubmitSearch}
	{onClearFilters}
/>

{#if libraryError}
	<ReaderErrorPanel
		title="Works failed to load"
		message={libraryError}
		retryLabel="Load works again"
		onRetry={onRetryLibrary}
	/>
{:else if !hasActiveDiscoveryQuery}
	<!-- Shelf cards are the default discovery surface; raw works appear after a choice. -->
{:else if libraryLoading && !works.length}
	<ReaderLoadingRows
		statusLabel={loadingWorksStatusLabel}
		elapsedLabel={loadingWorksElapsedLabel}
		variant="work"
		count={5}
	/>
{:else if works.length}
	{#if libraryLoading}
		<ReaderLoadingStrip
			statusLabel={updatingWorksStatusLabel}
			elapsedLabel={updatingWorksElapsedLabel}
		/>
	{/if}
	<ReaderDiscoverySummary
		primary={`${works.length} works`}
		secondary={facetValueLabel(discoverySorts, discoverySort)}
		{onSummaryElement}
	/>
	<ReaderShelfWorkResults
		{works}
		{selectedWorkId}
		{activeAuthorLabel}
		{discoveryGroups}
		{discoveryTags}
		{facetValueLabel}
		{workListLabel}
		{workListDiscriminator}
		{workMetaLine}
		{onOpenWork}
		{onFilterByAuthor}
		{onClearAuthorFilter}
	/>
	<ReaderDiscoveryPager
		{previousCursor}
		{nextCursor}
		previousLabel="Previous works"
		nextLabel="Next works"
		loading={libraryLoading}
		{onOpenPrevious}
		{onOpenNext}
	/>
{:else if hasActiveDiscoveryQuery && !libraryLoading}
	<ReaderDeskEmpty icon="telescope" message="No works found for this selection." />
{/if}
