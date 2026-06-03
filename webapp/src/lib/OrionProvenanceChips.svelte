<script lang="ts">
	type Props = {
		chips?: string[] | null;
		label?: string;
	};

	let { chips = [], label = 'Provenance' }: Props = $props();
</script>

{#if chips?.length}
	<div class="orion-reader-provenance-row" aria-label={label}>
		{#each chips as chip}
			<span class="orion-reader-provenance-chip">{chip}</span>
		{/each}
	</div>
{/if}

<style>
	.orion-reader-provenance-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.28rem;
	}

	.orion-reader-provenance-chip {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
		border-radius: 0.25rem;
		background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-accent) 8%);
		padding: 0.1rem 0.32rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-primary));
		font-size: 0.66rem;
		font-weight: 800;
		line-height: 1.2;
	}
</style>
