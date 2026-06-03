<script lang="ts">
	import type { WordIndexSection } from '$lib/word-index';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		sections: WordIndexSection[];
		activeSection: WordIndexSection | null | undefined;
		sectionsTitle: string;
		sectionsLoading: boolean;
		canOpenSection: (section: WordIndexSection) => boolean;
		onBrowseSection: (section: WordIndexSection) => void;
		onOpenSection: (section: WordIndexSection) => void;
	};

	let {
		sections,
		activeSection,
		sectionsTitle,
		sectionsLoading,
		canOpenSection,
		onBrowseSection,
		onOpenSection
	}: Props = $props();
</script>

{#if sections.length}
	<section class="orion-index-section-rail" aria-label={sectionsTitle}>
		<div class="orion-index-section-head">
			<span>{sectionsTitle}</span>
			<div class="orion-index-section-actions">
				{#if activeSection?.anchor?.query}
					<button
						type="button"
						class="orion-index-section-browse"
						onclick={() => onBrowseSection(activeSection)}
					>
						{uiCopy.wordIndex.browseSection}
					</button>
				{/if}
				{#if sectionsLoading}
					<span title={uiCopy.wordIndex.sectionsLoading}>
						<span class="loading loading-spinner loading-xs"></span>
					</span>
				{/if}
			</div>
		</div>
		<div class="orion-index-section-list">
			{#each sections as section}
				{@const sectionCanOpen = canOpenSection(section)}
				<button
					type="button"
					class={activeSection?.id === section.id
						? 'orion-index-section-button orion-index-section-button-active'
						: sectionCanOpen
							? 'orion-index-section-button'
							: 'orion-index-section-button orion-index-section-button-unavailable'}
					disabled={!sectionCanOpen}
					title={`${section.label} ${section.transliteration}`}
					aria-current={activeSection?.id === section.id ? 'true' : undefined}
					onclick={() => onOpenSection(section)}
				>
					<span>{section.label}</span>
					<small>{section.transliteration}</small>
				</button>
			{/each}
		</div>
	</section>
{/if}

<style>
	.orion-index-section-rail {
		display: grid;
		gap: 0.42rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.48rem;
	}

	.orion-index-section-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.45rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-family: var(--font-serif);
		font-size: 0.72rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1.2;
	}

	.orion-index-section-actions {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
	}

	.orion-index-section-browse {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 0.22rem;
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-accent) 5%);
		padding: 0.08rem 0.38rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, var(--color-accent));
		font-size: 0.62rem;
		font-variant-caps: small-caps;
		font-weight: 750;
		line-height: 1.2;
	}

	.orion-index-section-browse:hover {
		border-color: color-mix(in oklab, var(--color-accent) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 80%, var(--color-accent) 10%);
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-accent));
	}

	.orion-index-section-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		max-height: 8.5rem;
		overflow: auto;
		padding-right: 0.1rem;
	}

	.orion-index-section-button {
		display: inline-grid;
		min-width: 2.2rem;
		min-height: 2.25rem;
		place-items: center;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 0.24rem;
		background: color-mix(in oklab, var(--color-base-100) 94%, var(--color-base-200));
		padding: 0.18rem 0.34rem 0.16rem;
		color: color-mix(in oklab, var(--color-base-content) 78%, var(--color-primary));
		cursor: pointer;
		line-height: 1.05;
	}

	.orion-index-section-button:hover {
		border-color: color-mix(in oklab, var(--color-secondary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-secondary) 7%);
		color: color-mix(in oklab, var(--color-base-content) 88%, var(--color-secondary));
	}

	.orion-index-section-button-active {
		border-color: color-mix(in oklab, var(--color-primary) 48%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-primary) 12%);
		box-shadow:
			inset 0 0 0 1px color-mix(in oklab, var(--color-primary) 18%, transparent),
			0 0.14rem 0.32rem color-mix(in oklab, var(--color-primary) 8%, transparent);
		color: color-mix(in oklab, var(--color-base-content) 90%, var(--color-primary));
	}

	.orion-index-section-button-unavailable,
	.orion-index-section-button:disabled {
		border-color: color-mix(in oklab, var(--color-base-content) 7%, transparent);
		background: color-mix(in oklab, var(--color-base-100) 76%, var(--color-base-200));
		color: color-mix(in oklab, var(--color-base-content) 38%, transparent);
		cursor: default;
		opacity: 0.62;
	}

	.orion-index-section-button span {
		font-family: var(--font-reader);
		font-size: 1rem;
		font-weight: 700;
	}

	.orion-index-section-button small {
		max-width: 3rem;
		overflow: hidden;
		color: color-mix(in oklab, var(--color-base-content) 48%, transparent);
		font-size: 0.54rem;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
