<script lang="ts">
	import '$lib/desk/desk-entry.css';
	import { ChevronDown } from 'lucide-svelte';
	import DeskHeadwordBookplate from '$lib/desk/DeskHeadwordBookplate.svelte';
	import type { HeadwordDisplay } from '$lib/headword-display';
	import type {
		EncounterComponent,
		EncounterComponentMeaning,
		ToolId,
		ToolMeta
	} from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type TextLayerState = Record<string, 'reader' | 'source'>;
	type ExpandedState = Record<string, boolean>;
	type IconComponent = typeof ChevronDown;

	type ComponentLedgerHelpers = {
		countLabel: (count: number, singular: string, plural?: string) => string;
		componentPrimaryTool: (component: EncounterComponent) => ToolId;
		componentToolIds: (component: EncounterComponent) => ToolId[];
		componentHeadwordDisplay: (component: EncounterComponent) => HeadwordDisplay;
		componentLookupLine: (component: EncounterComponent) => string;
		componentCanSwitchTextLayer: (component: EncounterComponent) => boolean;
		componentLayerIsSource: (component: EncounterComponent, layerState: TextLayerState) => boolean;
		setComponentTextLayer: (component: EncounterComponent, layer: 'reader' | 'source') => void;
		componentSourceLayerLabel: (component: EncounterComponent) => string;
		componentHasTranslationToggle: (component: EncounterComponent) => boolean;
		componentAwaitsReaderTranslation: (component: EncounterComponent) => boolean;
		componentTranslationModel: (component: EncounterComponent) => string | undefined;
		componentMeaningSegments: (
			meaning: EncounterComponentMeaning,
			layerState: TextLayerState,
			expansionState: ExpandedState
		) => string[];
		componentMeaningCanToggle: (
			meaning: EncounterComponentMeaning,
			layerState: TextLayerState
		) => boolean;
		componentMeaningToggleLabel: (
			meaning: EncounterComponentMeaning,
			expansionState: ExpandedState
		) => string;
		componentMeaningKey: (meaning: EncounterComponentMeaning) => string;
		componentMeaningSourceLabel: (meaning: EncounterComponentMeaning) => string;
		toggleComponentMeaning: (meaning: EncounterComponentMeaning) => void;
		toolMeta: (tool: ToolId) => ToolMeta;
		toolMnemonic: (tool: ToolId) => { Icon: IconComponent; name: string };
		translationModelLabel: (model: string | undefined) => string;
	};

	type Props = {
		components: EncounterComponent[];
		textLayers: TextLayerState;
		expandedSections: ExpandedState;
		toolStyle: Record<ToolId, { accent: string; badge: string }>;
		helpers: ComponentLedgerHelpers;
	};

	let { components, textLayers, expandedSections, toolStyle, helpers }: Props = $props();
</script>

