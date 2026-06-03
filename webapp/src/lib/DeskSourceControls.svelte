<script lang="ts">
	import { BookOpen, Database, SlidersHorizontal } from 'lucide-svelte';
	import DeskToolChip from '$lib/DeskToolChip.svelte';
	import type { ToolId, ToolMeta } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type Mnemonic = {
		Icon: typeof BookOpen;
		name: string;
	};

	type Props = {
		availableTools: ToolMeta[];
		lookupTools: ToolId[];
		isAllLookupSelected: boolean;
		returnedTools: ToolMeta[];
		visibleTools: ToolId[];
		toolMnemonic: (toolId: ToolId) => Mnemonic;
		onShowAllLookupTools: () => void;
		onToggleLookupTool: (toolId: ToolId) => void;
		onShowAllReturnedTools: () => void;
		onToggleVisibleTool: (toolId: ToolId) => void;
	};

	let {
		availableTools,
		lookupTools,
		isAllLookupSelected,
		returnedTools,
		visibleTools,
		toolMnemonic,
		onShowAllLookupTools,
		onToggleLookupTool,
		onShowAllReturnedTools,
		onToggleVisibleTool
	}: Props = $props();
</script>

<fieldset class="fieldset orion-manuscript-panel w-full min-w-0 p-4">
	<legend class="fieldset-legend gap-2">
		<SlidersHorizontal size={16} />
		{uiCopy.sidebar.sourceTitle}
	</legend>

	<p class="text-base-content/65 mb-3 font-serif text-xs leading-5">
		{uiCopy.sidebar.sourceIntro}
	</p>

	<div class="orion-source-grid">
		<DeskToolChip
			Icon={BookOpen}
			active={isAllLookupSelected}
			label={uiCopy.sidebar.all}
			onSelect={onShowAllLookupTools}
			title={uiCopy.sidebar.generatorAllTitle}
		/>

		{#each availableTools as tool}
			{@const mnemonic = toolMnemonic(tool.id)}
			<DeskToolChip
				Icon={mnemonic.Icon}
				active={lookupTools.includes(tool.id)}
				label={tool.shortLabel}
				onSelect={() => onToggleLookupTool(tool.id)}
				title={`${mnemonic.name}: ${tool.description}`}
			/>
		{/each}
	</div>
</fieldset>

{#if returnedTools.length}
	<fieldset class="fieldset orion-manuscript-panel w-full min-w-0 p-4">
		<legend class="fieldset-legend gap-2">
			<Database size={16} />
			{uiCopy.sidebar.returnedTitle}
		</legend>

		<div class="orion-source-grid">
			<DeskToolChip
				Icon={Database}
				active={visibleTools.length === returnedTools.length}
				label={uiCopy.sidebar.all}
				onSelect={onShowAllReturnedTools}
				title={uiCopy.sidebar.showLoaded}
			/>

			{#each returnedTools as tool}
				{@const mnemonic = toolMnemonic(tool.id)}
				<DeskToolChip
					Icon={mnemonic.Icon}
					active={visibleTools.includes(tool.id)}
					label={tool.shortLabel}
					onSelect={() => onToggleVisibleTool(tool.id)}
					title={`${mnemonic.name}: ${tool.label}`}
				/>
			{/each}
		</div>
	</fieldset>
{/if}

<style>
	.orion-source-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.45rem;
	}
</style>
