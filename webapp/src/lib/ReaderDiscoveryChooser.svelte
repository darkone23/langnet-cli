<script lang="ts">
	type ReaderDiscoveryView = 'shelves' | 'authors' | 'search';

	type Props = {
		languageLabel: string;
		onSelectView: (view: ReaderDiscoveryView) => void;
	};

	let { languageLabel, onSelectView }: Props = $props();
</script>

<div class="orion-reader-shelf-grid">
	<button type="button" class="orion-reader-shelf-card" onclick={() => onSelectView('shelves')}>
		<span>Browse</span>
		<strong>Shelves</strong>
		<small>{languageLabel} works by art, subject, and genre</small>
		<p>
			Enter the library by discipline and use, then narrow from broad learning to a particular work.
		</p>
	</button>
	<button type="button" class="orion-reader-shelf-card" onclick={() => onSelectView('authors')}>
		<span>Browse</span>
		<strong>Authors</strong>
		<small>{languageLabel} author index</small>
		<p>
			Begin with teachers, poets, historians, and witnesses, then open the works attached to their
			names.
		</p>
	</button>
	<button type="button" class="orion-reader-shelf-card" onclick={() => onSelectView('search')}>
		<span>Search</span>
		<strong>Text search</strong>
		<small>Trace words and phrases inside {languageLabel} texts</small>
		<p>
			Follow a form through its passages, with enough nearby context to turn a match into a lesson.
		</p>
	</button>
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

	.orion-reader-shelf-card:hover {
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
