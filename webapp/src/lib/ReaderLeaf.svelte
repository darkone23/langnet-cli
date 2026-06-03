<script lang="ts">
	import type { LanguageMode } from './search-data';
	import type { ReaderSegment, ReaderTokenPart } from './reader';

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

<div class="orion-reader-leaf" lang={langAttribute}>
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
		display: grid;
		gap: 0.2rem;
		min-height: 28rem;
		padding: clamp(1.35rem, 3.4vw, 3rem) clamp(1rem, 3vw, 2.4rem);
		background:
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

	.orion-reader-leaf-line {
		display: grid;
		grid-template-columns: minmax(3.5rem, 4.5rem) minmax(0, 58rem);
		align-items: baseline;
		gap: 0.9rem;
		justify-content: center;
		border-left: 0.2rem solid transparent;
		border-radius: 0.18rem;
		padding: 0.18rem 0.4rem 0.18rem 0.2rem;
	}

	.orion-reader-leaf-ref {
		border: 0;
		background: transparent;
		color: color-mix(in oklab, var(--color-base-content) 32%, transparent);
		cursor: pointer;
		font-family: var(--font-serif);
		font-size: 0.72rem;
		font-weight: 700;
		line-height: 1.2;
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
		max-width: 58rem;
		color: color-mix(in oklab, var(--color-base-content) 88%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: clamp(1.12rem, 1.55vw, 1.45rem);
		font-kerning: normal;
		line-height: 1.9;
	}

	.orion-reader-desk-text.interlinear {
		line-height: 2.45;
	}

	.orion-reader-token {
		display: inline;
		border: 0;
		border-radius: 0.16rem;
		background: transparent;
		padding: 0.02rem 0.08rem;
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
			grid-template-columns: 3.25rem minmax(0, 1fr);
			gap: 0.55rem;
		}

		.orion-reader-leaf-ref {
			font-size: 0.72rem;
		}
	}
</style>
