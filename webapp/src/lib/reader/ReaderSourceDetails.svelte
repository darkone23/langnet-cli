<script lang="ts">
	type Props = {
		sourceText?: string | null;
		transliteration?: string | null;
	};

	let { sourceText = null, transliteration = null }: Props = $props();

	const hasDetails = $derived(Boolean(sourceText || transliteration));
</script>

{#if hasDetails}
	<details class="orion-reader-desk-source">
		<summary>Source / transliteration</summary>
		{#if transliteration}
			<p>{transliteration}</p>
		{/if}
		{#if sourceText}
			<p>{sourceText}</p>
		{/if}
	</details>
{/if}

<style>
	.orion-reader-desk-source {
		margin: 0 1.15rem 1rem;
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding-top: 0.75rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.82rem;
	}

	.orion-reader-desk-source summary {
		cursor: pointer;
		font-family: var(--font-serif);
		font-weight: 700;
	}

	.orion-reader-desk-source p {
		margin-top: 0.45rem;
		font-family: var(--font-reader);
		line-height: 1.6;
	}
</style>
