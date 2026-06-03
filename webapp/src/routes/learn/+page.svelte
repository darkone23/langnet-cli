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

<style>
	.orion-learn-page {
		font-family: var(--font-sans);
	}

	.orion-learn-shell {
		align-items: start;
	}

	.orion-learn-sidebar,
	.orion-learn-foundation,
	.orion-learn-script,
	.orion-learn-lesson,
	.orion-learn-steps {
		display: grid;
		gap: 1rem;
		padding: 1rem;
	}

	.orion-learn-sidebar {
		position: sticky;
		top: 1rem;
	}

	.orion-learn-sidebar h1,
	.orion-learn-foundation h2,
	.orion-learn-script h2,
	.orion-learn-lesson h2,
	.orion-learn-steps h2 {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-family: var(--font-serif);
		font-weight: 760;
		line-height: 1.12;
	}

	.orion-learn-sidebar h1 {
		font-size: clamp(2rem, 5vw, 3rem);
	}

	.orion-learn-foundation h2,
	.orion-learn-script h2 {
		font-size: clamp(1.8rem, 3.4vw, 2.65rem);
	}

	.orion-learn-lesson h2 {
		font-size: clamp(2.2rem, 5vw, 4rem);
	}

	.orion-learn-steps h2 {
		font-size: clamp(1.65rem, 3vw, 2.35rem);
	}

	.orion-learn-sidebar p,
	.orion-learn-foundation p,
	.orion-learn-script p,
	.orion-learn-lesson-head p,
	.orion-learn-section-head p,
	.orion-learn-panel p,
	.orion-learn-step p {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 64%, transparent);
		font-family: var(--font-serif);
		line-height: 1.65;
	}

	.orion-learn-kicker,
	.orion-learn-kind,
	.orion-learn-question span,
	.orion-learn-native span,
	.orion-learn-source span,
	.orion-learn-practice-card span,
	.orion-learn-script-cell span {
		color: color-mix(in oklab, var(--color-base-content) 50%, transparent);
		font-size: 0.72rem;
		font-variant-caps: small-caps;
		font-weight: 780;
		letter-spacing: 0;
		line-height: 1.15;
	}

	.orion-learn-kicker {
		margin: 0 0 0.35rem;
	}

	.orion-learn-concepts {
		display: grid;
		gap: 0.45rem;
	}

	.orion-learn-concept {
		display: grid;
		gap: 0.16rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.65rem 0.75rem;
		text-align: left;
		transition:
			border-color 160ms ease,
			background 160ms ease,
			transform 160ms ease;
	}

	.orion-learn-concept:hover,
	.orion-learn-concept-active {
		border-color: color-mix(in oklab, var(--color-secondary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 7%);
		transform: translateY(-1px);
	}

	.orion-learn-concept span {
		color: color-mix(in oklab, var(--color-base-content) 78%, var(--color-secondary));
		font-family: var(--font-serif);
		font-weight: 740;
		line-height: 1.25;
	}

	.orion-learn-concept small {
		color: color-mix(in oklab, var(--color-base-content) 56%, transparent);
		font-size: 0.78rem;
		line-height: 1.3;
	}

	.orion-learn-main {
		display: grid;
		gap: 1rem;
		min-width: 0;
	}

	.orion-learn-start-grid {
		display: grid;
		gap: 0.75rem;
		grid-template-columns: repeat(4, minmax(0, 1fr));
	}

	.orion-learn-start-card {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 0.65rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 91%, var(--color-primary) 4%);
		padding: 0.85rem;
	}

	.orion-learn-start-card > span {
		display: grid;
		width: 1.85rem;
		height: 1.85rem;
		place-items: center;
		border-radius: 50%;
		background: color-mix(in oklab, var(--color-primary) 78%, var(--color-secondary));
		color: var(--color-primary-content);
		font-size: 0.8rem;
		font-weight: 800;
	}

	.orion-learn-start-card h3,
	.orion-learn-script-cell small {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 1.02rem;
		font-weight: 740;
		line-height: 1.22;
	}

	.orion-learn-start-card strong {
		display: block;
		margin-top: 0.45rem;
		color: color-mix(in oklab, var(--color-base-content) 76%, var(--color-secondary));
		font-size: 0.86rem;
		font-weight: 750;
		line-height: 1.35;
	}

	.orion-learn-script-grid {
		display: grid;
		gap: 0.6rem;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
	}

	.orion-learn-script-cell {
		display: grid;
		gap: 0.12rem;
		min-height: 7.25rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-accent) 5%);
		padding: 0.75rem;
	}

	.orion-learn-script-cell strong {
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-accent));
		font-family: var(--font-reader);
		font-size: 1.55rem;
		font-weight: 760;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}

	.orion-learn-script-cell small {
		font-size: 0.9rem;
	}

	.orion-learn-script-cell em {
		color: color-mix(in oklab, var(--color-base-content) 54%, transparent);
		font-size: 0.78rem;
		font-style: normal;
		line-height: 1.35;
	}

	.orion-learn-lesson-head {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 1rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		padding-bottom: 1rem;
	}

	.orion-learn-kind {
		align-self: start;
		border: 1px solid color-mix(in oklab, var(--color-accent) 30%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-accent) 8%);
		padding: 0.28rem 0.55rem;
	}

	.orion-learn-question {
		display: grid;
		gap: 0.25rem;
		border-left: 0.22rem solid color-mix(in oklab, var(--color-secondary) 58%, var(--color-accent));
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 5%);
		padding: 0.8rem 1rem;
	}

	.orion-learn-question strong {
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-secondary));
		font-family: var(--font-serif);
		font-size: clamp(1.2rem, 2.4vw, 1.65rem);
		line-height: 1.35;
	}

	.orion-learn-grid {
		display: grid;
		gap: 0.75rem;
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.orion-learn-panel {
		display: grid;
		gap: 0.65rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.85rem;
	}

	.orion-learn-panel h3,
	.orion-learn-section-head h3,
	.orion-learn-step h3 {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 80%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 1.08rem;
		font-weight: 740;
		line-height: 1.25;
	}

	.orion-learn-native-list,
	.orion-learn-source-list,
	.orion-learn-practice-list,
	.orion-learn-step-list {
		display: grid;
		gap: 0.55rem;
	}

	.orion-learn-native {
		display: grid;
		gap: 0.18rem;
		border-left: 0.15rem solid color-mix(in oklab, var(--color-accent) 48%, var(--color-base-300));
		padding-left: 0.6rem;
	}

	.orion-learn-native strong {
		color: color-mix(in oklab, var(--color-base-content) 80%, var(--color-accent));
		font-family: var(--font-reader);
		font-size: 1.08rem;
		line-height: 1.3;
		overflow-wrap: anywhere;
	}

	.orion-learn-native em {
		color: color-mix(in oklab, var(--color-base-content) 54%, transparent);
		font-style: normal;
		line-height: 1.3;
	}

	.orion-learn-sources {
		display: grid;
		gap: 0.65rem;
	}

	.orion-learn-source {
		display: grid;
		gap: 0.16rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid
			color-mix(in oklab, var(--color-secondary) 48%, var(--color-base-300));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 91%, var(--color-secondary) 4%);
		padding: 0.65rem 0.75rem;
		text-decoration: none;
	}

	.orion-learn-source:hover {
		border-color: color-mix(in oklab, var(--color-secondary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 7%);
	}

	.orion-learn-source strong {
		color: color-mix(in oklab, var(--color-base-content) 80%, var(--color-secondary));
		font-family: var(--font-serif);
		font-size: 1rem;
		line-height: 1.3;
	}

	.orion-learn-source small {
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-size: 0.82rem;
		line-height: 1.35;
	}

	.orion-learn-source em {
		color: color-mix(in oklab, var(--color-base-content) 48%, transparent);
		font-family: var(--font-serif);
		font-size: 0.72rem;
		font-style: normal;
		line-height: 1.3;
		overflow-wrap: anywhere;
	}

	.orion-learn-practice {
		display: grid;
		gap: 0.65rem;
	}

	.orion-learn-section-head {
		display: grid;
		gap: 0.22rem;
	}

	.orion-learn-practice-list {
		grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	}

	.orion-learn-practice-card {
		position: relative;
		display: grid;
		gap: 0.18rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-accent) 5%);
		padding: 0.75rem 2.1rem 0.75rem 0.8rem;
		text-decoration: none;
		transition:
			border-color 160ms ease,
			background 160ms ease,
			transform 160ms ease;
	}

	.orion-learn-practice-card:hover {
		border-color: color-mix(in oklab, var(--color-secondary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 7%);
		transform: translateY(-1px);
	}

	.orion-learn-practice-card strong {
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: 1.34rem;
		line-height: 1.18;
		overflow-wrap: anywhere;
	}

	.orion-learn-practice-card small {
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-size: 0.82rem;
		line-height: 1.3;
	}

	.orion-learn-practice-card em {
		color: color-mix(in oklab, var(--color-base-content) 50%, var(--color-accent));
		font-size: 0.76rem;
		font-style: normal;
		line-height: 1.3;
	}

	:global(.orion-learn-practice-card svg) {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		color: color-mix(in oklab, var(--color-base-content) 52%, var(--color-secondary));
	}

	.orion-learn-step-list {
		grid-template-columns: repeat(4, minmax(0, 1fr));
	}

	.orion-learn-step {
		position: relative;
		display: grid;
		gap: 0.45rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.8rem;
	}

	.orion-learn-step > span {
		display: grid;
		width: 1.7rem;
		height: 1.7rem;
		place-items: center;
		border-radius: 50%;
		background: color-mix(in oklab, var(--color-secondary) 82%, var(--color-primary));
		color: var(--color-secondary-content);
		font-size: 0.78rem;
		font-weight: 800;
	}

	:global(.orion-learn-step svg) {
		position: absolute;
		right: 0.7rem;
		top: 0.7rem;
		color: color-mix(in oklab, var(--color-success) 70%, var(--color-base-content));
	}

	@media (max-width: 48rem) {
		.orion-learn-sidebar {
			position: static;
		}

		.orion-learn-grid,
		.orion-learn-start-grid,
		.orion-learn-step-list {
			grid-template-columns: 1fr;
		}
	}
</style>
