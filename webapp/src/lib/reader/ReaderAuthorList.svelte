<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ReaderAuthor, ReaderWork } from '$lib/reader';

	type Props = {
		authors: ReaderAuthor[];
		works: ReaderWork[];
		selectedAuthorId?: string | null;
		selectedWorkId?: string | null;
		libraryLoading: boolean;
		workListLabel: (work: ReaderWork) => string;
		workListDiscriminator: (work: ReaderWork) => string;
		workMetaLine: (work: ReaderWork) => string;
		onOpenAuthor: (author: ReaderAuthor) => void;
		onOpenWork: (work: ReaderWork) => void;
		loadingAuthorWorks: Snippet;
	};

	let {
		authors,
		works,
		selectedAuthorId = null,
		selectedWorkId = null,
		libraryLoading,
		workListLabel,
		workListDiscriminator,
		workMetaLine,
		onOpenAuthor,
		onOpenWork,
		loadingAuthorWorks
	}: Props = $props();
</script>

<div class="orion-reader-author-list">
	{#each authors as author}
		<section class="orion-reader-author-group">
			<div class="orion-reader-author-heading">
				<button
					type="button"
					class="orion-reader-author-button"
					onclick={() => onOpenAuthor(author)}
				>
					<h3>{author.display_name || author.author}</h3>
					{#if author.index_name && author.index_name !== author.display_name}
						<small>{author.index_name}</small>
					{/if}
				</button>
				<span>{author.work_count} {author.work_count === 1 ? 'work' : 'works'}</span>
			</div>
			{#if selectedAuthorId === author.author_id}
				{#if libraryLoading}
					{@render loadingAuthorWorks()}
				{:else if works.length}
					<div class="orion-reader-work-list">
						{#each works as work}
							<button
								type="button"
								class:selected={selectedWorkId === work.work_id}
								class="orion-reader-work-row"
								onclick={() => onOpenWork(work)}
							>
								<strong>
									{workListLabel(work)}
									{#if workListDiscriminator(work)}
										<small>{workListDiscriminator(work)}</small>
									{/if}
								</strong>
								<span>{workMetaLine(work) || 'First page'}</span>
							</button>
						{/each}
					</div>
				{/if}
			{/if}
		</section>
	{/each}
</div>

<style>
	.orion-reader-author-list {
		display: grid;
		gap: 1rem;
	}

	.orion-reader-author-group {
		display: grid;
		gap: 0.65rem;
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		padding-top: 0.9rem;
	}

	.orion-reader-author-heading {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
	}

	.orion-reader-author-heading h3 {
		font-family: var(--font-serif);
		font-size: 1.12rem;
		font-weight: 700;
		line-height: 1.2;
	}

	.orion-reader-author-button {
		display: grid;
		min-width: 0;
		border: 0;
		background: transparent;
		color: inherit;
		cursor: pointer;
		padding: 0;
		text-align: left;
	}

	.orion-reader-author-button:hover h3 {
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-primary));
		text-decoration: underline;
		text-decoration-thickness: 1px;
		text-underline-offset: 0.16em;
	}

	.orion-reader-author-button small {
		color: color-mix(in oklab, var(--color-base-content) 52%, transparent);
		font-family: var(--font-serif);
		font-size: 0.76rem;
		line-height: 1.25;
	}

	.orion-reader-author-heading span {
		color: color-mix(in oklab, var(--color-base-content) 52%, transparent);
		font-size: 0.75rem;
		font-weight: 700;
		white-space: nowrap;
	}

	.orion-reader-work-list {
		display: grid;
		gap: 0.42rem;
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
</style>
