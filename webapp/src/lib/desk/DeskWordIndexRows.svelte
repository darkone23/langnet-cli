<script lang="ts">
	import { BookmarkCheck, BookmarkPlus, Compass } from 'lucide-svelte';
	import type { WordIndexItem, WordIndexMergedPosition, WordIndexMergedRow } from '$lib/word-index';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		initialLoading: boolean;
		rows: WordIndexMergedRow[];
		hasRows: boolean;
		sourceSetCount: number;
		orderTitle: string;
		error: string;
		emptyMessage: string;
		hasResponse: boolean;
		wordIndexPrimaryItem: (row: WordIndexMergedRow) => WordIndexItem;
		wordIndexRowPosition: (row: WordIndexMergedRow) => WordIndexMergedPosition;
		wordIndexRowMatched: (row: WordIndexMergedRow) => boolean;
		wordIndexRowSources: (row: WordIndexMergedRow) => string[];
		wordIndexHref: (item: WordIndexItem) => string;
		wordIndexDisplay: (item: WordIndexItem) => string;
		wordIndexLookup: (item: WordIndexItem) => string;
		wordIndexEntryCountLabel: (item: WordIndexItem) => string;
		isEarmarked: (item: WordIndexItem) => boolean;
		onNavigate: (event: MouseEvent, item: WordIndexItem) => void;
		onToggleEarmark: (item: WordIndexItem) => void;
	};

	let {
		initialLoading,
		rows,
		hasRows,
		sourceSetCount,
		orderTitle,
		error,
		emptyMessage,
		hasResponse,
		wordIndexPrimaryItem,
		wordIndexRowPosition,
		wordIndexRowMatched,
		wordIndexRowSources,
		wordIndexHref,
		wordIndexDisplay,
		wordIndexLookup,
		wordIndexEntryCountLabel,
		isEarmarked,
		onNavigate,
		onToggleEarmark
	}: Props = $props();
</script>

