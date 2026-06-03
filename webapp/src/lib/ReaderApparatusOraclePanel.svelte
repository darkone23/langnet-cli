<script lang="ts">
	import { Sparkles } from 'lucide-svelte';
	import OrionProvenanceChips from './OrionProvenanceChips.svelte';
	import {
		encounterBriefingCompactText,
		type EncounterBriefingSummary
	} from './encounter-briefing';
	import { uiCopy } from './ui-copy';

	type Props = {
		selectedWord: string;
		selectedWordBriefingOutput: EncounterBriefingSummary | null;
		selectedWordBriefingBadge: string;
		selectedWordBriefingCanGenerate: boolean;
		selectedWordBriefingLoading: boolean;
		selectedWordBriefingGenerating: boolean;
		onGenerateBriefing: () => void;
	};

	let {
		selectedWord,
		selectedWordBriefingOutput,
		selectedWordBriefingBadge,
		selectedWordBriefingCanGenerate,
		selectedWordBriefingLoading,
		selectedWordBriefingGenerating,
		onGenerateBriefing
	}: Props = $props();

	function grammarSummaries(summary: EncounterBriefingSummary | null) {
		return (summary?.grammar_functions ?? []).slice(0, 2);
	}
</script>

{#snippet loadingStrip(label: string)}
	<div class="orion-reader-loading-strip" aria-busy="true" aria-live="polite">
		<span>{label}</span>
	</div>
{/snippet}

<div class="orion-reader-apparatus-oracle-panel">
	<div>
		<span>{uiCopy.orionObjects.oracle}</span>
		<strong>{uiCopy.encounterBriefing.title}</strong>
	</div>
	{#if selectedWordBriefingOutput}
		<OrionProvenanceChips chips={[selectedWordBriefingBadge]} />
		<p>{encounterBriefingCompactText(selectedWordBriefingOutput.short, 240)}</p>
		{#if grammarSummaries(selectedWordBriefingOutput).length}
			<ul>
				{#each grammarSummaries(selectedWordBriefingOutput) as grammar}
					<li>{grammar.summary || grammar.analysis}</li>
				{/each}
			</ul>
		{/if}
	{:else if selectedWordBriefingLoading}
		{@render loadingStrip(uiCopy.encounterBriefing.loading)}
	{:else}
		<p>{uiCopy.encounterBriefing.empty}</p>
	{/if}
	{#if selectedWord && selectedWordBriefingCanGenerate}
		<button
			type="button"
			class="btn btn-sm btn-outline"
			disabled={selectedWordBriefingLoading}
			onclick={onGenerateBriefing}
		>
			{#if selectedWordBriefingGenerating}
				<span class="loading loading-spinner loading-xs"></span>
				{uiCopy.encounterBriefing.generateLoading}
			{:else}
				<Sparkles size={14} />
				{uiCopy.encounterBriefing.generateReady}
			{/if}
		</button>
	{/if}
</div>

<style>
	.orion-reader-apparatus-oracle-panel {
		display: grid;
		justify-items: start;
		gap: 0.55rem;
		min-width: 0;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-accent) 44%, var(--color-primary));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.68rem 0.75rem;
	}

	.orion-reader-apparatus-oracle-panel p,
	.orion-reader-apparatus-oracle-panel li {
		color: color-mix(in oklab, var(--color-base-content) 72%, transparent);
		font-family: var(--font-serif);
		font-size: 0.86rem;
		line-height: 1.42;
	}

	.orion-reader-apparatus-oracle-panel ul {
		display: grid;
		gap: 0.35rem;
		padding-left: 1rem;
	}

	.orion-reader-apparatus-oracle-panel > div:first-child {
		display: grid;
		gap: 0.12rem;
	}

	.orion-reader-apparatus-oracle-panel span {
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-size: 0.72rem;
		font-weight: 750;
		line-height: 1.25;
	}

	.orion-reader-apparatus-oracle-panel strong {
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.96rem;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}
</style>
