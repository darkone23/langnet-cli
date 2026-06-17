<script lang="ts">
	import IlluminatedSprite from '$lib/ornament/IlluminatedSprite.svelte';
	import type { LanguageMode } from '../search-data';
	import type { ReaderSegment, ReaderTokenPart } from '$lib/reader';

	type Props = {
		pageSegments: ReaderSegment[];
		language: LanguageMode;
		selectedWord: string;
		showTransliteration: boolean;
		segmentParts: (segment: ReaderSegment) => ReaderTokenPart[];
		onOpenSegment: (segment: ReaderSegment) => void;
		onSelectToken: (token: string) => void;
	};

	let {
		pageSegments,
		language,
		selectedWord,
		showTransliteration,
		segmentParts,
		onOpenSegment,
		onSelectToken
	}: Props = $props();

	const langAttribute = $derived(language === 'grc' ? 'grc' : language === 'san' ? 'sa' : 'la');
</script>

<div class="orion-reader-leaf orion-reader-page-enter" lang={langAttribute}>
	<div class="orion-reader-book-pet">
		<IlluminatedSprite variant="beast" scale="sm" label="Kells-style marginal book pet" />
	</div>
	{#each pageSegments as segment}
		<section class="orion-reader-leaf-line">
			<button type="button" class="orion-reader-leaf-ref" onclick={() => onOpenSegment(segment)}>
				{segment.citation_path}
			</button>
			<p class:interlinear={showTransliteration} class="orion-reader-desk-text">
				{#each segmentParts(segment) as part}
					{#if part.isWord}
						<button
							type="button"
							class:selected={selectedWord === part.word}
							class:interlinear={Boolean(showTransliteration && part.transliteration)}
							class="orion-reader-token"
							onclick={() => onSelectToken(part.text)}
						>
							<span class="orion-reader-token-native">{part.text}</span>
							{#if showTransliteration && part.transliteration}
								<span class="orion-reader-token-translit">{part.transliteration}</span>
							{/if}
						</button>
					{:else}
						<span>{part.text}</span>
					{/if}
				{/each}
			</p>
		</section>
	{/each}
</div>

<style>
	.orion-reader-leaf {
		position: relative;
		display: grid;
		gap: 0.42rem;
		min-height: 28rem;
		padding: clamp(1.8rem, 4vw, 3.6rem) clamp(1rem, 3.4vw, 2.8rem);
		background:
			radial-gradient(
				circle at 9% 4%,
				color-mix(in oklab, var(--reader-ornament-gold) 18%, transparent),
				transparent 14rem
			),
			linear-gradient(
				90deg,
				color-mix(in oklab, var(--color-accent) 8%, transparent),
				transparent 12%,
				transparent 88%,
				color-mix(in oklab, var(--color-accent) 8%, transparent)
			),
			color-mix(in oklab, var(--color-base-100) 98%, var(--color-accent) 2%);
		box-shadow:
			inset 0.9rem 0 1.2rem -1.2rem color-mix(in oklab, var(--color-neutral) 24%, transparent),
			inset -0.9rem 0 1.2rem -1.2rem color-mix(in oklab, var(--color-neutral) 16%, transparent);
	}

	.orion-reader-leaf::before {
		content: '';
		position: absolute;
		inset: 0.72rem;
		pointer-events: none;
		border: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 28%, transparent);
		border-radius: 0.28rem;
		box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-base-100) 58%, transparent);
	}

	.orion-reader-book-pet {
		position: absolute;
		top: clamp(0.85rem, 2vw, 1.25rem);
		left: clamp(0.9rem, 2vw, 1.4rem);
		pointer-events: none;
		opacity: 0.94;
	}

	.orion-reader-leaf-line {
		display: grid;
		grid-template-columns: var(--reader-citation-gutter) minmax(0, var(--reader-measure));
		align-items: baseline;
		gap: clamp(0.7rem, 2vw, 1.15rem);
		justify-content: center;
		border-left: 0.2rem solid transparent;
		border-radius: 0.18rem;
		padding: 0.18rem 0.4rem 0.28rem 0.2rem;
	}

	.orion-reader-leaf-ref {
		border: 0;
		background: transparent;
		color: color-mix(in oklab, var(--color-base-content) 32%, transparent);
		cursor: pointer;
		font-family: var(--font-serif);
		font-size: 0.7rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		letter-spacing: 0.035em;
		line-height: 1.15;
		opacity: 0.72;
		text-align: right;
	}

	.orion-reader-leaf-ref:hover {
		color: color-mix(in oklab, var(--color-base-content) 58%, var(--color-primary));
		opacity: 1;
		text-decoration: underline;
		text-decoration-thickness: 1px;
		text-underline-offset: 0.15em;
	}

	.orion-reader-desk-text {
		margin: 0;
		max-width: var(--reader-measure);
		color: color-mix(in oklab, var(--color-base-content) 88%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: clamp(1.14rem, 1.48vw, 1.38rem);
		font-kerning: normal;
		hyphens: none;
		letter-spacing: 0.002em;
		line-height: var(--reader-line-height);
		text-wrap: pretty;
	}

	.orion-reader-leaf[lang='grc'] .orion-reader-desk-text {
		font-size: clamp(1.18rem, 1.55vw, 1.43rem);
		line-height: calc(var(--reader-line-height) + 0.06);
	}

	.orion-reader-leaf[lang='sa'] .orion-reader-desk-text {
		font-size: clamp(1.2rem, 1.62vw, 1.48rem);
		line-height: calc(var(--reader-line-height) + 0.14);
	}

	.orion-reader-desk-text.interlinear {
		line-height: 2.45;
	}

	.orion-reader-token {
		display: inline;
		border: 0;
		border-radius: 0.16rem;
		background: transparent;
		padding: 0.015rem 0.075rem;
		color: inherit;
		cursor: pointer;
		font: inherit;
		line-height: inherit;
		text-align: inherit;
		transition:
			background-color 120ms ease,
			color 120ms ease,
			box-shadow 120ms ease;
	}

	.orion-reader-token.interlinear {
		display: inline-grid;
		grid-template-rows: auto auto;
		align-items: center;
		justify-items: center;
		gap: 0.02rem;
		margin: 0 0.03rem;
		vertical-align: middle;
		line-height: 1.18;
	}

	.orion-reader-token-native {
		display: block;
	}

	.orion-reader-token-translit {
		display: block;
		max-width: 7.5rem;
		overflow-wrap: anywhere;
		color: color-mix(in oklab, var(--color-base-content) 46%, transparent);
		font-family: var(--font-serif);
		font-size: 0.62em;
		font-weight: 500;
		line-height: 1.05;
		text-align: center;
	}

	.orion-reader-token:hover,
	.orion-reader-token.selected {
		background: color-mix(in oklab, var(--color-accent) 18%, transparent);
		box-shadow: inset 0 -0.08em 0 color-mix(in oklab, var(--color-primary) 42%, transparent);
		color: color-mix(in oklab, var(--color-base-content) 92%, var(--color-secondary));
	}

	@media (max-width: 48rem) {
		.orion-reader-leaf-line {
			grid-template-columns: 3rem minmax(0, 1fr);
			gap: 0.55rem;
		}

		.orion-reader-book-pet {
			opacity: 0.52;
			transform: scale(0.82);
		}

		.orion-reader-leaf-ref {
			font-size: 0.72rem;
		}
	}
</style>