{#if initialLoading}
	<div class="orion-index-skeleton" aria-busy="true">
		<span></span>
		<span></span>
		<span></span>
		<span class="sr-only">{uiCopy.wordIndex.loading}</span>
	</div>
{:else if hasRows}
	<div class="orion-index-groups">
		<section class="orion-index-group">
			<div class="orion-index-group-head">
				<span class="orion-source-beast orion-source-beast-sm">
					<Compass size={13} />
				</span>
				<span>{orderTitle}</span>
				<span>{sourceSetCount} source sets</span>
			</div>

			<div class="orion-index-rows">
				{#each rows as row}
					{@const item = wordIndexPrimaryItem(row)}
					{@const position = wordIndexRowPosition(row)}
					{@const matched = wordIndexRowMatched(row)}
					<div
						class={matched
							? 'orion-index-row orion-index-row-matched'
							: position === 'anchor'
								? 'orion-index-row orion-index-row-anchor'
								: 'orion-index-row'}
					>
						<a
							class="orion-index-link"
							href={wordIndexHref(item)}
							aria-current={position === 'anchor' ? 'page' : undefined}
							onclick={(event) => onNavigate(event, item)}
						>
							<span class="orion-index-word">{wordIndexDisplay(item)}</span>
							<span class="orion-index-source-list">
								{#each wordIndexRowSources(row) as source}
									<span>{source}</span>
								{/each}
							</span>
							{#if wordIndexLookup(item)}
								<span class="orion-index-lookup">{wordIndexLookup(item)}</span>
							{/if}
							{#if wordIndexEntryCountLabel(item)}
								<span class="orion-index-entry-count">
									{wordIndexEntryCountLabel(item)}
								</span>
							{/if}
							<span class="orion-index-position">
								{matched ? uiCopy.wordIndex.active : uiCopy.wordIndex.position(position)}
							</span>
						</a>
						<button
							type="button"
							class="orion-index-earmark"
							title={isEarmarked(item)
								? uiCopy.wordIndex.removeEarmarkTitle
								: uiCopy.wordIndex.earmarkTitle}
							aria-label={isEarmarked(item)
								? uiCopy.wordIndex.removeEarmarkTitle
								: uiCopy.wordIndex.earmarkTitle}
							onclick={() => onToggleEarmark(item)}
						>
							{#if isEarmarked(item)}
								<BookmarkCheck size={14} />
							{:else}
								<BookmarkPlus size={14} />
							{/if}
						</button>
					</div>
				{/each}
			</div>
		</section>
	</div>
{:else if error}
	<div class="orion-index-warning">{error}</div>
{:else if hasResponse}
	<div class="orion-index-warning">{emptyMessage}</div>
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

	.orion-index-skeleton {
		display: grid;
		gap: 0.45rem;
	}

	.orion-index-skeleton span:not(.sr-only) {
		position: relative;
		display: block;
		overflow: hidden;
		height: 2.35rem;
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-content) 9%, var(--color-base-200));
		animation: orion-motd-line 1.65s ease-in-out infinite;
	}

	.orion-index-skeleton span:nth-child(2) {
		animation-delay: 0.12s;
	}

	.orion-index-skeleton span:nth-child(3) {
		animation-delay: 0.24s;
	}

	.orion-index-skeleton span:not(.sr-only)::after {
		position: absolute;
		inset: -55%;
		background: radial-gradient(
			circle at 45% 50%,
			color-mix(in oklab, var(--color-accent) 18%, transparent),
			transparent 58%
		);
		content: '';
		animation: orion-motd-blob 1.7s ease-in-out infinite;
	}

	.orion-index-groups {
		display: grid;
		gap: 0.65rem;
	}

	.orion-index-group {
		display: grid;
		gap: 0.42rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.48rem;
	}

	.orion-index-group-head {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: 0.45rem;
		align-items: center;
		color: color-mix(in oklab, var(--color-base-content) 64%, transparent);
		font-family: var(--font-serif);
		font-size: 0.74rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1.2;
	}

	.orion-index-rows {
		display: grid;
		gap: 0.26rem;
	}

	.orion-index-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.28rem;
		align-items: stretch;
	}

	.orion-index-link {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.04rem 0.45rem;
		min-width: 0;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		border-left: 0.18rem solid
			color-mix(in oklab, var(--color-accent) 26%, var(--color-base-content));
		border-radius: 0.24rem;
		background: color-mix(in oklab, var(--color-base-100) 96%, var(--color-base-200));
		padding: 0.38rem 0.48rem;
		color: inherit;
		text-decoration: none;
	}

	.orion-index-link:hover {
		border-color: color-mix(in oklab, var(--color-secondary) 36%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 6%);
	}

	.orion-index-row-anchor .orion-index-link {
		border-left-color: color-mix(in oklab, var(--color-primary) 58%, var(--color-accent));
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-accent) 8%);
	}

	.orion-index-row-matched .orion-index-link {
		border-color: color-mix(in oklab, var(--color-primary) 24%, var(--color-base-300));
		border-left-color: color-mix(in oklab, var(--color-primary) 62%, var(--color-accent));
		background: color-mix(in oklab, var(--color-base-100) 84%, var(--color-primary) 7%);
	}

	.orion-index-word {
		min-width: 0;
		overflow: hidden;
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: 0.93rem;
		font-weight: 650;
		line-height: 1.25;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.orion-index-source-list {
		display: flex;
		flex-wrap: wrap;
		justify-content: end;
		gap: 0.18rem;
	}

	.orion-index-source-list span {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-base-200));
		padding: 0.04rem 0.28rem;
		color: color-mix(in oklab, var(--color-base-content) 54%, var(--color-secondary));
		font-family: var(--font-serif);
		font-size: 0.58rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1.2;
	}

	.orion-index-lookup,
	.orion-index-entry-count,
	.orion-index-position {
		color: color-mix(in oklab, var(--color-base-content) 52%, transparent);
		font-size: 0.68rem;
		line-height: 1.25;
	}

	.orion-index-lookup,
	.orion-index-entry-count {
		grid-column: 1;
		min-width: 0;
		overflow: hidden;
		font-family: var(--font-reader);
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.orion-index-entry-count {
		color: color-mix(in oklab, var(--color-base-content) 54%, var(--color-accent));
		font-family: var(--font-serif);
		font-variant-caps: small-caps;
		font-weight: 700;
	}

	.orion-index-position {
		grid-column: 2;
		grid-row: 1 / span 2;
		align-self: center;
		font-family: var(--font-serif);
		font-variant-caps: small-caps;
	}

	.orion-index-earmark {
		display: inline-grid;
		width: 2rem;
		min-width: 2rem;
		place-items: center;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 0.24rem;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		color: color-mix(in oklab, var(--color-base-content) 58%, var(--color-accent));
		cursor: pointer;
	}

	.orion-index-earmark:hover {
		border-color: color-mix(in oklab, var(--color-accent) 40%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--color-accent) 8%);
		color: color-mix(in oklab, var(--color-base-content) 76%, var(--color-primary));
	}
</style>
