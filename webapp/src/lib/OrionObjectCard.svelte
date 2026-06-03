<script lang="ts">
	import OrionProvenanceChips from './OrionProvenanceChips.svelte';

	type Props = {
		kind: string;
		title: string;
		subtitle?: string;
		chips?: string[] | null;
	};

	let { kind, title, subtitle = '', chips = [] }: Props = $props();
</script>

<article class="orion-object-card">
	<span>{kind}</span>
	<strong>{title}</strong>
	{#if subtitle}
		<small>{subtitle}</small>
	{/if}
	<OrionProvenanceChips {chips} />
</article>

<style>
	.orion-object-card {
		display: grid;
		gap: 0.3rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-primary) 44%, var(--color-accent));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 92%, var(--color-base-200));
		padding: 0.62rem;
	}

	.orion-object-card > span {
		color: color-mix(in oklab, var(--color-base-content) 48%, transparent);
		font-size: 0.68rem;
		font-weight: 800;
		line-height: 1.2;
		text-transform: uppercase;
	}

	.orion-object-card strong {
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 1rem;
		line-height: 1.2;
	}

	.orion-object-card small {
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.78rem;
		line-height: 1.35;
	}
</style>
