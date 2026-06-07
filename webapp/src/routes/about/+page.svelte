<script lang="ts">
	import {
		BookOpen,
		Database,
		FileText,
		GraduationCap,
		Layers3,
		Search,
		ShieldCheck,
		Sparkles,
		Telescope
	} from 'lucide-svelte';
	import { uiCopy } from '$lib/ui-copy';

	const copy = uiCopy.publicSite.about;
	const nav = uiCopy.publicSite.nav;
	const principleIcons = [BookOpen, GraduationCap, ShieldCheck];
	const sourceIcons = [BookOpen, Database, Search, FileText, Sparkles];
</script>

<svelte:head>
	<title>About | {uiCopy.app.title}</title>
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
			<a class="btn btn-sm btn-ghost" href="/learn">{nav.learn}</a>
			<a class="btn btn-sm btn-ghost" href="/evidence">{nav.evidence}</a>
			<a class="btn btn-sm btn-ghost" href="/languages/latin">{nav.latin}</a>
			<a class="btn btn-sm btn-ghost" href="/languages/greek">{nav.greek}</a>
			<a class="btn btn-sm btn-ghost" href="/languages/sanskrit">{nav.sanskrit}</a>
			<a class="btn btn-sm btn-primary" href="/q">{nav.openLookup}</a>
		</nav>
	</header>

	<section class="from-base-100 via-base-200 to-secondary/10 border-base-300 border-b bg-gradient-to-br px-6 py-16 lg:px-12 lg:py-24">
		<div class="mx-auto max-w-5xl">
			<p class="text-secondary mb-4 text-sm font-bold tracking-[0.35em] uppercase">
				{copy.eyebrow}
			</p>
			<h1 class="max-w-4xl text-4xl leading-tight font-black tracking-tight lg:text-6xl">
				{copy.title}
			</h1>
			<p class="text-base-content/75 mt-6 max-w-3xl text-lg leading-8">{copy.intro}</p>
		</div>
	</section>

	<section class="mx-auto max-w-6xl px-6 py-10 lg:px-12">
		<div class="bg-base-100 border-base-300 rounded-[2rem] border p-6 md:p-8">
			<h2 class="text-3xl font-black">{copy.productPromiseTitle}</h2>
			<p class="text-base-content/70 mt-4 max-w-4xl leading-7">{copy.productPromise}</p>
		</div>
	</section>

	<section class="mx-auto grid max-w-6xl gap-5 px-6 pb-12 md:grid-cols-3 lg:px-12">
		{#each copy.principles as principle, index}
			{@const PrincipleIcon = principleIcons[index]}
			<article class="bg-base-100 border-base-300 rounded-3xl border p-6 shadow-sm">
				<PrincipleIcon class="text-primary mb-4" size={30} />
				<h2 class="text-2xl font-bold">{principle.title}</h2>
				<p class="text-base-content/70 mt-3">{principle.body}</p>
			</article>
		{/each}
	</section>

	<section class="mx-auto max-w-6xl px-6 pb-16 lg:px-12">
		<div class="from-base-100 via-base-100 to-primary/5 border-base-300 rounded-[2rem] border bg-gradient-to-br p-6 md:p-8">
			<div class="flex max-w-4xl flex-col gap-4 md:flex-row md:items-start">
				<div class="bg-primary/10 text-primary rounded-2xl p-3">
					<Layers3 size={30} />
				</div>
				<div>
					<h2 class="text-3xl font-black">{copy.provenanceTitle}</h2>
					<p class="text-base-content/70 mt-3 leading-7">{copy.provenanceIntro}</p>
				</div>
			</div>

			<div class="mt-8 grid gap-5 md:grid-cols-2">
				{#each copy.sourceGroups as group, index}
					{@const SourceIcon = sourceIcons[index]}
					<article class="bg-base-100/80 border-base-300 rounded-3xl border p-5">
						<SourceIcon class="text-secondary mb-4" size={26} />
						<h3 class="text-xl font-bold">{group.title}</h3>
						<p class="text-base-content/65 mt-2 leading-6">{group.body}</p>
						<ul class="mt-4 space-y-2 text-sm leading-6">
							{#each group.items as item}
								<li class="flex gap-2">
									<span class="text-primary mt-0.5 font-black">·</span>
									<span>{item}</span>
								</li>
							{/each}
						</ul>
					</article>
				{/each}
			</div>

			<div class="border-base-300 bg-base-200/70 mt-6 rounded-3xl border p-5">
				<h3 class="text-xl font-bold">{copy.provenanceNoteTitle}</h3>
				<p class="text-base-content/70 mt-2 leading-7">{copy.provenanceNote}</p>
			</div>
		</div>
	</section>

	<section class="mx-auto grid max-w-6xl gap-5 px-6 pb-16 md:grid-cols-[0.9fr_1.1fr] lg:px-12">
		<div class="bg-base-100 border-base-300 rounded-[2rem] border p-6 md:p-8">
			<h2 class="text-3xl font-black">{copy.audiencesTitle}</h2>
			<ul class="text-base-content/75 mt-4 space-y-3">
				{#each copy.audiences as audience}
					<li>{audience}</li>
				{/each}
			</ul>
		</div>
		<div class="bg-base-100 border-base-300 rounded-[2rem] border p-6 md:p-8">
			<h2 class="text-3xl font-black">{copy.startTitle}</h2>
			<p class="text-base-content/70 mt-3 max-w-3xl">{copy.startBody}</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<a class="btn btn-primary" href="/q">
					<Search size={18} />
					Study a word
				</a>
				<a class="btn btn-outline" href="/learn">{nav.learn}</a>
				<a class="btn btn-ghost" href="/evidence">{nav.evidence}</a>
			</div>
		</div>
	</section>
</main>
