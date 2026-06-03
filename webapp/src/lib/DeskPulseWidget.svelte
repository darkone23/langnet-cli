<script lang="ts">
	import { BookOpen } from 'lucide-svelte';

	type Props = Record<string, never>;

	let {}: Props = $props();
</script>

<div class="orion-pulse-widget" aria-hidden="true">
	<div class="orion-pulse-core">
		<BookOpen size={30} />
	</div>
	<span class="orion-pulse-dot orion-pulse-dot-a"></span>
	<span class="orion-pulse-dot orion-pulse-dot-b"></span>
	<span class="orion-pulse-dot orion-pulse-dot-c"></span>
</div>

<style>
	.orion-pulse-widget {
		position: relative;
		display: grid;
		width: 8rem;
		height: 8rem;
		place-items: center;
	}

	.orion-pulse-widget::before,
	.orion-pulse-widget::after {
		position: absolute;
		inset: 1rem;
		border: 1px solid color-mix(in oklab, var(--color-primary) 45%, transparent);
		border-radius: 999px;
		content: '';
		animation: orion-pulse-ring 1.8s ease-out infinite;
	}

	.orion-pulse-widget::after {
		animation-delay: 0.55s;
	}

	.orion-pulse-core {
		z-index: 1;
		display: grid;
		width: 4.5rem;
		height: 4.5rem;
		place-items: center;
		border-radius: 1rem;
		background: var(--color-secondary);
		color: var(--color-secondary-content);
		box-shadow: 0 1rem 2rem color-mix(in oklab, var(--color-secondary) 25%, transparent);
		animation: orion-pulse-core 1.3s ease-in-out infinite;
	}

	.orion-pulse-dot {
		position: absolute;
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 999px;
		background: var(--color-secondary);
		animation: orion-pulse-dot 1.4s ease-in-out infinite;
	}

	.orion-pulse-dot-a {
		top: 1rem;
		right: 1.5rem;
	}

	.orion-pulse-dot-b {
		right: 1rem;
		bottom: 1.5rem;
		animation-delay: 0.2s;
	}

	.orion-pulse-dot-c {
		bottom: 2rem;
		left: 1rem;
		animation-delay: 0.4s;
	}

	@keyframes orion-pulse-ring {
		0% {
			opacity: 0.7;
			transform: scale(0.7);
		}

		100% {
			opacity: 0;
			transform: scale(1.35);
		}
	}

	@keyframes orion-pulse-core {
		0%,
		100% {
			transform: scale(1);
		}

		50% {
			transform: scale(1.06);
		}
	}

	@keyframes orion-pulse-dot {
		0%,
		100% {
			opacity: 0.45;
			transform: scale(0.82);
		}

		50% {
			opacity: 1;
			transform: scale(1.15);
		}
	}
</style>
