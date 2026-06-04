<script lang="ts">
	import OrionObjectCard from '../OrionObjectCard.svelte';
	import ReaderWorkDossier from './ReaderWorkDossier.svelte';
	import type { ReaderStructureNode, ReaderWorkDossierResponse } from '$lib/reader';
	import { uiCopy } from '../ui-copy';

	type Props = {
		workTitle: string;
		workSubtitle: string;
		classificationConfidence?: string | null;
		dossier: ReaderWorkDossierResponse | null;
		dossierLoading: boolean;
		dossierLoadingLabel: string;
		dossierError: string;
		currentDivisionNode: ReaderStructureNode | null;
		onOpenDivision: (workId: string, citation: string) => void;
		onRetry: () => void;
	};

	let {
		workTitle,
		workSubtitle,
		classificationConfidence = '',
		dossier,
		dossierLoading,
		dossierLoadingLabel,
		dossierError,
		currentDivisionNode,
		onOpenDivision,
		onRetry
	}: Props = $props();
</script>

<section class="orion-reader-work-desk" aria-label="Reader work desk">
	<OrionObjectCard
		kind={uiCopy.orionObjects.work}
		title={workTitle}
		subtitle={workSubtitle}
		chips={classificationConfidence ? [classificationConfidence] : []}
	/>
	<ReaderWorkDossier
		{dossier}
		loading={dossierLoading}
		loadingLabel={dossierLoadingLabel}
		error={dossierError}
		{currentDivisionNode}
		{onOpenDivision}
		{onRetry}
	/>
</section>

<style>
	.orion-reader-work-desk {
		display: grid;
		gap: 0.75rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding: 0 0 0.25rem;
	}

	.orion-reader-work-desk :global(.orion-object-card) {
		max-width: 42rem;
	}

	@media (max-width: 48rem) {
		.orion-reader-work-desk {
			padding-inline: 0;
		}

		.orion-reader-work-desk :global(.orion-object-card) {
			max-width: none;
		}
	}
</style>
