<script lang="ts">
	import { BookOpen, ScrollText } from 'lucide-svelte';
	import type { EncounterBriefingSummary } from './encounter-briefing';
	import ReaderCanonTable from './ReaderCanonTable.svelte';
	import ReaderContentsList from './ReaderContentsList.svelte';
	import ReaderErrorPanel from './ReaderErrorPanel.svelte';
	import ReaderLoadingRows from './ReaderLoadingRows.svelte';
	import ReaderLoadingStrip from './ReaderLoadingStrip.svelte';
	import ReaderSelectedWordPanel from './ReaderSelectedWordPanel.svelte';
	import type { ReaderSegment, ReaderStructureNode } from './reader';
	import { uiCopy } from './ui-copy';

	type Romanization = { label: string; value: string } | null;

	type Props = {
		structure: ReaderStructureNode[];
		structureLoading: boolean;
		structureError: string;
		structureStatusLabel: string;
		structureElapsedLabel: string | number;
		hasSelectedWork: boolean;
		contents: ReaderSegment[];
		contentsLoading: boolean;
		contentsError: string;
		contentsStatusLabel: string;
		contentsElapsedLabel: string | number;
		selectedWord: string;
		selectedWordRomanization: Romanization;
		selectedWordHref: string;
		selectedWordBriefingOutput: EncounterBriefingSummary | null;
		selectedWordBriefingBadge: string;
		selectedWordBriefingCanGenerate: boolean;
		selectedWordBriefingLoading: boolean;
		selectedWordBriefingGenerating: boolean;
		selectedWordBriefingError: string;
		segmentIsActive: (segment: ReaderSegment) => boolean;
		onRetryStructure: () => void;
		onRetryContents: () => void;
		onOpenDivision: (workId: string, citation: string) => void;
		onOpenSegment: (segment: ReaderSegment) => void;
		onGenerateBriefing: () => void;
	};

	let {
		structure,
		structureLoading,
		structureError,
		structureStatusLabel,
		structureElapsedLabel,
		hasSelectedWork,
		contents,
		contentsLoading,
		contentsError,
		contentsStatusLabel,
		contentsElapsedLabel,
		selectedWord,
		selectedWordRomanization,
		selectedWordHref,
		selectedWordBriefingOutput,
		selectedWordBriefingBadge,
		selectedWordBriefingCanGenerate,
		selectedWordBriefingLoading,
		selectedWordBriefingGenerating,
		selectedWordBriefingError,
		segmentIsActive,
		onRetryStructure,
		onRetryContents,
		onOpenDivision,
		onOpenSegment,
		onGenerateBriefing
	}: Props = $props();
</script>

<aside class="orion-reader-sidebar space-y-4">
	<section class="orion-manuscript-panel p-4">
		<div class="mb-3 flex items-start justify-between gap-3">
			<div>
				<h2 class="font-serif text-lg font-semibold">{uiCopy.readerStructure.title}</h2>
			</div>
			<ScrollText class="text-base-content/45 mt-1" size={18} />
		</div>
		{#if structureLoading && !structure.length}
			<ReaderLoadingRows
				statusLabel={structureStatusLabel}
				elapsedLabel={structureElapsedLabel}
				variant="contents"
				count={4}
			/>
		{:else if structureError}
			<ReaderErrorPanel
				title="Structure failed to load"
				message={structureError}
				retryLabel="Load structure again"
				onRetry={onRetryStructure}
			/>
		{:else if structure.length}
			{#if structureLoading}
				<ReaderLoadingStrip
					statusLabel={structureStatusLabel}
					elapsedLabel={structureElapsedLabel}
				/>
			{/if}
			<ReaderCanonTable items={structure} {onOpenDivision} />
		{:else if hasSelectedWork}
			<p class="text-base-content/55 text-sm">{uiCopy.readerStructure.empty}</p>
		{:else}
			<p class="text-base-content/55 text-sm">No book selected.</p>
		{/if}

		{#if contentsLoading}
			<div class="mt-4">
				<ReaderLoadingRows
					statusLabel={contentsStatusLabel}
					elapsedLabel={contentsElapsedLabel}
					variant="contents"
					count={4}
				/>
			</div>
		{:else if contentsError}
			<ReaderErrorPanel
				title="Contents failed to load"
				message={contentsError}
				retryLabel="Load contents again"
				onRetry={onRetryContents}
			/>
		{:else if contents.length && hasSelectedWork}
			<ReaderContentsList {contents} {segmentIsActive} {onOpenSegment} />
		{/if}
	</section>

	<section class="orion-manuscript-panel p-4">
		<div class="mb-3 flex items-start justify-between gap-3">
			<div>
				<h2 class="font-serif text-lg font-semibold">{uiCopy.encounterBriefing.title}</h2>
				<p class="text-base-content/60 text-sm">{uiCopy.encounterBriefing.subtitle}</p>
			</div>
			<BookOpen class="text-base-content/45 mt-1" size={18} />
		</div>
		<ReaderSelectedWordPanel
			{selectedWord}
			{selectedWordRomanization}
			{selectedWordHref}
			{selectedWordBriefingOutput}
			{selectedWordBriefingBadge}
			{selectedWordBriefingCanGenerate}
			{selectedWordBriefingLoading}
			{selectedWordBriefingGenerating}
			{selectedWordBriefingError}
			{onGenerateBriefing}
		/>
	</section>
</aside>
