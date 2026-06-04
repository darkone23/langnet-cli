<script lang="ts">
	import { Search } from 'lucide-svelte';
	import type { ReaderFacetValue, ReaderRouteState } from '$lib/reader';

	type DiscoverySort = NonNullable<ReaderRouteState['discoverySort']>;

	type Props = {
		workQuery: string;
		discoveryGroup: string;
		discoveryTag: string;
		discoverySort: DiscoverySort;
		discoveryGroups: ReaderFacetValue[];
		discoveryTags: ReaderFacetValue[];
		discoverySorts: ReaderFacetValue[];
		loading: boolean;
		canSearch: boolean;
		canClear: boolean;
		onWorkQueryInput: (value: string) => void;
		onDiscoveryGroupChange: (value: string) => void;
		onDiscoveryTagChange: (value: string) => void;
		onDiscoverySortChange: (value: DiscoverySort) => void;
		onApplyFilters: () => void;
		onSubmitSearch: () => void;
		onClearFilters: () => void;
	};

	let {
		workQuery,
		discoveryGroup,
		discoveryTag,
		discoverySort,
		discoveryGroups,
		discoveryTags,
		discoverySorts,
		loading,
		canSearch,
		canClear,
		onWorkQueryInput,
		onDiscoveryGroupChange,
		onDiscoveryTagChange,
		onDiscoverySortChange,
		onApplyFilters,
		onSubmitSearch,
		onClearFilters
	}: Props = $props();

	function handleWorkQueryInput(event: Event) {
		onWorkQueryInput((event.currentTarget as HTMLInputElement).value);
	}

	function handleGroupChange(event: Event) {
		onDiscoveryGroupChange((event.currentTarget as HTMLSelectElement).value);
		onApplyFilters();
	}

	function handleTagChange(event: Event) {
		onDiscoveryTagChange((event.currentTarget as HTMLSelectElement).value);
		onApplyFilters();
	}

	function handleSortChange(event: Event) {
		onDiscoverySortChange((event.currentTarget as HTMLSelectElement).value as DiscoverySort);
		onApplyFilters();
	}
</script>

<form
	class="orion-reader-discovery-search"
	onsubmit={(event) => {
		event.preventDefault();
		onSubmitSearch();
	}}
>
	<label class="input input-bordered flex min-w-0 items-center gap-2">
		<Search size={16} class="text-base-content/45" />
		<input
			value={workQuery}
			type="search"
			placeholder="Search titles or authors"
			autocomplete="off"
			oninput={handleWorkQueryInput}
		/>
	</label>
	<select class="select select-bordered" value={discoveryGroup} onchange={handleGroupChange}>
		<option value="">All groups</option>
		{#each discoveryGroups as group}
			<option value={group.id}>{group.label}</option>
		{/each}
	</select>
	<select class="select select-bordered" value={discoveryTag} onchange={handleTagChange}>
		<option value="">All tags</option>
		{#each discoveryTags as tag}
			<option value={tag.id}>{tag.label}</option>
		{/each}
	</select>
	<select class="select select-bordered" value={discoverySort} onchange={handleSortChange}>
		{#if discoverySorts.length}
			{#each discoverySorts as sort}
				<option value={sort.id}>{sort.label}</option>
			{/each}
		{:else}
			<option value="global-popularity">Global popularity</option>
			<option value="group-popularity">Group popularity</option>
			<option value="catalog">Catalog order</option>
		{/if}
	</select>
	<button class="btn btn-neutral" disabled={loading || !canSearch}>
		<Search size={16} />
		{loading ? 'Searching' : 'Search'}
	</button>
	<button
		type="button"
		class="btn btn-ghost"
		disabled={loading || !canClear}
		onclick={onClearFilters}
	>
		Clear
	</button>
</form>

<style>
	.orion-reader-discovery-search {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 10.5rem), 1fr));
		align-items: center;
		gap: 0.55rem;
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding-bottom: 1rem;
	}

	@media (max-width: 80rem) {
		.orion-reader-discovery-search {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}

		.orion-reader-discovery-search .btn {
			width: 100%;
		}
	}

	@media (max-width: 48rem) {
		.orion-reader-discovery-search {
			grid-template-columns: 1fr;
		}
	}
</style>
