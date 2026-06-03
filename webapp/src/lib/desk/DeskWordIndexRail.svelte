<script lang="ts">
	import { Compass } from 'lucide-svelte';
	import DeskWordIndexEarmarks from '$lib/desk/DeskWordIndexEarmarks.svelte';
	import DeskWordIndexRows from '$lib/desk/DeskWordIndexRows.svelte';
	import DeskWordIndexSections from '$lib/desk/DeskWordIndexSections.svelte';
	import type { LanguageMode } from '$lib/search-data';
	import type {
		WordIndexItem,
		WordIndexMergedPosition,
		WordIndexMergedRow,
		WordIndexSection
	} from '$lib/word-index';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		query: string;
		sections: WordIndexSection[];
		activeSection: WordIndexSection | null | undefined;
		sectionsTitle: string;
		sectionsLoading: boolean;
		sectionsError: string;
		loading: boolean;
		initialLoading: boolean;
		rows: WordIndexMergedRow[];
		hasRows: boolean;
		sourceSetCount: number;
		orderTitle: string;
		error: string;
		emptyMessage: string;
		hasResponse: boolean;
		earmarks: WordIndexItem[];
		canOpenSection: (section: WordIndexSection) => boolean;
		wordIndexPrimaryItem: (row: WordIndexMergedRow) => WordIndexItem;
		wordIndexRowPosition: (row: WordIndexMergedRow) => WordIndexMergedPosition;
		wordIndexRowMatched: (row: WordIndexMergedRow) => boolean;
		wordIndexRowSources: (row: WordIndexMergedRow) => string[];
		wordIndexHref: (item: WordIndexItem) => string;
		wordIndexDisplay: (item: WordIndexItem) => string;
		wordIndexLookup: (item: WordIndexItem) => string;
		wordIndexEntryCountLabel: (item: WordIndexItem) => string;
		isEarmarked: (item: WordIndexItem) => boolean;
		languageLabel: (language: LanguageMode) => string;
		onBrowseSection: (section: WordIndexSection) => void;
		onOpenSection: (section: WordIndexSection) => void;
		onNavigate: (event: MouseEvent, item: WordIndexItem) => void;
		onToggleEarmark: (item: WordIndexItem) => void;
		onClearEarmarks: () => void;
	};

	let {
		query,
		sections,
		activeSection,
		sectionsTitle,
		sectionsLoading,
		sectionsError,
		loading,
		initialLoading,
		rows,
		hasRows,
		sourceSetCount,
		orderTitle,
		error,
		emptyMessage,
		hasResponse,
		earmarks,
		canOpenSection,
		wordIndexPrimaryItem,
		wordIndexRowPosition,
		wordIndexRowMatched,
		wordIndexRowSources,
		wordIndexHref,
		wordIndexDisplay,
		wordIndexLookup,
		wordIndexEntryCountLabel,
		isEarmarked,
		languageLabel,
		onBrowseSection,
		onOpenSection,
		onNavigate,
		onToggleEarmark,
		onClearEarmarks
	}: Props = $props();

	let shouldShow = $derived(Boolean(query.trim() || sections.length || earmarks.length));
</script>

{#if shouldShow}
	<section class="card orion-manuscript-panel w-full min-w-0">
		<div class="card-body min-w-0 gap-3 p-4">
			<h2 class="card-title text-base">
				<Compass size={17} />
				{uiCopy.wordIndex.title}
				{#if loading && !initialLoading}
					<span class="orion-index-busy" title={uiCopy.wordIndex.loading}>
						<span class="loading loading-spinner loading-xs"></span>
					</span>
				{/if}
			</h2>
			<p class="text-base-content/65 font-serif text-xs leading-5">
				{uiCopy.wordIndex.intro}
			</p>

			<DeskWordIndexSections
				{sections}
				{activeSection}
				{sectionsTitle}
				{sectionsLoading}
				{canOpenSection}
				{onBrowseSection}
				{onOpenSection}
			/>

			{#if !sections.length && sectionsError}
				<div class="orion-index-warning">{sectionsError}</div>
			{/if}

			<DeskWordIndexRows
				{initialLoading}
				{rows}
				{hasRows}
				{sourceSetCount}
				{orderTitle}
				{error}
				{emptyMessage}
				{hasResponse}
				{wordIndexPrimaryItem}
				{wordIndexRowPosition}
				{wordIndexRowMatched}
				{wordIndexRowSources}
				{wordIndexHref}
				{wordIndexDisplay}
				{wordIndexLookup}
				{wordIndexEntryCountLabel}
				{isEarmarked}
				{onNavigate}
				{onToggleEarmark}
			/>

			<DeskWordIndexEarmarks
				items={earmarks}
				{wordIndexHref}
				{wordIndexDisplay}
				{languageLabel}
				onClear={onClearEarmarks}
				{onNavigate}
			/>
		</div>
	</section>
{/if}

<style>
	.orion-index-warning {
		border-left: 0.18rem solid
			color-mix(in oklab, var(--color-warning) 52%, var(--color-base-content));
		padding-left: 0.55rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.72rem;
		line-height: 1.35;
	}

	.orion-index-busy {
		display: inline-grid;
		width: 1.15rem;
		height: 1.15rem;
		place-items: center;
		margin-left: auto;
		border: 1px solid color-mix(in oklab, var(--color-accent) 28%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--color-accent) 6%);
		color: color-mix(in oklab, var(--color-base-content) 56%, var(--color-accent));
	}
</style>
