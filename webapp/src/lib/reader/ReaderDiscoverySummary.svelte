<script lang="ts">
	type Props = {
		primary: string;
		secondary: string;
		onSummaryElement?: (element: HTMLElement | null) => void;
	};

	let { primary, secondary, onSummaryElement = undefined }: Props = $props();
	let summaryElement = $state<HTMLElement | null>(null);

	$effect(() => {
		onSummaryElement?.(summaryElement);

		return () => {
			onSummaryElement?.(null);
		};
	});
</script>

<div bind:this={summaryElement} class="orion-reader-discovery-summary">
	<span>{primary}</span>
	<span>{secondary}</span>
</div>

<style>
	.orion-reader-discovery-summary {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		color: color-mix(in oklab, var(--color-base-content) 54%, transparent);
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
	}
</style>
