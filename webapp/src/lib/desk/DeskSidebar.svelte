<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import DeskColophonPanel from '$lib/desk/DeskColophonPanel.svelte';
	import DeskPageMarksPanel from '$lib/desk/DeskPageMarksPanel.svelte';
	import DeskSourceControls from '$lib/desk/DeskSourceControls.svelte';
	import DeskWordIndexRail from '$lib/desk/DeskWordIndexRail.svelte';

	type WordIndexRailProps = ComponentProps<typeof DeskWordIndexRail>;
	type SourceControlsProps = ComponentProps<typeof DeskSourceControls>;
	type ColophonPanelProps = ComponentProps<typeof DeskColophonPanel>;
	type PageMarksPanelProps = ComponentProps<typeof DeskPageMarksPanel>;

	type Props = {
		fullHeight: boolean;
		wordIndex: WordIndexRailProps;
		sourceControls: SourceControlsProps;
		colophon: ColophonPanelProps | null;
		pageMarks: PageMarksPanelProps;
		onWheel: (event: WheelEvent) => void;
	};

	let { fullHeight, wordIndex, sourceControls, colophon, pageMarks, onWheel }: Props = $props();
</script>

<aside
	class={fullHeight
		? 'orion-sidebar orion-sidebar-full min-w-0 space-y-4'
		: 'orion-sidebar min-w-0 space-y-4'}
	onwheel={onWheel}
>
	<DeskWordIndexRail {...wordIndex} />
	<DeskSourceControls {...sourceControls} />

	{#if colophon}
		<DeskColophonPanel {...colophon} />
	{/if}

	<DeskPageMarksPanel {...pageMarks} />
</aside>

<style>
	.orion-sidebar {
		width: 100%;
		min-width: 0;
	}

	@media (min-width: 64rem) {
		.orion-sidebar {
			position: fixed;
			z-index: 20;
			top: 5.75rem;
			right: max(2rem, calc((100vw - 82rem) / 2 + 2rem));
			bottom: 1.5rem;
			width: 21rem;
			max-width: calc(100vw - 4rem);
			overflow-y: scroll;
			overscroll-behavior-y: contain;
			padding-right: 0.2rem;
			pointer-events: auto;
			scrollbar-gutter: stable;
			touch-action: pan-y;
			transition:
				top 160ms ease,
				bottom 160ms ease;
		}

		.orion-sidebar-full {
			top: 0.75rem;
			bottom: 0.75rem;
		}
	}
</style>
