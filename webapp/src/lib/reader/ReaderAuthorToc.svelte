<script lang="ts">
	import type { ReaderAuthorSection } from '$lib/reader';

	type Props = {
		languageLabel: string;
		sections: ReaderAuthorSection[];
		activeAuthorSection: string;
		romanHintForSection: (sectionKey: string) => string;
		onJumpToSection: (sectionKey: string) => void;
		onClearSection: () => void;
	};

	let {
		languageLabel,
		sections,
		activeAuthorSection,
		romanHintForSection,
		onJumpToSection,
		onClearSection
	}: Props = $props();
</script>

<div class="orion-reader-author-toc" aria-label="Author sections">
	<div>
		<span>{languageLabel} author index</span>
		{#if activeAuthorSection}
			<button type="button" class="btn btn-xs btn-ghost" onclick={onClearSection}>All</button>
		{/if}
	</div>
	<div class="orion-reader-author-toc-grid">
		{#each sections as section}
			{@const nativeLabel = section.native_label || section.label || section.key}
			{@const romanHint = romanHintForSection(section.key)}
			<button
				type="button"
				class:active={activeAuthorSection === section.key}
				onclick={() => onJumpToSection(section.key)}
				title={`${section.author_count} authors, ${section.work_count} works`}
			>
				<span class="orion-reader-author-section-native">{nativeLabel}</span>
				{#if romanHint && romanHint !== nativeLabel}
					<span class="orion-reader-author-section-roman">{romanHint}</span>
				{/if}
			</button>
		{/each}
	</div>
</div>

<style>
	.orion-reader-author-toc {
		display: grid;
		gap: 0.55rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding-bottom: 0.9rem;
	}

	.orion-reader-author-toc > div:first-child {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		font-weight: 700;
	}

	.orion-reader-author-toc-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
	}

	.orion-reader-author-toc-grid button {
		display: inline-flex;
		min-width: 2rem;
		align-items: baseline;
		justify-content: center;
		gap: 0.26rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 0.25rem;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.28rem 0.42rem;
		color: color-mix(in oklab, var(--color-base-content) 72%, var(--color-primary));
		cursor: pointer;
		font-family: var(--font-serif);
		font-size: 0.82rem;
		font-weight: 700;
		line-height: 1.1;
	}

	.orion-reader-author-section-native {
		color: inherit;
	}

	.orion-reader-author-section-roman {
		color: color-mix(in oklab, currentColor 46%, transparent);
		font-family: var(--font-sans);
		font-size: 0.68rem;
		font-weight: 650;
	}

	.orion-reader-author-toc-grid button:hover,
	.orion-reader-author-toc-grid button.active {
		border-color: color-mix(in oklab, var(--color-primary) 36%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-primary) 12%);
		color: color-mix(in oklab, var(--color-base-content) 88%, var(--color-primary));
	}
</style>
