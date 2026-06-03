<script lang="ts">
	import { BookOpen, Moon, Search, Sun, Telescope } from 'lucide-svelte';
	import ReaderAddressLookup from './ReaderAddressLookup.svelte';
	import { languageModes, type LanguageMode } from './search-data';
	import { uiCopy } from './ui-copy';

	type ReaderTheme = 'manuscript' | 'vespers';

	type Props = {
		theme: ReaderTheme;
		language: LanguageMode;
		indexSummaryLabel: string;
		catalogError: string;
		showAddressLookup: boolean;
		addressInput: string;
		segmentLoading: boolean;
		catalogReady: boolean;
		onThemeSelect: (theme: ReaderTheme) => void;
		onLanguageSelect: (language: LanguageMode) => void;
		onAddressInput: (value: string) => void;
		onOpenAddress: () => void;
		onCloseLookup: () => void;
		onShowLookup: () => void;
	};

	let {
		theme,
		language,
		indexSummaryLabel,
		catalogError,
		showAddressLookup,
		addressInput,
		segmentLoading,
		catalogReady,
		onThemeSelect,
		onLanguageSelect,
		onAddressInput,
		onOpenAddress,
		onCloseLookup,
		onShowLookup
	}: Props = $props();
</script>

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
				<div class="text-base-content/60 truncate text-sm">Reader Desk</div>
			</div>
		</div>
	</div>

	<div class="flex items-center gap-2">
		<a class="btn btn-sm btn-ghost hidden sm:inline-flex" href="/">
			<Search size={15} />
			Dictionary
		</a>
		<div class="join">
			<button
				type="button"
				class={theme === 'manuscript' ? 'btn btn-sm join-item btn-primary' : 'btn btn-sm join-item'}
				aria-label={uiCopy.theme.readerAria}
				onclick={() => onThemeSelect('manuscript')}
			>
				<Sun size={16} />
			</button>
			<button
				type="button"
				class={theme === 'vespers' ? 'btn btn-sm join-item btn-primary' : 'btn btn-sm join-item'}
				aria-label={uiCopy.theme.nightAria}
				onclick={() => onThemeSelect('vespers')}
			>
				<Moon size={16} />
			</button>
		</div>
	</div>
</header>

<div class="orion-manuscript-panel p-5 lg:p-6">
	<div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
		<div class="min-w-0">
			<div class="badge badge-secondary badge-outline mb-3 gap-2">
				<BookOpen size={14} />
				Unified reader
			</div>
			<h1 class="font-serif text-3xl leading-tight md:text-4xl">Reader Desk</h1>
			<p class="text-base-content/68 mt-3 max-w-2xl font-serif text-lg leading-7">
				A common desk for Sanskrit, Greek, and Latin: read the text, find the form, and follow the
				lesson through the sources.
			</p>
		</div>

		<div class="grid gap-3 sm:min-w-80">
			<div class="tabs tabs-box">
				{#each languageModes as mode}
					<button
						type="button"
						class={mode.id === language ? 'tab tab-active' : 'tab'}
						onclick={() => onLanguageSelect(mode.id)}
					>
						{mode.label}
					</button>
				{/each}
			</div>
			<p class="text-base-content/55 font-serif text-sm">
				{indexSummaryLabel}
			</p>
			{#if catalogError}
				<p class="text-error text-sm">{catalogError}</p>
			{/if}
		</div>
	</div>

	<ReaderAddressLookup
		showing={showAddressLookup}
		{addressInput}
		placeholder={language === 'grc' ? 'Od. 3.74' : 'Reader address'}
		{segmentLoading}
		canOpen={catalogReady}
		{onAddressInput}
		{onOpenAddress}
		{onCloseLookup}
		{onShowLookup}
	/>
</div>
