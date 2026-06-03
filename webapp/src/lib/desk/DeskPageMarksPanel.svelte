<script lang="ts">
	import { Eraser, Sparkles } from 'lucide-svelte';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		pageLink: string;
		endpoint: string;
		onClear: () => void;
	};

	let { pageLink, endpoint, onClear }: Props = $props();
</script>

<section class="card orion-manuscript-panel w-full min-w-0">
	<div class="card-body min-w-0 gap-3 p-4">
		<h2 class="card-title text-base">
			<span class="flex min-w-0 flex-1 items-center gap-2">
				<Sparkles size={17} />
				{uiCopy.pageMarks.title}
			</span>
			<button
				type="button"
				class="btn btn-ghost btn-xs gap-1"
				onclick={onClear}
				title={uiCopy.pageMarks.clearTitle}
			>
				<Eraser size={14} />
				Clear
			</button>
		</h2>
		<div>
			<div class="text-base-content/50 mb-1 text-xs font-medium uppercase">
				{uiCopy.pageMarks.pageLink}
			</div>
			<div class="mockup-code orion-endpoint-code w-full min-w-0 overflow-x-auto text-xs">
				<pre class="break-all whitespace-pre-wrap"><code>{pageLink}</code></pre>
			</div>
		</div>
		<div>
			<div class="text-base-content/50 mb-1 text-xs font-medium uppercase">
				{uiCopy.pageMarks.endpoint}
			</div>
			<div class="mockup-code orion-endpoint-code w-full min-w-0 overflow-x-auto text-xs">
				<pre class="break-all whitespace-pre-wrap"><code>{endpoint}</code></pre>
			</div>
		</div>
		<p class="text-base-content/65 font-serif text-sm leading-6">
			{uiCopy.pageMarks.contractPrefix}
			<code>dictionary=all</code>
			{uiCopy.pageMarks.contractSuffix}
		</p>
	</div>
</section>

<style>
	.orion-endpoint-code {
		min-width: 0;
	}

	.orion-endpoint-code::before {
		display: none;
	}

	.orion-endpoint-code pre {
		min-width: 0;
		padding-inline-start: 1rem;
	}
</style>
