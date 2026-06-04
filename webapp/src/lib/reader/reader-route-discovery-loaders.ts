import {
	readerFacetValuesForLanguage,
	readerAuthorMatchesId,
	type ReaderRouteState
} from '$lib/reader';
import { readerIndexStatsFromSections } from '$lib/reader/index-stats';
import {
	readerFacetValues,
	readerSyntheticAuthorFromRoute,
	upsertReaderAuthor
} from '$lib/reader/page-authors';
import { fetchReaderApi, readerAuthorSectionsUrl, readerAuthorsUrl, readerFacetsUrl, readerShelvesUrl, readerTextSearchUrl, readerWorksUrl } from '$lib/reader/reader-api';
import type { ReaderRouteOverrides } from '$lib/reader/page-routing';
import type { ReaderLoadingKey } from '$lib/reader/loading-timers';
import type {
	ReaderAuthor,
	ReaderAuthorSection,
	ReaderAuthorSectionsResponse,
	ReaderAuthorsResponse,
	ReaderFacet,
	ReaderFacetsResponse,
	ReaderIndexStats,
	ReaderShelvesResponse,
	ReaderSearchResponse,
	ReaderWorksResponse
} from '$lib/reader';
import type { ReaderHistoryMode } from './reader-route-workspace';

type ReaderRouteDiscoveryLoaderState = Record<string, unknown>;

type ReaderRouteDiscoveryLoaderDeps = {
	readerLoadingTimers: {
		start: (kind: ReaderLoadingKey) => void;
		stop: (kind: ReaderLoadingKey) => void;
	};
	updateReaderUrl: (overrides?: ReaderRouteOverrides, historyMode?: ReaderHistoryMode) => void;
	saveReaderIndexState: () => void;
	upsertReaderIndexStats: (stats: ReaderIndexStats) => void;
	scrollReaderResultsIntoView: () => void;
};

export type ReaderRouteDiscoveryLoaders = {
	loadFacets: () => Promise<void>;
	loadShelves: () => Promise<void>;
	loadAuthorSections: (historyMode?: ReaderHistoryMode) => Promise<void>;
	loadAuthors: (
		cursor?: string | null,
		historyMode?: ReaderHistoryMode,
		loadingAlreadyStarted?: boolean
	) => Promise<void>;
	findAuthorById: (authorId: string) => ReaderAuthor | null;
	findAuthorByQuery: (authorId: string, authorName: string) => Promise<ReaderAuthor | null>;
	resolveRouteAuthor: (authorId: string, authorName?: string) => Promise<ReaderAuthor | null>;
	searchWorks: (
		cursor?: string | null,
		authorId?: string,
		historyMode?: ReaderHistoryMode,
		authorName?: string
	) => Promise<void>;
	searchReaderText: (cursor?: string | null, historyMode?: ReaderHistoryMode) => Promise<void>;
};

const DEFAULT_DISCOVERY_SORT: ReaderRouteState['discoverySort'] = 'global-popularity';

