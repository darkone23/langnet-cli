<script lang="ts">
	import { Clock3 } from 'lucide-svelte';
	import DeskPulseWidget from '$lib/DeskPulseWidget.svelte';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		query: string;
		languageName: string;
		allSourcesSelected: boolean;
		elapsedSeconds: number;
	};

	let { query, languageName, allSourcesSelected, elapsedSeconds }: Props = $props();

	let dictionaryMode = $derived(allSourcesSelected ? 'all' : 'custom');
</script>

<section class="card orion-manuscript-panel">
	<div class="card-body items-center gap-6 p-8 text-center">
		<DeskPulseWidget />

		<div class="max-w-xl">
			<div class="orion-lookup-timer">
				<Clock3 size={14} />
				<span>{elapsedSeconds}s</span>
			</div>
			<h3 class="font-serif text-3xl leading-tight">{uiCopy.search.loadingTitle}</h3>
			<p class="text-base-content/65 mt-3 font-serif text-lg leading-7">
				Looking up <em>{query.trim()}</em> in {languageName} with
				<code class="mx-1">dictionary={dictionaryMode}</code>.
			</p>
			<p class="text-base-content/60 mt-2 text-sm leading-6">
				{uiCopy.search.coldSources}
			</p>
		</div>

		<ul class="steps steps-vertical md:steps-horizontal w-full max-w-2xl">
			{#each uiCopy.search.loadingSteps as step}
				<li class="step step-primary">{step}</li>
			{/each}
		</ul>
	</div>
</section>

<style>
	.orion-lookup-timer {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		margin-bottom: 0.75rem;
		border: 1px solid color-mix(in oklab, var(--color-secondary) 24%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 6%);
		padding: 0.22rem 0.58rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-secondary));
		font-size: 0.78rem;
		font-variant-numeric: tabular-nums;
		font-weight: 900;
	}
</style>
