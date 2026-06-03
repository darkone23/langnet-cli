<script lang="ts">
	import ReaderAuthorDiscoveryView from './ReaderAuthorDiscoveryView.svelte';
	import ReaderDiscoveryChooser from './ReaderDiscoveryChooser.svelte';
	import ReaderDiscoveryHeader from './ReaderDiscoveryHeader.svelte';
	import ReaderShelfWorkView from './ReaderShelfWorkView.svelte';
	import ReaderTextSearchView from './ReaderTextSearchView.svelte';
	import type {
		ReaderAuthor,
		ReaderAuthorSection,
		ReaderDiscoveryShelf,
		ReaderFacetValue,
		ReaderRouteState,
		ReaderSearchMode,
		ReaderSearchQueryCandidate,
		ReaderSearchResult,
		ReaderWork
	} from './reader';

	type ReaderIndexView = 'choose' | NonNullable<ReaderRouteState['readerView']>;
	type ReaderSelectableView = Exclude<ReaderIndexView, 'choose'>;
	type DiscoverySort = NonNullable<ReaderRouteState['discoverySort']>;

	type Props = {
		activeDiscoveryTitle: string;
		readerView: ReaderIndexView;
		languageLabel: string;
		catalogReady: boolean;
		textQuery: string;
		textSearchMode: ReaderSearchMode;
		textSearchLoading: boolean;
		textSearchError: string;
		textSearchResults: ReaderSearchResult[];
		textSearchQueryCandidates: ReaderSearchQueryCandidate[];
		textSearchCandidateLabel: (candidate: ReaderSearchQueryCandidate) => string;
		textSearchPrevCursor: string | null;
		textSearchNextCursor: string | null;
		textSearchingStatusLabel: string;
		textSearchingElapsedLabel: string | number;
		textUpdatingStatusLabel: string;
		textUpdatingElapsedLabel: string | number;
		discoveryShelves: ReaderDiscoveryShelf[];
		shelvesLoading: boolean;
		workQuery: string;
		discoveryGroup: string;
		discoveryTag: string;
		discoveryAuthorId: string;
		discoveryAuthorLabel: string;
		discoverySort: DiscoverySort;
		discoveryGroups: ReaderFacetValue[];
		discoveryTags: ReaderFacetValue[];
		discoverySorts: ReaderFacetValue[];
		libraryLoading: boolean;
		libraryError: string;
		hasActiveDiscoveryQuery: boolean;
		works: ReaderWork[];
		selectedWorkId?: string | null;
		worksPrevCursor: string | null;
		worksNextCursor: string | null;
		shelvesStatusLabel: string;
		shelvesElapsedLabel: string | number;
		loadingWorksStatusLabel: string;
		loadingWorksElapsedLabel: string | number;
		updatingWorksStatusLabel: string;
		updatingWorksElapsedLabel: string | number;
		authorAgentKind: string;
		authorHistoricity: string;
		authorAgentKinds: ReaderFacetValue[];
		authorHistoricityStatuses: ReaderFacetValue[];
		authorsLoading: boolean;
		authorsError: string;
		authors: ReaderAuthor[];
		selectedAuthorId?: string | null;
		authorSections: ReaderAuthorSection[];
		activeAuthorSection: string;
		indexSummaryLabel: string;
		authorsPrevCursor: string | null;
		authorsNextCursor: string | null;
		searchingAuthorsStatusLabel: string;
		searchingAuthorsElapsedLabel: string | number;
		updatingAuthorsStatusLabel: string;
		updatingAuthorsElapsedLabel: string | number;
		loadingAuthorWorksStatusLabel: string;
		loadingAuthorWorksElapsedLabel: string | number;
		facetValueLabel: (values: ReaderFacetValue[], id: string) => string;
		workListLabel: (work: ReaderWork) => string;
		workListDiscriminator: (work: ReaderWork) => string;
		workMetaLine: (work: ReaderWork) => string;
		shelfIsActive: (shelf: ReaderDiscoveryShelf) => boolean;
		shelfMetaLabel: (shelf: ReaderDiscoveryShelf) => string;
		romanHintForSection: (sectionKey: string) => string;
		onSelectView: (view: ReaderSelectableView) => void;
		onTextQueryInput: (value: string) => void;
		onTextSearchModeChange: (mode: ReaderSearchMode) => void;
		onSubmitTextSearch: () => void;
		onClearTextSearch: () => void;
		onRetryTextSearch: () => void;
		onOpenTextResult: (result: ReaderSearchResult) => void;
		onOpenTextAuthor: (result: ReaderSearchResult) => void;
		onOpenPreviousText: (cursor: string) => void;
		onOpenNextText: (cursor: string) => void;
		onSelectShelf: (shelf: ReaderDiscoveryShelf) => void;
		onWorkQueryInput: (value: string) => void;
		onDiscoveryGroupChange: (value: string) => void;
		onDiscoveryTagChange: (value: string) => void;
		onDiscoverySortChange: (value: DiscoverySort) => void;
		onApplyDiscoveryFilters: () => void;
		onSubmitDiscoverySearch: () => void;
		onClearDiscoveryFilters: () => void;
		onRetryLibrary: () => void;
		onSummaryElement: (element: HTMLElement | null) => void;
		onOpenWork: (work: ReaderWork) => void | Promise<void>;
		onFilterByAuthor: (work: ReaderWork) => void;
		onClearAuthorFilter: () => void;
		onOpenPreviousWorks: (cursor: string) => void;
		onOpenNextWorks: (cursor: string) => void;
		onAuthorAgentKindChange: (value: string) => void;
		onAuthorHistoricityChange: (value: string) => void;
		onApplyAuthorFilters: () => void;
		onSubmitAuthorSearch: () => void;
		onJumpToAuthorSection: (sectionKey: string) => void;
		onClearAuthorSection: () => void;
		onRetryAuthors: () => void;
		onOpenAuthor: (author: ReaderAuthor) => void;
		onOpenAuthorWork: (work: ReaderWork) => void;
		onOpenPreviousAuthors: (cursor: string) => void;
		onOpenNextAuthors: (cursor: string) => void;
	};

	let {
		activeDiscoveryTitle,
		readerView,
		languageLabel,
		catalogReady,
		textQuery,
		textSearchMode,
		textSearchLoading,
		textSearchError,
		textSearchResults,
		textSearchQueryCandidates,
		textSearchCandidateLabel,
		textSearchPrevCursor,
		textSearchNextCursor,
		textSearchingStatusLabel,
		textSearchingElapsedLabel,
		textUpdatingStatusLabel,
		textUpdatingElapsedLabel,
		discoveryShelves,
		shelvesLoading,
		workQuery,
		discoveryGroup,
		discoveryTag,
		discoveryAuthorId,
		discoveryAuthorLabel,
		discoverySort,
		discoveryGroups,
		discoveryTags,
		discoverySorts,
		libraryLoading,
		libraryError,
		hasActiveDiscoveryQuery,
		works,
		selectedWorkId = null,
		worksPrevCursor,
		worksNextCursor,
		shelvesStatusLabel,
		shelvesElapsedLabel,
		loadingWorksStatusLabel,
		loadingWorksElapsedLabel,
		updatingWorksStatusLabel,
		updatingWorksElapsedLabel,
		authorAgentKind,
		authorHistoricity,
		authorAgentKinds,
		authorHistoricityStatuses,
		authorsLoading,
		authorsError,
		authors,
		selectedAuthorId = null,
		authorSections,
		activeAuthorSection,
		indexSummaryLabel,
		authorsPrevCursor,
		authorsNextCursor,
		searchingAuthorsStatusLabel,
		searchingAuthorsElapsedLabel,
		updatingAuthorsStatusLabel,
		updatingAuthorsElapsedLabel,
		loadingAuthorWorksStatusLabel,
		loadingAuthorWorksElapsedLabel,
		facetValueLabel,
		workListLabel,
		workListDiscriminator,
		workMetaLine,
		shelfIsActive,
		shelfMetaLabel,
		romanHintForSection,
		onSelectView,
		onTextQueryInput,
		onTextSearchModeChange,
		onSubmitTextSearch,
		onClearTextSearch,
		onRetryTextSearch,
		onOpenTextResult,
		onOpenTextAuthor,
		onOpenPreviousText,
		onOpenNextText,
		onSelectShelf,
		onWorkQueryInput,
		onDiscoveryGroupChange,
		onDiscoveryTagChange,
		onDiscoverySortChange,
		onApplyDiscoveryFilters,
		onSubmitDiscoverySearch,
		onClearDiscoveryFilters,
		onRetryLibrary,
		onSummaryElement,
		onOpenWork,
		onFilterByAuthor,
		onClearAuthorFilter,
		onOpenPreviousWorks,
		onOpenNextWorks,
		onAuthorAgentKindChange,
		onAuthorHistoricityChange,
		onApplyAuthorFilters,
		onSubmitAuthorSearch,
		onJumpToAuthorSection,
		onClearAuthorSection,
		onRetryAuthors,
		onOpenAuthor,
		onOpenAuthorWork,
		onOpenPreviousAuthors,
		onOpenNextAuthors
	}: Props = $props();
