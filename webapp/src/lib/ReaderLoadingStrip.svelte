<script lang="ts">
	type Props = {
		statusLabel: string;
		elapsedLabel?: string | number;
	};

	let { statusLabel, elapsedLabel = '' }: Props = $props();
</script>

<div class="orion-reader-loading-strip" aria-busy="true" aria-live="polite">
	<span>{statusLabel}</span>
	{#if elapsedLabel}
		<span class="sr-only">{elapsedLabel}</span>
	{/if}
</div>

<style>
	.orion-reader-loading-strip {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-accent) 36%, var(--color-base-300));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.45rem 0.62rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		font-weight: 700;
	}
</style>
