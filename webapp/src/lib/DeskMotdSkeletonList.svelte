<script lang="ts">
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		rows: readonly number[];
	};

	let { rows }: Props = $props();
</script>

<div class="orion-motd-list" aria-busy="true" aria-label={uiCopy.margin.prepareAria}>
	{#each rows as _}
		<div class="orion-motd-link orion-motd-skeleton-card">
			<span class="orion-motd-skeleton-block orion-motd-skeleton-heading"></span>
			<span class="orion-motd-skeleton-block orion-motd-skeleton-gloss"></span>
			<span class="orion-motd-skeleton-block orion-motd-skeleton-foot"></span>
		</div>
	{/each}
	<span class="sr-only">{uiCopy.margin.prepareAria}</span>
</div>

<style>
	.orion-motd-list {
		display: grid;
		gap: 0.45rem;
	}

	.orion-motd-link {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.12rem 0.7rem;
		overflow: hidden;
		min-height: 8.15rem;
		align-content: start;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid
			color-mix(in oklab, var(--color-accent) 30%, var(--color-base-content));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 96%, var(--color-base-200));
		padding: 0.75rem 0.82rem;
		color: var(--color-base-content);
	}

	.orion-motd-skeleton-card {
		pointer-events: none;
	}

	.orion-motd-skeleton-card:nth-child(2) {
		border-left-color: color-mix(in oklab, var(--color-secondary) 28%, var(--color-base-content));
	}

	.orion-motd-skeleton-card:nth-child(3) {
		border-left-color: color-mix(in oklab, var(--color-primary) 28%, var(--color-base-content));
	}

	.orion-motd-skeleton-card:nth-child(2) .orion-motd-skeleton-block::after {
		animation-delay: 0.18s;
	}

	.orion-motd-skeleton-card:nth-child(3) .orion-motd-skeleton-block::after {
		animation-delay: 0.36s;
	}

	.orion-motd-skeleton-block {
		position: relative;
		display: block;
		overflow: hidden;
		border-radius: 0.38rem;
		background: color-mix(in oklab, var(--color-base-content) 11%, var(--color-base-200));
		animation: orion-motd-line 1.65s ease-in-out infinite;
	}

	.orion-motd-skeleton-block::after {
		position: absolute;
		inset: -40%;
		background: radial-gradient(
			circle at 50% 50%,
			color-mix(in oklab, var(--color-accent) 20%, transparent),
			transparent 58%
		);
		content: '';
		animation: orion-motd-blob 1.7s ease-in-out infinite;
	}

	.orion-motd-skeleton-heading {
		grid-column: 1 / -1;
		width: 78%;
		height: 1.15rem;
		animation-delay: 0.08s;
	}

	.orion-motd-skeleton-card:nth-child(2) .orion-motd-skeleton-heading {
		width: 66%;
	}

	.orion-motd-skeleton-card:nth-child(3) .orion-motd-skeleton-heading {
		width: 72%;
	}

	.orion-motd-skeleton-gloss {
		grid-column: 1 / -1;
		width: 100%;
		height: 2.75rem;
		animation-delay: 0.2s;
	}

	.orion-motd-skeleton-card:nth-child(2) .orion-motd-skeleton-gloss {
		height: 2.35rem;
	}

	.orion-motd-skeleton-card:nth-child(3) .orion-motd-skeleton-gloss {
		height: 2.55rem;
	}

	.orion-motd-skeleton-foot {
		grid-column: 1 / -1;
		width: 42%;
		height: 0.9rem;
		border-radius: 999px;
		animation-delay: 0.32s;
	}

	.orion-motd-skeleton-card:nth-child(2) .orion-motd-skeleton-foot {
		width: 36%;
	}

	.orion-motd-skeleton-card:nth-child(3) .orion-motd-skeleton-foot {
		width: 48%;
	}
</style>
