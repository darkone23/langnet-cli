<script lang="ts">
	import ReaderDeskEmpty from './ReaderDeskEmpty.svelte';
	import ReaderDiscoveryPager from './ReaderDiscoveryPager.svelte';
	import ReaderDiscoverySummary from './ReaderDiscoverySummary.svelte';
	import ReaderErrorPanel from './ReaderErrorPanel.svelte';
	import ReaderLoadingRows from './ReaderLoadingRows.svelte';
	import ReaderLoadingStrip from './ReaderLoadingStrip.svelte';
	import ReaderTextSearchForm from './ReaderTextSearchForm.svelte';
	import ReaderTextSearchResults from './ReaderTextSearchResults.svelte';
	import type {
		ReaderSearchMode,
		ReaderSearchQueryCandidate,
		ReaderSearchResult
	} from '$lib/reader';

	type Props = {
		textQuery: string;
		textSearchMode: ReaderSearchMode;
		loading: boolean;
		canSearch: boolean;
		canClear: boolean;
		error: string;
		results: ReaderSearchResult[];
		queryCandidates: ReaderSearchQueryCandidate[];
		candidateLabel: (candidate: ReaderSearchQueryCandidate) => string;
		previousCursor: string | null;
		nextCursor: string | null;
		searchingStatusLabel: string;
		searchingElapsedLabel: string | number;
		updatingStatusLabel: string;
		updatingElapsedLabel: string | number;
		onTextQueryInput: (value: string) => void;
		onTextSearchModeChange: (mode: ReaderSearchMode) => void;
		onSubmitSearch: () => void;
		onClearSearch: () => void;
		onRetrySearch: () => void;
		onOpenResult: (result: ReaderSearchResult) => void;
		onOpenAuthor: (result: ReaderSearchResult) => void;
		onOpenPrevious: (cursor: string) => void;
		onOpenNext: (cursor: string) => void;
	};

	let {
		textQuery,
		textSearchMode,
		loading,
		canSearch,
		canClear,
		error,
		results,
		queryCandidates,
		candidateLabel,
		previousCursor,
		nextCursor,
		searchingStatusLabel,
		searchingElapsedLabel,
		updatingStatusLabel,
		updatingElapsedLabel,
		onTextQueryInput,
		onTextSearchModeChange,
		onSubmitSearch,
		onClearSearch,
		onRetrySearch,
		onOpenResult,
		onOpenAuthor,
		onOpenPrevious,
		onOpenNext
	}: Props = $props();
</script>

<ReaderTextSearchForm
	{textQuery}
	{textSearchMode}
	{loading}
	{canSearch}
	{canClear}
	{onTextQueryInput}
	{onTextSearchModeChange}
	{onSubmitSearch}
	{onClearSearch}
/>

{#if error}
	<ReaderErrorPanel
		title="Text search failed"
		message={error}
		retryLabel="Search again"
		onRetry={onRetrySearch}
	/>
{:else if loading && !results.length}
	<ReaderLoadingRows
		statusLabel={searchingStatusLabel}
		elapsedLabel={searchingElapsedLabel}
		variant="search"
		count={5}
	/>
{:else if results.length}
	{#if loading}
		<ReaderLoadingStrip statusLabel={updatingStatusLabel} elapsedLabel={updatingElapsedLabel} />
	{/if}
	<ReaderDiscoverySummary
		primary={`${results.length} matches on this page`}
		secondary={textSearchMode === 'fuzzy' ? 'Fuzzy text search' : `${textSearchMode} search`}
	/>
	<ReaderTextSearchResults
		{results}
		{queryCandidates}
		{candidateLabel}
		{onOpenResult}
		{onOpenAuthor}
	/>
	<ReaderDiscoveryPager
		{previousCursor}
		{nextCursor}
		previousLabel="Previous matches"
		nextLabel="Next matches"
		{loading}
		{onOpenPrevious}
		{onOpenNext}
	/>
{:else if textQuery.trim()}
	<ReaderDeskEmpty
		icon="file-search"
		message={`No text matches found for "${textQuery.trim()}".`}
	/>
{/if}