</script>

<div class="orion-reader-discovery">
	<ReaderDiscoveryHeader title={activeDiscoveryTitle} activeView={readerView} {onSelectView} />

	{#if readerView === 'choose'}
		<ReaderDiscoveryChooser {languageLabel} {onSelectView} />
	{:else if readerView === 'search'}
		<ReaderTextSearchView
			{textQuery}
			{textSearchMode}
			loading={textSearchLoading}
			canSearch={catalogReady}
			canClear={Boolean(textQuery.trim() || textSearchResults.length)}
			error={textSearchError}
			results={textSearchResults}
			queryCandidates={textSearchQueryCandidates}
			candidateLabel={textSearchCandidateLabel}
			previousCursor={textSearchPrevCursor}
			nextCursor={textSearchNextCursor}
			searchingStatusLabel={textSearchingStatusLabel}
			searchingElapsedLabel={textSearchingElapsedLabel}
			updatingStatusLabel={textUpdatingStatusLabel}
			updatingElapsedLabel={textUpdatingElapsedLabel}
			{onTextQueryInput}
			{onTextSearchModeChange}
			onSubmitSearch={onSubmitTextSearch}
			onClearSearch={onClearTextSearch}
			onRetrySearch={onRetryTextSearch}
			onOpenResult={onOpenTextResult}
			onOpenAuthor={onOpenTextAuthor}
			onOpenPrevious={onOpenPreviousText}
			onOpenNext={onOpenNextText}
		/>
	{:else if readerView === 'shelves'}
		<ReaderShelfWorkView
			{discoveryShelves}
			{shelvesLoading}
			{workQuery}
			{discoveryGroup}
			{discoveryTag}
			{discoverySort}
			{discoveryGroups}
			{discoveryTags}
			{discoverySorts}
			{libraryLoading}
			canSearch={catalogReady}
			canClear={Boolean(
				workQuery.trim() ||
				discoveryGroup ||
				discoveryTag ||
				discoveryAuthorId ||
				discoverySort !== 'global-popularity'
			)}
			{libraryError}
			{hasActiveDiscoveryQuery}
			{works}
			{selectedWorkId}
			activeAuthorLabel={discoveryAuthorId ? discoveryAuthorLabel || 'Author' : ''}
			previousCursor={worksPrevCursor}
			nextCursor={worksNextCursor}
			{shelvesStatusLabel}
			{shelvesElapsedLabel}
			{loadingWorksStatusLabel}
			{loadingWorksElapsedLabel}
			{updatingWorksStatusLabel}
			{updatingWorksElapsedLabel}
			{facetValueLabel}
			{workListLabel}
			{workListDiscriminator}
			{workMetaLine}
			{shelfIsActive}
			{shelfMetaLabel}
			{onSelectShelf}
			{onWorkQueryInput}
			{onDiscoveryGroupChange}
			{onDiscoveryTagChange}
			{onDiscoverySortChange}
			onApplyFilters={onApplyDiscoveryFilters}
			onSubmitSearch={onSubmitDiscoverySearch}
			onClearFilters={onClearDiscoveryFilters}
			{onRetryLibrary}
			{onSummaryElement}
			{onOpenWork}
			{onFilterByAuthor}
			{onClearAuthorFilter}
			onOpenPrevious={onOpenPreviousWorks}
			onOpenNext={onOpenNextWorks}
		/>
	{:else}
		<ReaderAuthorDiscoveryView
			{workQuery}
			{authorAgentKind}
			{authorHistoricity}
			{authorAgentKinds}
			{authorHistoricityStatuses}
			{authorsLoading}
			canSearch={catalogReady}
			{authorsError}
			{libraryError}
			{authors}
			{works}
			{selectedAuthorId}
			{selectedWorkId}
			{libraryLoading}
			{authorSections}
			{activeAuthorSection}
			{languageLabel}
			{indexSummaryLabel}
			previousCursor={authorsPrevCursor}
			nextCursor={authorsNextCursor}
			{searchingAuthorsStatusLabel}
			{searchingAuthorsElapsedLabel}
			{updatingAuthorsStatusLabel}
			{updatingAuthorsElapsedLabel}
			{loadingAuthorWorksStatusLabel}
			{loadingAuthorWorksElapsedLabel}
			{romanHintForSection}
			{workListLabel}
			{workListDiscriminator}
			{workMetaLine}
			{onWorkQueryInput}
			{onAuthorAgentKindChange}
			{onAuthorHistoricityChange}
			onApplyFilters={onApplyAuthorFilters}
			onSubmitSearch={onSubmitAuthorSearch}
			onJumpToSection={onJumpToAuthorSection}
			onClearSection={onClearAuthorSection}
			{onRetryAuthors}
			{onRetryLibrary}
			{onOpenAuthor}
			onOpenWork={onOpenAuthorWork}
			onOpenPrevious={onOpenPreviousAuthors}
			onOpenNext={onOpenNextAuthors}
		/>
	{/if}
</div>

<style>
	.orion-reader-discovery {
		display: grid;
		gap: 1rem;
		padding: 1rem;
	}
</style>
