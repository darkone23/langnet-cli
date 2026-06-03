<script lang="ts">
	import { Eraser } from 'lucide-svelte';
	import type { LanguageMode } from '$lib/search-data';
	import type { WordIndexItem } from '$lib/word-index';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		items: WordIndexItem[];
		wordIndexHref: (item: WordIndexItem) => string;
		wordIndexDisplay: (item: WordIndexItem) => string;
		languageLabel: (language: LanguageMode) => string;
		onClear: () => void;
		onNavigate: (event: MouseEvent, item: WordIndexItem) => void;
	};

	let { items, wordIndexHref, wordIndexDisplay, languageLabel, onClear, onNavigate }: Props =
		$props();
</script>

{#if items.length}
	<div class="orion-earmarks">
		<div class="orion-earmarks-head">
			<div class="orion-earmarks-title">{uiCopy.wordIndex.earmarks}</div>
			<button
				type="button"
				class="orion-earmarks-clear"
				title={uiCopy.wordIndex.clearEarmarksTitle}
				onclick={onClear}
			>
				<Eraser size={12} />
				{uiCopy.wordIndex.clearEarmarks}
			</button>
		</div>
		<div class="orion-earmark-list">
			{#each items as item}
				<a
					class="orion-earmark-link"
					href={wordIndexHref(item)}
					onclick={(event) => onNavigate(event, item)}
				>
					<span>{wordIndexDisplay(item)}</span>
					<small>{languageLabel(item.encounter.language)}</small>
				</a>
			{/each}
		</div>
	</div>
{/if}

<style>
	.orion-earmarks {
		display: grid;
		gap: 0.42rem;
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		padding-top: 0.62rem;
	}

	.orion-earmarks-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.orion-earmarks-title {
		color: color-mix(in oklab, var(--color-base-content) 56%, transparent);
		font-family: var(--font-serif);
		font-size: 0.76rem;
		font-variant-caps: small-caps;
		font-weight: 700;
	}

	.orion-earmarks-clear {
		display: inline-flex;
		align-items: center;
		gap: 0.22rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.14rem 0.42rem;
		color: color-mix(in oklab, var(--color-base-content) 56%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.64rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1;
		cursor: pointer;
	}

	.orion-earmarks-clear:hover {
		border-color: color-mix(in oklab, var(--color-primary) 32%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--color-primary) 7%);
	}

	.orion-earmark-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
	}

	.orion-earmark-link {
		display: inline-flex;
		max-width: 100%;
		align-items: center;
		gap: 0.32rem;
		border: 1px solid color-mix(in oklab, var(--color-accent) 28%, var(--color-base-300));
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--color-accent) 7%);
		padding: 0.22rem 0.48rem;
		color: color-mix(in oklab, var(--color-base-content) 72%, var(--color-secondary));
		font-family: var(--font-reader);
		font-size: 0.78rem;
		line-height: 1.2;
		text-decoration: none;
	}

	.orion-earmark-link span {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.orion-earmark-link small {
		color: color-mix(in oklab, var(--color-base-content) 50%, transparent);
		font-family: var(--font-serif);
		font-size: 0.62rem;
		font-variant-caps: small-caps;
	}
</style>
