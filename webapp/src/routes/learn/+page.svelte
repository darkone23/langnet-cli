<script lang="ts">
	import {
		ArrowRight,
		BookOpen,
		CheckCircle2,
		Flower2,
		Omega,
		ScrollText,
		Search,
		Sparkles,
		Telescope
	} from 'lucide-svelte';
	import {
		learnConceptById,
		learnConceptsForLanguage,
		learnScriptGuides,
		learnStartCards,
		learnSteps,
		practiceHref,
		sourceReferenceHref,
		type LearnConcept
	} from '$lib/learn';
	import { languageModes, type LanguageMode } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	let language = $state<LanguageMode>('san');
	let selectedConceptId = $state('case.accusative');
	let concepts = $derived(learnConceptsForLanguage(language));
	let selectedConcept = $derived(
		concepts.find((concept) => concept.id === selectedConceptId) ??
			learnConceptById(selectedConceptId)
	);
	let selectedGateways = $derived(selectedConcept.gateways[language] ?? []);
	let selectedSources = $derived(selectedConcept.sources[language] ?? []);
	let selectedPractice = $derived(
		selectedConcept.practice.filter((item) => item.language === language)
	);
	let selectedScriptGuide = $derived(learnScriptGuides[language]);

	function selectLanguage(nextLanguage: LanguageMode) {
		language = nextLanguage;
		if (
			!learnConceptsForLanguage(nextLanguage).some((concept) => concept.id === selectedConceptId)
		) {
			selectedConceptId = learnConceptsForLanguage(nextLanguage)[0]?.id ?? 'case.accusative';
		}
	}

	function languageLabel(mode: LanguageMode) {
		return languageModes.find((candidate) => candidate.id === mode)?.label ?? mode;
	}

	function languageModeIcon(mode: LanguageMode) {
		const icons = {
			san: Flower2,
			grc: Omega,
			lat: ScrollText
		};

		return icons[mode];
	}

	function conceptClass(concept: LearnConcept) {
		return concept.id === selectedConceptId
			? 'orion-learn-concept orion-learn-concept-active'
			: 'orion-learn-concept';
	}
</script>

<svelte:head>
	<title>Learn | {uiCopy.app.title}</title>
	<meta
		name="description"
		content="A Foster-first learning path for Sanskrit, Greek, and Latin morphology."
	/>
</svelte:head>

