<script lang="ts">
	import '$lib/desk-entry.css';
	import { Asterisk, ChevronDown, RefreshCw } from 'lucide-svelte';
	import DeskHeadwordBookplate from '$lib/DeskHeadwordBookplate.svelte';
	import type { HeadwordDisplay } from '$lib/headword-display';
	import type { EncounterBucket, LanguageMode, ToolId, ToolMeta } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type TextLayerState = Record<string, 'reader' | 'source'>;
	type ExpandedState = Record<string, boolean>;
	type IconComponent = typeof ChevronDown;

	type BucketGroup = {
		id: string;
		toolId: ToolId;
		dictionary: string;
		lexeme: string;
		buckets: EncounterBucket[];
		witnessCount: number;
		sourceRefCount: number;
		reasons: string[];
	};

	type DictionaryGroupHelpers = {
		countLabel: (count: number, singular: string, plural?: string) => string;
		groupHeadwordDisplay: (group: BucketGroup) => HeadwordDisplay;
		groupLead: (
			group: BucketGroup,
			layerState: TextLayerState,
			expansionState: ExpandedState
		) => string;
		groupToolIds: (group: BucketGroup) => ToolId[];
		groupWitnesses: (group: BucketGroup) => unknown[];
		readerEntryLabel: (group: BucketGroup, layerState: TextLayerState) => string;
		groupCanSwitchTextLayer: (group: BucketGroup) => boolean;
		groupLayerIsSource: (group: BucketGroup, layerState: TextLayerState) => boolean;
		groupHasReaderTranslation: (group: BucketGroup) => boolean;
		setGroupTextLayer: (group: BucketGroup, layer: 'reader' | 'source') => void;
		groupSourceLayerLabel: (group: BucketGroup) => string;
		groupTranslationModel: (group: BucketGroup) => string | undefined;
		groupHasTranslationToggle: (group: BucketGroup) => boolean;
		groupAwaitsReaderTranslation: (group: BucketGroup) => boolean;
		retryableGroupTranslation: (group: BucketGroup) => unknown;
		groupTranslationRetrying: (group: BucketGroup) => boolean;
		retryGroupTranslation: (group: BucketGroup) => void;
		visibleGroupBuckets: (group: BucketGroup) => EncounterBucket[];
		sectionSegments: (
			bucket: EncounterBucket,
			layerState: TextLayerState,
			expansionState: ExpandedState
		) => string[];
		sectionHasTreeChildren: (group: BucketGroup, bucket: EncounterBucket) => boolean;
		sectionId: (group: BucketGroup, bucket: EncounterBucket) => string;
		readerSectionClass: (bucket: EncounterBucket, layerState: TextLayerState) => string;
		readerSectionStyle: (bucket: EncounterBucket) => string;
		branchToggleLabel: (bucket: EncounterBucket) => string;
		toggleBranchCollapse: (bucket: EncounterBucket) => void;
		sectionExpansionKey: (bucket: EncounterBucket) => string;
		sectionCanToggle: (bucket: EncounterBucket, layerState: TextLayerState) => boolean;
		sectionToggleLabel: (
			bucket: EncounterBucket,
			layerState: TextLayerState,
			expansionState: ExpandedState
		) => string;
		toggleSectionExpansion: (bucket: EncounterBucket) => void;
		sectionShowsReturnedEndingNote: (
			bucket: EncounterBucket,
			layerState: TextLayerState,
			expansionState: ExpandedState
		) => boolean;
		toolMeta: (tool: ToolId, mode?: LanguageMode) => ToolMeta;
		toolMnemonic: (tool: ToolId) => { Icon: IconComponent; name: string };
		translationModelLabel: (model: string | undefined) => string;
	};

	type Props = {
		group: BucketGroup;
		language: LanguageMode;
		textLayers: TextLayerState;
		expandedSections: ExpandedState;
		collapsedBranches: ExpandedState;
		toolStyle: Record<ToolId, { accent: string; badge: string }>;
		helpers: DictionaryGroupHelpers;
	};

	let {
		group,
		language,
		textLayers,
		expandedSections,
		collapsedBranches,
		toolStyle,
		helpers
	}: Props = $props();

	let groupTool = $derived(helpers.toolMeta(group.toolId, language));
	let GroupIcon = $derived(helpers.toolMnemonic(group.toolId).Icon);
	let headwordDisplay = $derived(helpers.groupHeadwordDisplay(group));
</script>

