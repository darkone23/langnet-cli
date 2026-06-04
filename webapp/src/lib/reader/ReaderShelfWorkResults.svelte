<script lang="ts">
	import ReaderActiveFilter from './ReaderActiveFilter.svelte';
	import {
		readerPopularityLabel,
		readerWorkDiscoveryTags,
		readerWorkDisplayAuthor,
		type ReaderFacetValue,
		type ReaderWork
	} from '$lib/reader';

	type Props = {
		works: ReaderWork[];
		selectedWorkId?: string | null;
		activeAuthorLabel?: string;
		discoveryGroups: ReaderFacetValue[];
		discoveryTags: ReaderFacetValue[];
		facetValueLabel: (values: ReaderFacetValue[], id: string) => string;
		workListLabel: (work: ReaderWork) => string;
		workListDiscriminator: (work: ReaderWork) => string;
		workMetaLine: (work: ReaderWork) => string;
		onOpenWork: (work: ReaderWork) => void | Promise<void>;
		onFilterByAuthor: (work: ReaderWork) => void;
		onClearAuthorFilter: () => void;
	};

	let {
		works,
		selectedWorkId = null,
		activeAuthorLabel = '',
		discoveryGroups,
		discoveryTags,
		facetValueLabel,
		workListLabel,
		workListDiscriminator,
		workMetaLine,
		onOpenWork,
		onFilterByAuthor,
		onClearAuthorFilter
	}: Props = $props();
</script>

<div class="orion-reader-work-list orion-reader-work-list-discovery">
	{#if activeAuthorLabel}
		<ReaderActiveFilter label={activeAuthorLabel} onClear={onClearAuthorFilter} />
	{/if}
	{#each works as work}
		<article class:selected={selectedWorkId === work.work_id} class="orion-reader-work-row">
			<div class="orion-reader-work-row-main">
				<button type="button" class="orion-reader-work-open" onclick={() => void onOpenWork(work)}>
					<strong>
						{workListLabel(work)}
						{#if workListDiscriminator(work)}
							<small>{workListDiscriminator(work)}</small>
						{/if}
					</strong>
				</button>
				<button
					type="button"
					class="orion-reader-work-author"
					disabled={!(work.canonical_author_id || work.source_author_id || work.author_id)}
					onclick={() => onFilterByAuthor(work)}
				>
					{readerWorkDisplayAuthor(work)}
				</button>
			</div>
			{#if workMetaLine(work)}
				<span>{workMetaLine(work)}</span>
			{/if}
			<div class="orion-reader-work-meta">
				{#if work.classification_discovery_group_id}
					<small>
						{facetValueLabel(discoveryGroups, work.classification_discovery_group_id)}
					</small>
				{/if}
				{#each readerWorkDiscoveryTags(work).slice(0, 4) as tag}
					<small>{facetValueLabel(discoveryTags, tag)}</small>
				{/each}
				{#if readerPopularityLabel(work)}
					<small>{readerPopularityLabel(work)}</small>
				{/if}
			</div>
		</article>
	{/each}
</div>

<style>
	.orion-reader-work-list {
		display: grid;
		gap: 0.42rem;
	}

	.orion-reader-work-list-discovery {
		gap: 0.55rem;
	}

	.orion-reader-work-row {
		display: grid;
		gap: 0.22rem;
		width: 100%;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-accent) 38%, var(--color-base-300));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 92%, var(--color-base-200));
		padding: 0.55rem 0.62rem;
		text-align: left;
		transition:
			border-color 120ms ease,
			background-color 120ms ease;
	}

	.orion-reader-work-open,
	.orion-reader-work-author {
		border: 0;
		background: transparent;
		cursor: pointer;
		padding: 0;
		text-align: left;
	}

	.orion-reader-work-open {
		min-width: 0;
		color: inherit;
	}

	.orion-reader-work-author {
		color: color-mix(in oklab, var(--color-base-content) 48%, transparent);
		font-size: 0.74rem;
		font-weight: 650;
		line-height: 1.25;
	}

	.orion-reader-work-author:hover:not(:disabled) {
		color: color-mix(in oklab, var(--color-base-content) 76%, var(--color-primary));
		text-decoration: underline;
		text-underline-offset: 0.16em;
	}

	.orion-reader-work-author:disabled {
		cursor: default;
		opacity: 0.7;
	}

	.orion-reader-work-row-main {
		display: flex;
		min-width: 0;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
	}

	.orion-reader-work-row:hover,
	.orion-reader-work-row.selected {
		border-color: color-mix(in oklab, var(--color-secondary) 30%, var(--color-base-300));
		border-left-color: color-mix(in oklab, var(--color-primary) 54%, var(--color-accent));
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-secondary) 6%);
	}

	.orion-reader-work-row strong {
		display: flex;
		min-width: 0;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.28rem;
		overflow: hidden;
		font-family: var(--font-serif);
		font-size: 0.92rem;
		line-height: 1.25;
		text-overflow: ellipsis;
	}

	.orion-reader-work-row strong small {
		color: color-mix(in oklab, var(--color-base-content) 42%, transparent);
		font-family: var(--font-serif);
		font-size: 0.68em;
		font-weight: 600;
		line-height: 1;
	}

	.orion-reader-work-row span {
		color: color-mix(in oklab, var(--color-base-content) 56%, transparent);
		font-size: 0.74rem;
		line-height: 1.25;
	}

	.orion-reader-work-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
	}

	.orion-reader-work-meta small {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 0.25rem;
		background: color-mix(in oklab, var(--color-base-100) 76%, var(--color-base-200));
		padding: 0.12rem 0.34rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.68rem;
		font-weight: 700;
		line-height: 1.2;
	}

	@media (max-width: 48rem) {
		.orion-reader-work-row-main {
			align-items: stretch;
			flex-direction: column;
		}
	}
</style>
