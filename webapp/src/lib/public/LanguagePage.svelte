<script lang="ts">
	import { onMount } from 'svelte';
	import { BookOpen, GraduationCap, Search, Telescope } from 'lucide-svelte';
	import { uiCopy } from '$lib/ui-copy';
	import type { LanguageMode } from '$lib/search-data';
	import type { PublicWordOfDay } from './word-of-day';

	type Feature = {
		title: string;
		body: string;
		icon: 'search' | 'book' | 'learn';
	};

	type Props = {
		copy: {
			language: LanguageMode;
			label: string;
			accentText: string;
			accentTo: string;
			Icon: typeof BookOpen;
			metaDescription: string;
			lookupLabel: string;
			eyebrow: string;
			title: string;
			intro: string;
			features: Feature[];
			wordOfDayTitle: string;
			wordOfDayIntro: string;
		};
	};

	let { copy }: Props = $props();
	let HeroIcon = $derived(copy.Icon);
	let word = $state<PublicWordOfDay | null>(null);
	let wordError = $state(false);

	onMount(async () => {
		try {
			const response = await fetch(`/api/word-of-day?language=${copy.language}`);
			if (!response.ok) throw new Error(`Word of the day failed with ${response.status}`);
			word = (await response.json()) as PublicWordOfDay;
		} catch {
			wordError = true;
		}
	});

	function featureIcon(icon: Feature['icon']) {
		if (icon === 'search') return Search;
		if (icon === 'book') return BookOpen;
		return GraduationCap;
	}
</script>

<svelte:head>
	<title>{copy.label} | {uiCopy.app.title}</title>
	<meta name="description" content={copy.metaDescription} />
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen">
	<header class="navbar border-base-300 bg-base-100 border-b px-4 lg:px-8">
		<div class="flex-1">
			<a href="/" class="flex items-center gap-3 font-semibold">
				<Telescope size={22} />
				<span>{uiCopy.app.name}</span>
			</a>
		</div>
		<a class="btn btn-sm btn-primary" href={`/q?lang=${copy.language}`}>{copy.lookupLabel}</a>
	</header>

	<section class={`from-base-100 via-base-200 ${copy.accentTo} border-base-300 border-b bg-gradient-to-br px-6 py-16 lg:px-12 lg:py-24`}>
		<div class="mx-auto max-w-5xl">
			<HeroIcon class={`${copy.accentText} mb-5`} size={42} />
			<p class={`${copy.accentText} mb-4 text-sm font-bold tracking-[0.35em] uppercase`}>{copy.eyebrow}</p>
			<h1 class="max-w-4xl text-4xl leading-tight font-black tracking-tight lg:text-6xl">
				{copy.title}
			</h1>
			<p class="text-base-content/75 mt-6 max-w-3xl text-lg leading-8">{copy.intro}</p>
		</div>
	</section>

	<section class="mx-auto grid max-w-6xl gap-5 px-6 py-12 md:grid-cols-3 lg:px-12">
		{#each copy.features as feature}
			{@const FeatureIcon = featureIcon(feature.icon)}
			<div class="bg-base-100 border-base-300 rounded-3xl border p-6">
				<FeatureIcon class={`${copy.accentText} mb-4`} size={28} />
				<h2 class="text-xl font-bold">{feature.title}</h2>
				<p class="text-base-content/70 mt-2">{feature.body}</p>
			</div>
		{/each}
	</section>

	<section class="mx-auto max-w-6xl px-6 pb-16 lg:px-12">
		<div class="bg-base-100 border-base-300 grid gap-6 rounded-[2rem] border p-6 shadow-sm md:grid-cols-[0.9fr_1.1fr] md:p-8 md:items-center">
			<div>
				<p class={`${copy.accentText} mb-3 text-xs font-bold tracking-[0.3em] uppercase`}>Daily lookup</p>
				<h2 class="text-3xl font-black">{copy.wordOfDayTitle}</h2>
				<p class="text-base-content/70 mt-3 leading-7">{copy.wordOfDayIntro}</p>
			</div>
			<div class="bg-base-200 rounded-3xl p-5">
				{#if word}
					<p class="text-base-content/60 text-sm">{word.date}</p>
					<h3 class="mt-1 text-4xl font-black">{word.display}</h3>
					{#if word.transliteration}
						<p class="text-base-content/60 mt-1 font-semibold">{word.transliteration}</p>
					{/if}
					<p class="mt-4 text-lg font-bold">{word.gloss}</p>
					<p class="text-base-content/70 mt-2">{word.note}</p>
					<p class="text-base-content/60 mt-3 text-sm">{word.sourceNote}</p>
					<a class="btn btn-primary mt-5" href={word.href}>
						<Search size={18} />
						Open this lookup
					</a>
				{:else if wordError}
					<p class="text-base-content/70">The daily lookup card is unavailable. The lookup desk is still open.</p>
					<a class="btn btn-primary mt-5" href={`/q?lang=${copy.language}`}>Open lookup</a>
				{:else}
					<div class="space-y-3">
						<div class="skeleton h-8 w-36"></div>
						<div class="skeleton h-5 w-full"></div>
						<div class="skeleton h-5 w-3/4"></div>
					</div>
				{/if}
			</div>
		</div>
	</section>
</main>
