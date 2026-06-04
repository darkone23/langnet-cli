<script lang="ts">
	type Props = {
		previousCursor: string | null;
		nextCursor: string | null;
		previousLabel: string;
		nextLabel: string;
		loading: boolean;
		onOpenPrevious: (cursor: string) => void;
		onOpenNext: (cursor: string) => void;
	};

	let {
		previousCursor,
		nextCursor,
		previousLabel,
		nextLabel,
		loading,
		onOpenPrevious,
		onOpenNext
	}: Props = $props();

	function openPrevious() {
		if (previousCursor) onOpenPrevious(previousCursor);
	}

	function openNext() {
		if (nextCursor) onOpenNext(nextCursor);
	}
</script>

{#if previousCursor || nextCursor}
	<div class="orion-reader-discovery-pager">
		<button
			type="button"
			class="btn btn-sm"
			disabled={!previousCursor || loading}
			onclick={openPrevious}
		>
			{previousLabel}
		</button>
		<button
			type="button"
			class="btn btn-sm btn-neutral"
			disabled={!nextCursor || loading}
			onclick={openNext}
		>
			{nextLabel}
		</button>
	</div>
{/if}

<style>
	.orion-reader-discovery-pager {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 0.5rem;
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding-top: 0.85rem;
	}
</style>
