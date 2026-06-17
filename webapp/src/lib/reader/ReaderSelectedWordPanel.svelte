<script lang="ts">
	import { Search, Sparkles } from 'lucide-svelte';
	import {
		encounterBriefingCompactText,
		type EncounterBriefingSummary
	} from '../encounter-briefing';
	import type { ReaderWordContextResponse } from '$lib/reader';
	import { uiCopy } from '../ui-copy';

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
		selectedWordContext: ReaderWordContextResponse | null;
		selectedWordContextLoading: boolean;
		selectedWordContextError: string;
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
		selectedWordContext,
		selectedWordContextLoading,
		selectedWordContextError,
		onGenerateBriefing
	}: Props = $props();

	function meaningSummaries(summary: EncounterBriefingSummary | null) {
		return (summary?.meanings ?? []).slice(0, 2);
	}

	function grammarSummaries(summary: EncounterBriefingSummary | null) {
		return (summary?.grammar_functions ?? []).slice(0, 2);
	}

	function readerHitCount(context: ReaderWordContextResponse | null) {
		return context?.reader_hits?.items?.length ?? 0;
	}

	function readerHitStatus(context: ReaderWordContextResponse | null) {
		const status = context?.reader_hits?.status;
		if (status === 'available') return `${readerHitCount(context)} corpus witness hits`;
		if (status === 'no_hits') return 'No indexed corpus hits';
		if (status === 'index_unavailable') return 'Corpus index unavailable';
		if (status === 'error') return 'Corpus search error';
		return 'Corpus status pending';
	}
</script>

{#if selectedWord}
	<div class="orion-reader-selected-word">
		<span class="orion-reader-liturgical-label">Marginalia</span>
		<strong>{selectedWord}</strong>
		{#if selectedWordRomanization}
			<span>{selectedWordRomanization.label}: {selectedWordRomanization.value}</span>
		{/if}
		<div class="orion-reader-word-context">
			{#if selectedWordContextLoading && !selectedWordContext}
				<div class="text-base-content/60 flex items-center gap-2 text-xs">
					<span class="loading loading-spinner loading-xs"></span>
					<span>Checking word evidence...</span>
				</div>
			{:else if selectedWordContextError && !selectedWordContext}
				<div class="text-error text-xs">{selectedWordContextError}</div>
			{:else if selectedWordContext}
				<div class="flex flex-wrap gap-1.5">
					<span class="badge badge-xs badge-outline">{readerHitStatus(selectedWordContext)}</span>
					<span class="badge badge-xs badge-outline">
						{Math.round(selectedWordContext.timing.total_ms)} ms
					</span>
					{#if selectedWordContext.provenance.collection_id}
						<span class="badge badge-xs badge-outline">
							{selectedWordContext.provenance.collection_id}
						</span>
					{/if}
				</div>
				{#if selectedWordContext.normalization.candidates.length}
					<div class="text-base-content/60 text-xs">
						Forms: {selectedWordContext.normalization.candidates.join(', ')}
					</div>
				{/if}
				<div class="grid gap-1 text-xs">
					<div>
						<span class="text-base-content/50">Lexicon:</span>
						<span>{selectedWordContext.lexical_evidence.status}</span>
					</div>
					<div>
						<span class="text-base-content/50">Morphology:</span>
						<span>{selectedWordContext.morphology.status}</span>
					</div>
				</div>
				{#if readerHitCount(selectedWordContext)}
					<ul class="orion-reader-word-hits">
						{#each selectedWordContext.reader_hits.items.slice(0, 3) as hit}
							<li>
								<strong>{hit.title || hit.work_id}</strong>
								<span>{hit.citation_path}</span>
							</li>
						{/each}
					</ul>
				{/if}
				{#if selectedWordContext.caveats.length}
					<div class="text-base-content/55 text-xs">
						{selectedWordContext.caveats.slice(0, 2).join(' ')}
					</div>
				{/if}
			{/if}
		</div>
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
				<p class="orion-reader-selected-word-summary">
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
		position: relative;
		display: grid;
		justify-items: start;
		gap: 0.28rem;
		border-left: 0.18rem solid color-mix(in oklab, var(--reader-ornament-ink) 48%, var(--reader-ornament-gold));
		padding-left: 0.72rem;
	}

	.orion-reader-selected-word::before {
		content: '';
		position: absolute;
		top: 0.28rem;
		left: -0.43rem;
		width: 0.62rem;
		height: 0.62rem;
		border: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 48%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 80%, var(--reader-ornament-gold) 16%);
	}

	.orion-reader-selected-word strong {
		font-family: var(--font-reader);
		font-size: 1.45rem;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}

	.orion-reader-selected-word span {
		color: color-mix(in oklab, var(--color-base-content) 60%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
	}

	.orion-reader-selected-word-summary {
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: 0.94rem;
		line-height: 1.58;
	}

	.orion-reader-word-context {
		display: grid;
		gap: 0.45rem;
		width: 100%;
		margin-top: 0.35rem;
		padding: 0.6rem;
		border: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 20%, transparent);
		border-radius: 0.85rem;
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--reader-ornament-gold) 8%);
	}

	.orion-reader-word-hits {
		display: grid;
		gap: 0.45rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.orion-reader-word-hits li {
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		padding-top: 0.45rem;
	}

	.orion-reader-word-hits strong {
		display: block;
		font-size: 0.82rem;
	}

</style>
