<script lang="ts">
	import { BookOpen, RefreshCw, Search, Sparkles } from 'lucide-svelte';
	import DeskMotdSkeletonList from '$lib/desk/DeskMotdSkeletonList.svelte';
	import type { WordRecommendationItem, WordRecommendationResult } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type MotdWarning = {
		message: string;
	};

	type Props = {
		motd: WordRecommendationResult | null;
		items: WordRecommendationItem[];
		visibleWarnings: MotdWarning[];
		pending: boolean;
		refreshing: boolean;
		error: string;
		linksLoad: boolean;
		skeletonRows: readonly number[];
		languageLabel: (language: WordRecommendationItem['language']) => string;
		isActiveMotd: (item: WordRecommendationItem) => boolean;
		motdHref: (item: WordRecommendationItem) => string;
		motdWordClass: (item: WordRecommendationItem) => string;
		motdWordLang: (item: WordRecommendationItem) => string;
		motdDisplayWord: (item: WordRecommendationItem) => string;
		motdDisplayLookup: (item: WordRecommendationItem) => string;
		motdDisplayGloss: (item: WordRecommendationItem) => string;
		motdDisplayNote: (item: WordRecommendationItem) => string;
		onToggleLinksLoad: () => void;
		onRefresh: () => void;
		onNavigate: (event: MouseEvent, item: WordRecommendationItem) => void;
	};

	let {
		motd,
		items,
		visibleWarnings,
		pending,
		refreshing,
		error,
		linksLoad,
		skeletonRows,
		languageLabel,
		isActiveMotd,
		motdHref,
		motdWordClass,
		motdWordLang,
		motdDisplayWord,
		motdDisplayLookup,
		motdDisplayGloss,
		motdDisplayNote,
		onToggleLinksLoad,
		onRefresh,
		onNavigate
	}: Props = $props();
</script>

