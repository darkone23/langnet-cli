<script lang="ts">
	import { BookOpen, Database, ScrollText, Sparkles } from 'lucide-svelte';
	import { uiCopy } from '../ui-copy';

	type ApparatusPanel = 'structure' | 'word' | 'oracle' | 'evidence';

	type Props = {
		showing: boolean;
		onOpenPanel: (panel: ApparatusPanel) => void;
	};

	let { showing, onOpenPanel }: Props = $props();
</script>

{#if showing}
	<nav class="orion-reader-apparatus-tabs" aria-label="Reader apparatus">
		<button type="button" onclick={() => onOpenPanel('structure')}>
			<ScrollText size={15} />
			<span>{uiCopy.apparatus.structure}</span>
		</button>
		<button type="button" onclick={() => onOpenPanel('word')}>
			<BookOpen size={15} />
			<span>{uiCopy.apparatus.word}</span>
		</button>
		<button type="button" onclick={() => onOpenPanel('oracle')}>
			<Sparkles size={15} />
			<span>{uiCopy.apparatus.oracle}</span>
		</button>
		<button type="button" onclick={() => onOpenPanel('evidence')}>
			<Database size={15} />
			<span>{uiCopy.apparatus.evidence}</span>
		</button>
	</nav>
{/if}

<style>
	.orion-reader-apparatus-tabs {
		display: none;
	}

	@media (max-width: 64rem) {
		.orion-reader-apparatus-tabs {
			position: fixed;
			z-index: 35;
			right: 0.75rem;
			bottom: 0.75rem;
			left: 0.75rem;
			display: grid;
			grid-template-columns: repeat(4, minmax(0, 1fr));
			gap: 0.25rem;
			border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
			border-radius: var(--radius-box);
			background: color-mix(in oklab, var(--color-base-100) 94%, var(--color-base-200));
			padding: 0.3rem;
			box-shadow: 0 0.6rem 1.4rem color-mix(in oklab, var(--color-neutral) 18%, transparent);
		}

		.orion-reader-apparatus-tabs button {
			display: grid;
			min-width: 0;
			justify-items: center;
			gap: 0.18rem;
			border: 0;
			border-radius: var(--radius-field);
			background: transparent;
			padding: 0.34rem 0.2rem;
			color: color-mix(in oklab, var(--color-base-content) 70%, var(--color-primary));
			font-size: 0.68rem;
			font-weight: 800;
			line-height: 1.1;
		}

		.orion-reader-apparatus-tabs button:hover,
		.orion-reader-apparatus-tabs button:focus-visible {
			background: color-mix(in oklab, var(--color-accent) 12%, var(--color-base-100));
		}
	}
</style>
