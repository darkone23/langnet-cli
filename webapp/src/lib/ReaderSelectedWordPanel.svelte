<script lang="ts">
	import { Search, Sparkles } from 'lucide-svelte';
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
		selectedWordBriefingCanGenerate: boolean;
		selectedWordBriefingLoading: boolean;
		selectedWordBriefingGenerating: boolean;
		selectedWordBriefingError: string;
		onGenerateBriefing: () => void;
	};

	let {
		selectedWord,
		selectedWordRomanization,
		selectedWordHref,
		selectedWordBriefingOutput,
		selectedWordBriefingBadge,
		selectedWordBriefingCanGenerate,
		selectedWordBriefingLoading,
		selectedWordBriefingGenerating,
		selectedWordBriefingError,
		onGenerateBriefing
	}: Props = $props();

	function meaningSummaries(summary: EncounterBriefingSummary | null) {
		return (summary?.meanings ?? []).slice(0, 2);
	}

	function grammarSummaries(summary: EncounterBriefingSummary | null) {
		return (summary?.grammar_functions ?? []).slice(0, 2);
	}
</script>

{#if selectedWord}
	<div class="orion-reader-selected-word">
		<strong>{selectedWord}</strong>
		{#if selectedWordRomanization}
			<span>{selectedWordRomanization.label}: {selectedWordRomanization.value}</span>
		{/if}
		{#if selectedWordBriefingLoading && !selectedWordBriefingOutput}
			<div class="text-base-content/60 mt-3 flex items-center gap-2 text-sm">
				<span class="loading loading-spinner loading-xs"></span>
				<span>{uiCopy.encounterBriefing.loading}</span>
			</div>
		{:else if selectedWordBriefingError && !selectedWordBriefingOutput}
			<div class="text-error mt-3 text-sm">{selectedWordBriefingError}</div>
		{:else if selectedWordBriefingOutput}
			<div class="mt-3 space-y-3 text-sm">
				<div class="flex items-center justify-between gap-2">
					<span class="badge badge-sm badge-outline">
						{selectedWordBriefingBadge}
					</span>
					{#if selectedWordBriefingCanGenerate}
						<button
							type="button"
							class="btn btn-xs btn-outline"
							disabled={selectedWordBriefingLoading}
							title={uiCopy.encounterBriefing.generateTitle}
							onclick={onGenerateBriefing}
						>
							{#if selectedWordBriefingGenerating}
								<span class="loading loading-spinner loading-xs"></span>
								{uiCopy.encounterBriefing.generateLoading}
							{:else}
								<Sparkles size={13} />
								{uiCopy.encounterBriefing.generateReady}
							{/if}
						</button>
					{/if}
				</div>
				{#if selectedWordBriefingGenerating}
					<div class="text-base-content/60 flex items-center gap-2 text-xs">
						<span class="loading loading-spinner loading-xs"></span>
						<span>{uiCopy.encounterBriefing.generatingNotice}</span>
					</div>
				{/if}
				{#if selectedWordBriefingError}
					<div class="text-error text-xs">{selectedWordBriefingError}</div>
				{/if}
				<p class="text-base-content/85 leading-relaxed">
					{encounterBriefingCompactText(selectedWordBriefingOutput.short, 220)}
				</p>
				{#if meaningSummaries(selectedWordBriefingOutput).length}
					<ul class="space-y-2">
						{#each meaningSummaries(selectedWordBriefingOutput) as meaning}
							<li>
								<div class="text-base-content/90 font-medium">
									{encounterBriefingCompactText(meaning.summary, 150)}
								</div>
								{#if meaning.sources.length}
									<div class="text-base-content/55 text-xs">
										{meaning.sources.join(', ')}
									</div>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
				{#if grammarSummaries(selectedWordBriefingOutput).length}
					<div class="border-base-content/10 space-y-1 border-t pt-3">
						{#each grammarSummaries(selectedWordBriefingOutput) as grammar}
							<div>
								<div class="text-base-content/80">
									{grammar.summary || grammar.analysis}
								</div>
								{#if grammar.lemma}
									<div class="text-base-content/55 text-xs">{grammar.lemma}</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
				{#if selectedWordBriefingOutput.caveats.length}
					<div class="text-base-content/55 text-xs">
						{selectedWordBriefingOutput.caveats.slice(0, 2).join(' ')}
					</div>
				{/if}
			</div>
		{/if}
		<a class="btn btn-sm btn-secondary mt-3" href={selectedWordHref}>
			<Search size={15} />
			{uiCopy.encounterBriefing.studyWord}
		</a>
	</div>
{:else}
	<p class="text-base-content/55 text-sm">
		{uiCopy.encounterBriefing.empty}
	</p>
{/if}

<style>
	.orion-reader-selected-word {
		display: grid;
		justify-items: start;
		gap: 0.25rem;
	}

	.orion-reader-selected-word strong {
		font-family: var(--font-reader);
		font-size: 1.35rem;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}

	.orion-reader-selected-word span {
		color: color-mix(in oklab, var(--color-base-content) 60%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
	}
</style>
