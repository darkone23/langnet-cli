<script lang="ts">
	import {
		BookOpen,
		Database,
		FileSearch,
		Filter,
		LibraryBig,
		Search,
		Telescope
	} from 'lucide-svelte';
	import {
		fetchReaderApi,
		readerCollectionsUrl,
		readerLibraryWatchlistUrl,
		readerSourceIndexUrl
	} from '$lib/reader/reader-api';
	import type { ReaderCatalogLanguage, ReaderSourceIndexResponse } from '$lib/reader';
	import { readerIsDeprecatedWorkRef, readerSourceIndexPublicKey } from '$lib/reader';
	import {
		findReaderWatchlistMatches,
		type ReaderWatchlistResponse,
		type ReaderWatchlistTarget
	} from '$lib/reader/library-watchlist';
	import { uiCopy } from '$lib/ui-copy';

	type ReaderCollection = {
		collection_id: string;
		work_count?: number;
		edition_count?: number;
		segment_count?: number;
		token_count?: number;
		languages?: ReaderCatalogLanguage[];
	};

	type ReaderCollectionsResponse = {
		schema_version: string;
		mode: 'collections';
		items: ReaderCollection[];
		error?: string;
	};

	const nav = uiCopy.publicSite.nav;
	let { data } = $props();
	const initialData = () => data;
	const initialCollections = (initialData().collections ?? []) as ReaderCollection[];
	const initialSourceRows = (initialData().sourceRows ?? []) as ReaderSourceIndexResponse['items'];
	const initialSourceRowLimit = Number(initialData().sourceRowLimit ?? 20000);
	const initialSourcePagination = initialData().sourcePagination as
		| ReaderSourceIndexResponse['pagination']
		| undefined;
	const initialWatchlistTargets = (initialData().watchlistTargets ?? []) as ReaderWatchlistTarget[];
	const initialLoadError = initialData().loadError ?? '';
	const SOURCE_INDEX_PAGE_SIZE = 100;
	const languageOptions: { value: '' | ReaderCatalogLanguage; label: string }[] = [
		{ value: '', label: 'All languages' },
		{ value: 'lat', label: 'Latin' },
		{ value: 'grc', label: 'Greek' },
		{ value: 'san', label: 'Sanskrit' },
		{ value: 'eng', label: 'English' },
		{ value: 'und', label: 'Unknown language' }
	];

	let collections = $state<ReaderCollection[]>(initialCollections);
	let rows = $state<ReaderSourceIndexResponse['items']>(initialSourceRows);
	let sourceRowLimit = $state(initialSourceRowLimit);
	let sourcePagination = $state<ReaderSourceIndexResponse['pagination'] | undefined>(
		initialSourcePagination
	);
	let sourcePageCursor = $state<string | null>(null);
	let sourcePageNumber = $state(1);
	let watchlistTargets = $state<ReaderWatchlistTarget[]>(initialWatchlistTargets);
	let selectedCollection = $state('all');
	let selectedLanguage = $state<'' | ReaderCatalogLanguage>('');
	let query = $state('');
	let pendingQuery = $state('');
	let loading = $state(false);
	let error = $state(initialLoadError);
	let searched = $state(false);

	let selectedCollectionLabel = $derived(
		selectedCollection === 'all' ? 'All collections' : selectedCollection.replaceAll('_', ' ')
	);
	let totalSegments = $derived(rows.reduce((sum, item) => sum + item.segment_count, 0));
	let totalWords = $derived(rows.reduce((sum, item) => sum + item.token_count, 0));
	let watchlistMatches = $derived(findReaderWatchlistMatches(watchlistTargets, query || pendingQuery));
	let watchlistPreview = $derived(
		watchlistMatches.length > 0 ? watchlistMatches : watchlistTargets.slice(0, 6)
	);
	let hasPreviousSourcePage = $derived(sourcePageNumber > 1);
	let hasNextSourcePage = $derived(Boolean(sourcePagination?.next_cursor));
	let sourcePageNumbers = $derived(
		Array.from(
			new Set(
				[1, sourcePageNumber - 1, sourcePageNumber, sourcePageNumber + 1].filter(
					(page) => page >= 1 && (page <= sourcePageNumber || hasNextSourcePage)
				)
			)
		)
	);

	async function loadInitial() {
		loading = true;
		error = '';
		try {
			const [collectionPayload, sourcePayload, watchlistPayload] = await Promise.all([
				fetchReaderApi<ReaderCollectionsResponse>(readerCollectionsUrl()),
				fetchReaderApi<ReaderSourceIndexResponse>(
					readerSourceIndexUrl({ limit: SOURCE_INDEX_PAGE_SIZE })
				),
				fetchReaderApi<ReaderWatchlistResponse>(readerLibraryWatchlistUrl({ limit: 100 }))
			]);
			if (collectionPayload.data.error) throw new Error(collectionPayload.data.error);
			if (sourcePayload.data.error) throw new Error(sourcePayload.data.error);
			if (watchlistPayload.data.error) throw new Error(watchlistPayload.data.error);
			collections = collectionPayload.data.items ?? [];
			rows = sourcePayload.data.items ?? [];
			sourceRowLimit = SOURCE_INDEX_PAGE_SIZE;
			sourcePagination = sourcePayload.data.pagination;
			sourcePageCursor = null;
			sourcePageNumber = 1;
			watchlistTargets = watchlistPayload.data.items ?? [];
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Unable to load the library index.';
		} finally {
			loading = false;
		}
	}

	async function loadSourceIndex(cursor: string | null = null, pageNumber = 1) {
		loading = true;
		error = '';
		searched = Boolean(query.trim() || selectedCollection !== 'all' || selectedLanguage);
		try {
			const payload = await fetchReaderApi<ReaderSourceIndexResponse>(
				readerSourceIndexUrl({
					collection: selectedCollection,
					language: (selectedLanguage || null) as ReaderCatalogLanguage | null,
					query,
					cursor,
					limit: SOURCE_INDEX_PAGE_SIZE
				})
			);
			if (payload.data.error) throw new Error(payload.data.error);
			rows = payload.data.items ?? [];
			sourceRowLimit = SOURCE_INDEX_PAGE_SIZE;
			sourcePagination = payload.data.pagination;
			sourcePageCursor = cursor;
			sourcePageNumber = pageNumber;
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Unable to search the library index.';
			rows = [];
		} finally {
			loading = false;
		}
	}

	function selectCollection(collectionId: string) {
		selectedCollection = collectionId;
		void loadSourceIndex(null, 1);
	}

	function submitSearch() {
		query = pendingQuery.trim();
		void loadSourceIndex(null, 1);
	}

	function clearSearch() {
		pendingQuery = '';
		query = '';
		selectedCollection = 'all';
		selectedLanguage = '';
		void loadSourceIndex(null, 1);
	}

	function openSourcePage(pageNumber: number) {
		if (pageNumber === sourcePageNumber) return;
		if (pageNumber === 1) {
			void loadSourceIndex(null, 1);
			return;
		}
		const currentOffset = Number.parseInt(sourcePageCursor ?? '0', 10) || 0;
		const targetOffset = Math.max(0, (pageNumber - 1) * SOURCE_INDEX_PAGE_SIZE);
		if (pageNumber === sourcePageNumber + 1 && sourcePagination?.next_cursor) {
			void loadSourceIndex(sourcePagination.next_cursor, pageNumber);
			return;
		}
		if (pageNumber === sourcePageNumber - 1) {
			const previousOffset = Math.max(0, currentOffset - SOURCE_INDEX_PAGE_SIZE);
			void loadSourceIndex(previousOffset ? String(previousOffset) : null, pageNumber);
			return;
		}
		void loadSourceIndex(targetOffset ? String(targetOffset) : null, pageNumber);
	}

	function openPreviousSourcePage() {
		if (!hasPreviousSourcePage) return;
		openSourcePage(sourcePageNumber - 1);
	}

	function openNextSourcePage() {
		if (!sourcePagination?.next_cursor) return;
		void loadSourceIndex(sourcePagination.next_cursor, sourcePageNumber + 1);
	}

	function formatNumber(value?: number) {
		return new Intl.NumberFormat('en-US').format(value ?? 0);
	}

	function readerHref(workId: string) {
		return `/reader?work=${encodeURIComponent(workId)}`;
	}

	function workPortalHref(workId: string) {
		return `/library/work/${encodeURIComponent(workId)}`;
	}

	function authorPortalHref(authorId: string | null, author: string) {
		const ref = authorId || author;
		return ref ? `/library/author/${encodeURIComponent(ref)}` : '';
	}

	function rowWorkRef(row: ReaderSourceIndexResponse['items'][number]) {
		return row.canonical_text_id || row.work_id;
	}

	function visibleCanonicalRef(value: string | null | undefined) {
		return value && !readerIsDeprecatedWorkRef(value) ? value : '';
	}
