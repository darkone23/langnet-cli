<script lang="ts">
	import type { EncounterBriefingSummary } from '../encounter-briefing';
	import type { ReaderSegment, ReaderStructureNode } from '$lib/reader';
	import ReaderApparatusEvidencePanel from './ReaderApparatusEvidencePanel.svelte';
	import ReaderApparatusOraclePanel from './ReaderApparatusOraclePanel.svelte';
	import ReaderApparatusStructurePanel from './ReaderApparatusStructurePanel.svelte';
	import ReaderApparatusWordPanel from './ReaderApparatusWordPanel.svelte';
	import { uiCopy } from '../ui-copy';

	type ApparatusPanel = 'structure' | 'word' | 'oracle' | 'evidence' | '';
	type Romanization = { label: string; value: string } | null;

	type Props = {
		activePanel: ApparatusPanel;
		structure: ReaderStructureNode[];
		selectedWord: string;
		selectedWordRomanization: Romanization;
		selectedWordHref: string;
		selectedWordBriefingOutput: EncounterBriefingSummary | null;
		selectedWordBriefingBadge: string;
		selectedWordBriefingCanGenerate: boolean;
		selectedWordBriefingLoading: boolean;
		selectedWordBriefingGenerating: boolean;
		selectedWordBriefingError: string;
		currentDivisionTrail: ReaderStructureNode[];
		currentDivisionNode: ReaderStructureNode | null;
		selectedSegment: ReaderSegment | null;
		selectedWorkTitle: string;
		selectedWorkAddress: string;
		onClose: () => void;
		onOpenDivision: (workId: string, citation: string) => void;
		onGenerateBriefing: () => void;
	};

	let {
		activePanel,
		structure,
		selectedWord,
		selectedWordRomanization,
		selectedWordHref,
		selectedWordBriefingOutput,
		selectedWordBriefingBadge,
		selectedWordBriefingCanGenerate,
		selectedWordBriefingLoading,
		selectedWordBriefingGenerating,
		selectedWordBriefingError,
		currentDivisionTrail,
		currentDivisionNode,
		selectedSegment,
		selectedWorkTitle,
		selectedWorkAddress,
		onClose,
		onOpenDivision,
		onGenerateBriefing
	}: Props = $props();
</script>

{#if activePanel}
	<section class="orion-reader-apparatus-sheet open" aria-label="Reader apparatus sheet">
		<div class="orion-reader-apparatus-sheet-head">
			<strong>{activePanel}</strong>
			<button type="button" class="btn btn-xs" onclick={onClose}>
				{uiCopy.apparatus.close}
			</button>
		</div>

		{#if activePanel === 'structure'}
			<ReaderApparatusStructurePanel {structure} {onOpenDivision} />
		{:else if activePanel === 'word'}
			<ReaderApparatusWordPanel
				{selectedWord}
				{selectedWordRomanization}
				{selectedWordHref}
				{selectedWordBriefingOutput}
				{selectedWordBriefingBadge}
				{selectedWordBriefingLoading}
				{selectedWordBriefingError}
			/>
		{:else if activePanel === 'oracle'}
			<ReaderApparatusOraclePanel
				{selectedWord}
				{selectedWordBriefingOutput}
				{selectedWordBriefingBadge}
				{selectedWordBriefingCanGenerate}
				{selectedWordBriefingLoading}
				{selectedWordBriefingGenerating}
				{onGenerateBriefing}
			/>
		{:else}
			<ReaderApparatusEvidencePanel
				{currentDivisionTrail}
				{currentDivisionNode}
				{selectedSegment}
				{selectedWorkTitle}
				{selectedWorkAddress}
				{onOpenDivision}
			/>
		{/if}
	</section>
{/if}

<style>
	.orion-reader-apparatus-sheet {
		display: none;
	}

	@media (max-width: 48rem) {
		.orion-reader-apparatus-sheet {
			position: fixed;
			z-index: 40;
			right: 0;
			bottom: 0;
			left: 0;
			display: grid;
			max-height: min(78vh, 42rem);
			gap: 0.75rem;
			border-top: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
			border-radius: 0.65rem 0.65rem 0 0;
			background: var(--color-base-100);
			padding: 0.85rem;
			box-shadow: 0 -1rem 2.2rem color-mix(in oklab, var(--color-neutral) 20%, transparent);
			overflow: auto;
		}

		.orion-reader-apparatus-sheet-head {
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 1rem;
			font-family: var(--font-serif);
			text-transform: capitalize;
		}
	}
</style>
