<script lang="ts">
	type Props = {
		previousCursor: string | null;
		nextCursor: string | null;
		disabled?: boolean;
		rangeLabel: string;
		contextLabel?: string;
		contextDetail?: string;
		placement?: 'top' | 'bottom';
		onOpenPage: (cursor: string | null) => void;
	};

	let {
		previousCursor,
		nextCursor,
		disabled = false,
		rangeLabel,
		contextLabel = 'page',
		contextDetail = '',
		placement = 'top',
		onOpenPage
	}: Props = $props();

	function openPage(cursor: string | null) {
		if (!cursor || disabled) return;
		onOpenPage(cursor);
	}
</script>

<div class:orion-reader-page-nav-bottom={placement === 'bottom'} class="orion-reader-page-nav">
	<button
		type="button"
		class="btn btn-sm"
		disabled={!previousCursor || disabled}
		onclick={() => openPage(previousCursor)}
	>
		Previous page
	</button>
	<div>
		<span class:orion-reader-page-work-label={Boolean(contextDetail)}>
			{contextLabel}
			{#if contextDetail}
				<small>{contextDetail}</small>
			{/if}
		</span>
		<strong>{rangeLabel}</strong>
	</div>
	<button
		type="button"
		class="btn btn-sm"
		disabled={!nextCursor || disabled}
		onclick={() => openPage(nextCursor)}
	>
		Next page
	</button>
</div>

<style>
	.orion-reader-page-nav {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: center;
		gap: 0.75rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
		padding: 0.7rem 1rem;
	}

	.orion-reader-page-nav-bottom {
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		border-bottom: 0;
	}

	.orion-reader-page-nav > div {
		display: grid;
		justify-items: center;
		gap: 0.1rem;
		max-width: 22rem;
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-family: var(--font-serif);
		font-size: 0.72rem;
		font-variant-caps: small-caps;
		font-weight: 700;
		line-height: 1.1;
		overflow: hidden;
		white-space: nowrap;
	}

	.orion-reader-page-nav > div span {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.orion-reader-page-nav > div strong {
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-primary));
		font-size: 1rem;
		font-variant-caps: normal;
	}

	.orion-reader-page-nav button:first-child {
		justify-self: start;
	}

	.orion-reader-page-nav button:last-child {
		justify-self: end;
	}

	.orion-reader-page-work-label {
		display: inline-flex;
		max-width: 18rem;
		min-width: 0;
		align-items: center;
		justify-content: center;
		gap: 0.25rem;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.orion-reader-page-work-label small {
		max-width: 7rem;
		overflow: hidden;
		color: color-mix(in oklab, var(--color-base-content) 46%, transparent);
		text-overflow: ellipsis;
	}

	@media (max-width: 48rem) {
		.orion-reader-page-nav {
			grid-template-columns: 1fr 1fr;
		}

		.orion-reader-page-nav > div {
			grid-column: 1 / -1;
			grid-row: 1;
		}

		.orion-reader-page-nav button:first-child,
		.orion-reader-page-nav button:last-child {
			grid-row: 2;
		}
	}
</style>
