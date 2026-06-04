<script lang="ts">
	import { FileSearch, Search } from 'lucide-svelte';
	import type { ReaderSearchMode } from '$lib/reader';

	type Props = {
		textQuery: string;
		textSearchMode: ReaderSearchMode;
		loading: boolean;
		canSearch: boolean;
		canClear: boolean;
		onTextQueryInput: (value: string) => void;
		onTextSearchModeChange: (mode: ReaderSearchMode) => void;
		onSubmitSearch: () => void;
		onClearSearch: () => void;
	};

	let {
		textQuery,
		textSearchMode,
		loading,
		canSearch,
		canClear,
		onTextQueryInput,
		onTextSearchModeChange,
		onSubmitSearch,
		onClearSearch
	}: Props = $props();

	function handleQueryInput(event: Event) {
		onTextQueryInput((event.currentTarget as HTMLInputElement).value);
	}

	function handleModeChange(event: Event) {
		onTextSearchModeChange((event.currentTarget as HTMLSelectElement).value as ReaderSearchMode);
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
		<FileSearch size={16} class="text-base-content/45" />
		<input
			value={textQuery}
			type="search"
			placeholder="Search inside texts"
			autocomplete="off"
			oninput={handleQueryInput}
		/>
	</label>
	<select class="select select-bordered" value={textSearchMode} onchange={handleModeChange}>
		<option value="fuzzy">Fuzzy</option>
		<option value="keyword">Keyword</option>
		<option value="phrase">Phrase</option>
		<option value="exact">Exact</option>
	</select>
	<button class="btn btn-neutral" disabled={loading || !canSearch}>
		<Search size={16} />
		{loading ? 'Searching' : 'Search'}
	</button>
	<button
		type="button"
		class="btn btn-ghost"
		disabled={loading || !canClear}
		onclick={onClearSearch}
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