<section class="orion-result-group">
	<div class="orion-result-group-head">
		<div class="min-w-0">
			<div class="mb-2 flex flex-wrap items-center gap-2">
				<span class="orion-source-beast" title={helpers.toolMnemonic(group.toolId).name}>
					<GroupIcon size={16} />
				</span>
				<span class={`badge ${toolStyle[group.toolId].badge}`}>
					{groupTool.shortLabel}
				</span>
			</div>
			<DeskHeadwordBookplate
				display={headwordDisplay}
				lead={helpers.groupLead(group, textLayers, expandedSections)}
				sourceLine={group.dictionary !== group.toolId
					? `${groupTool.label} · ${group.dictionary}`
					: groupTool.label}
			/>
		</div>
		<div class="orion-entry-chrome">
			<div class="orion-entry-source-strip">
				{#each helpers.groupToolIds(group) as tool}
					{@const ToolIcon = helpers.toolMnemonic(tool).Icon}
					<span
						class="orion-source-beast orion-source-beast-sm"
						title={helpers.toolMnemonic(tool).name}
					>
						<ToolIcon size={14} />
					</span>
				{/each}
				<span>{helpers.readerEntryLabel(group, textLayers)}</span>
				<span>{helpers.countLabel(group.buckets.length, 'section')}</span>
				<span>{helpers.countLabel(helpers.groupWitnesses(group).length, 'source entry')}</span>
			</div>

			{#if helpers.groupCanSwitchTextLayer(group)}
				<div class="flex shrink-0 flex-col items-end gap-1">
					<div class="orion-layer-switch join">
						<button
							type="button"
							class={helpers.groupLayerIsSource(group, textLayers)
								? 'btn btn-xs join-item'
								: 'btn btn-xs join-item btn-secondary'}
							onclick={() => helpers.setGroupTextLayer(group, 'reader')}
						>
							Reader English
						</button>
						<button
							type="button"
							class={helpers.groupLayerIsSource(group, textLayers) ||
							!helpers.groupHasReaderTranslation(group)
								? 'btn btn-xs join-item btn-secondary'
								: 'btn btn-xs join-item'}
							onclick={() => helpers.setGroupTextLayer(group, 'source')}
						>
							{helpers.groupSourceLayerLabel(group)}
						</button>
					</div>
					{#if helpers.translationModelLabel(helpers.groupTranslationModel(group)) || helpers.retryableGroupTranslation(group)}
						<div class="text-base-content/50 flex items-center gap-1 text-[0.68rem] leading-none">
							{#if helpers.translationModelLabel(helpers.groupTranslationModel(group))}
								<span
									>EN by {helpers.translationModelLabel(helpers.groupTranslationModel(group))}</span
								>
							{/if}
							{#if helpers.retryableGroupTranslation(group)}
								<button
									type="button"
									class="btn btn-ghost btn-xs h-5 min-h-0 px-1"
									disabled={helpers.groupTranslationRetrying(group)}
									aria-label="Retry English translation"
									title="Retry English translation"
									onclick={() => helpers.retryGroupTranslation(group)}
								>
									{#if helpers.groupTranslationRetrying(group)}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<RefreshCw size={12} />
									{/if}
								</button>
							{/if}
						</div>
					{/if}
				</div>
			{:else if helpers.groupHasTranslationToggle(group)}
				<div class="flex shrink-0 items-center gap-1">
					<span class="badge badge-outline">{helpers.groupSourceLayerLabel(group)} only</span>
					{#if helpers.retryableGroupTranslation(group)}
						<button
							type="button"
							class="btn btn-ghost btn-xs h-5 min-h-0 px-1"
							disabled={helpers.groupTranslationRetrying(group)}
							aria-label="Retry English translation"
							title="Retry English translation"
							onclick={() => helpers.retryGroupTranslation(group)}
						>
							{#if helpers.groupTranslationRetrying(group)}
								<span class="loading loading-spinner loading-xs"></span>
							{:else}
								<RefreshCw size={12} />
							{/if}
						</button>
					{/if}
				</div>
			{/if}
			{#if helpers.groupAwaitsReaderTranslation(group)}
				<span class="orion-translator-sigil" title={uiCopy.translator.title}>
					<span>{uiCopy.translator.badge}</span>
					<i></i><i></i><i></i>
				</span>
			{/if}
		</div>
	</div>

	<article class={`orion-entry-reader ${toolStyle[group.toolId].accent}`}>
		<div class="orion-reader-sections">
			{#each helpers.visibleGroupBuckets(group) as bucket}
				{@const segments = helpers.sectionSegments(bucket, textLayers, expandedSections)}
				{@const hasTreeChildren = helpers.sectionHasTreeChildren(group, bucket)}
				<section
					id={helpers.sectionId(group, bucket)}
					class={helpers.readerSectionClass(bucket, textLayers)}
					style={helpers.readerSectionStyle(bucket)}
				>
					<div class="orion-reader-marker">
						{#if hasTreeChildren}
							<button
								type="button"
								class="orion-branch-toggle"
								aria-label={helpers.branchToggleLabel(bucket)}
								title={helpers.branchToggleLabel(bucket)}
								onclick={() => helpers.toggleBranchCollapse(bucket)}
							>
								<Asterisk
									size={11}
									strokeWidth={2.2}
									class={collapsedBranches[helpers.sectionExpansionKey(bucket)]
										? 'orion-branch-mark-collapsed'
										: ''}
								/>
							</button>
						{/if}
					</div>
					<div class="orion-reader-copy">
						{#each segments as gloss, segmentIndex}
							<p>
								{gloss}
								{#if segmentIndex === segments.length - 1}
									{#if helpers.sectionCanToggle(bucket, textLayers)}
										<button
											type="button"
											class="orion-section-detail-toggle"
											aria-label={helpers.sectionToggleLabel(bucket, textLayers, expandedSections)}
											title={helpers.sectionToggleLabel(bucket, textLayers, expandedSections)}
											onclick={() => helpers.toggleSectionExpansion(bucket)}
										>
											<ChevronDown
												size={12}
												class={expandedSections[helpers.sectionExpansionKey(bucket)]
													? 'orion-chevron-open'
													: ''}
											/>
										</button>
									{/if}
									{#if helpers.sectionShowsReturnedEndingNote(bucket, textLayers, expandedSections)}
										<span class="orion-section-detail-note">
											{uiCopy.results.returnedEnding}
										</span>
									{/if}
								{/if}
							</p>
						{/each}
					</div>
				</section>
			{/each}
		</div>
	</article>
</section>
