<script lang="ts">
	type Props = {
		label: string;
		onClear: () => void;
	};

	let { label, onClear }: Props = $props();
</script>

<div class="orion-reader-active-filter">
	<span>{label}</span>
	<button type="button" class="btn btn-xs btn-ghost" onclick={onClear}>Clear author</button>
</div>

<style>
	.orion-reader-active-filter {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		border: 1px solid color-mix(in oklab, var(--color-primary) 16%, var(--color-base-300));
		border-radius: 0.35rem;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-primary) 5%);
		padding: 0.38rem 0.5rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-size: 0.75rem;
		font-weight: 700;
	}
</style>
