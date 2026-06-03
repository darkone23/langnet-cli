<script lang="ts">
	import { Feather, Flower2, Omega, Search, ScrollText } from 'lucide-svelte';
	import DeskSearchReading from '$lib/DeskSearchReading.svelte';
	import { languageModes, type LanguageMode } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type SearchReading = {
		label: string;
		value: string;
	};

	type Props = {
		language: LanguageMode;
		query: string;
		loading: boolean;
		statusDetail: string;
		searchRomanization: SearchReading | null;
		languageLabel: (mode: LanguageMode) => string;
		onSelectLanguage: (mode: LanguageMode) => void;
		onQueryInput: (value: string) => void;
		onSubmit: (event: SubmitEvent) => void;
		onClear: () => void;
	};

	let {
		language,
		query,
		loading,
		statusDetail,
		searchRomanization,
		languageLabel,
		onSelectLanguage,
		onQueryInput,
		onSubmit,
		onClear
	}: Props = $props();

	function languageModeIcon(mode: LanguageMode) {
		const icons = {
			san: Flower2,
			grc: Omega,
			lat: ScrollText
		};

		return icons[mode];
	}
</script>

<section class="hero orion-manuscript-panel">
	<div class="hero-content block w-full p-6 lg:p-8">
		<div class="max-w-3xl">
			<div class="badge badge-secondary badge-outline mb-4 gap-2">
				<Feather size={14} />
				{uiCopy.hero.badge}
			</div>
			<h1 class="font-serif text-4xl leading-tight md:text-5xl">
				{uiCopy.hero.title(language)}
			</h1>
			<p class="text-base-content/70 mt-4 max-w-2xl font-serif text-xl leading-8">
				{uiCopy.hero.intro}
			</p>
		</div>

		<div class="mt-6">
			<div class="tabs tabs-box w-full md:w-auto">
				{#each languageModes as mode}
					{@const ModeIcon = languageModeIcon(mode.id)}
					<button
						type="button"
						class={mode.id === language ? 'tab tab-active gap-2' : 'tab gap-2'}
						title={`Set the desk for ${mode.label}`}
						onclick={() => onSelectLanguage(mode.id)}
					>
						<ModeIcon size={15} />
						{mode.label}
					</button>
				{/each}
			</div>
		</div>

		<form class="mt-6" onsubmit={onSubmit}>
			<div class="join w-full">
				<label class="input input-lg join-item flex-1">
					<Search size={20} class="text-base-content/50" />
					<input
						value={query}
						type="search"
						placeholder={uiCopy.search.placeholder(languageLabel(language))}
						aria-label={uiCopy.search.inputAria}
						autocomplete="off"
						disabled={loading}
						oninput={(event) => onQueryInput(event.currentTarget.value)}
					/>
				</label>
				<button class="btn btn-neutral btn-lg join-item" disabled={loading}>
					{#if loading}
						<span class="loading loading-spinner loading-sm"></span>
					{:else}
						<Search size={17} />
					{/if}
					<span class="hidden sm:inline">{uiCopy.search.button(loading)}</span>
				</button>
			</div>
			{#if searchRomanization}
				<DeskSearchReading label={searchRomanization.label} value={searchRomanization.value} />
			{/if}

			<div class="mt-4 flex flex-wrap items-center gap-3">
				<button type="button" class="btn btn-ghost btn-sm" disabled={loading} onclick={onClear}>
					{uiCopy.search.clear}
				</button>
				<span class={loading ? 'loading loading-spinner loading-sm' : 'hidden'}></span>
				<span class="text-base-content/60 text-sm" role="status" aria-live="polite">
					{statusDetail}
				</span>
			</div>
		</form>
	</div>
</section>
