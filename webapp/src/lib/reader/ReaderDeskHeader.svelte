<script lang="ts">
	import { Database, Feather } from 'lucide-svelte';
	import type { ReaderWork } from '$lib/reader';

	type Props = {
		languageLabel: string;
		workAuthorLabel?: string | null;
		workTitle?: string | null;
		workDiscriminator?: string | null;
		workContributorLine?: string | null;
		selectedWork?: ReaderWork | null;
		canOpenAuthor: boolean;
		segmentWorkId?: string | null;
		hasSelectedSegment: boolean;
		showTransliteration: boolean;
		pageRangeLabel: string;
		onOpenAuthor: () => void;
		onToggleTransliteration: () => void;
		onShowLibrary: () => void;
	};

	let {
		languageLabel,
		workAuthorLabel = null,
		workTitle = null,
		workDiscriminator = null,
		workContributorLine = null,
		selectedWork = null,
		canOpenAuthor,
		segmentWorkId = null,
		hasSelectedSegment,
		showTransliteration,
		pageRangeLabel,
		onOpenAuthor,
		onToggleTransliteration,
		onShowLibrary
	}: Props = $props();

	const sourceQualityBadges = $derived(
		[
			selectedWork?.collection_id,
			selectedWork?.classification_period,
			selectedWork?.classification_authorship_status,
			selectedWork?.classification_confidence
		]
			.filter((value): value is string => Boolean(value?.trim()))
			.slice(0, 4)
	);
</script>

<div class="orion-reader-desk-head">
	<div class="min-w-0">
		<div class="orion-reader-desk-kicker">
			{#if workTitle}
				keyed work
			{:else}
				{languageLabel} memory index
			{/if}
		</div>
		<h2>
			{#if workTitle}
				<span class="orion-reader-work-heading">
					<button
						type="button"
						class="orion-reader-desk-author"
						disabled={!canOpenAuthor}
						onclick={onOpenAuthor}
					>
						{workAuthorLabel}
					</button>
					<span>{workTitle}</span>
					{#if workDiscriminator}
						<small>{workDiscriminator}</small>
					{/if}
					{#if workContributorLine}
						<small>{workContributorLine}</small>
					{/if}
				</span>
			{:else if segmentWorkId}
				{segmentWorkId}
			{:else}
				Library
			{/if}
		</h2>
		{#if sourceQualityBadges.length}
			<div class="orion-reader-source-badges" aria-label="Source and work quality">
				{#each sourceQualityBadges as badge}
					<span>{badge.replaceAll('_', ' ')}</span>
				{/each}
			</div>
		{/if}
	</div>
	{#if hasSelectedSegment}
		<div class="orion-reader-desk-actions">
			<button
				type="button"
				class={showTransliteration ? 'btn btn-xs btn-secondary' : 'btn btn-xs'}
				aria-pressed={showTransliteration}
				onclick={onToggleTransliteration}
			>
				<Feather size={13} />
				Transliteration
			</button>
			<button type="button" class="btn btn-xs" onclick={onShowLibrary}>
				<Database size={13} />
				Library
			</button>
			<div class="orion-reader-desk-citation">
				<span>citation key</span>
				<strong>{pageRangeLabel}</strong>
			</div>
		</div>
	{/if}
</div>

<style>
	.orion-reader-desk-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		padding: 1rem 1.15rem;
	}

	.orion-reader-desk-head h2 {
		margin-top: 0.18rem;
		font-family: var(--font-serif);
		font-size: clamp(1.15rem, 2.3vw, 1.7rem);
		font-weight: 700;
		line-height: 1.2;
	}

	.orion-reader-desk-kicker {
		color: color-mix(in oklab, var(--color-base-content) 56%, transparent);
		font-family: var(--font-serif);
		font-size: 0.72rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		letter-spacing: 0.12em;
	}

	.orion-reader-work-heading {
		display: flex;
		min-width: 0;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.35rem;
	}

	.orion-reader-work-heading small {
		color: color-mix(in oklab, var(--color-base-content) 42%, transparent);
		font-family: var(--font-serif);
		font-size: 0.68em;
		font-weight: 600;
		line-height: 1;
	}

	.orion-reader-source-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
		margin-top: 0.48rem;
	}

	.orion-reader-source-badges span {
		border: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 32%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--reader-ornament-gold) 8%);
		padding: 0.13rem 0.42rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-secondary));
		font-family: var(--font-serif);
		font-size: 0.68rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1.15;
	}

	.orion-reader-desk-author {
		border: 0;
		background: transparent;
		color: color-mix(in oklab, var(--color-base-content) 76%, var(--color-primary));
		cursor: pointer;
		font: inherit;
		font-weight: 750;
		padding: 0;
		text-align: left;
	}

	.orion-reader-desk-author::after {
		content: ',';
		color: color-mix(in oklab, var(--color-base-content) 64%, transparent);
	}

	.orion-reader-desk-author:hover:not(:disabled) {
		text-decoration: underline;
		text-underline-offset: 0.16em;
	}

	.orion-reader-desk-author:disabled {
		color: inherit;
		cursor: default;
	}

	.orion-reader-desk-actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: flex-end;
		gap: 0.5rem;
	}

	.orion-reader-desk-citation {
		display: grid;
		justify-items: end;
		gap: 0.1rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-accent) 5%);
		padding: 0.42rem 0.55rem;
		white-space: nowrap;
	}

	.orion-reader-desk-citation span {
		color: color-mix(in oklab, var(--color-base-content) 52%, transparent);
		font-size: 0.62rem;
		font-weight: 700;
		text-transform: uppercase;
	}

	.orion-reader-desk-citation strong {
		font-family: var(--font-serif);
		font-size: 1rem;
		line-height: 1;
	}
</style>
