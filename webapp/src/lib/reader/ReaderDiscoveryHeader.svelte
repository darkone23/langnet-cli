<script lang="ts">
	import { BookOpen, FileSearch, Telescope } from 'lucide-svelte';

	type ReaderDiscoveryView = 'choose' | 'shelves' | 'authors' | 'search';
	type ReaderSelectableView = Exclude<ReaderDiscoveryView, 'choose'>;

	type Props = {
		title: string;
		activeView: ReaderDiscoveryView;
		onSelectView: (view: ReaderSelectableView) => void;
	};

	let { title, activeView, onSelectView }: Props = $props();
</script>

<div class="orion-reader-discovery-topline">
	<div class="min-w-0">
		<div class="orion-reader-desk-kicker">Library discovery</div>
		<h3>{title}</h3>
	</div>
	<div class="join">
		<button
			type="button"
			class="btn join-item btn-sm"
			class:btn-neutral={activeView === 'shelves'}
			aria-pressed={activeView === 'shelves'}
			onclick={() => onSelectView('shelves')}
		>
			<Telescope size={15} />
			Shelves
		</button>
		<button
			type="button"
			class="btn join-item btn-sm"
			class:btn-neutral={activeView === 'authors'}
			aria-label="Top authors"
			aria-pressed={activeView === 'authors'}
			onclick={() => onSelectView('authors')}
		>
			<BookOpen size={15} />
			Authors & works
		</button>
		<button
			type="button"
			class="btn join-item btn-sm"
			class:btn-neutral={activeView === 'search'}
			aria-pressed={activeView === 'search'}
			onclick={() => onSelectView('search')}
		>
			<FileSearch size={15} />
			Text search
		</button>
	</div>
</div>

<style>
	.orion-reader-discovery-topline {
		display: flex;
		align-items: end;
		justify-content: space-between;
		gap: 1rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding-bottom: 1rem;
	}

	.orion-reader-discovery-topline .join {
		flex-wrap: wrap;
		justify-content: flex-end;
	}

	.orion-reader-discovery-topline .btn {
		min-width: max-content;
	}

	.orion-reader-discovery-topline h3 {
		font-family: var(--font-serif);
		font-size: clamp(1.25rem, 2.2vw, 1.75rem);
		font-weight: 700;
		line-height: 1.15;
	}

	@media (max-width: 48rem) {
		.orion-reader-discovery-topline {
			align-items: stretch;
			flex-direction: column;
		}
	}
</style>
