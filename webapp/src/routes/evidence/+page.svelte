<script lang="ts">
	import { BookOpen, Database, Search, ShieldCheck, Sparkles, Telescope } from 'lucide-svelte';
	import { uiCopy } from '$lib/ui-copy';

	const copy = uiCopy.publicSite.evidence;
	const nav = uiCopy.publicSite.nav;
	const sectionIcons = [BookOpen, Search, Sparkles, ShieldCheck];
</script>

<svelte:head>
	<title>Evidence | {uiCopy.app.title}</title>
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
		<nav class="hidden gap-2 md:flex">
			<a class="btn btn-sm btn-ghost" href="/about">About</a>
			<a class="btn btn-sm btn-ghost" href="/learn">{nav.learn}</a>
			<a class="btn btn-sm btn-ghost" href="/library">Library</a>
			<a class="btn btn-sm btn-ghost" href="/languages/latin">{nav.latin}</a>
			<a class="btn btn-sm btn-ghost" href="/languages/greek">{nav.greek}</a>
			<a class="btn btn-sm btn-ghost" href="/languages/sanskrit">{nav.sanskrit}</a>
			<a class="btn btn-sm btn-primary" href="/q">{nav.openLookup}</a>
		</nav>
	</header>

	<section class="from-base-100 via-base-200 to-accent/10 border-base-300 border-b bg-gradient-to-br px-6 py-16 lg:px-12 lg:py-24">
		<div class="mx-auto max-w-5xl">
			<Database class="text-accent mb-5" size={42} />
			<p class="text-accent mb-4 text-sm font-bold tracking-[0.35em] uppercase">
				{copy.eyebrow}
			</p>
			<h1 class="max-w-4xl text-4xl leading-tight font-black tracking-tight lg:text-6xl">
				{copy.title}
			</h1>
			<p class="text-base-content/75 mt-6 max-w-3xl text-lg leading-8">{copy.intro}</p>
		</div>
	</section>

	<section class="mx-auto grid max-w-6xl gap-5 px-6 py-12 md:grid-cols-2 lg:px-12">
		{#each copy.sections as section, index}
			{@const SectionIcon = sectionIcons[index]}
			<article class="bg-base-100 border-base-300 rounded-3xl border p-6 shadow-sm">
				<SectionIcon class="text-accent mb-4" size={30} />
				<h2 class="text-2xl font-bold">{section.title}</h2>
				<p class="text-base-content/70 mt-3 leading-7">{section.body}</p>
			</article>
		{/each}
	</section>

	<section class="mx-auto max-w-6xl px-6 pb-16 lg:px-12">
		<div class="bg-base-100 border-base-300 rounded-[2rem] border p-6 md:p-8">
			<h2 class="text-3xl font-black">{copy.ctaTitle}</h2>
			<p class="text-base-content/70 mt-3 max-w-3xl leading-7">{copy.ctaBody}</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<a class="btn btn-primary" href="/q">
					<Search size={18} />
					{nav.openLookup}
				</a>
				<a class="btn btn-outline" href="/learn">{nav.learn}</a>
				<a class="btn btn-ghost" href="/library">Library</a>
			</div>
		</div>
	</section>
</main>
