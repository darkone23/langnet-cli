<script lang="ts">
	import type { ReaderDiscoveryShelf } from './reader';

	type Props = {
		shelves: ReaderDiscoveryShelf[];
		shelfIsActive: (shelf: ReaderDiscoveryShelf) => boolean;
		shelfMetaLabel: (shelf: ReaderDiscoveryShelf) => string;
		onSelectShelf: (shelf: ReaderDiscoveryShelf) => void;
	};

	let { shelves, shelfIsActive, shelfMetaLabel, onSelectShelf }: Props = $props();
</script>

<div class="orion-reader-shelf-grid">
	{#each shelves as shelf}
		<button
			type="button"
			class="orion-reader-shelf-card"
			class:active={shelfIsActive(shelf)}
			aria-pressed={shelfIsActive(shelf)}
			onclick={() => onSelectShelf(shelf)}
		>
			<span>{shelf.query.tag ? 'Tag' : 'Shelf'}</span>
			<strong>{shelf.label}</strong>
			<small>{shelfMetaLabel(shelf)}</small>
			{#if shelf.description}
				<p>{shelf.description}</p>
			{/if}
		</button>
	{/each}
</div>

<style>
	.orion-reader-shelf-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(12.5rem, 1fr));
		gap: 0.55rem;
	}

	.orion-reader-shelf-card {
		display: grid;
		min-height: 8.6rem;
		align-content: start;
		gap: 0.28rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 0.45rem;
		background: color-mix(in oklab, var(--color-base-100) 92%, var(--color-base-200));
		padding: 0.8rem;
		color: inherit;
		cursor: pointer;
		text-align: left;
	}

	.orion-reader-shelf-card:hover,
	.orion-reader-shelf-card.active {
		border-color: color-mix(in oklab, var(--color-primary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 84%, var(--color-primary) 9%);
	}

	.orion-reader-shelf-card > span {
		color: color-mix(in oklab, var(--color-base-content) 46%, transparent);
		font-size: 0.68rem;
		font-weight: 800;
		letter-spacing: 0;
		text-transform: uppercase;
	}

	.orion-reader-shelf-card strong {
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 1.02rem;
		font-weight: 750;
		line-height: 1.15;
	}

	.orion-reader-shelf-card small {
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.76rem;
		font-weight: 750;
		line-height: 1.25;
	}

	.orion-reader-shelf-card p {
		display: -webkit-box;
		overflow: hidden;
		margin-top: 0.14rem;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		color: color-mix(in oklab, var(--color-base-content) 64%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		line-height: 1.34;
	}
</style>
