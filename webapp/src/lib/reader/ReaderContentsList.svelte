<script lang="ts">
	import { readerSegmentDisplayText, type ReaderSegment } from '$lib/reader';

	type Props = {
		contents: ReaderSegment[];
		segmentIsActive: (segment: ReaderSegment) => boolean;
		onOpenSegment: (segment: ReaderSegment) => void;
	};

	let { contents, segmentIsActive, onOpenSegment }: Props = $props();
</script>

<details class="orion-reader-page-segments mt-4">
	<summary>Page segments</summary>
	<div class="orion-reader-contents-list">
		{#each contents as segment}
			<button
				type="button"
				class:active={segmentIsActive(segment)}
				onclick={() => onOpenSegment(segment)}
			>
				<span>{segment.citation_path}</span>
				<small>{readerSegmentDisplayText(segment)}</small>
			</button>
		{/each}
	</div>
</details>

<style>
	.orion-reader-page-segments summary {
		cursor: pointer;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		font-weight: 700;
	}

	.orion-reader-contents-list {
		display: grid;
		max-height: 22rem;
		overflow: auto;
		gap: 0.34rem;
		padding-right: 0.12rem;
	}

	.orion-reader-contents-list button {
		display: grid;
		grid-template-columns: 4.25rem minmax(0, 1fr);
		gap: 0.45rem;
		width: 100%;
		align-items: baseline;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.42rem 0.5rem;
		text-align: left;
	}

	.orion-reader-contents-list button:hover,
	.orion-reader-contents-list button.active {
		border-color: color-mix(in oklab, var(--color-primary) 36%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 84%, var(--color-primary) 8%);
	}

	.orion-reader-contents-list span {
		color: color-mix(in oklab, var(--color-base-content) 70%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 0.76rem;
		font-weight: 700;
	}

	.orion-reader-contents-list small {
		overflow: hidden;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-reader);
		font-size: 0.76rem;
		line-height: 1.25;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
