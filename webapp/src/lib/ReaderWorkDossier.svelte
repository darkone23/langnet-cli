<script lang="ts">
	import OrionProvenanceChips from './OrionProvenanceChips.svelte';
	import type { ReaderStructureNode, ReaderWorkDossierResponse } from './reader';
	import { uiCopy } from './ui-copy';

	type Props = {
		dossier: ReaderWorkDossierResponse | null;
		loading: boolean;
		loadingLabel: string;
		error: string;
		currentDivisionNode: ReaderStructureNode | null;
		onOpenDivision: (workId: string, citation: string) => void;
		onRetry: () => void;
	};

	let {
		dossier,
		loading,
		loadingLabel,
		error,
		currentDivisionNode,
		onOpenDivision,
		onRetry
	}: Props = $props();

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

	function dossierStatItems(nextDossier: ReaderWorkDossierResponse) {
		return [
			{
				label: uiCopy.workDossier.structureSummary,
				value:
					nextDossier.summary.structure_label || `${nextDossier.summary.structure_count} divisions`
			},
			{
				label: uiCopy.workDossier.headings,
				value: String(nextDossier.summary.top_level_count)
			},
			{
				label: uiCopy.workDossier.divisionBios,
				value: String(nextDossier.summary.division_bio_count)
			},
			{
				label: uiCopy.provenance.curated,
				value: nextDossier.summary.has_division_metadata
					? uiCopy.workDossier.metadataReady
					: uiCopy.workDossier.metadataPending
			}
		];
	}
</script>

<div class="orion-reader-work-dossier">
	<div>
		<span>{uiCopy.orionObjects.dossier}</span>
		<strong>{uiCopy.workDossier.title}</strong>
		{#if dossier?.summary.structure_label}
			<small>{dossier.summary.structure_label}</small>
		{/if}
	</div>
	<OrionProvenanceChips chips={dossier?.provenance_chips} />
	{#if loading && !dossier}
		<div class="orion-reader-loading-strip" aria-busy="true" aria-live="polite">
			<span>{loadingLabel}</span>
		</div>
	{:else if error}
		<div class="orion-reader-state-panel orion-reader-state-error" role="alert">
			<strong>Work dossier failed to load</strong>
			<p>{error}</p>
			<button type="button" class="btn btn-sm" onclick={onRetry}>Load dossier again</button>
		</div>
	{:else if dossier}
		<div class="orion-reader-work-dossier-stats" aria-label={uiCopy.workDossier.structureSummary}>
			{#each dossierStatItems(dossier) as item}
				<div>
					<span>{item.label}</span>
					<strong>{item.value}</strong>
				</div>
			{/each}
		</div>
		{#if currentDivisionNode}
			<div class="orion-reader-work-dossier-current">
				<span>{uiCopy.workDossier.currentDivision}</span>
				<button
					type="button"
					onclick={() =>
						onOpenDivision(currentDivisionNode.work_id, currentDivisionNode.start_citation)}
				>
					<strong>{structureNodeTitle(currentDivisionNode)}</strong>
					<small>{structureNodeSubtitle(currentDivisionNode)}</small>
				</button>
				<OrionProvenanceChips chips={currentDivisionNode.provenance_chips} />
			</div>
		{/if}
		{#if dossier.headings.length}
			<div class="orion-reader-work-dossier-headings">
				<span>{uiCopy.workDossier.headings}</span>
				{#each dossier.headings.slice(0, 8) as heading}
					<button
						type="button"
						onclick={() => onOpenDivision(heading.work_id, heading.start_citation)}
					>
						{structureNodeTitle(heading)}
					</button>
				{/each}
			</div>
		{/if}
		{#if dossier.division_bios.length}
			<div class="orion-reader-work-dossier-bio">
				<span>{uiCopy.workDossier.divisionBios}</span>
				{#each dossier.division_bios.slice(0, 3) as division}
					<article class="orion-reader-work-dossier-note">
						<button
							type="button"
							onclick={() => onOpenDivision(division.work_id, division.start_citation)}
						>
							<strong>{structureNodeTitle(division)}</strong>
							<small>{structureNodeSubtitle(division)}</small>
						</button>
						{#if division.summary}
							<p>{division.summary}</p>
						{/if}
						<OrionProvenanceChips chips={division.provenance_chips} />
					</article>
				{/each}
			</div>
		{/if}
	{:else}
		<p>{uiCopy.workDossier.empty}</p>
	{/if}
</div>

<style>
	.orion-reader-work-dossier {
		display: grid;
		gap: 0.55rem;
		max-width: 56rem;
		border-left: 0.18rem solid color-mix(in oklab, var(--color-secondary) 36%, var(--color-accent));
		padding: 0.15rem 0 0.15rem 0.75rem;
	}

	.orion-reader-work-dossier > div:first-child {
		display: grid;
		gap: 0.12rem;
	}

	.orion-reader-work-dossier span,
	.orion-reader-work-dossier small {
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-size: 0.72rem;
		font-weight: 750;
		line-height: 1.25;
	}

	.orion-reader-work-dossier strong {
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.96rem;
		line-height: 1.2;
	}

	.orion-reader-work-dossier p {
		max-width: 54rem;
		color: color-mix(in oklab, var(--color-base-content) 68%, transparent);
		font-family: var(--font-serif);
		font-size: 0.86rem;
		line-height: 1.42;
	}

	.orion-reader-work-dossier-stats {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.35rem;
	}

	.orion-reader-work-dossier-stats div,
	.orion-reader-work-dossier-note,
	.orion-reader-work-dossier-current {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-field);
		background: color-mix(in oklab, var(--color-base-100) 84%, var(--color-base-200));
		padding: 0.45rem 0.52rem;
	}

	.orion-reader-work-dossier-stats strong {
		display: block;
		margin-top: 0.12rem;
		font-size: 0.82rem;
	}

	.orion-reader-work-dossier-current {
		display: grid;
		gap: 0.28rem;
	}

	.orion-reader-work-dossier-current button,
	.orion-reader-work-dossier-note button {
		display: grid;
		width: 100%;
		min-width: 0;
		gap: 0.12rem;
		border: 0;
		background: transparent;
		padding: 0;
		text-align: left;
	}

	.orion-reader-work-dossier-headings {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
		align-items: center;
	}

	.orion-reader-work-dossier-headings button {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
		border-radius: 0.25rem;
		background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-base-200));
		padding: 0.12rem 0.38rem;
		color: color-mix(in oklab, var(--color-base-content) 74%, var(--color-primary));
		font-size: 0.72rem;
		font-weight: 750;
		line-height: 1.2;
	}

	.orion-reader-work-dossier-bio {
		display: grid;
		gap: 0.35rem;
	}

	.orion-reader-work-dossier-note {
		display: grid;
		gap: 0.26rem;
	}

	@media (max-width: 48rem) {
		.orion-reader-work-dossier-stats {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
</style>
