<script lang="ts">
	import { Sparkles } from 'lucide-svelte';
	import type { EncounterResult } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type Props = {
		encounter: EncounterResult;
		cacheAccount: string;
		readerLayerStatus: string;
	};

	let { encounter, cacheAccount, readerLayerStatus }: Props = $props();
</script>

<section class="card orion-manuscript-panel w-full min-w-0">
	<div class="card-body min-w-0 gap-3 p-4">
		<h2 class="card-title text-base">
			<Sparkles size={17} />
			{uiCopy.colophon.title}
		</h2>
		<div class="flex flex-wrap gap-2">
			{#each encounter.lexeme_anchors as anchor}
				<span class="badge badge-outline">{anchor}</span>
			{/each}
		</div>
		<div class="rounded-box bg-base-200 p-3 text-sm leading-6">
			<div class="font-medium">{uiCopy.colophon.translationAccount}</div>
			<div class="text-base-content/65">
				{encounter.translation_cache.after.hits}/{encounter.translation_cache.after.total} hits,
				{encounter.translation_cache.written} written
			</div>
			<div class="text-base-content/65">Account: {cacheAccount}</div>
		</div>
		<div class="rounded-box bg-base-200 p-3 text-sm leading-6">
			<div class="font-medium">{uiCopy.colophon.requestSeal}</div>
			<div class="text-base-content/65">
				backend={encounter.backend}, translation={encounter.request.translation_mode}, reader={encounter
					.request.reader_lang}
			</div>
			<div class="text-base-content/65 mt-1">{readerLayerStatus}</div>
		</div>
		{#if encounter.warnings.length}
			<div class="alert alert-warning text-sm">
				{encounter.warnings[0]}
			</div>
		{/if}
	</div>
</section>
