<script lang="ts">
	type Props = {
		statusLabel: string;
		elapsedLabel?: string | number;
		variant: string;
		count?: number;
	};

	let { statusLabel, elapsedLabel = '', variant, count = 4 }: Props = $props();
</script>

<div class="orion-reader-loading-region" aria-busy="true" aria-live="polite">
	<div class="orion-reader-loading-status">
		<span>{statusLabel}</span>
		{#if elapsedLabel}
			<span class="sr-only">{elapsedLabel}</span>
		{/if}
	</div>
	<div class={`orion-reader-skeleton-list orion-reader-skeleton-${variant}`}>
		{#each Array.from({ length: count }) as _}
			<article class="orion-reader-skeleton-row" aria-hidden="true">
				<span class="orion-reader-skeleton-block orion-reader-skeleton-title"></span>
				<span class="orion-reader-skeleton-block orion-reader-skeleton-line"></span>
				<span class="orion-reader-skeleton-block orion-reader-skeleton-line short"></span>
				<span class="orion-reader-skeleton-chip-row">
					<span class="orion-reader-skeleton-block orion-reader-skeleton-chip"></span>
					<span class="orion-reader-skeleton-block orion-reader-skeleton-chip"></span>
				</span>
			</article>
		{/each}
	</div>
</div>

<style>
	.orion-reader-loading-region {
		display: grid;
		gap: 0.72rem;
		min-height: 10rem;
		align-content: start;
	}

	.orion-reader-loading-status {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.45rem 0.62rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		font-weight: 700;
	}

	.orion-reader-skeleton-list {
		display: grid;
		gap: 0.55rem;
	}

	.orion-reader-skeleton-row {
		display: grid;
		gap: 0.38rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-accent) 30%, var(--color-base-300));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.62rem;
	}

	.orion-reader-skeleton-block {
		position: relative;
		display: block;
		overflow: hidden;
		border-radius: 0.34rem;
		background: color-mix(in oklab, var(--color-base-content) 10%, var(--color-base-200));
		animation: orion-motd-line 1.65s ease-in-out infinite;
	}

	.orion-reader-skeleton-block::after {
		position: absolute;
		inset: -50%;
		background: radial-gradient(
			circle at 45% 50%,
			color-mix(in oklab, var(--color-accent) 18%, transparent),
			transparent 58%
		);
		content: '';
		animation: orion-motd-blob 1.7s ease-in-out infinite;
	}

	.orion-reader-skeleton-row:nth-child(2) .orion-reader-skeleton-block::after {
		animation-delay: 0.16s;
	}

	.orion-reader-skeleton-row:nth-child(3) .orion-reader-skeleton-block::after {
		animation-delay: 0.28s;
	}

	.orion-reader-skeleton-title {
		width: min(72%, 28rem);
		height: 1.1rem;
	}

	.orion-reader-skeleton-line {
		width: 100%;
		height: 0.78rem;
	}

	.orion-reader-skeleton-line.short {
		width: 58%;
	}

	.orion-reader-skeleton-chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.34rem;
	}

	.orion-reader-skeleton-chip {
		width: 4.8rem;
		height: 1rem;
		border-radius: 999px;
	}

	.orion-reader-skeleton-passage .orion-reader-skeleton-row {
		min-height: 5.7rem;
		border-left-color: color-mix(in oklab, var(--color-primary) 34%, var(--color-base-300));
	}

	.orion-reader-skeleton-author .orion-reader-skeleton-row {
		border-left-color: color-mix(in oklab, var(--color-secondary) 30%, var(--color-base-300));
	}

	.orion-reader-skeleton-contents .orion-reader-skeleton-row {
		grid-template-columns: 4rem minmax(0, 1fr);
		align-items: center;
		padding: 0.48rem 0.5rem;
	}

	.orion-reader-skeleton-contents .orion-reader-skeleton-title {
		width: 3.15rem;
	}

	.orion-reader-skeleton-contents .orion-reader-skeleton-line {
		width: 100%;
	}

	.orion-reader-skeleton-contents .orion-reader-skeleton-line.short,
	.orion-reader-skeleton-contents .orion-reader-skeleton-chip-row {
		display: none;
	}
</style>
