<script lang="ts">
	import { BookOpen, Moon, Sparkles, Sun, Telescope } from 'lucide-svelte';
	import type { LanguageMode, TranslationMode } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		theme: 'manuscript' | 'vespers';
		language: LanguageMode;
		translationMode: TranslationMode;
		enrichingTranslations: boolean;
		languageLabel: (mode: LanguageMode) => string;
		statusLabel: string;
		onHomeNavigation: (event: MouseEvent) => void;
		onTranslationModeChange: (mode: TranslationMode) => void;
		onSetTheme: (theme: 'manuscript' | 'vespers') => void;
	};

	let {
		theme,
		language,
		translationMode,
		enrichingTranslations,
		languageLabel,
		statusLabel,
		onHomeNavigation,
		onTranslationModeChange,
		onSetTheme
	}: Props = $props();

	function handleTranslationModeChange(event: Event) {
		onTranslationModeChange((event.currentTarget as HTMLSelectElement).value as TranslationMode);
	}
</script>

<header class="navbar border-base-300 bg-base-100 border-b px-4 lg:px-8">
	<div class="min-w-0 flex-1">
		<div class="flex items-center gap-3">
			<a
				href="/"
				class="orion-home-seal grid h-10 w-10 place-items-center rounded transition-opacity hover:opacity-85"
				aria-label={uiCopy.nav.homeAria}
				onclick={onHomeNavigation}
			>
				<Telescope size={21} />
			</a>
			<div class="min-w-0">
				<div class="truncate text-base font-semibold">{uiCopy.app.name}</div>
				<div class="text-base-content/60 truncate text-sm">
					{uiCopy.app.motto}
				</div>
			</div>
		</div>
	</div>

	<div class="hidden items-center gap-3 md:flex">
		<a class="btn btn-sm btn-ghost" href="/reader">
			<BookOpen size={15} />
			Reader
		</a>
		<a class="btn btn-sm btn-ghost" href="/learn">
			<Sparkles size={15} />
			Learn
		</a>

		<label class="orion-topbar-control">
			<span>{uiCopy.readerLayer.label}</span>
			<select
				class="select select-xs border-base-300 bg-base-100"
				aria-label={uiCopy.readerLayer.modeAria}
				value={translationMode}
				onchange={handleTranslationModeChange}
			>
				<option value="auto">auto</option>
				<option value="cache">cache</option>
				<option value="off">off</option>
				<option value="populate">populate</option>
			</select>
			{#if enrichingTranslations}
				<span class="loading loading-spinner loading-xs" aria-label={uiCopy.readerLayer.loadingAria}
				></span>
			{/if}
		</label>

		<div class="stats stats-horizontal border-base-300 bg-base-100 border shadow-none">
			<div class="stat px-4 py-2">
				<div class="stat-title text-xs">{uiCopy.nav.languageStat}</div>
				<div class="stat-value text-lg">{languageLabel(language)}</div>
			</div>
			<div class="stat px-4 py-2">
				<div class="stat-title text-xs">{uiCopy.nav.statusStat}</div>
				<div class="stat-value text-lg">{statusLabel}</div>
			</div>
		</div>

		<div class="join">
			<button
				type="button"
				class={theme === 'manuscript' ? 'btn btn-sm join-item btn-primary' : 'btn btn-sm join-item'}
				aria-label={uiCopy.theme.readerAria}
				onclick={() => onSetTheme('manuscript')}
			>
				<Sun size={16} />
				<span class="hidden lg:inline">{uiCopy.theme.reader}</span>
			</button>
			<button
				type="button"
				class={theme === 'vespers' ? 'btn btn-sm join-item btn-primary' : 'btn btn-sm join-item'}
				aria-label={uiCopy.theme.nightAria}
				onclick={() => onSetTheme('vespers')}
			>
				<Moon size={16} />
				<span class="hidden lg:inline">{uiCopy.theme.night}</span>
			</button>
		</div>
	</div>
</header>

<style>
	.orion-home-seal {
		border: 1px solid color-mix(in oklab, var(--color-accent) 54%, var(--color-base-content));
		background: color-mix(in oklab, var(--color-primary) 82%, var(--color-accent));
		color: var(--color-primary-content);
		box-shadow:
			inset 0 0 0 1px color-mix(in oklab, var(--color-base-100) 18%, transparent),
			0 0.2rem 0 color-mix(in oklab, var(--color-secondary) 18%, transparent);
	}

	.orion-home-seal :global(svg) {
		filter: drop-shadow(0 1px 0 color-mix(in oklab, var(--color-base-content) 20%, transparent));
	}

	.orion-topbar-control {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		border: 1px solid var(--color-base-300);
		border-radius: var(--radius-field);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.32rem 0.45rem 0.32rem 0.55rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-family: var(--font-serif);
		font-size: 0.78rem;
		font-variant-caps: small-caps;
		letter-spacing: 0;
	}

	.orion-topbar-control select {
		min-height: 1.55rem;
		height: 1.55rem;
		padding-inline: 0.45rem 1.45rem;
		font-family: var(--font-sans);
		font-size: 0.76rem;
		font-variant-caps: normal;
	}
</style>