<section class="card orion-manuscript-panel orion-motd-folio">
	<div class="card-body gap-5 p-5 lg:p-6">
		<div class="orion-motd-folio-head">
			<div class="orion-motd-folio-title">
				<span class="orion-motd-emblem" aria-hidden="true">
					<BookOpen size={18} />
					<Sparkles size={12} />
				</span>
				<div>
					<h2 class="card-title text-lg">{uiCopy.margin.title}</h2>
					<p class="text-base-content/65 font-serif text-sm leading-6">
						{uiCopy.margin.intro}
						{#if !pending}
							{uiCopy.margin.linkMode(linksLoad)}
						{/if}
					</p>
				</div>
			</div>

			<div class="orion-motd-actions">
				{#if pending}
					<span
						class="orion-motd-control-skeleton orion-motd-control-skeleton-load"
						aria-hidden="true"
					></span>
					<span
						class="orion-motd-control-skeleton orion-motd-control-skeleton-refresh"
						aria-hidden="true"
					></span>
				{:else}
					<button
						type="button"
						class={linksLoad ? 'btn btn-xs btn-secondary' : 'btn btn-xs'}
						disabled={refreshing}
						title={uiCopy.margin.loadTitle}
						onclick={onToggleLinksLoad}
					>
						<Search size={13} />
						{uiCopy.margin.linkToggle(linksLoad)}
					</button>
					<button
						type="button"
						class="btn btn-xs"
						disabled={refreshing}
						title={uiCopy.margin.refreshTitle}
						onclick={onRefresh}
					>
						{#if refreshing}
							<span class="loading loading-spinner loading-xs"></span>
						{:else}
							<RefreshCw size={13} />
						{/if}
						{uiCopy.margin.refresh}
					</button>
				{/if}
			</div>
		</div>

		{#if pending}
			<DeskMotdSkeletonList rows={skeletonRows} />
		{:else if motd}
			{#if items.length}
				<div
					class={refreshing ? 'orion-motd-list orion-motd-list-refreshing' : 'orion-motd-list'}
					aria-busy={refreshing}
				>
					{#each items as item}
						{@const activeMotd = isActiveMotd(item)}
						<a
							class={activeMotd ? 'orion-motd-link orion-motd-link-active' : 'orion-motd-link'}
							href={motdHref(item)}
							aria-current={activeMotd ? 'page' : undefined}
							onclick={(event) => onNavigate(event, item)}
						>
							<span class="orion-motd-lang">{languageLabel(item.language)}</span>
							<span class={motdWordClass(item)} lang={motdWordLang(item)}>
								<span>{motdDisplayWord(item)}</span>
								{#if motdDisplayLookup(item)}
									<span class="orion-motd-lookup">{motdDisplayLookup(item)}</span>
								{/if}
							</span>
							<span class="orion-motd-gloss">{motdDisplayGloss(item)}</span>
							<span class="orion-motd-note">{motdDisplayNote(item)}</span>
							<span class="orion-motd-action">
								{uiCopy.margin.cardAction(item.language, linksLoad)}
							</span>
							{#if item.ambiguity.has_multiple_lexemes}
								<span class="orion-motd-caveat">{uiCopy.margin.multipleAnchors}</span>
							{/if}
							{#if item.novelty?.is_repeat}
								<span class="orion-motd-caveat">{uiCopy.margin.repeat}</span>
							{/if}
							{#if activeMotd}
								<span class="orion-motd-active-label">{uiCopy.margin.active}</span>
							{/if}
						</a>
					{/each}
				</div>
			{/if}

			{#if error}
				<div class="orion-motd-warning">
					{error}
				</div>
			{/if}
			{#if refreshing}
				<div class="orion-motd-warning">
					{uiCopy.margin.refreshingPrevious}
				</div>
			{/if}
			{#if visibleWarnings.length}
				<div class="orion-motd-warning">
					{visibleWarnings[0].message}
				</div>
			{/if}
			{#if motd.exhaustion?.fresh_requested && !motd.exhaustion.fresh_satisfied}
				<div class="orion-motd-warning">
					{motd.exhaustion.reason || uiCopy.margin.noFreshWord}
				</div>
			{/if}
		{:else if error}
			<div class="alert alert-warning text-sm">{error}</div>
		{/if}
	</div>
</section>

<style>
	.orion-motd-list {
		display: grid;
		gap: 0.45rem;
	}

	.orion-motd-folio {
		overflow: hidden;
	}

	.orion-motd-folio-head {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		align-items: flex-start;
		justify-content: space-between;
	}

	.orion-motd-folio-title {
		display: flex;
		min-width: 0;
		max-width: 38rem;
		gap: 0.8rem;
		align-items: flex-start;
	}

	.orion-motd-emblem {
		position: relative;
		display: grid;
		width: 2.45rem;
		height: 2.45rem;
		flex: 0 0 auto;
		place-items: center;
		border: 1px double color-mix(in oklab, var(--color-accent) 48%, var(--color-base-300));
		border-radius: 0.35rem;
		background:
			linear-gradient(
				135deg,
				color-mix(in oklab, var(--color-base-100) 88%, var(--color-primary) 5%),
				color-mix(in oklab, var(--color-base-100) 78%, var(--color-accent) 8%)
			),
			var(--color-base-100);
		color: color-mix(in oklab, var(--color-base-content) 70%, var(--color-secondary));
		box-shadow:
			inset 0 0 0 0.18rem color-mix(in oklab, var(--color-base-100) 62%, transparent),
			0 0.2rem 0.8rem color-mix(in oklab, var(--color-base-content) 8%, transparent);
	}

	:global(.orion-motd-emblem svg:last-child) {
		position: absolute;
		right: 0.18rem;
		bottom: 0.18rem;
		color: color-mix(in oklab, var(--color-primary) 64%, var(--color-accent));
	}

	.orion-motd-folio .orion-motd-list {
		grid-template-columns: repeat(auto-fit, minmax(13.5rem, 1fr));
		gap: 0.7rem;
	}

	.orion-motd-folio .orion-motd-link {
		min-height: 8.15rem;
		grid-template-columns: minmax(0, 1fr);
		align-content: start;
		gap: 0.2rem;
		padding: 0.75rem 0.82rem;
	}

	.orion-motd-folio .orion-motd-gloss {
		justify-self: start;
		max-width: none;
		font-size: 0.86rem;
		text-align: left;
	}

	.orion-motd-folio .orion-motd-note {
		margin-top: 0.12rem;
	}

	.orion-motd-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		align-items: center;
	}

	:global(.orion-motd-actions .btn) {
		font-family: var(--font-serif);
		font-size: 0.72rem;
		font-variant-caps: small-caps;
		letter-spacing: 0;
	}

	.orion-motd-control-skeleton {
		position: relative;
		display: block;
		overflow: hidden;
		height: 1.5rem;
		border-radius: var(--radius-selector);
		background: color-mix(in oklab, var(--color-base-content) 10%, var(--color-base-200));
		animation: orion-motd-line 1.65s ease-in-out infinite;
	}

	.orion-motd-control-skeleton::after {
		position: absolute;
		inset: -60%;
		background: radial-gradient(
			circle at 50% 50%,
			color-mix(in oklab, var(--color-secondary) 16%, transparent),
			transparent 58%
		);
		content: '';
		animation: orion-motd-blob 1.7s ease-in-out infinite;
	}

	.orion-motd-control-skeleton-load {
		width: 4.7rem;
	}

	.orion-motd-control-skeleton-refresh {
		width: 4.25rem;
		animation-delay: 0.16s;
	}

	.orion-motd-link {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.12rem 0.7rem;
		overflow: hidden;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid
			color-mix(in oklab, var(--color-accent) 30%, var(--color-base-content));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 96%, var(--color-base-200));
		padding: 0.55rem 0.65rem;
		color: var(--color-base-content);
		text-decoration: none;
		transition:
			border-color 140ms ease,
			background-color 140ms ease,
			transform 140ms ease;
	}

	.orion-motd-link:hover {
		border-color: color-mix(in oklab, var(--color-secondary) 34%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-accent) 4%);
		transform: translateY(-1px);
	}

	.orion-motd-link-active {
		border-color: color-mix(in oklab, var(--color-secondary) 38%, var(--color-base-content));
		border-left-color: color-mix(in oklab, var(--color-primary) 54%, var(--color-accent));
		background: color-mix(in oklab, var(--color-base-100) 89%, var(--color-secondary) 6%);
		box-shadow: inset 0.14rem 0 0 color-mix(in oklab, var(--color-primary) 52%, var(--color-accent));
	}

	.orion-motd-list-refreshing .orion-motd-link {
		animation: orion-motd-refresh-card 1.8s ease-in-out infinite;
	}

	.orion-motd-list-refreshing .orion-motd-link::after {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			105deg,
			transparent 0%,
			color-mix(in oklab, var(--color-accent) 12%, transparent) 38%,
			color-mix(in oklab, var(--color-secondary) 10%, transparent) 50%,
			transparent 64%
		);
		content: '';
		pointer-events: none;
		transform: translateX(-115%);
		animation: orion-motd-refresh-gloss 1.8s ease-in-out infinite;
	}

	.orion-motd-lang {
		color: color-mix(in oklab, var(--color-base-content) 52%, transparent);
		font-size: 0.68rem;
		font-weight: 700;
		line-height: 1.1;
		text-transform: uppercase;
	}

	.orion-motd-word {
		grid-column: 1;
		display: inline-flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.28rem;
		min-width: 0;
		overflow-wrap: anywhere;
		font-family: var(--font-reader);
		font-kerning: normal;
		font-size: 1.08rem;
		font-weight: 700;
		line-height: 1.15;
	}

	.orion-motd-word-grc {
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-secondary));
		font-size: 1.2rem;
		font-weight: 600;
		line-height: 1.05;
		text-wrap: balance;
	}

	.orion-motd-word-san {
		padding-top: 0.06rem;
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-size: 1.22rem;
		font-weight: 600;
		line-height: 1.28;
		text-wrap: balance;
	}

	.orion-motd-word-grc > span:first-child {
		padding-bottom: 0.05rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-accent) 28%, transparent);
	}

	.orion-motd-word-san > span:first-child {
		transform: translateY(0.03rem);
		padding-bottom: 0.05rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-primary) 24%, transparent);
	}

	.orion-motd-lookup {
		color: color-mix(in oklab, var(--color-base-content) 42%, transparent);
		font-family: var(--font-serif);
		font-size: 0.66rem;
		font-style: italic;
		font-weight: 600;
		line-height: 1;
	}

	.orion-motd-gloss {
		align-self: start;
		justify-self: end;
		max-width: 8.25rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-reader);
		font-kerning: normal;
		font-size: 0.78rem;
		line-height: 1.25;
		text-align: right;
	}

	.orion-motd-note {
		grid-column: 1 / -1;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.72rem;
		line-height: 1.35;
	}

	.orion-motd-action {
		grid-column: 1 / -1;
		margin-top: 0.08rem;
		color: color-mix(in oklab, var(--color-base-content) 64%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.68rem;
		font-style: italic;
		font-weight: 700;
		line-height: 1.25;
	}

	.orion-motd-caveat,
	.orion-motd-active-label {
		justify-self: start;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.08rem 0.42rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.64rem;
		font-weight: 700;
		line-height: 1.2;
		text-transform: uppercase;
	}

	.orion-motd-active-label {
		color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-primary));
	}
</style>
