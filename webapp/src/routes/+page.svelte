<script lang="ts">
	import { BookOpen, Flower2, GraduationCap, Omega, Search, Sparkles, ScrollText } from 'lucide-svelte';
	import { uiCopy } from '$lib/ui-copy';

	const copy = uiCopy.publicSite.home;

	function languageIcon(icon: (typeof copy.languages)[number]['icon']) {
		if (icon === 'latin') return ScrollText;
		if (icon === 'greek') return Omega;
		return Flower2;
	}

	function languageAccent(tone: (typeof copy.languages)[number]['tone']) {
		if (tone === 'warning') return 'text-warning mb-4';
		if (tone === 'info') return 'text-info mb-4';
		return 'text-success mb-4';
	}

	function principleIcon(tone: (typeof copy.principles)[number]['tone']) {
		return tone === 'primary' ? BookOpen : Sparkles;
	}
</script>

<svelte:head>
	<title>{uiCopy.app.title}</title>
	<meta name="description" content={copy.metaDescription} />
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen">
	<section class="from-base-100 via-base-200 to-primary/10 border-base-300 border-b bg-gradient-to-br px-6 py-16 lg:px-12 lg:py-24">
		<div class="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
			<div>
				<p class="text-primary mb-4 text-sm font-bold tracking-[0.35em] uppercase">
					{copy.eyebrow}
				</p>
				<h1 class="max-w-3xl text-5xl leading-tight font-black tracking-tight lg:text-7xl">
					{copy.title}
				</h1>
				<p class="text-base-content/75 mt-6 max-w-2xl text-lg leading-8">{copy.intro}</p>
				<div class="mt-8 flex flex-wrap gap-3">
					<a class="btn btn-primary btn-lg" href="/q">
						<Search size={20} />
						{copy.primaryCta}
					</a>
					<a class="btn btn-outline btn-lg" href="/learn">
						<GraduationCap size={20} />
						{copy.secondaryCta}
					</a>
					<a class="btn btn-ghost btn-lg" href="/about">{copy.aboutCta}</a>
					<a class="btn btn-ghost btn-lg" href="/evidence">{uiCopy.publicSite.nav.evidence}</a>
				</div>
			</div>
			<div class="border-base-300 bg-base-100/80 rounded-[2rem] border p-6 shadow-xl backdrop-blur">
				<div class="grid gap-4">
					{#each copy.principles as principle}
						{@const PrincipleIcon = principleIcon(principle.tone)}
						<div class="bg-base-200 rounded-2xl p-5">
							<PrincipleIcon class={principle.tone === 'primary' ? 'text-primary mb-3' : 'text-secondary mb-3'} size={28} />
							<h2 class="text-xl font-bold">{principle.title}</h2>
							<p class="text-base-content/70 mt-2">{principle.body}</p>
						</div>
					{/each}
				</div>
			</div>
		</div>
	</section>
	<section class="mx-auto grid max-w-6xl gap-5 px-6 py-12 md:grid-cols-3 lg:px-12">
		{#each copy.languages as language}
			{@const LanguageIcon = languageIcon(language.icon)}
			<a class="bg-base-100 border-base-300 rounded-3xl border p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md" href={language.href}>
				<LanguageIcon class={languageAccent(language.tone)} size={30} />
				<h2 class="text-2xl font-bold">{language.label}</h2>
				<p class="text-base-content/70 mt-2">{language.body}</p>
			</a>
		{/each}
	</section>
</main>
