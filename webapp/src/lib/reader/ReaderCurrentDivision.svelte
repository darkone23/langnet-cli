<script lang="ts">
	import OrionProvenanceChips from '../OrionProvenanceChips.svelte';
	import type { ReaderStructureNode } from '$lib/reader';
	import { uiCopy } from '../ui-copy';

	type Props = {
		currentDivisionTrail: ReaderStructureNode[];
		currentDivisionNode: ReaderStructureNode | null;
		onOpenDivision: (workId: string, citation: string) => void;
	};

	let { currentDivisionTrail, currentDivisionNode, onOpenDivision }: Props = $props();

	function structureNodeTitle(node: ReaderStructureNode) {
		return node.traditional_reference || node.short_label || node.label || node.start_citation;
	}

	function structureNodeSubtitle(node: ReaderStructureNode) {
		return [node.native_label || '', structureNodeRange(node)].filter(Boolean).join(' · ');
	}

	function structureNodeRange(node: ReaderStructureNode) {
		if (node.start_citation && node.end_citation && node.start_citation !== node.end_citation) {
			return `${node.start_citation} - ${node.end_citation}`;
		}
		return node.start_citation || node.end_citation || '';
	}
</script>

{#if currentDivisionTrail.length}
	<aside class="orion-reader-current-division" aria-label={uiCopy.readerStructure.current}>
		<div>
			<span>current memory place</span>
			<strong>{structureNodeTitle(currentDivisionNode ?? currentDivisionTrail[0])}</strong>
			<small>{structureNodeSubtitle(currentDivisionNode ?? currentDivisionTrail[0])}</small>
		</div>
		<div class="orion-reader-current-division-trail">
			{#each currentDivisionTrail as division}
				<button
					type="button"
					onclick={() => onOpenDivision(division.work_id, division.start_citation)}
				>
					{structureNodeTitle(division)}
				</button>
			{/each}
		</div>
		{#if currentDivisionNode?.summary}
			<p>{currentDivisionNode.summary}</p>
		{/if}
		<OrionProvenanceChips chips={currentDivisionNode?.provenance_chips} />
	</aside>
{/if}

<style>
	.orion-reader-current-division {
		position: relative;
		display: grid;
		gap: 0.45rem;
		margin: 0.75rem 1rem 0;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-secondary) 44%, var(--color-accent));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.62rem 0.72rem;
	}

	.orion-reader-current-division::before {
		content: '✦';
		position: absolute;
		top: -0.55rem;
		left: 0.7rem;
		display: grid;
		width: 1.05rem;
		height: 1.05rem;
		place-items: center;
		border: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 38%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--reader-ornament-gold) 12%);
		color: color-mix(in oklab, var(--reader-ornament-ink) 82%, var(--reader-ornament-gold));
		font-size: 0.68rem;
		line-height: 1;
	}

	.orion-reader-current-division > div:first-child {
		display: grid;
		gap: 0.12rem;
	}

	.orion-reader-current-division span,
	.orion-reader-current-division small {
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-size: 0.72rem;
		font-variant-caps: small-caps;
		font-weight: 750;
		letter-spacing: 0.08em;
		line-height: 1.25;
	}

	.orion-reader-current-division strong {
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.98rem;
		line-height: 1.2;
	}

	.orion-reader-current-division p {
		color: color-mix(in oklab, var(--color-base-content) 68%, transparent);
		font-family: var(--font-serif);
		font-size: 0.84rem;
		line-height: 1.4;
	}

	.orion-reader-current-division-trail {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
	}

	.orion-reader-current-division-trail button {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
		border-radius: 0.25rem;
		background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-base-200));
		padding: 0.12rem 0.38rem;
		color: color-mix(in oklab, var(--color-base-content) 74%, var(--color-primary));
		font-size: 0.72rem;
		font-weight: 750;
		line-height: 1.2;
	}
</style>
