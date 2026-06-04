<script lang="ts">
	import { BookOpen, GraduationCap, Search, Sparkles } from 'lucide-svelte';
	import { uiCopy } from '$lib/ui-copy';
</script>

<svelte:head>
	<title>{uiCopy.app.title}</title>
	<meta
		name="description"
		content="Classical language tools for learning Sanskrit, Greek, and Latin with dictionary evidence, morphology, and reader support."
	/>
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen">
	<section class="from-base-100 via-base-200 to-primary/10 border-base-300 border-b bg-gradient-to-br px-6 py-16 lg:px-12 lg:py-24">
		<div class="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
			<div>
				<p class="text-primary mb-4 text-sm font-bold tracking-[0.35em] uppercase">
					Project Orion
				</p>
				<h1 class="max-w-3xl text-5xl leading-tight font-black tracking-tight lg:text-7xl">
					Classical language tools for deliberate reading.
				</h1>
				<p class="text-base-content/75 mt-6 max-w-2xl text-lg leading-8">
					Explore Sanskrit, Greek, and Latin with dictionary-backed lookup, morphology,
					reader context, and learner-facing explanations.
				</p>
				<div class="mt-8 flex flex-wrap gap-3">
					<a class="btn btn-primary btn-lg" href="/q">
						<Search size={20} />
						Open lookup
					</a>
					<a class="btn btn-outline btn-lg" href="/learn">
						<GraduationCap size={20} />
						Learn the grammar
					</a>
				</div>
			</div>
			<div class="border-base-300 bg-base-100/80 rounded-[2rem] border p-6 shadow-xl backdrop-blur">
				<div class="grid gap-4">
					<div class="bg-base-200 rounded-2xl p-5">
						<BookOpen class="text-primary mb-3" size={28} />
						<h2 class="text-xl font-bold">Reader-first evidence</h2>
						<p class="text-base-content/70 mt-2">
							Use lookup as a bridge back to texts, source layers, and grammatical context.
						</p>
					</div>
					<div class="bg-base-200 rounded-2xl p-5">
						<Sparkles class="text-secondary mb-3" size={28} />
						<h2 class="text-xl font-bold">Built for learners</h2>
						<p class="text-base-content/70 mt-2">
							Traditional labels are paired with practical reading questions and examples.
						</p>
					</div>
				</div>
			</div>
		</div>
	</section>
</main>
