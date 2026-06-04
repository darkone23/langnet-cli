<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		children: Snippet;
		sidebar: Snippet;
	};

	let { children, sidebar }: Props = $props();
</script>

<div
	class="orion-reader-shell mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,1fr)_24rem] lg:px-8"
>
	<section class="orion-reader-main min-w-0 space-y-6">
		{@render children()}
	</section>

	<div class="orion-reader-sidebar-frame">
		{@render sidebar()}
	</div>
</div>

<style>
	.orion-reader-shell {
		position: relative;
	}

	.orion-reader-main {
		min-width: 0;
	}

	.orion-reader-sidebar-frame {
		min-width: 0;
	}

	:global(.orion-reader-desk-passage) {
		max-width: 72rem;
		margin-inline: auto;
		overflow: hidden;
	}

	@media (max-width: 48rem) {
		.orion-reader-shell {
			padding-bottom: 4.5rem;
		}
	}

	@media (min-width: 64rem) {
		.orion-reader-sidebar-frame {
			position: sticky;
			top: 1rem;
			align-self: start;
			max-height: calc(100svh - 2rem);
			overflow-y: auto;
			overscroll-behavior-y: contain;
			padding-right: 0.15rem;
			scrollbar-gutter: stable;
		}
	}
</style>
