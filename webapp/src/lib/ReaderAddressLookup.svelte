<script lang="ts">
	import { ScrollText } from 'lucide-svelte';

	type Props = {
		showing: boolean;
		addressInput: string;
		placeholder: string;
		segmentLoading: boolean;
		canOpen: boolean;
		onAddressInput: (value: string) => void;
		onOpenAddress: () => void;
		onCloseLookup: () => void;
		onShowLookup: () => void;
	};

	let {
		showing,
		addressInput,
		placeholder,
		segmentLoading,
		canOpen,
		onAddressInput,
		onOpenAddress,
		onCloseLookup,
		onShowLookup
	}: Props = $props();

	function handleAddressInput(event: Event) {
		onAddressInput((event.currentTarget as HTMLInputElement).value);
	}
</script>

<div class="mt-5">
	{#if showing}
		<form
			class="orion-reader-address-lookup"
			onsubmit={(event) => {
				event.preventDefault();
				onOpenAddress();
			}}
		>
			<label class="input input-bordered flex min-w-0 items-center gap-2">
				<ScrollText size={16} class="text-base-content/45" />
				<input
					class="font-serif"
					value={addressInput}
					{placeholder}
					autocomplete="off"
					oninput={handleAddressInput}
				/>
			</label>
			<button class="btn btn-neutral" disabled={segmentLoading || !canOpen}>
				<ScrollText size={16} />
				{segmentLoading ? 'Opening' : 'Open'}
			</button>
			<button type="button" class="btn btn-ghost" onclick={onCloseLookup}>Close</button>
		</form>
	{:else}
		<button type="button" class="btn btn-sm btn-ghost" onclick={onShowLookup}>
			<ScrollText size={15} />
			Open reference
		</button>
	{/if}
</div>

<style>
	.orion-reader-address-lookup {
		display: grid;
		grid-template-columns: minmax(14rem, 26rem) auto auto;
		align-items: center;
		gap: 0.5rem;
	}

	@media (max-width: 48rem) {
		.orion-reader-address-lookup {
			grid-template-columns: 1fr;
		}
	}
</style>
