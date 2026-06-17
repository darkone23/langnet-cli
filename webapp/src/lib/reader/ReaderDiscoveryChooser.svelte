<script lang="ts">
	type ReaderDiscoveryView = 'shelves' | 'authors' | 'search';

	type Props = {
		languageLabel: string;
		onSelectView: (view: ReaderDiscoveryView) => void;
	};

	let { languageLabel, onSelectView }: Props = $props();
</script>

<div class="orion-reader-shelf-grid">
	<button
		type="button"
		class="orion-reader-shelf-card"
		aria-label="Shelves"
		onclick={() => onSelectView('shelves')}
	>
		<span>Enter</span>
		<strong>Shelves of memory</strong>
		<small>{languageLabel} works by art, discipline, and tradition</small>
		<p>
			Move by ordered places: poetry, theology, grammar, history, philosophy, and the
			other rooms where a work keeps company.
		</p>
	</button>
	<button
		type="button"
		class="orion-reader-shelf-card"
		aria-label="Authors"
		onclick={() => onSelectView('authors')}
	>
		<span>Consult</span>
		<strong>Names and attributions</strong>
		<small>{languageLabel} authors, personae, and witnesses</small>
		<p>
			Find the named figure, the uncertain hand, the attributed corpus, and the works
			that gather around them.
		</p>
	</button>
	<button
		type="button"
		class="orion-reader-shelf-card"
		aria-label="Text search"
		onclick={() => onSelectView('search')}
	>
		<span>Trace</span>
		<strong>Words through passages</strong>
		<small>Follow forms and phrases inside {languageLabel} texts</small>
		<p>
			Let a word become a thread: from form to passage, from passage to witness, from
			witness back to memory.
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
		transition:
			border-color 160ms ease,
			background-color 160ms ease,
			transform 160ms ease,
			box-shadow 160ms ease;
	}

	.orion-reader-shelf-card:hover {
		border-color: color-mix(in oklab, var(--color-primary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 84%, var(--color-primary) 9%);
		box-shadow: 0 0.7rem 1.4rem color-mix(in oklab, var(--color-neutral) 9%, transparent);
		transform: translateY(-0.08rem);
	}

	.orion-reader-shelf-card > span {
		color: color-mix(in oklab, var(--color-base-content) 46%, transparent);
		font-size: 0.68rem;
		font-weight: 800;
		letter-spacing: 0.14em;
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
