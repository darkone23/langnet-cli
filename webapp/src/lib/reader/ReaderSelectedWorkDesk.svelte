<script lang="ts">
	import OrionObjectCard from '../OrionObjectCard.svelte';
	import IlluminatedSprite from '$lib/ornament/IlluminatedSprite.svelte';
	import ReaderWorkDossier from './ReaderWorkDossier.svelte';
	import type { ReaderStructureNode, ReaderWork, ReaderWorkDossierResponse } from '$lib/reader';
	import { readerWorkPublicKey } from '$lib/reader';
	import { uiCopy } from '../ui-copy';

	type Props = {
		workTitle: string;
		workSubtitle: string;
		classificationConfidence?: string | null;
		selectedWork?: ReaderWork | null;
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
		selectedWork = null,
		dossier,
		dossierLoading,
		dossierLoadingLabel,
		dossierError,
		currentDivisionNode,
		onOpenDivision,
		onRetry
	}: Props = $props();

	const witnessChips = $derived(
		[
			selectedWork ? readerWorkPublicKey(selectedWork) : '',
			selectedWork?.language,
			selectedWork?.work_kind,
			selectedWork?.classification_category,
			selectedWork?.classification_period,
			selectedWork?.classification_authorship_status
		]
			.filter((value): value is string => Boolean(value?.trim()))
			.slice(0, 6)
	);
</script>

<section class="orion-reader-work-desk" aria-label="Reader work desk">
	{#if selectedWork}
		<div class="orion-reader-threshold-card">
			<div class="orion-reader-threshold-ornament">
				<IlluminatedSprite variant="vineInitial" scale="sm" label="Memory-key vine initial" />
			</div>
			<div>
				<span class="orion-reader-liturgical-label">Threshold</span>
				<strong>Enter the work by witness, citation, and tradition.</strong>
				<p>
					This reader opens a keyed work, not an isolated word list. Read the passage first;
					then let forms, sources, and apparatus gather around it.
				</p>
			</div>
			<div class="orion-reader-threshold-keys" aria-label="Work keys">
				{#each witnessChips as chip}
					<span>{chip.replaceAll('_', ' ')}</span>
				{/each}
			</div>
		</div>
	{/if}
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

	.orion-reader-threshold-card {
		position: relative;
		display: grid;
		gap: 0.75rem;
		max-width: 56rem;
		overflow: hidden;
		border: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 28%, var(--color-base-300));
		border-left: 0.22rem solid color-mix(in oklab, var(--reader-ornament-ink) 60%, var(--reader-ornament-gold));
		border-radius: var(--radius-box);
		background:
			radial-gradient(
				circle at 96% 12%,
				color-mix(in oklab, var(--reader-ornament-gold) 18%, transparent),
				transparent 7rem
			),
			color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.82rem 0.92rem;
	}

	.orion-reader-threshold-ornament {
		position: absolute;
		right: 0.55rem;
		bottom: 0.4rem;
		opacity: 0.24;
	}

	.orion-reader-threshold-card strong {
		display: block;
		margin-top: 0.14rem;
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: clamp(1rem, 1.6vw, 1.22rem);
		line-height: 1.22;
	}

	.orion-reader-threshold-card p {
		max-width: 62ch;
		margin-top: 0.35rem;
		color: color-mix(in oklab, var(--color-base-content) 66%, transparent);
		font-family: var(--font-reader);
		font-size: 0.9rem;
		line-height: 1.55;
	}

	.orion-reader-threshold-keys {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
	}

	.orion-reader-threshold-keys span {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 72%, var(--reader-ornament-gold) 10%);
		padding: 0.14rem 0.46rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-secondary));
		font-family: var(--font-serif);
		font-size: 0.68rem;
		font-variant-caps: small-caps;
		font-weight: 750;
		line-height: 1.15;
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
