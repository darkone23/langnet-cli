<script lang="ts">
	import OrionProvenanceChips from '../OrionProvenanceChips.svelte';
	import type { ReaderStructureNode } from '$lib/reader';
	import { uiCopy } from '../ui-copy';

	type Props = {
		items: ReaderStructureNode[];
		onOpenDivision: (workId: string, citation: string) => void;
		emptyLabel?: string;
	};

	let { items, onOpenDivision, emptyLabel = uiCopy.readerStructure.empty }: Props = $props();
</script>

{#if items.length}
	<div class="orion-reader-canon-table">
		{#each items as item}
			<article
				class="orion-reader-division-card"
				style={`--division-depth: ${Math.max(0, item.level - 1)}`}
			>
				<div>
					<span>{item.kind}</span>
					<strong>{item.short_label || item.label}</strong>
					{#if item.native_label}
						<small>{item.native_label}</small>
					{/if}
				</div>
				<div>
					<span>{item.traditional_reference || item.start_citation}</span>
					<small>{item.start_citation}..{item.end_citation}</small>
				</div>
				{#if item.summary}
					<p>{item.summary}</p>
				{/if}
				<OrionProvenanceChips chips={item.provenance_chips} />
				<button
					type="button"
					class="btn btn-xs"
					onclick={() => onOpenDivision(item.work_id, item.start_citation)}
				>
					{uiCopy.readerStructure.open}
				</button>
			</article>
		{/each}
	</div>
{:else}
	<p>{emptyLabel}</p>
{/if}

<style>
	.orion-reader-canon-table {
		display: grid;
		gap: 0.45rem;
		max-height: 28rem;
		overflow: auto;
	}

	.orion-reader-division-card {
		display: grid;
		gap: 0.35rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-primary) 42%, var(--color-accent));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.55rem;
		padding-left: calc(0.55rem + var(--division-depth, 0) * 0.7rem);
	}

	.orion-reader-division-card strong {
		display: block;
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.95rem;
		line-height: 1.2;
	}

	.orion-reader-division-card span,
	.orion-reader-division-card small {
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-size: 0.72rem;
		font-weight: 700;
		line-height: 1.25;
	}

	.orion-reader-division-card p {
		color: color-mix(in oklab, var(--color-base-content) 68%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		line-height: 1.35;
	}
</style>
