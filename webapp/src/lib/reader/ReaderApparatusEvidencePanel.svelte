<script lang="ts">
	import OrionProvenanceChips from '../OrionProvenanceChips.svelte';
	import type { ReaderSegment, ReaderStructureNode } from '$lib/reader';
	import { uiCopy } from '../ui-copy';

	type Props = {
		currentDivisionTrail: ReaderStructureNode[];
		currentDivisionNode: ReaderStructureNode | null;
		selectedSegment: ReaderSegment | null;
		selectedWorkTitle: string;
		selectedWorkAddress: string;
		onOpenDivision: (workId: string, citation: string) => void;
	};

	let {
		currentDivisionTrail,
		currentDivisionNode,
		selectedSegment,
		selectedWorkTitle,
		selectedWorkAddress,
		onOpenDivision
	}: Props = $props();

	function structureNodeTitle(node: ReaderStructureNode) {
		return node.traditional_reference || node.short_label || node.label || node.start_citation;
	}
</script>

<div class="orion-reader-apparatus-evidence-panel">
	<div>
		<span>{uiCopy.apparatus.evidence}</span>
		<strong>
			{selectedSegment?.canonical_address ||
				selectedSegment?.address ||
				selectedWorkAddress ||
				selectedWorkTitle ||
				uiCopy.apparatus.evidence}
		</strong>
	</div>
	{#if currentDivisionTrail.length}
		<div class="orion-reader-apparatus-evidence-list">
			<span>{uiCopy.readerStructure.current}</span>
			{#each currentDivisionTrail as division}
				<button
					type="button"
					onclick={() => onOpenDivision(division.work_id, division.start_citation)}
				>
					{structureNodeTitle(division)}
				</button>
			{/each}
		</div>
		<OrionProvenanceChips chips={currentDivisionNode?.provenance_chips} />
	{/if}
	{#if selectedSegment}
		<dl>
			<div>
				<dt>{uiCopy.orionObjects.leaf}</dt>
				<dd>{selectedSegment.citation_path}</dd>
			</div>
			{#if selectedSegment.canonical_text_id}
				<div>
					<dt>Text</dt>
					<dd>{selectedSegment.canonical_text_id}</dd>
				</div>
			{/if}
		</dl>
	{/if}
</div>

<style>
	.orion-reader-apparatus-evidence-panel {
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

	.orion-reader-apparatus-evidence-panel > div:first-child {
		display: grid;
		gap: 0.12rem;
	}

	.orion-reader-apparatus-evidence-panel span,
	.orion-reader-apparatus-evidence-panel dt {
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-size: 0.72rem;
		font-weight: 750;
		line-height: 1.25;
	}

	.orion-reader-apparatus-evidence-panel strong,
	.orion-reader-apparatus-evidence-panel dd {
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.96rem;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}

	.orion-reader-apparatus-evidence-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
		align-items: center;
	}

	.orion-reader-apparatus-evidence-list button {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
		border-radius: 0.25rem;
		background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-base-200));
		padding: 0.12rem 0.38rem;
		color: color-mix(in oklab, var(--color-base-content) 74%, var(--color-primary));
		font-size: 0.72rem;
		font-weight: 750;
		line-height: 1.2;
	}

	.orion-reader-apparatus-evidence-panel dl {
		display: grid;
		gap: 0.35rem;
		width: 100%;
	}

	.orion-reader-apparatus-evidence-panel dl > div {
		display: grid;
		gap: 0.08rem;
	}
</style>
