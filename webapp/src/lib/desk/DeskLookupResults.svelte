<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import { Database, Search } from 'lucide-svelte';
	import DeskComponentLedger from '$lib/desk/DeskComponentLedger.svelte';
	import DeskDictionaryGroupCard from '$lib/desk/DeskDictionaryGroupCard.svelte';
	import DeskOracleTrace from '$lib/desk/DeskOracleTrace.svelte';
	import DeskLookupLoadingPanel from '$lib/desk/DeskLookupLoadingPanel.svelte';
	import DeskParadigmPanel from '$lib/desk/DeskParadigmPanel.svelte';
	import type { EncounterResult } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type ComponentLedgerProps = ComponentProps<typeof DeskComponentLedger>;
	type DictionaryGroupProps = ComponentProps<typeof DeskDictionaryGroupCard>;
	type ParadigmPanelProps = ComponentProps<typeof DeskParadigmPanel>;

	type Props = {
		errorMessage: string;
		enrichmentError: string;
		enrichingTranslations: boolean;
		encounter: EncounterResult | null;
		loading: boolean;
		translationArrived: boolean;
		visibleComponents: ComponentLedgerProps['components'];
		visibleBucketGroups: DictionaryGroupProps['group'][];
		textLayers: ComponentLedgerProps['textLayers'];
		expandedSections: ComponentLedgerProps['expandedSections'];
		collapsedBranches: DictionaryGroupProps['collapsedBranches'];
		toolStyle: ComponentLedgerProps['toolStyle'];
		componentLedgerHelpers: ComponentLedgerProps['helpers'];
		dictionaryGroupHelpers: DictionaryGroupProps['helpers'];
		query: string;
		languageName: string;
		allSourcesSelected: boolean;
		lookupElapsedSeconds: number;
		paradigmCandidates: ParadigmPanelProps['candidates'];
		paradigmHiddenCount: ParadigmPanelProps['hiddenCount'];
		paradigmPayloads: ParadigmPanelProps['payloads'];
		paradigmLoading: ParadigmPanelProps['loading'];
		paradigmErrors: ParadigmPanelProps['errors'];
		countLabel: (count: number, singular: string, plural?: string) => string;
		onShowAllReturnedTools: () => void;
		onLoadParadigm: ParadigmPanelProps['onLoadParadigm'];
		onWitnessesElement: (element: HTMLElement | null) => void;
	};

	let {
		errorMessage,
		enrichmentError,
		enrichingTranslations,
		encounter,
		loading,
		translationArrived,
		visibleComponents,
		visibleBucketGroups,
		textLayers,
		expandedSections,
		collapsedBranches,
		toolStyle,
		componentLedgerHelpers,
		dictionaryGroupHelpers,
		query,
		languageName,
		allSourcesSelected,
		lookupElapsedSeconds,
		paradigmCandidates,
		paradigmHiddenCount,
		paradigmPayloads,
		paradigmLoading,
		paradigmErrors,
		countLabel,
		onShowAllReturnedTools,
		onLoadParadigm,
		onWitnessesElement
	}: Props = $props();

	let dictionaryWitnessesSection: HTMLElement | null = $state(null);

	$effect(() => {
		onWitnessesElement(dictionaryWitnessesSection);
		return () => onWitnessesElement(null);
	});
</script>

{#if errorMessage}
	<div class="alert alert-warning">
		<Search size={18} />
		<span>{errorMessage}</span>
	</div>
{/if}

{#if enrichingTranslations && encounter}
	<div class="alert alert-info">
		<span class="loading loading-spinner loading-sm"></span>
		<span>{uiCopy.translator.alert}</span>
	</div>
{/if}

{#if enrichmentError}
	<div class="alert alert-warning">
		<Search size={18} />
		<span>{uiCopy.translator.failed(enrichmentError)}</span>
	</div>
{/if}

{#if !loading && encounter}
	<DeskComponentLedger
		components={visibleComponents}
		{textLayers}
		{expandedSections}
		{toolStyle}
		helpers={componentLedgerHelpers}
	/>
{/if}

<section
	bind:this={dictionaryWitnessesSection}
	class={translationArrived
		? 'orion-dictionary-witnesses orion-translation-arrived space-y-4'
		: 'orion-dictionary-witnesses space-y-4'}
>
	<DeskOracleTrace {encounter} {query} />

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h2 class="font-serif text-3xl">{uiCopy.results.title}</h2>
			<p class="text-base-content/60 text-sm">{uiCopy.results.intro}</p>
		</div>
		<div class="join">
			<button type="button" class="btn btn-sm join-item" onclick={onShowAllReturnedTools}>
				{uiCopy.results.all}
			</button>
			<button type="button" class="btn btn-sm join-item btn-ghost">
				{countLabel(visibleBucketGroups.length, 'source group')}
			</button>
		</div>
	</div>

	{#if loading}
		<DeskLookupLoadingPanel
			{query}
			{languageName}
			{allSourcesSelected}
			elapsedSeconds={lookupElapsedSeconds}
		/>
	{:else if encounter}
		<DeskParadigmPanel
			candidates={paradigmCandidates}
			hiddenCount={paradigmHiddenCount}
			payloads={paradigmPayloads}
			loading={paradigmLoading}
			errors={paradigmErrors}
			searchedForm={encounter.paradigm_resolution?.searched_form}
			normalizedForm={encounter.paradigm_resolution?.normalized_form}
			fallbackQuery={encounter.query ?? query}
			fallbackLanguage={encounter.language}
			{onLoadParadigm}
		/>

		{#each visibleBucketGroups as group}
			<DeskDictionaryGroupCard
				{group}
				language={encounter.language}
				{textLayers}
				{expandedSections}
				{collapsedBranches}
				{toolStyle}
				helpers={dictionaryGroupHelpers}
			/>
		{:else}
			<div class="alert alert-info">
				<Database size={18} />
				<span>{uiCopy.results.noFilterMatch}</span>
			</div>
		{/each}
	{/if}
</section>
