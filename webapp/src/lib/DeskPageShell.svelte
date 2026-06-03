<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		theme: 'manuscript' | 'vespers';
		children: Snippet;
		topbar: Snippet;
		sidebar: Snippet;
	};

	let { theme, children, topbar, sidebar }: Props = $props();
</script>

<main class="orion-page bg-base-200 text-base-content min-h-screen" data-theme={theme}>
	{@render topbar()}

	<div
		class="orion-page-shell mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,48rem)_21rem] lg:px-8"
	>
		<article class="min-w-0 space-y-6">
			{@render children()}
		</article>

		{@render sidebar()}
	</div>
</main>

<style>
	.orion-page {
		background:
			linear-gradient(
				90deg,
				color-mix(in oklab, var(--color-base-300) 18%, transparent) 0,
				transparent 0.08rem,
				transparent calc(100% - 0.08rem),
				color-mix(in oklab, var(--color-base-300) 18%, transparent) 100%
			),
			var(--color-base-100);
		font-family: var(--font-sans);
	}

	.orion-page :global(.navbar) {
		background: color-mix(in oklab, var(--color-base-100) 95%, var(--color-base-200));
		box-shadow: 0 1px 0 color-mix(in oklab, var(--color-base-content) 6%, transparent);
	}

	.orion-page :global(input[type='search']) {
		font-family: var(--font-reader);
		font-kerning: normal;
	}

	.orion-page-shell {
		position: relative;
	}

	@media (min-width: 64rem) {
		.orion-page-shell {
			display: block;
			max-width: 82rem;
			padding-right: 24rem;
		}

		.orion-page-shell > article {
			max-width: 48rem;
		}
	}
</style>
