<script lang="ts">
	import ReaderCurrentDivision from './ReaderCurrentDivision.svelte';
	import ReaderErrorPanel from './ReaderErrorPanel.svelte';
	import ReaderLeaf from './ReaderLeaf.svelte';
	import ReaderLoadingRows from './ReaderLoadingRows.svelte';
	import ReaderLoadingStrip from './ReaderLoadingStrip.svelte';
	import ReaderPageNav from './ReaderPageNav.svelte';
	import ReaderSourceDetails from './ReaderSourceDetails.svelte';
	import type { ReaderSegment, ReaderStructureNode, ReaderTokenPart } from '$lib/reader';
	import type { LanguageMode } from '../search-data';

	type Props = {
		segmentError: string;
		segmentLoading: boolean;
		selectedSegment: ReaderSegment | null;
		pagePrevCursor: string | null;
		pageNextCursor: string | null;
		contentsLoading: boolean;
		pageRangeLabel: string;
		currentDivisionTrail: ReaderStructureNode[];
		currentDivisionNode: ReaderStructureNode | null;
		pageSegments: ReaderSegment[];
		language: LanguageMode;
		selectedWord: string;
		showTransliteration: boolean;
		selectedWorkLabel: string;
		selectedWorkDetail: string;
		openingStatusLabel: string;
		openingElapsedLabel: string | number;
		updatingStatusLabel: string;
		updatingElapsedLabel: string | number;
		segmentParts: (segment: ReaderSegment) => ReaderTokenPart[];
		onRetrySegment: () => void;
		onOpenPage: (cursor: string | null) => void;
		onOpenDivision: (workId: string, citation: string) => void;
		onOpenSegment: (segment: ReaderSegment) => void;
		onSelectToken: (token: string) => void;
	};

	let {
		segmentError,
		segmentLoading,
		selectedSegment,
		pagePrevCursor,
		pageNextCursor,
		contentsLoading,
		pageRangeLabel,
		currentDivisionTrail,
		currentDivisionNode,
		pageSegments,
		language,
		selectedWord,
		showTransliteration,
		selectedWorkLabel,
		selectedWorkDetail,
		openingStatusLabel,
		openingElapsedLabel,
		updatingStatusLabel,
		updatingElapsedLabel,
		segmentParts,
		onRetrySegment,
		onOpenPage,
		onOpenDivision,
		onOpenSegment,
		onSelectToken
	}: Props = $props();
</script>

{#if segmentError}
	<div class="m-5">
		<ReaderErrorPanel
			title="Passage failed to load"
			message={segmentError}
			retryLabel="Try opening again"
			onRetry={onRetrySegment}
		/>
	</div>
{:else if segmentLoading && !selectedSegment}
	<ReaderLoadingRows
		statusLabel={openingStatusLabel}
		elapsedLabel={openingElapsedLabel}
		variant="passage"
		count={5}
	/>
{:else if selectedSegment}
	{#if segmentLoading}
		<ReaderLoadingStrip statusLabel={updatingStatusLabel} elapsedLabel={updatingElapsedLabel} />
	{/if}
	<ReaderPageNav
		previousCursor={pagePrevCursor}
		nextCursor={pageNextCursor}
		disabled={segmentLoading || contentsLoading}
		rangeLabel={pageRangeLabel}
		{onOpenPage}
	/>

	<ReaderCurrentDivision {currentDivisionTrail} {currentDivisionNode} {onOpenDivision} />

	<ReaderLeaf
		{pageSegments}
		{language}
		{selectedWord}
		{showTransliteration}
		{segmentParts}
		{onOpenSegment}
		{onSelectToken}
	/>

	<ReaderPageNav
		previousCursor={pagePrevCursor}
		nextCursor={pageNextCursor}
		disabled={segmentLoading || contentsLoading}
		rangeLabel={pageRangeLabel}
		contextLabel={selectedWorkLabel || 'reader page'}
		contextDetail={selectedWorkDetail}
		placement="bottom"
		{onOpenPage}
	/>

	<ReaderSourceDetails
		sourceText={selectedSegment.source_text}
		transliteration={selectedSegment.transliteration}
	/>
{/if}
