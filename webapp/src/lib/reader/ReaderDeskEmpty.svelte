<script lang="ts">
	import { Feather, FileSearch, Telescope } from 'lucide-svelte';
	import IlluminatedSprite from '$lib/ornament/IlluminatedSprite.svelte';

	type EmptyIcon = 'feather' | 'file-search' | 'telescope';

	type Props = {
		icon: EmptyIcon;
		message: string;
	};

	let { icon, message }: Props = $props();
</script>

<div class="orion-reader-desk-empty">
	<IlluminatedSprite variant="beast" scale="md" label="Kells-style marginal book pet" />
	{#if icon === 'file-search'}
		<FileSearch size={24} />
	{:else if icon === 'telescope'}
		<Telescope size={24} />
	{:else}
		<Feather size={24} />
	{/if}
	<span>{message}</span>
</div>

<style>
	.orion-reader-desk-empty {
		display: grid;
		min-height: 14rem;
		place-items: center;
		align-content: center;
		gap: 0.7rem;
		padding: 2rem;
		color: color-mix(in oklab, var(--color-base-content) 54%, transparent);
		font-family: var(--font-serif);
		text-align: center;
	}
</style>
