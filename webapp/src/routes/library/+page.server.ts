import {
	readerCollections,
	readerLibraryWatchlist,
	readerSourceIndex
} from '$lib/server/reader-cli';

const INITIAL_SOURCE_INDEX_LIMIT = 100;

export async function load() {
	try {
		const [collections, sourceIndex, watchlist] = await Promise.all([
			readerCollections(null, { timeoutMs: 300_000 }),
			readerSourceIndex({
				catalogId: null,
				limit: INITIAL_SOURCE_INDEX_LIMIT,
				options: { timeoutMs: 300_000 }
			}),
			readerLibraryWatchlist({ limit: 100, options: { timeoutMs: 120_000 } })
		]);
		return {
			collections: (collections as { items?: unknown[] }).items ?? [],
			sourceRows: sourceIndex.items ?? [],
			sourceRowLimit: INITIAL_SOURCE_INDEX_LIMIT,
			sourcePagination: sourceIndex.pagination,
			watchlistTargets: watchlist.items ?? [],
			loadError: ''
		};
	} catch (cause) {
		return {
			collections: [],
			sourceRows: [],
			sourceRowLimit: INITIAL_SOURCE_INDEX_LIMIT,
			sourcePagination: undefined,
			watchlistTargets: [],
			loadError: cause instanceof Error ? cause.message : 'Unable to load the library index.'
		};
	}
}
