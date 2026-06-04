<script lang="ts">
	import { Search } from 'lucide-svelte';
	import type { ReaderFacetValue } from '$lib/reader';

	type Props = {
		workQuery: string;
		authorAgentKind: string;
		authorHistoricity: string;
		authorAgentKinds: ReaderFacetValue[];
		authorHistoricityStatuses: ReaderFacetValue[];
		loading: boolean;
		canSearch: boolean;
		onWorkQueryInput: (value: string) => void;
		onAuthorAgentKindChange: (value: string) => void;
		onAuthorHistoricityChange: (value: string) => void;
		onApplyFilters: () => void;
		onSubmitSearch: () => void;
	};

	let {
		workQuery,
		authorAgentKind,
		authorHistoricity,
		authorAgentKinds,
		authorHistoricityStatuses,
		loading,
		canSearch,
		onWorkQueryInput,
		onAuthorAgentKindChange,
		onAuthorHistoricityChange,
		onApplyFilters,
		onSubmitSearch
	}: Props = $props();

	function handleWorkQueryInput(event: Event) {
		onWorkQueryInput((event.currentTarget as HTMLInputElement).value);
	}

	function handleAgentKindChange(event: Event) {
		onAuthorAgentKindChange((event.currentTarget as HTMLSelectElement).value);
		onApplyFilters();
	}

	function handleHistoricityChange(event: Event) {
		onAuthorHistoricityChange((event.currentTarget as HTMLSelectElement).value);
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
			placeholder="Search authors"
			autocomplete="off"
			oninput={handleWorkQueryInput}
		/>
	</label>
	<select class="select select-bordered" value={authorAgentKind} onchange={handleAgentKindChange}>
		<option value="">All author kinds</option>
		{#each authorAgentKinds as kind}
			<option value={kind.id}>{kind.label}</option>
		{/each}
	</select>
	<select
		class="select select-bordered"
		value={authorHistoricity}
		onchange={handleHistoricityChange}
	>
		<option value="">All historicity</option>
		{#each authorHistoricityStatuses as status}
			<option value={status.id}>{status.label}</option>
		{/each}
	</select>
	<button class="btn btn-neutral" disabled={loading || !canSearch}>
		<Search size={16} />
		{loading ? 'Searching' : 'Search'}
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
