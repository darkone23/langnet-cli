<script lang="ts">
	type Props = {
		sourceText?: string | null;
		transliteration?: string | null;
	};

	let { sourceText = null, transliteration = null }: Props = $props();

	const hasDetails = $derived(Boolean(sourceText || transliteration));
</script>

{#if hasDetails}
	<details class="orion-reader-desk-source" aria-label="Source / transliteration">
		<summary>
			<span class="orion-reader-liturgical-label">Apparatus</span>
			<strong>Source witness and transliteration</strong>
		</summary>
		{#if transliteration}
			<p class="orion-reader-apparatus-note">{transliteration}</p>
		{/if}
		{#if sourceText}
			<p class="orion-reader-apparatus-note">{sourceText}</p>
		{/if}
	</details>
{/if}

<style>
	.orion-reader-desk-source {
		margin: 0 1.15rem 1.15rem;
		border-top: 1px solid color-mix(in oklab, var(--reader-ornament-gold) 28%, transparent);
		padding-top: 0.95rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
	}

	.orion-reader-desk-source summary {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.55rem;
		cursor: pointer;
		font-family: var(--font-serif);
		font-weight: 700;
	}

	.orion-reader-desk-source summary strong {
		color: color-mix(in oklab, var(--color-base-content) 72%, var(--color-secondary));
		font-size: 0.92rem;
	}

	.orion-reader-desk-source p {
		margin-top: 0.58rem;
		max-width: 76ch;
	}
</style>
