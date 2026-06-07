import {
	readerCollections,
	readerLibraryWatchlist,
	readerSourceIndex
} from '$lib/server/reader-cli';

export async function load() {
	try {
		const [collections, sourceIndex, watchlist] = await Promise.all([
			readerCollections(null, { timeoutMs: 300_000 }),
			readerSourceIndex({ catalogId: null, limit: 100, options: { timeoutMs: 300_000 } }),
			readerLibraryWatchlist({ limit: 100, options: { timeoutMs: 120_000 } })
		]);
		return {
			collections: (collections as { items?: unknown[] }).items ?? [],
			sourceRows: sourceIndex.items ?? [],
			watchlistTargets: watchlist.items ?? [],
			loadError: ''
		};
	} catch (cause) {
		return {
			collections: [],
			sourceRows: [],
			watchlistTargets: [],
			loadError: cause instanceof Error ? cause.message : 'Unable to load the library index.'
		};
	}
}
