<script lang="ts">
	import { CheckCircle2 } from 'lucide-svelte';

	type IconComponent = typeof CheckCircle2;

	type Props = {
		Icon: IconComponent;
		label: string;
		title: string;
		active: boolean;
		onSelect: () => void;
	};

	let { Icon, label, title, active, onSelect }: Props = $props();
</script>

<button
	type="button"
	class={active ? 'orion-tool-chip orion-tool-chip-active' : 'orion-tool-chip'}
	onclick={onSelect}
	{title}
>
	<span class="orion-tool-icon">
		<Icon size={16} />
	</span>
	<span class="orion-tool-chip-label">{label}</span>
	{#if active}
		<CheckCircle2 size={14} class="orion-tool-check" />
	{/if}
</button>

<style>
	.orion-tool-chip {
		position: relative;
		display: grid;
		min-width: 0;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 0.45rem;
		align-items: center;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 11%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 94%, var(--color-base-200));
		padding: 0.42rem 0.5rem;
		color: var(--color-base-content);
		text-align: left;
		transition:
			border-color 140ms ease,
			background-color 140ms ease,
			box-shadow 140ms ease;
	}

	.orion-tool-chip:hover {
		border-color: color-mix(in oklab, var(--color-secondary) 45%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-accent) 5%);
	}

	.orion-tool-chip-active {
		border-color: color-mix(in oklab, var(--color-secondary) 62%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-secondary) 6%);
		box-shadow: inset 0.16rem 0 0
			color-mix(in oklab, var(--color-accent) 78%, var(--color-secondary));
	}

	.orion-tool-icon {
		display: grid;
		width: 1.8rem;
		height: 1.8rem;
		place-items: center;
		border: 1px solid color-mix(in oklab, var(--color-accent) 34%, var(--color-base-300));
		border-radius: 0.26rem;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-accent) 6%);
		color: color-mix(in oklab, var(--color-base-content) 66%, var(--color-secondary));
	}

	.orion-tool-chip-label {
		min-width: 0;
		overflow: hidden;
		font-size: 0.8rem;
		font-weight: 650;
		line-height: 1.15;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:global(.orion-tool-check) {
		position: absolute;
		top: 0.24rem;
		right: 0.24rem;
		color: var(--color-success);
	}
</style>
