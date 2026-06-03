<script lang="ts">
	type Props = {
		label: string;
		value: string;
	};

	let { label, value }: Props = $props();
</script>

<div class="orion-search-reading" aria-live="polite">
	<span>{label}</span>
	<code>{value}</code>
</div>

<style>
	.orion-search-reading {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.45rem;
		margin-top: 0.55rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.84rem;
		line-height: 1.35;
	}

	.orion-search-reading span {
		color: color-mix(in oklab, var(--color-base-content) 44%, transparent);
		font-size: 0.68rem;
		font-variant-caps: small-caps;
		font-weight: 750;
		letter-spacing: 0;
	}

	.orion-search-reading code {
		overflow-wrap: anywhere;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		border-radius: 0.22rem;
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-base-200));
		padding: 0.12rem 0.38rem;
		color: color-mix(in oklab, var(--color-base-content) 78%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: 0.84rem;
	}
</style>