export function createReaderRouteDiscoveryLoaders(
	state: ReaderRouteDiscoveryLoaderState,
	deps: ReaderRouteDiscoveryLoaderDeps
): ReaderRouteDiscoveryLoaders {
	const stateBag = state as Record<string, any>;

	async function loadFacets() {
		if (!stateBag.catalogId) return;

		try {
			const { response, data } = await fetchReaderApi<ReaderFacetsResponse>(
				readerFacetsUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader facets failed.');
			stateBag.facets = data.items as ReaderFacet[];
			const discoveryTags = readerFacetValuesForLanguage(
				readerFacetValues(stateBag.facets as ReaderFacet[], 'discovery_tags'),
				stateBag.language
			);
			if (
				stateBag.discoveryTag &&
				!discoveryTags.some((tag: { id: string }) => tag.id === stateBag.discoveryTag)
			) {
				stateBag.discoveryTag = '';
			}
			if (stateBag.discoverySort === 'popularity') stateBag.discoverySort = DEFAULT_DISCOVERY_SORT;
			deps.saveReaderIndexState();
		} catch {
			stateBag.facets = [];
		}
	}

	async function loadShelves() {
		if (!stateBag.catalogId) return;
		stateBag.shelvesLoading = true;
		deps.readerLoadingTimers.start('shelves');
		try {
			const { response, data } = await fetchReaderApi<ReaderShelvesResponse>(
				readerShelvesUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader shelves failed.');
			stateBag.discoveryShelves = data.items;
			deps.saveReaderIndexState();
		} catch {
			stateBag.discoveryShelves = [];
		} finally {
			stateBag.shelvesLoading = false;
			deps.readerLoadingTimers.stop('shelves');
		}
	}

	async function loadAuthorSections(historyMode: ReaderHistoryMode = 'replace') {
		stateBag.authorsLoading = true;
		deps.readerLoadingTimers.start('authors');
		stateBag.authorsError = '';
		const authorsPromise = !stateBag.activeAuthorSection
			? loadAuthors(stateBag.authorsCursorParam, historyMode, true)
			: null;
		try {
			const { response, data } = await fetchReaderApi<ReaderAuthorSectionsResponse>(
				readerAuthorSectionsUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader author sections failed.');
			const sections = data.items;
			stateBag.authorSections = sections;
			deps.upsertReaderIndexStats(readerIndexStatsFromSections(stateBag.language, stateBag.catalogId, sections));
			if (
				stateBag.activeAuthorSection &&
				!sections.some((section: ReaderAuthorSection) => section.key === stateBag.activeAuthorSection)
			) {
				stateBag.activeAuthorSection = '';
			}
			deps.saveReaderIndexState();
			if (authorsPromise) await authorsPromise;
			else await loadAuthors(stateBag.authorsCursorParam, historyMode, true);
		} catch (error) {
			const sectionError =
				error instanceof Error ? error.message : 'Reader author sections failed.';
			stateBag.authorSections = [];
			if (authorsPromise) {
				await authorsPromise;
				if (!stateBag.authors.length && !stateBag.authorsError) {
					stateBag.authorsError = sectionError;
				}
			} else {
				stateBag.authorsError = sectionError;
			}
		} finally {
			stateBag.authorsLoading = false;
			deps.readerLoadingTimers.stop('authors');
		}
	}

	async function loadAuthors(
		cursor?: string | null,
		historyMode: ReaderHistoryMode = 'replace',
		loadingAlreadyStarted = false
	) {
		stateBag.authorsLoading = true;
		if (!loadingAlreadyStarted) deps.readerLoadingTimers.start('authors');
		stateBag.authorsError = '';
		if (!cursor) {
			stateBag.authors = [];
			stateBag.selectedAuthor = null;
			stateBag.works = [];
		}
		try {
			const { response, data } = await fetchReaderApi<ReaderAuthorsResponse>(
				readerAuthorsUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					section: stateBag.activeAuthorSection,
					query: stateBag.activeAuthorSection ? '' : stateBag.workQuery,
					agentKind: stateBag.authorAgentKind,
					historicity: stateBag.authorHistoricity,
					sort: !stateBag.activeAuthorSection && !stateBag.workQuery.trim() ? 'prominence' : '',
					cursor
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader authors failed.');
			stateBag.authors = data.items;
			stateBag.authorsNextCursor = data.pagination?.next_cursor ?? null;
			stateBag.authorsPrevCursor = data.pagination?.prev_cursor ?? null;
			stateBag.authorsCursorParam = cursor ?? null;
			deps.saveReaderIndexState();
			deps.updateReaderUrl({}, historyMode);
		} catch (error) {
			stateBag.authorsError = error instanceof Error ? error.message : 'Reader authors failed.';
		} finally {
			stateBag.authorsLoading = false;
			if (!loadingAlreadyStarted) {
				deps.readerLoadingTimers.stop('authors');
			}
		}
	}

	function findAuthorById(authorId: string) {
		const authors = (stateBag.authors as ReaderAuthor[]) ?? [];
		return authors.find((author) => readerAuthorMatchesId(author, authorId)) ?? null;
	}

	async function findAuthorByQuery(authorId: string, authorName: string) {
		if (!authorName.trim()) return null;
		const { response, data } = await fetchReaderApi<ReaderAuthorsResponse>(
			readerAuthorsUrl({ catalogId: stateBag.catalogId, language: stateBag.language, query: authorName })
		);
		if (!response.ok) return null;
		return data.items.find((author) => readerAuthorMatchesId(author, authorId)) ?? null;
	}

	function upsertAuthor(author: ReaderAuthor) {
		stateBag.authors = upsertReaderAuthor(stateBag.authors as ReaderAuthor[], author);
	}

	async function resolveRouteAuthor(authorId: string, authorName?: string) {
		const existing = findAuthorById(authorId);
		if (existing) return existing;

		const resolved = await findAuthorByQuery(authorId, authorName ?? '');
		if (resolved) {
			upsertAuthor(resolved);
			return resolved;
		}

		if (!authorName) return null;
		const synthetic = readerSyntheticAuthorFromRoute(authorId, authorName, stateBag.language);
		upsertAuthor(synthetic);
		return synthetic;
	}

	function syncSelectedAuthorWorkCount(authorId: string, workCount: number) {
		const selectedAuthor = stateBag.selectedAuthor as ReaderAuthor | null;
		if (!selectedAuthor || !readerAuthorMatchesId(selectedAuthor, authorId) || !workCount) return;
		const updated = {
			...selectedAuthor,
			work_count: Math.max(selectedAuthor.work_count, workCount)
		};
		stateBag.selectedAuthor = updated;
		upsertAuthor(updated);
	}

	async function searchWorks(
		cursor?: string | null,
		authorId?: string,
		historyMode: ReaderHistoryMode = 'replace',
		authorName?: string
	) {
		stateBag.libraryLoading = true;
		deps.readerLoadingTimers.start('library');
		stateBag.libraryError = '';
		if (!cursor) {
			stateBag.selectedWork = null;
			stateBag.contents = [];
			stateBag.selectedSegment = null;
			stateBag.pageSegments = [];
			stateBag.navigation = { previous: null, next: null };
			stateBag.pageNextCursor = null;
			stateBag.pagePrevCursor = null;
			stateBag.selectedWord = '';
		}
		try {
			const { response, data: initialData } = await fetchReaderApi<ReaderWorksResponse>(
				readerWorksUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					authorId: authorId || stateBag.discoveryAuthorId,
					authorName,
					query: stateBag.workQuery,
					group: !authorId ? stateBag.discoveryGroup : '',
					tag: !authorId ? stateBag.discoveryTag : '',
					sort: !authorId ? stateBag.discoverySort : '',
					collection: stateBag.activeCollection,
					cursor
				})
			);
			let data = initialData;
			if (!response.ok) throw new Error(data.error || 'Reader work search failed.');
			if (authorName && authorId && !data.items.length && !cursor) {
				const { response: authorResponse, data: authorData } =
					await fetchReaderApi<ReaderWorksResponse>(
						readerWorksUrl({
							catalogId: stateBag.catalogId,
							language: stateBag.language,
							authorName,
							collection: stateBag.activeCollection
						})
					);
				if (authorResponse.ok && authorData.items.length) data = authorData;
			}
			if (authorName && !authorId && !data.items.length && !cursor) {
				const { response: fallbackResponse, data: fallbackData } =
					await fetchReaderApi<ReaderWorksResponse>(
						readerWorksUrl({
							catalogId: stateBag.catalogId,
							language: stateBag.language,
							query: authorName,
							collection: stateBag.activeCollection
						})
					);
				if (fallbackResponse.ok && fallbackData.items.length) data = fallbackData;
			}
			stateBag.works = data.items;
			stateBag.totalFiltered = data.pagination?.total_filtered ?? data.items.length;
			stateBag.worksNextCursor = data.pagination?.next_cursor ?? null;
			stateBag.worksPrevCursor = data.pagination?.prev_cursor ?? null;
			stateBag.worksCursorParam = cursor ?? null;
			if (authorId) stateBag.routeAuthorId = authorId;
			else stateBag.routeAuthorId = '';
			stateBag.routeAuthorName = authorName ?? '';
			if (authorId) syncSelectedAuthorWorkCount(authorId, data.items.length);
			deps.saveReaderIndexState();
			deps.updateReaderUrl({}, historyMode);
			if (data.items.length && historyMode === 'push') {
				deps.scrollReaderResultsIntoView();
			}
		} catch (error) {
			stateBag.libraryError = error instanceof Error ? error.message : 'Reader work search failed.';
		} finally {
			stateBag.libraryLoading = false;
			deps.readerLoadingTimers.stop('library');
		}
	}

	async function searchReaderText(cursor?: string | null, historyMode: ReaderHistoryMode = 'replace') {
		const query = String(stateBag.textQuery).trim();
		if (!query) {
			stateBag.textSearchResults = [];
			stateBag.textSearchQueryCandidates = [];
			stateBag.textSearchNextCursor = null;
			stateBag.textSearchPrevCursor = null;
			stateBag.textSearchCursorParam = null;
			deps.updateReaderUrl({}, historyMode);
			return;
		}
		stateBag.textSearchLoading = true;
		deps.readerLoadingTimers.start('textSearch');
		stateBag.textSearchError = '';
		try {
			const { response, data } = await fetchReaderApi<ReaderSearchResponse>(
				readerTextSearchUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					query,
					searchMode: stateBag.textSearchMode,
					collection: stateBag.activeCollection,
					cursor
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader text search failed.');
			stateBag.textSearchResults = data.items;
			stateBag.textSearchQueryCandidates = data.request.query_candidates ?? [];
			stateBag.textSearchNextCursor = data.pagination?.next_cursor ?? null;
			stateBag.textSearchPrevCursor = data.pagination?.prev_cursor ?? null;
			stateBag.textSearchCursorParam = cursor ?? null;
			deps.saveReaderIndexState();
			deps.updateReaderUrl({}, historyMode);
		} catch (error) {
			stateBag.textSearchError = error instanceof Error ? error.message : 'Reader text search failed.';
		} finally {
			stateBag.textSearchLoading = false;
			deps.readerLoadingTimers.stop('textSearch');
		}
	}

	return {
		loadFacets,
		loadShelves,
		loadAuthorSections,
		loadAuthors,
		findAuthorById,
		findAuthorByQuery,
		resolveRouteAuthor,
		searchWorks,
		searchReaderText
	};
}