{#if components.length}
	<section class="orion-component-ledger">
		<div class="orion-component-ledger-head">
			<div>
				<h2 class="font-serif text-2xl">{uiCopy.components.title}</h2>
				<p>{uiCopy.components.intro}</p>
			</div>
			<span class="orion-component-count">
				<span>{components.length}</span>
				<span>{components.length === 1 ? 'member' : 'members'}</span>
			</span>
		</div>

		<div class="orion-component-list">
			{#each components as component}
				{@const componentTool = helpers.componentPrimaryTool(component)}
				{@const ComponentIcon = helpers.toolMnemonic(componentTool).Icon}
				{@const componentDisplay = helpers.componentHeadwordDisplay(component)}
				<article class="orion-result-group orion-component-group">
					<header class="orion-result-group-head">
						<div class="min-w-0">
							<div class="mb-2 flex flex-wrap items-center gap-2">
								<span class="orion-source-beast" title={helpers.toolMnemonic(componentTool).name}>
									<ComponentIcon size={16} />
								</span>
								<span class={`badge ${toolStyle[componentTool].badge}`}>
									{helpers.toolMeta(componentTool).shortLabel}
								</span>
								<span class="badge badge-outline">member</span>
							</div>
							<DeskHeadwordBookplate
								display={componentDisplay}
								lead={helpers.componentLookupLine(component)}
								sourceLine={component.analysis}
							/>
						</div>
						<div class="orion-entry-chrome">
							<div class="orion-entry-source-strip">
								{#each helpers.componentToolIds(component) as tool}
									{@const ToolIcon = helpers.toolMnemonic(tool).Icon}
									<span
										class="orion-source-beast orion-source-beast-sm"
										title={helpers.toolMnemonic(tool).name}
									>
										<ToolIcon size={14} />
									</span>
								{/each}
								<span>{component.evidence.meanings.length} entries</span>
								<span>{component.evidence.status || 'linked'}</span>
							</div>

							{#if helpers.componentCanSwitchTextLayer(component)}
								<div class="flex shrink-0 flex-col items-end gap-1">
									<div class="orion-layer-switch join">
										<button
											type="button"
											class={helpers.componentLayerIsSource(component, textLayers)
												? 'btn btn-xs join-item'
												: 'btn btn-xs join-item btn-secondary'}
											onclick={() => helpers.setComponentTextLayer(component, 'reader')}
										>
											Reader English
										</button>
										<button
											type="button"
											class={helpers.componentLayerIsSource(component, textLayers)
												? 'btn btn-xs join-item btn-secondary'
												: 'btn btn-xs join-item'}
											onclick={() => helpers.setComponentTextLayer(component, 'source')}
										>
											{helpers.componentSourceLayerLabel(component)}
										</button>
									</div>
									{#if helpers.translationModelLabel(helpers.componentTranslationModel(component))}
										<div
											class="text-base-content/50 flex items-center gap-1 text-[0.68rem] leading-none"
										>
											<span>
												EN by {helpers.translationModelLabel(
													helpers.componentTranslationModel(component)
												)}
											</span>
										</div>
									{/if}
								</div>
							{:else if helpers.componentHasTranslationToggle(component)}
								<span class="badge badge-outline">
									{helpers.componentSourceLayerLabel(component)} only
								</span>
							{/if}
							{#if helpers.componentAwaitsReaderTranslation(component)}
								<span class="orion-translator-sigil" title={uiCopy.translator.title}>
									<span>{uiCopy.translator.badge}</span>
									<i></i><i></i><i></i>
								</span>
							{/if}
						</div>
					</header>

					{#if component.evidence.error}
						<div class="alert alert-warning text-sm">{component.evidence.error}</div>
					{:else if component.evidence.meanings.length}
						<div class={`orion-entry-reader ${toolStyle[componentTool].accent}`}>
							<div class="orion-reader-sections">
								{#each component.evidence.meanings as meaning}
									{@const segments = helpers.componentMeaningSegments(
										meaning,
										textLayers,
										expandedSections
									)}
									<section
										class={`orion-reader-section orion-reader-section-${componentTool} orion-component-meaning`}
									>
										<div class="orion-reader-marker"></div>
										<div>
											<div class="orion-component-source">
												{helpers.componentMeaningSourceLabel(meaning)}
											</div>
											<div class="orion-reader-copy">
												{#each segments as gloss, segmentIndex}
													<p>
														{gloss}
														{#if segmentIndex === segments.length - 1 && helpers.componentMeaningCanToggle(meaning, textLayers)}
															<button
																type="button"
																class="orion-section-detail-toggle"
																aria-label={helpers.componentMeaningToggleLabel(
																	meaning,
																	expandedSections
																)}
																title={helpers.componentMeaningToggleLabel(
																	meaning,
																	expandedSections
																)}
																onclick={() => helpers.toggleComponentMeaning(meaning)}
															>
																<ChevronDown
																	size={12}
																	class={expandedSections[helpers.componentMeaningKey(meaning)]
																		? 'orion-chevron-open'
																		: ''}
																/>
															</button>
														{/if}
													</p>
												{/each}
											</div>
										</div>
									</section>
								{/each}
							</div>
						</div>
					{:else}
						<div class="orion-component-empty">{uiCopy.components.empty}</div>
					{/if}
				</article>
			{/each}
		</div>
	</section>
{/if}

<style>
	.orion-component-ledger {
		display: grid;
		gap: 1rem;
	}

	.orion-component-ledger-head {
		display: flex;
		align-items: start;
		justify-content: space-between;
		gap: 1rem;
		padding-inline: 0.15rem;
	}

	.orion-component-ledger-head > div {
		min-width: 0;
	}

	.orion-component-ledger-head h2 {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-secondary));
		line-height: 1.1;
	}

	.orion-component-ledger-head p {
		margin: 0.25rem 0 0;
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-size: 0.9rem;
		line-height: 1.45;
	}

	.orion-component-count {
		display: inline-flex;
		flex: 0 0 auto;
		align-items: baseline;
		gap: 0.32rem;
		border: 1px solid color-mix(in oklab, var(--color-accent) 32%, var(--color-base-300));
		border-radius: 0.28rem;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-accent) 5%);
		padding: 0.28rem 0.46rem 0.3rem;
		color: color-mix(in oklab, var(--color-base-content) 64%, var(--color-secondary));
		font-family: var(--font-serif);
		font-variant-caps: small-caps;
		line-height: 1;
		box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-base-100) 54%, transparent);
	}

	.orion-component-count span:first-child {
		color: color-mix(in oklab, var(--color-base-content) 78%, var(--color-primary));
		font-size: 1.05rem;
		font-weight: 700;
	}

	.orion-component-count span:last-child {
		font-size: 0.7rem;
		font-weight: 700;
		white-space: nowrap;
	}

	.orion-component-list {
		display: grid;
		gap: 1rem;
	}

	.orion-component-source,
	.orion-component-empty {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.78rem;
		line-height: 1.35;
	}

	.orion-component-meaning {
		gap: 0.3rem;
	}
</style>
