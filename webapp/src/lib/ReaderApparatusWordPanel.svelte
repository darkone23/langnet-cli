<script lang="ts">
	import { Search } from 'lucide-svelte';
	import OrionObjectCard from './OrionObjectCard.svelte';
	import {
		encounterBriefingCompactText,
		type EncounterBriefingSummary
	} from './encounter-briefing';
	import { uiCopy } from './ui-copy';

	type Romanization = { label: string; value: string } | null;

	type Props = {
		selectedWord: string;
		selectedWordRomanization: Romanization;
		selectedWordHref: string;
		selectedWordBriefingOutput: EncounterBriefingSummary | null;
		selectedWordBriefingBadge: string;
		selectedWordBriefingLoading: boolean;
		selectedWordBriefingError: string;
	};

	let {
		selectedWord,
		selectedWordRomanization,
		selectedWordHref,
		selectedWordBriefingOutput,
		selectedWordBriefingBadge,
		selectedWordBriefingLoading,
		selectedWordBriefingError
	}: Props = $props();

	function meaningSummaries(summary: EncounterBriefingSummary | null) {
		return (summary?.meanings ?? []).slice(0, 2);
	}
</script>

{#snippet loadingStrip(label: string)}
	<div class="orion-reader-loading-strip" aria-busy="true" aria-live="polite">
		<span>{label}</span>
	</div>
{/snippet}

<div class="orion-reader-apparatus-word-panel">
	{#if selectedWord}
		<OrionObjectCard
			kind={uiCopy.orionObjects.word}
			title={selectedWord}
			subtitle={selectedWordRomanization
				? `${selectedWordRomanization.label}: ${selectedWordRomanization.value}`
				: ''}
			chips={selectedWordBriefingOutput ? [selectedWordBriefingBadge] : []}
		/>
		{#if selectedWordBriefingLoading && !selectedWordBriefingOutput}
			{@render loadingStrip(uiCopy.encounterBriefing.loading)}
		{:else if selectedWordBriefingOutput}
			<div class="orion-reader-apparatus-summary">
				<p>{encounterBriefingCompactText(selectedWordBriefingOutput.short, 180)}</p>
				{#if meaningSummaries(selectedWordBriefingOutput).length}
					<ul>
						{#each meaningSummaries(selectedWordBriefingOutput) as meaning}
							<li>{encounterBriefingCompactText(meaning.summary, 120)}</li>
						{/each}
					</ul>
				{/if}
			</div>
		{:else if selectedWordBriefingError}
			<p class="text-error text-sm">{selectedWordBriefingError}</p>
		{/if}
		<a class="btn btn-sm btn-secondary" href={selectedWordHref}>
			<Search size={15} />
			{uiCopy.encounterBriefing.studyWord}
		</a>
	{:else}
		<p>{uiCopy.encounterBriefing.empty}</p>
	{/if}
</div>

<style>
	.orion-reader-apparatus-word-panel,
	.orion-reader-apparatus-summary {
		display: grid;
		justify-items: start;
		gap: 0.55rem;
		min-width: 0;
	}

	.orion-reader-apparatus-word-panel {
		align-content: start;
	}

	.orion-reader-apparatus-summary {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-accent) 44%, var(--color-primary));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.68rem 0.75rem;
	}

	.orion-reader-apparatus-summary p,
	.orion-reader-apparatus-summary li {
		color: color-mix(in oklab, var(--color-base-content) 72%, transparent);
		font-family: var(--font-serif);
		font-size: 0.86rem;
		line-height: 1.42;
	}

	.orion-reader-apparatus-summary ul {
		display: grid;
		gap: 0.35rem;
		padding-left: 1rem;
	}
</style>