</script>

<svelte:head>
	<title>Library | {uiCopy.app.title}</title>
	<meta
		name="description"
		content="Explore the LangNet reader catalog by source collection, author, title, language, and provenance."
	/>
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen">
	<header class="navbar border-base-300 bg-base-100 border-b px-4 lg:px-8">
		<div class="flex-1">
			<a href="/" class="flex items-center gap-3 font-semibold">
				<Telescope size={22} />
				<span>{uiCopy.app.name}</span>
			</a>
		</div>
		<nav class="hidden gap-2 md:flex">
			<a class="btn btn-sm btn-ghost" href="/about">About</a>
			<a class="btn btn-sm btn-ghost" href="/reader">Reader</a>
			<a class="btn btn-sm btn-ghost" href="/evidence">{nav.evidence}</a>
			<a class="btn btn-sm btn-primary" href="/q">{nav.openLookup}</a>
		</nav>
	</header>

	<section
		class="from-base-100 via-base-200 to-info/10 border-base-300 border-b bg-gradient-to-br px-6 py-14 lg:px-12 lg:py-20"
	>
		<div class="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1fr_0.7fr] lg:items-end">
			<div>
				<LibraryBig class="text-info mb-5" size={44} />
				<p class="text-info mb-4 text-sm font-bold tracking-[0.35em] uppercase">
					Source-backed catalog
				</p>
				<h1 class="max-w-4xl text-4xl leading-tight font-black tracking-tight lg:text-6xl">
					Explore what is actually in the library.
				</h1>
				<p class="text-base-content/75 mt-6 max-w-3xl text-lg leading-8">
					Browse imported works by collection, language, title, author, source id, and raw
					provenance. This is the audit surface for questions like “do we have Axiochus?” or
					“what came from OpenGreekAndLatin CSEL?”
				</p>
			</div>
			<div class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm">
				<div class="grid grid-cols-3 gap-3 text-center">
					<div class="bg-base-200 rounded-2xl p-4">
						<p class="text-2xl font-black">{formatNumber(rows.length)}</p>
						<p class="text-base-content/60 text-xs uppercase">rows shown</p>
					</div>
					<div class="bg-base-200 rounded-2xl p-4">
						<p class="text-2xl font-black">{formatNumber(totalSegments)}</p>
						<p class="text-base-content/60 text-xs uppercase">segments</p>
					</div>
					<div class="bg-base-200 rounded-2xl p-4">
						<p class="text-2xl font-black">{formatNumber(totalWords)}</p>
						<p class="text-base-content/60 text-xs uppercase">words</p>
					</div>
				</div>
			</div>
		</div>
	</section>

	<section class="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[320px_1fr] lg:px-12">
		<aside class="space-y-5">
			<form
				class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm"
				onsubmit={(event) => {
					event.preventDefault();
					submitSearch();
				}}
			>
				<div class="flex items-center gap-2">
					<Search class="text-primary" size={22} />
					<h2 class="text-xl font-black">Search</h2>
				</div>
				<label class="form-control mt-4">
					<span class="label-text">Author, title, source, path, CTS, canonical id</span>
					<input
						class="input input-bordered mt-2"
						bind:value={pendingQuery}
						placeholder="Try Dionysius, CSEL, Odyssey, Vulgate"
					/>
				</label>
				<label class="form-control mt-3">
					<span class="label-text">Language</span>
					<select class="select select-bordered mt-2" bind:value={selectedLanguage}>
						{#each languageOptions as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</label>
				<div class="mt-4 flex gap-2">
					<button class="btn btn-primary flex-1" type="submit">
						<FileSearch size={18} />
						Search
					</button>
					<button class="btn btn-ghost" type="button" onclick={clearSearch}>Clear</button>
				</div>
			</form>

			<div class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm">
				<div class="flex items-center gap-2">
					<Database class="text-secondary" size={22} />
					<h2 class="text-xl font-black">Collections</h2>
				</div>
				<div class="mt-4 max-h-[34rem] space-y-2 overflow-auto pr-1">
					<button
						class:selected={selectedCollection === 'all'}
						class="btn btn-sm w-full justify-between"
						class:btn-primary={selectedCollection === 'all'}
						class:btn-ghost={selectedCollection !== 'all'}
						onclick={() => selectCollection('all')}
					>
						<span>All collections</span>
						<span>{formatNumber(collections.reduce((sum, item) => sum + (item.work_count ?? 0), 0))}</span>
					</button>
					{#each collections as collection}
						<button
							class="btn btn-sm w-full justify-between"
							class:btn-primary={selectedCollection === collection.collection_id}
							class:btn-ghost={selectedCollection !== collection.collection_id}
							onclick={() => selectCollection(collection.collection_id)}
						>
							<span class="truncate text-left">{collection.collection_id}</span>
							<span>{formatNumber(collection.work_count)}</span>
						</button>
					{/each}
				</div>
			</div>

			<div class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm">
				<div class="flex items-center gap-2">
					<Telescope class="text-accent" size={22} />
					<h2 class="text-xl font-black">Acquisition watchlist</h2>
				</div>
				<p class="text-base-content/60 mt-2 text-sm">
					Curated high-value targets from our corpus-building plan. Imported targets should
					resolve to catalog rows first; planned targets stay visible here as source work.
				</p>
				<div class="mt-4 space-y-3">
					{#each watchlistPreview as target}
						<article class="bg-base-200 rounded-2xl p-4">
							<div class="flex flex-wrap items-center gap-2">
								<span
									class="badge"
									class:badge-success={target.status === 'imported'}
									class:badge-warning={target.status !== 'imported'}
								>
									{target.status}
								</span>
								{#each target.languages as language}
									<span class="badge badge-outline">{language}</span>
								{/each}
							</div>
							<h3 class="mt-2 font-black">{target.displayName}</h3>
							<p class="text-base-content/65 mt-1 text-sm">{target.period}</p>
							<p class="text-base-content/55 mt-2 line-clamp-3 text-xs">{target.sourcePlan}</p>
						</article>
					{/each}
				</div>
			</div>
		</aside>

		<section class="min-w-0 space-y-5">
			<div class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm">
				<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
					<div>
						<div class="flex items-center gap-2">
							<Filter class="text-info" size={20} />
							<h2 class="text-2xl font-black">{selectedCollectionLabel}</h2>
						</div>
						<p class="text-base-content/60 mt-1 text-sm">
							{#if query}
								Searching for “{query}”
							{:else if searched}
								Filtered source-index rows
							{:else}
								Showing the first provenance rows from the current reader catalog
							{/if}
						</p>
						<p class="text-base-content/55 mt-2 text-sm">
							Page {sourcePageNumber}; showing up to {formatNumber(sourceRowLimit)} rows per page.
						</p>
					</div>
					<a class="btn btn-outline btn-sm" href="/reader">
						<BookOpen size={17} />
						Open Reader
					</a>
				</div>
			</div>

			{#if error}
				<div class="alert alert-error">
					<span>{error}</span>
				</div>
			{:else if loading}
				<div class="grid gap-4">
					{#each Array(5) as _}
						<div class="skeleton h-32 rounded-3xl"></div>
					{/each}
				</div>
			{:else if rows.length === 0}
				<div class="bg-base-100 border-base-300 rounded-[2rem] border p-8 shadow-sm">
					<h2 class="text-3xl font-black">No catalog rows found.</h2>
					<p class="text-base-content/70 mt-3 max-w-2xl">
						This means the current reader catalog does not expose a matching work or source row yet.
						Known acquisition targets are shown separately so planned or staged texts are not confused
						with imported reader works.
					</p>
					{#if watchlistMatches.length > 0}
						<div class="mt-6 grid gap-3 text-left">
							{#each watchlistMatches as target}
								<article class="bg-base-200 rounded-2xl p-4">
									<div class="flex flex-wrap items-center gap-2">
										<span class="badge badge-warning">{target.status}</span>
										{#each target.languages as language}
											<span class="badge badge-outline">{language}</span>
										{/each}
									</div>
									<h3 class="mt-3 text-xl font-black">{target.displayName}</h3>
									<p class="text-base-content/70 mt-1">{target.period} · {target.tradition}</p>
									<p class="mt-3 text-sm">{target.note}</p>
									<p class="text-base-content/55 mt-3 text-xs">
										Source plan: {target.sourcePlan}
									</p>
								</article>
							{/each}
						</div>
					{:else}
						<p class="text-base-content/60 mt-5 text-sm">
							Try a known target such as Eriugena, Pseudo-Dionysius, Aquinas, Bruno, Llull,
							Anselm, Descartes, or Axiochus.
						</p>
					{/if}
				</div>
			{:else}
				<div class="mb-3 flex flex-wrap items-center justify-between gap-3">
					<div class="join">
						<button
							class="btn btn-sm join-item"
							type="button"
							disabled={!hasPreviousSourcePage || loading}
							onclick={() => openSourcePage(1)}
						>
							First
						</button>
						<button
							class="btn btn-sm join-item"
							type="button"
							disabled={!hasPreviousSourcePage || loading}
							onclick={openPreviousSourcePage}
						>
							Previous
						</button>
						{#each sourcePageNumbers as page}
							<button
								class:btn-primary={page === sourcePageNumber}
								class="btn btn-sm join-item"
								type="button"
								disabled={loading}
								onclick={() => openSourcePage(page)}
							>
								{page}
							</button>
						{/each}
						<button
							class="btn btn-sm join-item"
							type="button"
							disabled={!hasNextSourcePage || loading}
							onclick={openNextSourcePage}
						>
							Next
						</button>
					</div>
					<p class="text-base-content/55 text-sm">
						{hasNextSourcePage
							? 'More source-index rows are available.'
							: 'End of the current source-index result set.'}
					</p>
				</div>
				<div class="bg-base-100 border-base-300 overflow-hidden rounded-[1.5rem] border shadow-sm">
					{#each rows as row}
						<details class="group border-base-300 border-b last:border-b-0">
							<summary
								class="hover:bg-base-200/70 grid cursor-pointer list-none gap-3 p-4 transition md:grid-cols-[1.2fr_0.8fr_0.8fr_auto] md:items-center"
							>
								<div class="min-w-0">
									<div class="mb-1 flex flex-wrap gap-2">
										<span class="badge badge-info">{row.language}</span>
										{#if row.file_status}
											<span class="badge badge-ghost">{row.file_status}</span>
										{/if}
										{#if row.source_witness_count > 1}
											<span class="badge badge-warning">{row.source_witness_count} witnesses</span>
										{/if}
									</div>
									<h3 class="truncate text-base font-black md:text-lg">{row.title}</h3>
									{#if authorPortalHref(row.author_id, row.author)}
										<a
											class="link-hover link text-base-content/65 block truncate text-sm"
											href={authorPortalHref(row.author_id, row.author)}
											onclick={(event) => event.stopPropagation()}
										>
											{row.author}
										</a>
									{:else}
										<p class="text-base-content/65 truncate text-sm">{row.author}</p>
									{/if}
								</div>
								<div class="text-sm">
									<p class="text-base-content/45 uppercase">Reader key</p>
									<p class="truncate font-semibold">{readerSourceIndexPublicKey(row)}</p>
								</div>
								<div class="text-sm">
									<p class="text-base-content/45 uppercase">Size</p>
									<p class="font-semibold">
										{formatNumber(row.segment_count)} seg · {formatNumber(row.token_count)} words
									</p>
								</div>
								<div class="flex items-center justify-between gap-3 md:justify-end">
									<span class="text-base-content/45 text-xs group-open:hidden">Expand</span>
									<span class="text-base-content/45 hidden text-xs group-open:inline">Collapse</span>
									<a
										class="btn btn-primary btn-xs"
										href={workPortalHref(rowWorkRef(row))}
										onclick={(event) => event.stopPropagation()}
									>
										<LibraryBig size={15} />
										{uiCopy.readerNavigation.workEntry}
									</a>
								</div>
							</summary>
							<div class="bg-base-200/60 border-base-300 border-t px-4 py-4">
								<div class="grid gap-3 text-sm md:grid-cols-3">
									<div class="bg-base-100 rounded-2xl p-3">
										<p class="text-base-content/50 uppercase">Edition</p>
										<p class="mt-1 font-semibold">{row.edition_label}</p>
									</div>
									<div class="bg-base-100 rounded-2xl p-3">
										<p class="text-base-content/50 uppercase">Reader key</p>
										<p class="mt-1 break-all font-semibold">{readerSourceIndexPublicKey(row)}</p>
									</div>
									<div class="bg-base-100 rounded-2xl p-3">
										<p class="text-base-content/50 uppercase">Artifact count</p>
										<p class="mt-1 font-semibold">{formatNumber(row.artifact_count)}</p>
									</div>
								</div>
								<div class="mt-4 flex flex-wrap gap-2">
									<a class="btn btn-primary btn-sm" href={workPortalHref(rowWorkRef(row))}>
										<LibraryBig size={16} />
										{uiCopy.readerNavigation.inspectWorkEntry}
									</a>
									<a class="btn btn-outline btn-sm" href={readerHref(rowWorkRef(row))}>
										<BookOpen size={16} />
										{uiCopy.readerNavigation.enterReaderDesk}
									</a>
									{#if authorPortalHref(row.author_id, row.author)}
										<a class="btn btn-ghost btn-sm" href={authorPortalHref(row.author_id, row.author)}>
											{uiCopy.readerNavigation.authorEntry}
										</a>
									{/if}
								</div>
								<div class="text-base-content/55 mt-4 space-y-1 text-xs">
									<p class="break-all">Path: {row.source_path}</p>
									{#if visibleCanonicalRef(row.canonical_text_id)}
										<p class="break-all">Canonical: {row.canonical_text_id}</p>
									{/if}
									{#if row.source_witness_collections}
										<p class="break-all">Witnesses: {row.source_witness_collections}</p>
									{/if}
								</div>
							</div>
						</details>
					{/each}
				</div>
				<div class="mt-3 flex flex-wrap items-center justify-between gap-3">
					<div class="join">
						<button
							class="btn btn-sm join-item"
							type="button"
							disabled={!hasPreviousSourcePage || loading}
							onclick={() => openSourcePage(1)}
						>
							First
						</button>
						<button
							class="btn btn-sm join-item"
							type="button"
							disabled={!hasPreviousSourcePage || loading}
							onclick={openPreviousSourcePage}
						>
							Previous
						</button>
						<button
							class="btn btn-sm join-item"
							type="button"
							disabled={!hasNextSourcePage || loading}
							onclick={openNextSourcePage}
						>
							Next
						</button>
					</div>
					<p class="text-base-content/55 text-sm">Page {sourcePageNumber}</p>
				</div>
			{/if}
		</section>
	</section>
</main>