<main class="orion-page orion-learn-page bg-base-200 text-base-content min-h-screen">
	<header class="navbar border-base-300 bg-base-100 border-b px-4 lg:px-8">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-3">
				<a
					href="/"
					class="orion-home-seal grid h-10 w-10 place-items-center rounded transition-opacity hover:opacity-85"
					aria-label={uiCopy.nav.homeAria}
				>
					<Telescope size={21} />
				</a>
				<div class="min-w-0">
					<div class="truncate text-base font-semibold">{uiCopy.app.name}</div>
					<div class="text-base-content/60 truncate text-sm">Learn morphology by function.</div>
				</div>
			</div>
		</div>

		<div class="hidden items-center gap-3 md:flex">
			<a class="btn btn-sm btn-ghost" href="/">
				<Search size={15} />
				Dictionary
			</a>
			<a class="btn btn-sm btn-ghost" href="/reader">
				<BookOpen size={15} />
				Reader
			</a>
			<a class="btn btn-sm btn-primary" href="/learn">
				<Sparkles size={15} />
				Learn
			</a>
		</div>
	</header>

	<div
		class="orion-learn-shell mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[18rem_minmax(0,1fr)] lg:px-8"
	>
		<aside class="orion-learn-sidebar orion-manuscript-panel">
			<div>
				<p class="orion-learn-kicker">Foster gateway</p>
				<h1>Learn Forms</h1>
				<p>
					Start with the shape of a word, ask what job it is doing, then learn the grammar name for
					the language in front of you.
				</p>
			</div>

			<div class="tabs tabs-box w-full">
				{#each languageModes as mode}
					{@const ModeIcon = languageModeIcon(mode.id)}
					<button
						type="button"
						class={mode.id === language ? 'tab tab-active gap-2' : 'tab gap-2'}
						title={`Study ${mode.label} grammar terms`}
						onclick={() => selectLanguage(mode.id)}
					>
						<ModeIcon size={15} />
						{mode.label}
					</button>
				{/each}
			</div>

			<nav class="orion-learn-concepts" aria-label="Learning concepts">
				{#each concepts as concept}
					<button
						type="button"
						class={conceptClass(concept)}
						onclick={() => {
							selectedConceptId = concept.id;
						}}
					>
						<span>{concept.foster}</span>
						<small>{concept.traditional}</small>
					</button>
				{/each}
			</nav>
		</aside>

		<section class="orion-learn-main">
			<section class="orion-learn-foundation orion-manuscript-panel">
				<div class="orion-learn-section-head">
					<p class="orion-learn-kicker">Start here</p>
					<h2>How Ancient Forms Work</h2>
					<p>
						The first skill is not memorizing a table. It is noticing that the word ending is
						carrying a sentence job.
					</p>
				</div>

				<div class="orion-learn-start-grid">
					{#each learnStartCards as card, index}
						<article class="orion-learn-start-card">
							<span>{index + 1}</span>
							<div>
								<h3>{card.title}</h3>
								<p>{card.body}</p>
								<strong>{card.prompt}</strong>
							</div>
						</article>
					{/each}
				</div>
			</section>

			<section class="orion-learn-script orion-manuscript-panel">
				<div class="orion-learn-section-head">
					<p class="orion-learn-kicker">{selectedScriptGuide.label} script</p>
					<h2>{selectedScriptGuide.script}</h2>
					<p>{selectedScriptGuide.intro}</p>
				</div>

				<div class="orion-learn-script-grid">
					{#each selectedScriptGuide.rows as row}
						<article class="orion-learn-script-cell">
							<strong>{row.symbol}</strong>
							<span>{row.roman}</span>
							<small>{row.name}</small>
							<em>{row.note}</em>
						</article>
					{/each}
				</div>
			</section>

			<article class="orion-learn-lesson orion-manuscript-panel">
				<div class="orion-learn-lesson-head">
					<div>
						<p class="orion-learn-kicker">{languageLabel(language)} morphology</p>
						<h2>{selectedConcept.foster}</h2>
						<p>{selectedConcept.plainEnglish}</p>
					</div>
					<span class="orion-learn-kind">{selectedConcept.kind}</span>
				</div>

				<div class="orion-learn-question">
					<span>Reader question</span>
					<strong>{selectedConcept.readerQuestion}</strong>
				</div>

				<div class="orion-learn-grid">
					<section class="orion-learn-panel">
						<h3>Native Grammar</h3>
						<div class="orion-learn-native-list">
							{#each selectedGateways as gateway}
								<div class="orion-learn-native">
									<span>{gateway.label}</span>
									<strong>{gateway.term}</strong>
									{#if gateway.role}<em>{gateway.role}</em>{/if}
								</div>
							{/each}
						</div>
					</section>

					<section class="orion-learn-panel">
						<h3>Table Cue</h3>
						<p>{selectedConcept.tableCue}</p>
					</section>
				</div>

				<section class="orion-learn-sources">
					<div class="orion-learn-section-head">
						<h3>Source Tradition</h3>
						<p>Native grammar references for the terms shown above.</p>
					</div>
					<div class="orion-learn-source-list">
						{#each selectedSources as source}
							<a class="orion-learn-source" href={sourceReferenceHref(source)}>
								<span>{source.segment ? `segment ${source.segment}` : 'work anchor'}</span>
								<strong>{source.label}</strong>
								<small>{source.note}</small>
								<em>{source.canonicalId}</em>
							</a>
						{/each}
					</div>
				</section>

				<section class="orion-learn-practice">
					<div class="orion-learn-section-head">
						<h3>Try A Source Word</h3>
						<p>Open a live lookup, read the first form card, then come back to the question.</p>
					</div>
					<div class="orion-learn-practice-list">
						{#each selectedPractice as item}
							<a class="orion-learn-practice-card" href={practiceHref(item)}>
								<span>{languageLabel(item.language)}</span>
								<strong>{item.word}</strong>
								<small>{item.gloss}</small>
								<em>{item.note}</em>
								<ArrowRight size={15} />
							</a>
						{/each}
					</div>
				</section>
			</article>

			<section class="orion-learn-steps orion-manuscript-panel">
				<div class="orion-learn-section-head">
					<h2>Reading Routine</h2>
					<p>A compact loop for turning a form into understanding.</p>
				</div>
				<div class="orion-learn-step-list">
					{#each learnSteps as step, index}
						<article class="orion-learn-step">
							<span>{index + 1}</span>
							<div>
								<h3>{step.title}</h3>
								<p>{step.body}</p>
							</div>
							<CheckCircle2 size={16} />
						</article>
					{/each}
				</div>
			</section>
		</section>
	</div>
</main>
