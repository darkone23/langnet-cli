<script lang="ts">
	type Props = {
		title: string;
		message: string;
		retryLabel: string;
		onRetry: () => void;
	};

	let { title, message, retryLabel, onRetry }: Props = $props();
</script>

<div class="orion-reader-state-panel orion-reader-state-error" role="alert">
	<strong>{title}</strong>
	<p>{message}</p>
	<button type="button" class="btn btn-sm" onclick={onRetry}>{retryLabel}</button>
</div>

<style>
	.orion-reader-state-panel {
		display: grid;
		justify-items: start;
		gap: 0.45rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.18rem solid color-mix(in oklab, var(--color-warning) 45%, var(--color-base-300));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.78rem 0.85rem;
		color: color-mix(in oklab, var(--color-base-content) 68%, transparent);
		font-family: var(--font-serif);
	}

	.orion-reader-state-panel strong {
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-warning));
		font-size: 0.96rem;
		line-height: 1.2;
	}

	.orion-reader-state-panel p {
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.84rem;
		line-height: 1.4;
	}

	.orion-reader-state-error {
		border-left-color: color-mix(in oklab, var(--color-error) 52%, var(--color-base-content));
	}
</style>
