<script lang="ts">
	import { AlertCircle, Boxes, Database, ScanSearch } from 'lucide-svelte';
	import OrionProvenanceChips from '$lib/OrionProvenanceChips.svelte';
	import { buildDeskOracleTrace, type OracleTrace } from './desk-oracle';
	import type { EncounterResult } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		encounter: EncounterResult | null;
		query: string;
	};

	let { encounter, query }: Props = $props();

	const trace: OracleTrace = $derived(buildDeskOracleTrace(encounter, query));
</script>

<section class="orion-oracle-trace panel card card-sm orion-manuscript-panel">
	<div class="card-body gap-4 p-4 md:p-5">
		<div class="orion-oracle-trace-head">
			<div class="orion-oracle-trace-title">
				<Database size={16} />
				<h2 class="card-title text-base">{uiCopy.oracleTrace.title}</h2>
			</div>
			<OrionProvenanceChips chips={trace.provenanceChips} label={uiCopy.oracleTrace.provenance} />
		</div>

		<div class="orion-oracle-trace-grid">
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.requested}</p>
				<p class="orion-oracle-value">{trace.requestWord || uiCopy.oracleTrace.prefill}</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.cache}</p>
				<p class="orion-oracle-value">{trace.cachePolicy}</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.backend}</p>
				<p class="orion-oracle-value">{trace.backend} / {trace.translationMode}</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.sources}</p>
				<p class="orion-oracle-value">{trace.sourceTools.join(', ') || uiCopy.oracleTrace.none}</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.candidates}</p>
				<p class="orion-oracle-value">
					{#if trace.normalizedCandidates.length}
						{trace.normalizedCandidates.join(' • ')}
					{:else}
						{uiCopy.oracleTrace.none}
					{/if}
				</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.dictionaryBuckets}</p>
				<p class="orion-oracle-value">
					{trace.bucketCount}
					{trace.bucketCount === 1 ? uiCopy.oracleTrace.bucketOne : uiCopy.oracleTrace.bucketMany}
				</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.wordIndexAnchors}</p>
				<p class="orion-oracle-value">
					{trace.indexAnchorCount}{' '}
					{trace.indexAnchorCount === 1 ? uiCopy.oracleTrace.anchor : uiCopy.oracleTrace.anchors}
					{#if trace.indexAnchorCount}
						{#each trace.indexAnchorPreview as anchor}
							<span class="orion-oracle-anchor">{anchor}</span>
						{/each}
					{/if}
				</p>
			</div>
			<div>
				<p class="orion-oracle-label">{uiCopy.oracleTrace.cacheWrites}</p>
				<p class="orion-oracle-value">
					<ScanSearch size={12} />
					{uiCopy.oracleTrace.normalization(trace.normalizationWrites)}
					{#if trace.translationWrites}
						{' · ' + uiCopy.oracleTrace.translationWrites}
					{/if}
				</p>
			</div>
		</div>

		{#if trace.warnings.length || trace.warningsOverflow}
			<div class="orion-oracle-warning" role="status">
				<AlertCircle size={14} />
				<div>
					<p>{uiCopy.oracleTrace.warnings}</p>
					<ul>
						{#each trace.warnings as warning}
							<li>{warning}</li>
						{/each}
						{#if trace.warningsOverflow}
							<li>{uiCopy.oracleTrace.moreWarnings(trace.warningsOverflow)}</li>
						{/if}
					</ul>
				</div>
			</div>
		{/if}

		{#if trace.bucketSources.length}
			<div class="orion-oracle-buckets">
				<span class="orion-oracle-label">
					<Boxes size={13} />
					{uiCopy.oracleTrace.bucketSamples}
				</span>
				<div class="orion-oracle-bucket-list">
					{#each trace.bucketSources as source}
						<span>{source}</span>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</section>

<style>
	.orion-oracle-trace-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.orion-oracle-trace-title {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		color: color-mix(in oklab, var(--color-base-content) 72%, transparent);
	}

	.orion-oracle-trace-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
		gap: 0.7rem;
	}

	.orion-oracle-label {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-size: 0.67rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1.1;
	}

	.orion-oracle-value {
		margin: 0.18rem 0 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		align-items: center;
		color: color-mix(in oklab, var(--color-base-content) 78%, transparent);
		font-size: 0.81rem;
		line-height: 1.35;
	}

	.orion-oracle-anchor {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
		border-radius: 0.2rem;
		padding: 0.05rem 0.34rem;
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-base-200));
		color: color-mix(in oklab, var(--color-base-content) 72%, transparent);
		font-size: 0.7rem;
	}

	.orion-oracle-warning {
		display: flex;
		align-items: flex-start;
		gap: 0.45rem;
		border: 1px solid color-mix(in oklab, var(--color-warning) 26%, transparent);
		border-radius: 0.35rem;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-warning) 6%);
		padding: 0.55rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.76rem;
		line-height: 1.35;
	}

	.orion-oracle-warning ul {
		margin: 0;
		padding-left: 1.1rem;
	}

	.orion-oracle-warning li {
		margin: 0;
	}

	.orion-oracle-buckets {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem;
	}

	.orion-oracle-bucket-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		min-width: 0;
	}

	.orion-oracle-bucket-list span {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 14%, transparent);
		border-radius: 999px;
		padding: 0.12rem 0.45rem;
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-accent) 8%);
		color: color-mix(in oklab, var(--color-base-content) 74%, transparent);
		font-size: 0.66rem;
		line-height: 1.2;
	}
</style>
