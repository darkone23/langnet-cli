<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount, tick } from 'svelte';
	import {
		BookOpen,
		Database,
		Feather,
		FileSearch,
		Moon,
		ScrollText,
		Search,
		Sun,
		Telescope
	} from 'lucide-svelte';
	import { fetchPayload } from '$lib/msgpack';
	import {
		buildReaderTokenParts,
		buildReaderRouteSearch,
		cleanReaderToken,
		parseReaderRouteState,
		readerAddressRouteValue,
		readerAuthorMatchesId,
		readerAuthorRouteStateFromWork,
		readerDiscoverySortValues,
		readerFacetValuesForLanguage,
		readerHasIndexStats,
		readerIndexSummaryLabel,
		readerIndexStatsKey,
		readerLanguageLabel,
		readerLoadingStatusLabel,
		readerPopularityLabel,
		readerSegmentDisplayText,
		readerShelfRouteState,
		readerWorkContributorLabels,
		readerWorkDisplayAuthor,
		readerWorkListDiscriminator,
		readerWorkListLabel,
		readerWorkDiscoveryTags,
		readerWorkRef,
		type ReaderAuthor,
		type ReaderAuthorSection,
		type ReaderAuthorSectionsResponse,
		type ReaderAuthorsResponse,
		type ReaderCatalog,
		type ReaderCatalogsResponse,
		type ReaderContentsResponse,
		type ReaderDiscoveryShelf,
		type ReaderFacet,
		type ReaderFacetValue,
		type ReaderFacetsResponse,
		type ReaderIndexStats,
		type ReaderNavigationTarget,
		type ReaderRouteState,
		type ReaderSearchMode,
		type ReaderSearchQueryCandidate,
		type ReaderSearchResponse,
		type ReaderSearchResult,
		type ReaderSegment,
		type ReaderShelvesResponse,
		type ReaderShowResponse,
		type ReaderTokenPart,
		type ReaderWork,
		type ReaderWorkResponse,
		type ReaderWorksResponse
	} from '$lib/reader';
	import { romanizeSearchTerm } from '$lib/search-romanization';
	import { languageModes, type LanguageMode } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type ReaderHistoryMode = 'push' | 'replace' | 'none';
	type ReaderIndexView = 'choose' | NonNullable<ReaderRouteState['readerView']>;
	type ReaderLoadingKey = 'shelves' | 'library' | 'authors' | 'textSearch' | 'contents' | 'segment';

	const readerIndexStorageKey = 'orion-reader-index-state:v6';
	const readerIndexStorageTtlMs = 2 * 60 * 60 * 1000;

	type StoredReaderIndexState = {
		version: 6;
		expiresAt: number;
		language: LanguageMode;
		catalogId: string;
		readerView: ReaderIndexView;
		activeAuthorSection: string;
		workQuery: string;
		textQuery: string;
		textSearchMode: ReaderSearchMode;
		discoveryGroup: string;
		discoveryTag: string;
		discoveryAuthorId: string;
		discoveryAuthorLabel: string;
		discoverySort: ReaderRouteState['discoverySort'];
		authorAgentKind: string;
		authorHistoricity: string;
		worksNextCursor: string | null;
		worksPrevCursor: string | null;
		authorsNextCursor: string | null;
		authorsPrevCursor: string | null;
		textSearchNextCursor: string | null;
		textSearchPrevCursor: string | null;
	};

	let theme = $state<'manuscript' | 'vespers'>('manuscript');
	let language = $state<LanguageMode>('grc');
	let catalogs = $state<ReaderCatalog[]>([]);
	let catalogDefaults = $state<Partial<Record<LanguageMode, string>>>({});
	let catalogId = $state('');
	let catalogError = $state('');
	let workQuery = $state('');
	let textQuery = $state('');
	let textSearchMode = $state<ReaderSearchMode>('fuzzy');
	let textSearchResults = $state<ReaderSearchResult[]>([]);
	let textSearchQueryCandidates = $state<ReaderSearchQueryCandidate[]>([]);
	let readerView = $state<ReaderIndexView>('choose');
	let facets = $state<ReaderFacet[]>([]);
	let discoveryShelves = $state<ReaderDiscoveryShelf[]>([]);
	let discoveryGroup = $state('');
	let discoveryTag = $state('');
	let discoveryAuthorId = $state('');
	let discoveryAuthorLabel = $state('');
	let discoverySort = $state<ReaderRouteState['discoverySort']>('global-popularity');
	let authorAgentKind = $state('');
	let authorHistoricity = $state('');
	let works = $state<ReaderWork[]>([]);
	let authorSections = $state<ReaderAuthorSection[]>([]);
	let readerIndexStats = $state<ReaderIndexStats[]>([]);
	let authors = $state<ReaderAuthor[]>([]);
	let selectedAuthor = $state<ReaderAuthor | null>(null);
	let selectedWork = $state<ReaderWork | null>(null);
	let contents = $state<ReaderSegment[]>([]);
	let selectedSegment = $state<ReaderSegment | null>(null);
	let pageSegments = $state<ReaderSegment[]>([]);
	let navigation = $state<{
		previous: ReaderNavigationTarget | null;
		next: ReaderNavigationTarget | null;
	}>({ previous: null, next: null });
	let addressInput = $state('Od. 3.74');
	let showAddressLookup = $state(false);
	let selectedWord = $state('');
	let shelvesLoading = $state(false);
	let libraryLoading = $state(false);
	let contentsLoading = $state(false);
	let segmentLoading = $state(false);
	let libraryError = $state('');
	let authorsLoading = $state(false);
	let textSearchLoading = $state(false);
	let shelvesLoadingElapsedSeconds = $state(0);
	let libraryLoadingElapsedSeconds = $state(0);
	let authorsLoadingElapsedSeconds = $state(0);
	let textSearchElapsedSeconds = $state(0);
	let contentsLoadingElapsedSeconds = $state(0);
	let segmentLoadingElapsedSeconds = $state(0);
	let authorsError = $state('');
	let textSearchError = $state('');
	let contentsError = $state('');
	let segmentError = $state('');
	let totalFiltered = $state(0);
	let worksNextCursor = $state<string | null>(null);
	let worksPrevCursor = $state<string | null>(null);
	let authorsNextCursor = $state<string | null>(null);
	let authorsPrevCursor = $state<string | null>(null);
	let textSearchNextCursor = $state<string | null>(null);
	let textSearchPrevCursor = $state<string | null>(null);
	let activeCollection = $state('all');
	let pageRadius = $state(4);
	let pageLimit = $state(14);
	let pageTextBudget = $state(7_500);
	let pageNextCursor = $state<string | null>(null);
	let pagePrevCursor = $state<string | null>(null);
	let activeAuthorSection = $state('');
	let routeAuthorId = $state('');
	let routeAuthorName = $state('');
	let authorsCursorParam = $state<string | null>(null);
	let textSearchCursorParam = $state<string | null>(null);
	let worksCursorParam = $state<string | null>(null);
	let contentsCursorParam = $state<string | null>(null);
	let pageCursorParam = $state<string | null>(null);
	let showTransliteration = $state(false);
	let readerResultsRegion = $state<HTMLElement | null>(null);
	const readerLoadingTimers = new Map<ReaderLoadingKey, ReturnType<typeof setInterval>>();
	const readerIndexStatsInFlight = new Set<string>();

	let selectedWordRomanization = $derived(
		selectedWord ? romanizeSearchTerm(language, selectedWord) : null
	);
	let selectedWordHref = $derived(
		selectedWord
			? `/?language=${language}&q=${encodeURIComponent(selectedWord)}&load=yes&backend=cli`
			: '/'
	);
	let activeReaderIndexStats = $derived(findReaderIndexStats(language, catalogId));
	let indexSummaryLabel = $derived(
		readerIndexSummaryLabel(language, catalogId, activeReaderIndexStats)
	);
	let pageRangeLabel = $derived(citationRangeLabel(pageSegments, selectedSegment));
	let discoveryGroups = $derived(facetValues(facets, 'discovery_groups'));
	let discoveryTags = $derived(
		readerFacetValuesForLanguage(facetValues(facets, 'discovery_tags'), language)
	);
	let discoverySorts = $derived(readerDiscoverySortValues(facetValues(facets, 'sorts')));
	let authorAgentKinds = $derived(facetValues(facets, 'author_agent_kinds'));
	let authorHistoricityStatuses = $derived(facetValues(facets, 'author_historicity_statuses'));
	let activeDiscoverySummary = $derived(discoverySummary());
	let hasActiveDiscoveryQuery = $derived(
		Boolean(
			workQuery.trim() || discoveryGroup || discoveryTag || discoveryAuthorId || worksCursorParam
		)
	);

	onMount(() => {
		const savedTheme = localStorage.getItem('orion-theme');
		if (savedTheme === 'manuscript' || savedTheme === 'vespers') {
			theme = savedTheme;
			document.documentElement.dataset.theme = savedTheme;
		}

		void initializeReaderFromUrl();
		const handlePopstate = () => void rehydrateReaderFromUrl();
		window.addEventListener('popstate', handlePopstate);

		return () => {
			window.removeEventListener('popstate', handlePopstate);
			stopAllReaderLoadingTimers();
		};
	});

	async function initializeReaderFromUrl() {
		const route = hydrateFromUrl();
		const restored = restoreReaderIndexState();
		applyReaderRouteState(route);
		if (!restored || !catalogId || !catalogs.length) await loadCatalogs();
		else {
			void loadAllReaderIndexStats();
			await loadChosenReaderView('replace');
		}
		await applyReaderRouteContent(route, 'replace');
		updateReaderUrl({}, 'replace');
	}

	async function rehydrateReaderFromUrl() {
		const route = hydrateFromUrl();
		applyReaderRouteState(route);
		if (!catalogId || !catalogs.length) await loadCatalogs();
		else await loadChosenReaderView('replace');
		await applyReaderRouteContent(route, 'replace');
	}

	async function loadChosenReaderView(historyMode: ReaderHistoryMode = 'replace') {
		if (readerView === 'shelves' && !discoveryShelves.length) await loadShelves();
		if (readerView === 'authors' && (!authorSections.length || !authors.length)) {
			await loadAuthorSections(historyMode);
		}
		if (readerView === 'search' && textQuery.trim()) {
			await searchReaderText(textSearchCursorParam, historyMode);
		}
	}

	function setTheme(nextTheme: 'manuscript' | 'vespers', sync = true) {
		theme = nextTheme;
		if (!browser) return;
		document.documentElement.dataset.theme = nextTheme;
		localStorage.setItem('orion-theme', nextTheme);
		if (sync) updateReaderUrl({ theme: nextTheme }, 'replace');
	}

	function hydrateFromUrl() {
		if (!browser) return {};
		const url = new URL(window.location.href);
		const route = parseReaderRouteState(url.searchParams);
		applyReaderRouteState(route);
		return route;
	}

	function applyReaderRouteState(route: Partial<ReaderRouteState>) {
		if (route.language) language = route.language;
		if (route.catalogId) catalogId = route.catalogId;
		const hasTextSearchRoute = Boolean(
			route.readerView === 'search' || route.textQuery || route.textSearchCursor
		);
		const hasShelfRoute =
			Boolean(route.readerView === 'shelves') ||
			Boolean(route.query || route.discoveryGroup || route.discoveryTag || route.worksCursor);
		readerView =
			route.discoveryAuthorId || route.authorId || route.authorSection
				? 'authors'
				: route.readerView === 'authors'
					? 'authors'
					: hasTextSearchRoute
						? 'search'
						: hasShelfRoute
							? 'shelves'
							: 'choose';
		showTransliteration = route.transliteration ?? false;
		workQuery = route.query ?? '';
		textQuery = route.textQuery ?? '';
		textSearchMode = route.textSearchMode ?? 'fuzzy';
		discoveryGroup = route.discoveryGroup ?? '';
		discoveryTag = route.discoveryTag ?? '';
		discoveryAuthorId = route.discoveryAuthorId ?? '';
		discoveryAuthorLabel = route.discoveryAuthorLabel ?? '';
		discoverySort = route.discoverySort ?? 'global-popularity';
		authorAgentKind = route.authorAgentKind ?? '';
		authorHistoricity = route.authorHistoricity ?? '';
		activeAuthorSection = route.authorSection ?? '';
		routeAuthorId = route.authorId ?? '';
		routeAuthorName = route.authorName ?? '';
		if (!route.authorId) selectedAuthor = null;
		authorsCursorParam = route.authorsCursor ?? null;
		textSearchCursorParam = route.textSearchCursor ?? null;
		worksCursorParam = route.worksCursor ?? null;
		contentsCursorParam = route.contentsCursor ?? null;
		pageCursorParam = route.pageCursor ?? null;
		activeCollection = route.collection ?? 'all';
		selectedWord = route.selectedWord ?? '';
		if (route.theme) setTheme(route.theme, false);
		if (route.address) {
			addressInput = route.address;
			showAddressLookup = true;
		} else if (!route.work && !route.segment) addressInput = defaultAddressForLanguage(language);
		if (!route.work && !route.segment) {
			selectedWork = null;
			selectedSegment = null;
			contents = [];
			pageSegments = [];
			navigation = { previous: null, next: null };
			pageNextCursor = null;
			pagePrevCursor = null;
		}
	}

	async function applyReaderRouteContent(
		route: Partial<ReaderRouteState>,
		historyMode: ReaderHistoryMode
	) {
		if (route.work && route.segment) {
			await showSegment(route.work, route.segment, historyMode);
			return;
		}
		if (route.work) {
			await ensureSelectedWork(route.work);
			await loadContentsPage(route.work, route.contentsCursor ?? null, historyMode);
			return;
		}
		if (route.address) {
			await openAddress(historyMode);
			return;
		}
		if (route.discoveryAuthorId && !route.authorId) {
			readerView = 'authors';
			routeAuthorId = route.discoveryAuthorId;
			routeAuthorName = route.discoveryAuthorLabel ?? '';
			selectedAuthor = syntheticAuthorFromRoute(
				route.discoveryAuthorId,
				route.discoveryAuthorLabel ?? route.discoveryAuthorId
			);
			if (!authors.some((author) => author.author_id === selectedAuthor?.author_id)) {
				authors = selectedAuthor ? [selectedAuthor, ...authors] : authors;
			}
			await searchWorks(
				route.worksCursor ?? null,
				route.discoveryAuthorId,
				historyMode,
				route.discoveryAuthorLabel
			);
			return;
		}
		if (route.authorId && !selectedAuthor) {
			readerView = 'authors';
			selectedAuthor = await resolveRouteAuthor(route.authorId, route.authorName);
			if (selectedAuthor)
				await searchWorks(route.worksCursor ?? null, route.authorId, historyMode, route.authorName);
			return;
		}
		if (!route.work && !route.segment && !route.address) {
			if (readerView === 'authors') {
				if (!authors.length) await loadAuthors(route.authorsCursor ?? null, historyMode);
			} else if (readerView === 'shelves') {
				if (hasActiveDiscoveryQuery && (!works.length || route.worksCursor)) {
					await searchWorks(route.worksCursor ?? null, undefined, historyMode);
				}
			}
		}
	}

	async function loadCatalogs(historyMode: ReaderHistoryMode = 'replace') {
		catalogError = '';
		try {
			const { response, data } = await fetchReaderApi<ReaderCatalogsResponse>(
				'/api/reader?mode=catalogs'
			);
			if (!response.ok) throw new Error(data.error || 'Reader catalogs failed.');
			catalogs = data.items;
			catalogDefaults = data.defaults;
			if (
				!catalogId ||
				!catalogs.some((catalog) => catalog.id === catalogId && catalog.available)
			) {
				catalogId =
					data.defaults[language] ?? data.items.find((catalog) => catalog.available)?.id ?? '';
			}
			saveReaderIndexState();
			void loadAllReaderIndexStats();
			await loadFacets();
			if (readerView === 'shelves') {
				await loadShelves();
			}
			if (readerView === 'authors') await loadAuthorSections(historyMode);
			if (readerView === 'search' && textQuery.trim())
				await searchReaderText(textSearchCursorParam, historyMode);
		} catch (error) {
			catalogError = error instanceof Error ? error.message : 'Reader catalogs failed.';
		}
	}

	async function fetchReaderApi<T>(url: string) {
		return fetchPayload<T & { error?: string }>(url);
	}

	async function loadFacets() {
		if (!catalogId) return;
		try {
			const params = new URLSearchParams({
				mode: 'facets',
				catalog: catalogId,
				language
			});
			const { response, data } = await fetchReaderApi<ReaderFacetsResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader facets failed.');
			facets = data.items;
			if (
				discoveryTag &&
				!readerFacetValuesForLanguage(facetValues(facets, 'discovery_tags'), language).some(
					(tag) => tag.id === discoveryTag
				)
			) {
				discoveryTag = '';
			}
			if (discoverySort === 'popularity') discoverySort = 'global-popularity';
			saveReaderIndexState();
		} catch {
			facets = [];
		}
	}

	async function loadShelves() {
		if (!catalogId) return;
		shelvesLoading = true;
		startReaderLoadingTimer('shelves');
		try {
			const params = new URLSearchParams({
				mode: 'shelves',
				catalog: catalogId,
				language,
				limit: '12',
				sample_limit: '2',
				timeout_ms: '300000'
			});
			const { response, data } = await fetchReaderApi<ReaderShelvesResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader shelves failed.');
			discoveryShelves = data.items;
			saveReaderIndexState();
		} catch {
			discoveryShelves = [];
		} finally {
			shelvesLoading = false;
			stopReaderLoadingTimer('shelves');
		}
	}

	function selectLanguage(nextLanguage: LanguageMode) {
		language = nextLanguage;
		catalogId =
			catalogDefaults[nextLanguage] ??
			catalogs.find((catalog) => catalog.available && catalog.languages.includes(nextLanguage))
				?.id ??
			catalogId;
		workQuery = '';
		textQuery = '';
		textSearchMode = 'fuzzy';
		textSearchResults = [];
		textSearchQueryCandidates = [];
		readerView = 'choose';
		discoveryGroup = '';
		discoveryTag = '';
		discoveryAuthorId = '';
		discoveryAuthorLabel = '';
		discoverySort = 'global-popularity';
		authorAgentKind = '';
		authorHistoricity = '';
		addressInput = defaultAddressForLanguage(nextLanguage);
		works = [];
		discoveryShelves = [];
		authorSections = [];
		authors = [];
		selectedAuthor = null;
		selectedWork = null;
		contents = [];
		selectedSegment = null;
		pageSegments = [];
		navigation = { previous: null, next: null };
		textSearchNextCursor = null;
		textSearchPrevCursor = null;
		pageNextCursor = null;
		pagePrevCursor = null;
		selectedWord = '';
		activeCollection = 'all';
		activeAuthorSection = '';
		routeAuthorId = '';
		routeAuthorName = '';
		authorsCursorParam = null;
		textSearchCursorParam = null;
		worksCursorParam = null;
		contentsCursorParam = null;
		pageCursorParam = null;
		libraryError = '';
		authorsError = '';
		textSearchError = '';
		contentsError = '';
		segmentError = '';
		updateReaderUrl({}, 'push');
		void loadReaderIndexStatsFor(nextLanguage, catalogId);
		void loadFacets();
	}

	async function fetchReaderAuthorSections(targetLanguage: LanguageMode, targetCatalogId: string) {
		const params = new URLSearchParams({
			mode: 'author-sections',
			catalog: targetCatalogId,
			language: targetLanguage
		});
		const { response, data } = await fetchReaderApi<ReaderAuthorSectionsResponse>(
			`/api/reader?${params.toString()}`
		);
		if (!response.ok) throw new Error(data.error || 'Reader author sections failed.');
		return data.items;
	}

	function readerIndexStatsFromSections(
		targetLanguage: LanguageMode,
		targetCatalogId: string,
		sections: ReaderAuthorSection[]
	): ReaderIndexStats {
		return {
			language: targetLanguage,
			catalogId: targetCatalogId,
			workCount: sections.reduce((count, section) => count + section.work_count, 0),
			authorCount: sections.reduce((count, section) => count + section.author_count, 0)
		};
	}

	function findReaderIndexStats(targetLanguage: LanguageMode, targetCatalogId: string) {
		const key = readerIndexStatsKey(targetLanguage, targetCatalogId);
		return readerIndexStats.find(
			(stats) => readerIndexStatsKey(stats.language, stats.catalogId) === key
		);
	}

	function upsertReaderIndexStats(stats: ReaderIndexStats) {
		const key = readerIndexStatsKey(stats.language, stats.catalogId);
		readerIndexStats = [
			...readerIndexStats.filter(
				(item) => readerIndexStatsKey(item.language, item.catalogId) !== key
			),
			stats
		];
		saveReaderIndexState();
	}

	function defaultCatalogForLanguage(targetLanguage: LanguageMode) {
		return (
			catalogDefaults[targetLanguage] ??
			catalogs.find((catalog) => catalog.available && catalog.languages.includes(targetLanguage))
				?.id ??
			''
		);
	}

	async function loadReaderIndexStatsFor(targetLanguage: LanguageMode, targetCatalogId: string) {
		if (!targetCatalogId) return;
		const key = readerIndexStatsKey(targetLanguage, targetCatalogId);
		if (
			readerHasIndexStats(readerIndexStats, targetLanguage, targetCatalogId) ||
			readerIndexStatsInFlight.has(key)
		) {
			return;
		}

		readerIndexStatsInFlight.add(key);
		try {
			const sections = await fetchReaderAuthorSections(targetLanguage, targetCatalogId);
			upsertReaderIndexStats(
				readerIndexStatsFromSections(targetLanguage, targetCatalogId, sections)
			);
		} catch {
			// The active author list still reports its own error; stats fall back to a neutral label.
		} finally {
			readerIndexStatsInFlight.delete(key);
		}
	}

	async function loadAllReaderIndexStats() {
		if (!catalogs.length) return;
		const targets = new Map<string, { language: LanguageMode; catalogId: string }>();
		for (const mode of languageModes) {
			const defaultCatalogId = defaultCatalogForLanguage(mode.id);
			if (defaultCatalogId) {
				targets.set(readerIndexStatsKey(mode.id, defaultCatalogId), {
					language: mode.id,
					catalogId: defaultCatalogId
				});
			}
		}
		if (catalogId) {
			targets.set(readerIndexStatsKey(language, catalogId), { language, catalogId });
		}

		await Promise.all(
			Array.from(targets.values()).map((target) =>
				loadReaderIndexStatsFor(target.language, target.catalogId)
			)
		);
	}

	async function loadAuthorSections(historyMode: ReaderHistoryMode = 'replace') {
		authorsLoading = true;
		startReaderLoadingTimer('authors');
		authorsError = '';
		const authorsPromise = !activeAuthorSection
			? loadAuthors(authorsCursorParam, historyMode, true)
			: null;
		try {
			authorSections = await fetchReaderAuthorSections(language, catalogId);
			upsertReaderIndexStats(readerIndexStatsFromSections(language, catalogId, authorSections));
			if (
				activeAuthorSection &&
				!authorSections.some((section) => section.key === activeAuthorSection)
			) {
				activeAuthorSection = '';
			}
			saveReaderIndexState();
			if (authorsPromise) await authorsPromise;
			else await loadAuthors(authorsCursorParam, historyMode, true);
		} catch (error) {
			const sectionError =
				error instanceof Error ? error.message : 'Reader author sections failed.';
			authorSections = [];
			if (authorsPromise) {
				await authorsPromise;
				if (!authors.length && !authorsError) {
					authorsError = sectionError;
				}
			} else {
				authorsError = sectionError;
				authorsLoading = false;
				stopReaderLoadingTimer('authors');
			}
		}
	}

	async function loadAuthors(
		cursor?: string | null,
		historyMode: ReaderHistoryMode = 'replace',
		loadingAlreadyStarted = false
	) {
		authorsLoading = true;
		if (!loadingAlreadyStarted) startReaderLoadingTimer('authors');
		authorsError = '';
		if (!cursor) {
			authors = [];
			selectedAuthor = null;
			works = [];
		}
		try {
			const params = new URLSearchParams({
				mode: 'authors',
				catalog: catalogId,
				language,
				limit: '50'
			});
			if (activeAuthorSection) params.set('section', activeAuthorSection);
			if (workQuery.trim() && !activeAuthorSection) params.set('q', workQuery.trim());
			if (authorAgentKind) params.set('agent_kind', authorAgentKind);
			if (authorHistoricity) params.set('historicity', authorHistoricity);
			if (!activeAuthorSection && !workQuery.trim()) params.set('sort', 'prominence');
			if (cursor) params.set('cursor', cursor);
			const { response, data } = await fetchReaderApi<ReaderAuthorsResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader authors failed.');
			authors = data.items;
			authorsNextCursor = data.pagination?.next_cursor ?? null;
			authorsPrevCursor = data.pagination?.prev_cursor ?? null;
			authorsCursorParam = cursor ?? null;
			saveReaderIndexState();
			updateReaderUrl({}, historyMode);
		} catch (error) {
			authorsError = error instanceof Error ? error.message : 'Reader authors failed.';
		} finally {
			authorsLoading = false;
			stopReaderLoadingTimer('authors');
		}
	}

	function findAuthorById(authorId: string) {
		return authors.find((author) => readerAuthorMatchesId(author, authorId)) ?? null;
	}

	function authorIdentityValues(author: ReaderAuthor) {
		return [author.author_id, author.source_author_id, author.canonical_author_id].filter(
			(value): value is string => Boolean(value)
		);
	}

	function authorsMatch(left: ReaderAuthor, right: ReaderAuthor) {
		return authorIdentityValues(right).some((id) => readerAuthorMatchesId(left, id));
	}

	function upsertAuthor(author: ReaderAuthor) {
		if (authors.some((item) => authorsMatch(item, author))) {
			authors = authors.map((item) => (authorsMatch(item, author) ? author : item));
			return;
		}
		authors = [author, ...authors];
	}

	async function findAuthorByQuery(authorId: string, authorName: string) {
		if (!authorName.trim()) return null;
		const params = new URLSearchParams({
			mode: 'authors',
			catalog: catalogId,
			language,
			q: authorName.trim(),
			limit: '50'
		});
		const { response, data } = await fetchReaderApi<ReaderAuthorsResponse>(
			`/api/reader?${params.toString()}`
		);
		if (!response.ok) return null;
		return data.items.find((author) => readerAuthorMatchesId(author, authorId)) ?? null;
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
		const synthetic = syntheticAuthorFromRoute(authorId, authorName);
		upsertAuthor(synthetic);
		return synthetic;
	}

	function syncSelectedAuthorWorkCount(authorId: string, workCount: number) {
		if (!selectedAuthor || !readerAuthorMatchesId(selectedAuthor, authorId) || !workCount) return;
		const updated = {
			...selectedAuthor,
			work_count: Math.max(selectedAuthor.work_count, workCount)
		};
		selectedAuthor = updated;
		upsertAuthor(updated);
	}

	async function searchWorks(
		cursor?: string | null,
		authorId?: string,
		historyMode: ReaderHistoryMode = 'replace',
		authorName?: string
	) {
		libraryLoading = true;
		startReaderLoadingTimer('library');
		libraryError = '';
		if (!cursor) {
			selectedWork = null;
			contents = [];
			selectedSegment = null;
			pageSegments = [];
			navigation = { previous: null, next: null };
			pageNextCursor = null;
			pagePrevCursor = null;
			selectedWord = '';
		}
		try {
			const params = new URLSearchParams({
				mode: 'works',
				catalog: catalogId,
				language,
				limit: '120'
			});
			if (authorId) params.set('author_id', authorId);
			else if (authorName) params.set('author', authorName);
			else if (discoveryAuthorId) params.set('author_id', discoveryAuthorId);
			else if (workQuery.trim()) params.set('q', workQuery.trim());
			if (!authorId && discoveryGroup) params.set('group', discoveryGroup);
			if (!authorId && discoveryTag) params.set('tag', discoveryTag);
			if (!authorId && discoverySort) params.set('sort', discoverySort);
			if (activeCollection !== 'all') params.set('collection', activeCollection);
			if (cursor) params.set('cursor', cursor);
			const { response, data: initialData } = await fetchReaderApi<ReaderWorksResponse>(
				`/api/reader?${params.toString()}`
			);
			let data = initialData;
			if (!response.ok) throw new Error(data.error || 'Reader work search failed.');
			if (authorName && authorId && !data.items.length && !cursor) {
				const authorParams = new URLSearchParams({
					mode: 'works',
					catalog: catalogId,
					language,
					limit: '120',
					author: authorName
				});
				if (activeCollection !== 'all') authorParams.set('collection', activeCollection);
				const { response: authorResponse, data: authorData } =
					await fetchReaderApi<ReaderWorksResponse>(`/api/reader?${authorParams.toString()}`);
				if (authorResponse.ok && authorData.items.length) data = authorData;
			}
			if (authorName && !authorId && !data.items.length && !cursor) {
				const fallbackParams = new URLSearchParams({
					mode: 'works',
					catalog: catalogId,
					language,
					limit: '120',
					q: authorName
				});
				if (activeCollection !== 'all') fallbackParams.set('collection', activeCollection);
				const { response: fallbackResponse, data: fallbackData } =
					await fetchReaderApi<ReaderWorksResponse>(`/api/reader?${fallbackParams.toString()}`);
				if (fallbackResponse.ok && fallbackData.items.length) data = fallbackData;
			}
			works = data.items;
			totalFiltered = data.pagination?.total_filtered ?? data.items.length;
			worksNextCursor = data.pagination?.next_cursor ?? null;
			worksPrevCursor = data.pagination?.prev_cursor ?? null;
			worksCursorParam = cursor ?? null;
			if (authorId) routeAuthorId = authorId;
			else routeAuthorId = '';
			routeAuthorName = authorName ?? '';
			if (authorId) syncSelectedAuthorWorkCount(authorId, data.items.length);
			saveReaderIndexState();
			updateReaderUrl({}, historyMode);
			if (data.items.length && historyMode === 'push') {
				await tick();
				scrollReaderResultsIntoView();
			}
		} catch (error) {
			libraryError = error instanceof Error ? error.message : 'Reader work search failed.';
		} finally {
			libraryLoading = false;
			stopReaderLoadingTimer('library');
		}
	}

	async function searchReaderText(
		cursor?: string | null,
		historyMode: ReaderHistoryMode = 'replace'
	) {
		const query = textQuery.trim();
		if (!query) {
			textSearchResults = [];
			textSearchQueryCandidates = [];
			textSearchNextCursor = null;
			textSearchPrevCursor = null;
			textSearchCursorParam = null;
			updateReaderUrl({}, historyMode);
			return;
		}
		textSearchLoading = true;
		startReaderLoadingTimer('textSearch');
		textSearchError = '';
		try {
			const params = new URLSearchParams({
				mode: 'search',
				catalog: catalogId,
				language,
				q: query,
				search_mode: textSearchMode,
				context: '1',
				limit: '5',
				timeout_ms: '90000'
			});
			if (activeCollection !== 'all') params.set('collection', activeCollection);
			if (cursor) params.set('cursor', cursor);
			const { response, data } = await fetchReaderApi<ReaderSearchResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader text search failed.');
			textSearchResults = data.items;
			textSearchQueryCandidates = data.request.query_candidates ?? [];
			textSearchNextCursor = data.pagination?.next_cursor ?? null;
			textSearchPrevCursor = data.pagination?.prev_cursor ?? null;
			textSearchCursorParam = cursor ?? null;
			saveReaderIndexState();
			updateReaderUrl({}, historyMode);
		} catch (error) {
			textSearchError = error instanceof Error ? error.message : 'Reader text search failed.';
		} finally {
			textSearchLoading = false;
			stopReaderLoadingTimer('textSearch');
		}
	}

	function showLibrary() {
		selectedWork = null;
		selectedSegment = null;
		pageSegments = [];
		contents = [];
		navigation = { previous: null, next: null };
		pageNextCursor = null;
		pagePrevCursor = null;
		selectedWord = '';
		contentsCursorParam = null;
		pageCursorParam = null;
		showAddressLookup = false;
		addressInput = defaultAddressForLanguage(language);
		updateReaderUrl({}, 'push');
		if (readerView === 'shelves' && hasActiveDiscoveryQuery && !works.length)
			void searchWorks(null, routeAuthorId || undefined, 'replace');
	}

	async function openWork(work: ReaderWork) {
		selectedWork = work;
		selectedSegment = null;
		selectedWord = '';
		contents = [];
		contentsError = '';
		contentsCursorParam = null;
		pageCursorParam = null;
		await loadContentsPage(readerWorkRef(work), null, 'push');
	}

	async function loadContentsPage(
		work: string,
		cursor?: string | null,
		historyMode: ReaderHistoryMode = 'replace'
	) {
		contentsLoading = true;
		startReaderLoadingTimer('contents');
		try {
			const params = new URLSearchParams({
				mode: 'contents',
				catalog: catalogId,
				language,
				work,
				limit: String(pageLimit),
				char_budget: String(pageTextBudget)
			});
			if (cursor) params.set('cursor', cursor);
			const { response, data } = await fetchReaderApi<ReaderContentsResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader contents failed.');
			contents = data.items;
			pageSegments = data.items;
			selectedSegment =
				data.items.find((item) => item.text && !/^\{.*\}$/u.test(item.text.trim())) ??
				data.items[0] ??
				null;
			pageNextCursor = data.pagination?.next_cursor ?? null;
			pagePrevCursor = data.pagination?.prev_cursor ?? null;
			navigation = { previous: null, next: null };
			selectedWord = '';
			contentsCursorParam = cursor ?? null;
			pageCursorParam = cursor ?? null;
			if (selectedSegment) syncUrl(work, selectedSegment.citation_path, historyMode);
		} catch (error) {
			contentsError = error instanceof Error ? error.message : 'Reader contents failed.';
		} finally {
			contentsLoading = false;
			stopReaderLoadingTimer('contents');
		}
	}

	async function showSegment(
		work: string,
		segment: string,
		historyMode: ReaderHistoryMode = 'replace'
	) {
		segmentLoading = true;
		startReaderLoadingTimer('segment');
		segmentError = '';
		selectedWord = '';
		try {
			await ensureSelectedWork(work);
			const params = new URLSearchParams({
				mode: 'show',
				catalog: catalogId,
				language,
				work,
				segment
			});
			const { response, data } = await fetchReaderApi<ReaderShowResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader segment failed.');
			selectedSegment = data.segment;
			navigation = data.navigation ?? { previous: null, next: null };
			if (data.segment) {
				await loadPageWindow(data.segment.work_id || work, data.segment.citation_path);
			}
			contentsCursorParam = null;
			pageCursorParam = null;
			syncUrl(work, segment, historyMode);
		} catch (error) {
			segmentError = error instanceof Error ? error.message : 'Reader segment failed.';
		} finally {
			segmentLoading = false;
			stopReaderLoadingTimer('segment');
		}
	}

	async function openAddress(historyMode: ReaderHistoryMode = 'replace') {
		const address = addressInput.trim();
		if (!address) return;
		updateReaderUrl(
			{
				address,
				work: null,
				segment: null,
				contentsCursor: null,
				pageCursor: null,
				selectedWord: null
			},
			historyMode
		);
		const workSegment = address.match(/^(.+)\s+([^\s]+)$/u);
		if (workSegment && isCanonicalReaderRef(workSegment[1])) {
			await showSegment(workSegment[1], workSegment[2], 'replace');
			return;
		}
		if (isCanonicalReaderRef(address)) {
			await showAddress(address, 'replace');
			return;
		}
		await resolveAddress(address, 'replace');
	}

	async function showAddress(address: string, historyMode: ReaderHistoryMode = 'replace') {
		segmentLoading = true;
		startReaderLoadingTimer('segment');
		segmentError = '';
		selectedWord = '';
		try {
			const params = new URLSearchParams({
				mode: 'show',
				catalog: catalogId,
				language,
				address
			});
			const { response, data } = await fetchReaderApi<ReaderShowResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader segment failed.');
			selectedSegment = data.segment;
			navigation = data.navigation ?? { previous: null, next: null };
			if (data.segment) {
				await ensureSelectedWork(data.segment.work_id);
				await loadPageWindow(data.segment.work_id, data.segment.citation_path);
				contentsCursorParam = null;
				pageCursorParam = null;
				syncUrl(data.segment.work_id, data.segment.citation_path, historyMode);
			}
		} catch (error) {
			segmentError = error instanceof Error ? error.message : 'Reader segment failed.';
		} finally {
			segmentLoading = false;
			stopReaderLoadingTimer('segment');
		}
	}

	async function resolveAddress(address: string, historyMode: ReaderHistoryMode = 'replace') {
		segmentLoading = true;
		startReaderLoadingTimer('segment');
		segmentError = '';
		selectedWord = '';
		try {
			const params = new URLSearchParams({
				mode: 'resolve-address',
				catalog: catalogId,
				language,
				address
			});
			const { response, data } = await fetchReaderApi<ReaderShowResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reference lookup failed.');
			selectedSegment = data.segment;
			navigation = data.navigation ?? { previous: null, next: null };
			if (data.segment) {
				await ensureSelectedWork(data.segment.work_id);
				await loadPageWindow(data.segment.work_id, data.segment.citation_path);
				contentsCursorParam = null;
				pageCursorParam = null;
				syncUrl(data.segment.work_id, data.segment.citation_path, historyMode);
			}
		} catch (error) {
			segmentError = error instanceof Error ? error.message : 'Reference lookup failed.';
		} finally {
			segmentLoading = false;
			stopReaderLoadingTimer('segment');
		}
	}

	function isCanonicalReaderRef(value: string) {
		return (
			value.startsWith('urn:ctsv2:') ||
			value.startsWith('ctsv2://') ||
			value.startsWith('urn:cts:') ||
			value.startsWith('langnet:reader:')
		);
	}

	async function ensureSelectedWork(work: string) {
		if (
			selectedWork &&
			(selectedWork.work_id === work ||
				selectedWork.cts_work_urn === work ||
				selectedWork.canonical_text_id === work ||
				selectedWork.canonical_address === work) &&
			workHasContributorMetadata(selectedWork)
		)
			return;
		try {
			const params = new URLSearchParams({
				mode: 'work',
				catalog: catalogId,
				language,
				work
			});
			const { response, data } = await fetchReaderApi<ReaderWorkResponse>(
				`/api/reader?${params.toString()}`
			);
			if (response.ok && data.item) selectedWork = data.item;
		} catch {
			// Work metadata is helpful chrome; failure should not block exact reading.
		}
	}

	function workHasContributorMetadata(work: ReaderWork) {
		return Boolean(
			work.translator_names?.length ||
			work.traditional_author_names?.length ||
			work.attributed_author_names?.length ||
			work.metadata_attributions?.length
		);
	}

	async function loadPageWindow(work: string, citation: string) {
		try {
			const params = new URLSearchParams({
				mode: 'contents',
				catalog: catalogId,
				language,
				work,
				around: citation,
				radius: String(pageRadius),
				limit: String(pageRadius * 2 + 1),
				char_budget: String(pageTextBudget)
			});
			const { response, data } = await fetchReaderApi<ReaderContentsResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader page window failed.');
			pageSegments = data.items.length ? data.items : selectedSegment ? [selectedSegment] : [];
			contents = data.items.length ? data.items : contents;
			const derivedPagination = derivePagePagination(pageSegments);
			pageNextCursor = data.pagination?.next_cursor ?? derivedPagination.next;
			pagePrevCursor = data.pagination?.prev_cursor ?? derivedPagination.previous;
		} catch {
			pageSegments = selectedSegment ? [selectedSegment] : [];
			pageNextCursor = null;
			pagePrevCursor = null;
		}
	}

	type ReaderRouteOverrides = Partial<{
		[K in keyof ReaderRouteState]: ReaderRouteState[K] | null;
	}>;

	function syncUrl(work: string, segment: string, historyMode: ReaderHistoryMode = 'replace') {
		addressInput = formatReaderAddress(work, segment);
		updateReaderUrl(
			{
				work,
				segment,
				address: null,
				contentsCursor: contentsCursorParam,
				pageCursor: pageCursorParam
			},
			historyMode
		);
	}

	function updateReaderUrl(overrides: ReaderRouteOverrides = {}, historyMode: ReaderHistoryMode) {
		if (!browser || historyMode === 'none') return;
		const state = currentReaderRouteState();
		for (const [key, value] of Object.entries(overrides) as [
			keyof ReaderRouteState,
			ReaderRouteState[keyof ReaderRouteState] | null
		][]) {
			if (value === null) delete state[key];
			else if (value !== undefined) state[key] = value as never;
		}
		const nextUrl = `/reader${buildReaderRouteSearch(state)}`;
		const currentUrl = `${window.location.pathname}${window.location.search}`;
		if (nextUrl === currentUrl) return;
		if (historyMode === 'push') window.history.pushState({}, '', nextUrl);
		else window.history.replaceState({}, '', nextUrl);
	}

	function currentReaderRouteState(): Partial<ReaderRouteState> {
		const work = selectedWork ? readerWorkRef(selectedWork) : selectedSegment?.work_id || undefined;
		const segment = selectedSegment?.citation_path || undefined;
		const address = readerAddressRouteValue({
			addressInput,
			defaultAddress: defaultAddressForLanguage(language),
			hasWork: Boolean(work),
			showAddressLookup
		});

		return {
			language,
			catalogId,
			readerView: readerView === 'choose' ? undefined : readerView,
			address,
			query: readerView === 'shelves' || readerView === 'authors' ? workQuery : undefined,
			textQuery: readerView === 'search' ? textQuery : undefined,
			textSearchMode: readerView === 'search' ? textSearchMode : undefined,
			textSearchCursor: readerView === 'search' ? (textSearchCursorParam ?? undefined) : undefined,
			discoveryGroup: readerView === 'shelves' ? discoveryGroup || undefined : undefined,
			discoveryTag: readerView === 'shelves' ? discoveryTag || undefined : undefined,
			discoveryAuthorId: readerView === 'shelves' ? discoveryAuthorId || undefined : undefined,
			discoveryAuthorLabel:
				readerView === 'shelves' ? discoveryAuthorLabel || undefined : undefined,
			discoverySort: readerView === 'shelves' ? discoverySort : undefined,
			authorAgentKind: readerView === 'authors' ? authorAgentKind || undefined : undefined,
			authorHistoricity: readerView === 'authors' ? authorHistoricity || undefined : undefined,
			authorSection: readerView === 'authors' ? activeAuthorSection : undefined,
			authorId: readerView === 'authors' ? (selectedAuthor?.author_id ?? routeAuthorId) : undefined,
			authorName: readerView === 'authors' ? routeAuthorName || undefined : undefined,
			authorsCursor: readerView === 'authors' ? (authorsCursorParam ?? undefined) : undefined,
			worksCursor: worksCursorParam ?? undefined,
			contentsCursor: contentsCursorParam ?? undefined,
			pageCursor: pageCursorParam ?? undefined,
			collection: activeCollection,
			work,
			segment,
			selectedWord,
			theme,
			transliteration: showTransliteration || undefined
		};
	}

	function defaultAddressForLanguage(nextLanguage: LanguageMode) {
		return nextLanguage === 'grc' ? 'Od. 3.74' : '';
	}

	function formatReaderAddress(work: string, segment: string) {
		if (work.startsWith('urn:ctsv2:') || work.startsWith('ctsv2://')) {
			return `${work}?ref=${encodeURIComponent(segment)}`;
		}
		return [work, segment].filter(Boolean).join(' ');
	}

	function selectToken(text: string) {
		const token = cleanReaderToken(text);
		if (!token) return;
		selectedWord = token;
		updateReaderUrl({ selectedWord: token }, 'replace');
	}

	function segmentIsActive(segment: ReaderSegment) {
		return selectedSegment?.citation_path === segment.citation_path;
	}

	function segmentParts(segment: ReaderSegment): ReaderTokenPart[] {
		return buildReaderTokenParts(segment, language, showTransliteration);
	}

	function toggleTransliteration() {
		showTransliteration = !showTransliteration;
		updateReaderUrl({ transliteration: showTransliteration || null }, 'replace');
	}

	function closeAddressLookup() {
		showAddressLookup = false;
		if (!selectedWork && !selectedSegment) {
			addressInput = defaultAddressForLanguage(language);
			updateReaderUrl({ address: null }, 'replace');
		}
	}

	function selectReaderView(nextView: Exclude<ReaderIndexView, 'choose'>) {
		readerView = nextView;
		worksCursorParam = null;
		authorsCursorParam = null;
		textSearchCursorParam = null;
		selectedAuthor = null;
		routeAuthorId = '';
		routeAuthorName = '';
		updateReaderUrl(
			{
				readerView,
				authorId: null,
				authorsCursor: null,
				worksCursor: null,
				textSearchCursor: null
			},
			'push'
		);
		if (nextView === 'shelves' && !discoveryShelves.length) void loadShelves();
		if (nextView === 'authors' && (!authorSections.length || !authors.length))
			void loadAuthorSections('replace');
		if (nextView === 'search' && textQuery.trim()) void searchReaderText(null, 'replace');
	}

	function submitDiscoverySearch() {
		worksCursorParam = null;
		selectedAuthor = null;
		routeAuthorId = '';
		routeAuthorName = '';
		void searchWorks(null, undefined, 'push');
	}

	function submitTextSearch() {
		textSearchCursorParam = null;
		void searchReaderText(null, 'push');
	}

	function applyTextSearchMode() {
		textSearchCursorParam = null;
		if (textQuery.trim()) void searchReaderText(null, 'push');
		else updateReaderUrl({}, 'push');
	}

	function submitAuthorSearch() {
		activeAuthorSection = '';
		authorsCursorParam = null;
		routeAuthorId = '';
		routeAuthorName = '';
		selectedAuthor = null;
		void loadAuthors(null, 'push');
	}

	function applyDiscoveryFilters() {
		worksCursorParam = null;
		void searchWorks(null, undefined, 'push');
	}

	function selectDiscoveryShelf(shelf: ReaderDiscoveryShelf) {
		const routeState = readerShelfRouteState(shelf);
		workQuery = '';
		discoveryAuthorId = '';
		discoveryAuthorLabel = '';
		discoveryGroup = routeState.discoveryGroup;
		discoveryTag = routeState.discoveryTag;
		discoverySort = routeState.discoverySort;
		worksCursorParam = null;
		void searchWorks(null, undefined, 'push');
	}

	function shelfIsActive(shelf: ReaderDiscoveryShelf) {
		return (
			(Boolean(shelf.query.group) && discoveryGroup === shelf.query.group && !discoveryTag) ||
			(Boolean(shelf.query.tag) && discoveryTag === shelf.query.tag && !discoveryGroup)
		);
	}

	function clearDiscoveryFilters() {
		workQuery = '';
		discoveryGroup = '';
		discoveryTag = '';
		discoveryAuthorId = '';
		discoveryAuthorLabel = '';
		discoverySort = 'global-popularity';
		worksCursorParam = null;
		void searchWorks(null, undefined, 'push');
	}

	function clearTextSearch() {
		textQuery = '';
		textSearchMode = 'fuzzy';
		textSearchResults = [];
		textSearchQueryCandidates = [];
		textSearchNextCursor = null;
		textSearchPrevCursor = null;
		textSearchCursorParam = null;
		textSearchError = '';
		textSearchElapsedSeconds = 0;
		updateReaderUrl({}, 'push');
	}

	function visibleTextSearchCandidates(candidates: ReaderSearchQueryCandidate[]) {
		return candidates
			.filter((candidate) => candidate.query && candidate.kind !== 'input')
			.slice(0, 8);
	}

	function textSearchCandidateLabel(candidate: ReaderSearchQueryCandidate) {
		if (candidate.kind === 'concept_alias' && candidate.concept_label) {
			return `${candidate.concept_label}: ${candidate.query}`;
		}
		return candidate.query;
	}

	function startReaderLoadingTimer(kind: ReaderLoadingKey) {
		stopReaderLoadingTimer(kind);
		const startedAt = Date.now();
		setReaderLoadingElapsedSeconds(kind, 0);
		readerLoadingTimers.set(
			kind,
			setInterval(() => {
				setReaderLoadingElapsedSeconds(kind, Math.floor((Date.now() - startedAt) / 1000));
			}, 1000)
		);
	}

	function stopReaderLoadingTimer(kind: ReaderLoadingKey) {
		const timer = readerLoadingTimers.get(kind);
		if (!timer) return;
		clearInterval(timer);
		readerLoadingTimers.delete(kind);
	}

	function stopAllReaderLoadingTimers() {
		for (const kind of readerLoadingTimers.keys()) stopReaderLoadingTimer(kind);
	}

	function setReaderLoadingElapsedSeconds(kind: ReaderLoadingKey, seconds: number) {
		if (kind === 'shelves') shelvesLoadingElapsedSeconds = seconds;
		else if (kind === 'library') libraryLoadingElapsedSeconds = seconds;
		else if (kind === 'authors') authorsLoadingElapsedSeconds = seconds;
		else if (kind === 'textSearch') textSearchElapsedSeconds = seconds;
		else if (kind === 'contents') contentsLoadingElapsedSeconds = seconds;
		else segmentLoadingElapsedSeconds = seconds;
	}

	function readerLoadingElapsedSeconds(kind: ReaderLoadingKey) {
		if (kind === 'shelves') return shelvesLoadingElapsedSeconds;
		if (kind === 'library') return libraryLoadingElapsedSeconds;
		if (kind === 'authors') return authorsLoadingElapsedSeconds;
		if (kind === 'textSearch') return textSearchElapsedSeconds;
		if (kind === 'contents') return contentsLoadingElapsedSeconds;
		return segmentLoadingElapsedSeconds;
	}

	function readerLoadingStatus(label: string, kind: ReaderLoadingKey) {
		return readerLoadingStatusLabel(label, readerLoadingElapsedSeconds(kind));
	}

	function retryTextSearch() {
		if (!textQuery.trim()) return;
		void searchReaderText(textSearchCursorParam, 'replace');
	}

	function retryLibrarySearch() {
		void searchWorks(
			worksCursorParam,
			routeAuthorId || discoveryAuthorId || undefined,
			'replace',
			routeAuthorName || discoveryAuthorLabel || undefined
		);
	}

	function retryAuthorSearch() {
		if (!authorSections.length) void loadAuthorSections('replace');
		else void loadAuthors(authorsCursorParam, 'replace');
	}

	function retryContentsLoad() {
		if (!selectedWork) return;
		void loadContentsPage(readerWorkRef(selectedWork), contentsCursorParam, 'replace');
	}

	function retrySegmentLoad() {
		if (selectedSegment) {
			void showSegment(selectedSegment.work_id, selectedSegment.citation_path, 'replace');
			return;
		}
		if (addressInput.trim()) void openAddress('replace');
	}

	function scrollReaderResultsIntoView() {
		if (!browser || !readerResultsRegion) return;
		requestAnimationFrame(() => {
			readerResultsRegion?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		});
	}

	function openSearchResult(result: ReaderSearchResult) {
		const work = result.target?.work_ref || result.cts_work_urn || result.work_id;
		if (!work || !result.citation_path) return;
		void showSegment(work, result.citation_path, 'push');
	}

	function filterDiscoveryByAuthor(work: ReaderWork) {
		const route = readerAuthorRouteStateFromWork(work);
		if (!route?.authorId) return;
		const author = syntheticAuthorFromWork(work, route.authorId);
		readerView = 'authors';
		selectedAuthor = author;
		if (!authors.some((item) => item.author_id === author.author_id))
			authors = [author, ...authors];
		routeAuthorId = route.authorId;
		routeAuthorName = route.authorName ?? '';
		discoveryAuthorId = '';
		discoveryAuthorLabel = '';
		workQuery = '';
		activeAuthorSection = '';
		discoveryGroup = '';
		discoveryTag = '';
		authorsCursorParam = null;
		worksCursorParam = null;
		void searchWorks(null, route.authorId, 'push', route.authorName);
	}

	function clearDiscoveryAuthor() {
		discoveryAuthorId = '';
		discoveryAuthorLabel = '';
		worksCursorParam = null;
		void searchWorks(null, undefined, 'push');
	}

	function applyAuthorFilters() {
		authorsCursorParam = null;
		selectedAuthor = null;
		routeAuthorId = '';
		routeAuthorName = '';
		void loadAuthors(null, 'push');
	}

	function showSelectedWorkSegment(segment: ReaderSegment) {
		if (!selectedWork) return;
		void showSegment(readerWorkRef(selectedWork), segment.citation_path, 'push');
	}

	function showPageCursor(cursor: string | null) {
		if (!cursor) return;
		const work = selectedWork ? readerWorkRef(selectedWork) : selectedSegment?.work_id;
		if (!work) return;
		void loadContentsPage(work, cursor, 'push');
	}

	function showNavigationTarget(target: ReaderNavigationTarget | null) {
		if (!target) return;
		const work = selectedWork ? readerWorkRef(selectedWork) : selectedSegment?.work_id;
		if (!work) return;
		void showSegment(work, target.citation_path, 'push');
	}

	function handleReaderKeydown(event: KeyboardEvent) {
		if (!selectedSegment || segmentLoading) return;
		const target = event.target;
		if (
			target instanceof HTMLElement &&
			target.closest('input, textarea, select, button, a, [contenteditable="true"]')
		) {
			return;
		}
		if (event.key === 'ArrowLeft' && pagePrevCursor) {
			event.preventDefault();
			showPageCursor(pagePrevCursor);
		}
		if (event.key === 'ArrowRight' && pageNextCursor) {
			event.preventDefault();
			showPageCursor(pageNextCursor);
		}
	}

	function jumpToAuthorSection(section: string) {
		activeAuthorSection = activeAuthorSection === section ? '' : section;
		workQuery = '';
		readerView = 'authors';
		authorsCursorParam = null;
		routeAuthorId = '';
		routeAuthorName = '';
		selectedAuthor = null;
		void loadAuthors(null, 'push');
	}

	function clearAuthorSection() {
		activeAuthorSection = '';
		authorsCursorParam = null;
		void loadAuthors(null, 'push');
	}

	function openAuthor(author: ReaderAuthor) {
		readerView = 'authors';
		selectedAuthor = author;
		routeAuthorId = author.author_id;
		routeAuthorName = '';
		workQuery = '';
		worksCursorParam = null;
		void searchWorks(null, author.author_id, 'push');
	}

	function syntheticAuthorFromWork(work: ReaderWork, authorId: string): ReaderAuthor {
		const displayName = readerWorkDisplayAuthor(work);
		return {
			author_id: authorId,
			source_author_id: work.source_author_id || '',
			display_name: displayName,
			author: displayName,
			index_name: displayName,
			native_name: displayName,
			section_key: '',
			language: work.language,
			work_count: 0,
			alternate_names: [work.source_author, work.canonical_author_name, work.author].filter(
				(value): value is string => Boolean(value && value !== displayName)
			),
			sort_key: displayName
		};
	}

	function syntheticAuthorFromRoute(authorId: string, authorName: string): ReaderAuthor {
		return {
			author_id: authorId,
			source_author_id: '',
			display_name: authorName,
			author: authorName,
			index_name: authorName,
			native_name: authorName,
			section_key: '',
			language,
			work_count: 0,
			alternate_names: [],
			sort_key: authorName
		};
	}

	function facetValues(items: ReaderFacet[], id: string): ReaderFacetValue[] {
		return items.find((item) => item.id === id)?.values ?? [];
	}

	function facetValueLabel(values: ReaderFacetValue[], id: string) {
		return values.find((value) => value.id === id)?.label || labelFromId(id);
	}

	function labelFromId(id: string) {
		return id
			.replace(/[_-]+/g, ' ')
			.replace(/\b\w/g, (letter) => letter.toUpperCase())
			.trim();
	}

	function discoverySummary() {
		const parts = [];
		if (discoveryGroup) parts.push(facetValueLabel(discoveryGroups, discoveryGroup));
		if (discoveryTag) parts.push(facetValueLabel(discoveryTags, discoveryTag));
		if (!parts.length && workQuery.trim()) parts.push(`Search: ${workQuery.trim()}`);
		if (discoveryAuthorLabel) parts.push(discoveryAuthorLabel);
		if (!parts.length) parts.push(`${readerLanguageLabel(language)} works`);
		return parts.join(' · ');
	}

	function workMetaLine(work: ReaderWork) {
		const parts = [
			work.classification_category || work.classification_scope || '',
			work.classification_period || '',
			wordCountLabel(work.word_count)
		].filter(Boolean);
		return parts.join(' · ');
	}

	function workListLabel(work: ReaderWork) {
		return readerWorkListLabel(work, works);
	}

	function workListDiscriminator(work: ReaderWork) {
		return readerWorkListDiscriminator(work, works);
	}

	function selectedWorkTitleLabel() {
		return selectedWork ? readerWorkListLabel(selectedWork, works) : '';
	}

	function selectedWorkDiscriminator() {
		return selectedWork ? readerWorkListDiscriminator(selectedWork, works) : '';
	}

	function selectedWorkContributorLine() {
		return selectedWork ? readerWorkContributorLabels(selectedWork).join(' · ') : '';
	}

	function selectedWorkAuthorLabel() {
		if (!selectedWork) return '';
		return readerWorkDisplayAuthor(selectedWork);
	}

	function openSelectedWorkAuthor() {
		if (!selectedWork) return;
		filterDiscoveryByAuthor(selectedWork);
	}

	function wordCountLabel(count: number | undefined) {
		if (!count) return '';
		return `${count.toLocaleString()} words`;
	}

	function shelfMetaLabel(shelf: ReaderDiscoveryShelf) {
		const workLabel = `${shelf.work_count.toLocaleString()} ${
			shelf.work_count === 1 ? 'work' : 'works'
		}`;
		const authorLabel = shelf.author_count
			? `${shelf.author_count.toLocaleString()} ${shelf.author_count === 1 ? 'author' : 'authors'}`
			: '';
		return [workLabel, authorLabel].filter(Boolean).join(' · ');
	}

	function authorSectionRomanHint(nextLanguage: LanguageMode, key: string) {
		if (nextLanguage === 'grc') {
			const hints: Record<string, string> = {
				Α: 'A',
				Β: 'B',
				Γ: 'G',
				Δ: 'D',
				Ε: 'E',
				Ζ: 'Z',
				Η: 'E',
				Θ: 'Th',
				Ι: 'I',
				Κ: 'K',
				Λ: 'L',
				Μ: 'M',
				Ν: 'N',
				Ξ: 'X',
				Ο: 'O',
				Π: 'P',
				Ρ: 'R',
				Σ: 'S',
				Τ: 'T',
				Υ: 'Y',
				Φ: 'Ph'
			};
			return hints[key] ?? '';
		}
		if (nextLanguage === 'san') {
			const hints: Record<string, string> = {
				अ: 'a',
				आ: 'aa',
				ई: 'ii',
				उ: 'u',
				ऐ: 'ai',
				क: 'ka',
				ग: 'ga',
				घ: 'gha',
				च: 'ca',
				छ: 'cha',
				ज: 'ja',
				त: 'ta',
				द: 'da',
				ध: 'dha',
				न: 'na',
				प: 'pa',
				ब: 'ba',
				भ: 'bha',
				म: 'ma',
				य: 'ya',
				र: 'ra',
				ल: 'la',
				व: 'va',
				श: 'sha',
				ष: 'ssa',
				स: 'sa',
				ह: 'ha'
			};
			return hints[key] ?? '';
		}
		return '';
	}

	function citationRangeLabel(items: ReaderSegment[], fallback: ReaderSegment | null) {
		const first = items[0]?.citation_path;
		const last = items[items.length - 1]?.citation_path;
		if (first && last && first !== last) return `${first} - ${last}`;
		return first || fallback?.citation_path || '';
	}

	function derivePagePagination(items: ReaderSegment[]) {
		const firstSortKey = items[0]?.sort_key;
		const lastSortKey = items[items.length - 1]?.sort_key;
		return {
			previous:
				typeof firstSortKey === 'number' && firstSortKey > pageLimit
					? String(Math.max(0, firstSortKey - 1 - pageLimit))
					: null,
			next: typeof lastSortKey === 'number' ? String(lastSortKey) : null
		};
	}

	function restoreReaderIndexState() {
		if (!browser) return false;

		try {
			const raw = sessionStorage.getItem(readerIndexStorageKey);
			if (!raw) return false;

			const stored = JSON.parse(raw) as Partial<StoredReaderIndexState>;
			if (
				stored.version !== 6 ||
				!stored.expiresAt ||
				stored.expiresAt <= Date.now() ||
				stored.language !== language ||
				(catalogId && stored.catalogId !== catalogId) ||
				!stored.catalogId
			) {
				sessionStorage.removeItem(readerIndexStorageKey);
				return false;
			}

			catalogId = stored.catalogId;
			readerView = stored.readerView ?? 'choose';
			activeAuthorSection = stored.activeAuthorSection ?? '';
			workQuery = stored.workQuery ?? '';
			textQuery = stored.textQuery ?? '';
			textSearchMode = stored.textSearchMode ?? 'fuzzy';
			discoveryGroup = stored.discoveryGroup ?? '';
			discoveryTag = stored.discoveryTag ?? '';
			discoveryAuthorId = stored.discoveryAuthorId ?? '';
			discoveryAuthorLabel = stored.discoveryAuthorLabel ?? '';
			discoverySort = stored.discoverySort ?? 'global-popularity';
			authorAgentKind = stored.authorAgentKind ?? '';
			authorHistoricity = stored.authorHistoricity ?? '';
			worksNextCursor = stored.worksNextCursor ?? null;
			worksPrevCursor = stored.worksPrevCursor ?? null;
			authorsNextCursor = stored.authorsNextCursor ?? null;
			authorsPrevCursor = stored.authorsPrevCursor ?? null;
			textSearchNextCursor = stored.textSearchNextCursor ?? null;
			textSearchPrevCursor = stored.textSearchPrevCursor ?? null;
			authorsLoading = false;
			textSearchLoading = false;
			libraryLoading = false;
			catalogError = '';
			authorsError = '';
			textSearchError = '';
			return true;
		} catch {
			sessionStorage.removeItem(readerIndexStorageKey);
			return false;
		}
	}

	function saveReaderIndexState() {
		if (!browser || !catalogId || !catalogs.length) return;

		const stored: StoredReaderIndexState = {
			version: 6,
			expiresAt: Date.now() + readerIndexStorageTtlMs,
			language,
			catalogId,
			readerView,
			activeAuthorSection,
			workQuery,
			textQuery,
			textSearchMode,
			discoveryGroup,
			discoveryTag,
			discoveryAuthorId,
			discoveryAuthorLabel,
			discoverySort,
			authorAgentKind,
			authorHistoricity,
			worksNextCursor,
			worksPrevCursor,
			authorsNextCursor,
			authorsPrevCursor,
			textSearchNextCursor,
			textSearchPrevCursor
		};

		try {
			sessionStorage.setItem(readerIndexStorageKey, JSON.stringify(stored));
		} catch {
			// Reader discovery remains usable through the API path when storage is unavailable.
		}
	}
</script>

{#snippet readerSkeletonRows(label: string, kind: ReaderLoadingKey, variant: string, count = 4)}
	<div class="orion-reader-loading-region" aria-busy="true" aria-live="polite">
		<div class="orion-reader-loading-status">
			<span>{readerLoadingStatus(label, kind)}</span>
		</div>
		<div class={`orion-reader-skeleton-list orion-reader-skeleton-${variant}`}>
			{#each Array.from({ length: count }) as _, index}
				<article class="orion-reader-skeleton-row" aria-hidden="true">
					<span class="orion-reader-skeleton-block orion-reader-skeleton-title"></span>
					<span class="orion-reader-skeleton-block orion-reader-skeleton-line"></span>
					<span class="orion-reader-skeleton-block orion-reader-skeleton-line short"></span>
					<span class="orion-reader-skeleton-chip-row">
						<span class="orion-reader-skeleton-block orion-reader-skeleton-chip"></span>
						<span class="orion-reader-skeleton-block orion-reader-skeleton-chip"></span>
					</span>
				</article>
			{/each}
		</div>
	</div>
{/snippet}

{#snippet readerLoadingStrip(label: string, kind: ReaderLoadingKey)}
	<div class="orion-reader-loading-strip" aria-busy="true" aria-live="polite">
		<span>{readerLoadingStatus(label, kind)}</span>
	</div>
{/snippet}

{#snippet readerErrorPanel(title: string, message: string, retryLabel: string, retry: () => void)}
	<div class="orion-reader-state-panel orion-reader-state-error" role="alert">
		<strong>{title}</strong>
		<p>{message}</p>
		<button type="button" class="btn btn-sm" onclick={retry}>{retryLabel}</button>
	</div>
{/snippet}

<svelte:window onkeydown={handleReaderKeydown} />

<svelte:head>
	<title>Reader Desk | {uiCopy.app.name}</title>
	<meta
		name="description"
		content="A didactic reader for Sanskrit, Greek, and Latin: search, read, and follow words through the sources."
	/>
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen" data-theme={theme}>
	<header class="navbar border-base-300 bg-base-100 border-b px-4 lg:px-8">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-3">
				<a
					href="/"
					class="orion-home-seal grid h-10 w-10 place-items-center rounded transition-opacity hover:opacity-85"
					aria-label={uiCopy.nav.homeAria}
				>
					<Telescope size={21} />
				</a>
				<div class="min-w-0">
					<div class="truncate text-base font-semibold">{uiCopy.app.name}</div>
					<div class="text-base-content/60 truncate text-sm">Reader Desk</div>
				</div>
			</div>
		</div>

		<div class="flex items-center gap-2">
			<a class="btn btn-sm btn-ghost hidden sm:inline-flex" href="/">
				<Search size={15} />
				Dictionary
			</a>
			<div class="join">
				<button
					type="button"
					class={theme === 'manuscript'
						? 'btn btn-sm join-item btn-primary'
						: 'btn btn-sm join-item'}
					aria-label={uiCopy.theme.readerAria}
					onclick={() => setTheme('manuscript')}
				>
					<Sun size={16} />
				</button>
				<button
					type="button"
					class={theme === 'vespers' ? 'btn btn-sm join-item btn-primary' : 'btn btn-sm join-item'}
					aria-label={uiCopy.theme.nightAria}
					onclick={() => setTheme('vespers')}
				>
					<Moon size={16} />
				</button>
			</div>
		</div>
	</header>

	<div
		class="orion-reader-shell mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,1fr)_24rem] lg:px-8"
	>
		<section class="min-w-0 space-y-6">
			<div class="orion-manuscript-panel p-5 lg:p-6">
				<div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
					<div class="min-w-0">
						<div class="badge badge-secondary badge-outline mb-3 gap-2">
							<BookOpen size={14} />
							Unified reader
						</div>
						<h1 class="font-serif text-3xl leading-tight md:text-4xl">Reader Desk</h1>
						<p class="text-base-content/68 mt-3 max-w-2xl font-serif text-lg leading-7">
							A common desk for Sanskrit, Greek, and Latin: read the text, find the form, and follow
							the lesson through the sources.
						</p>
					</div>

					<div class="grid gap-3 sm:min-w-80">
						<div class="tabs tabs-box">
							{#each languageModes as mode}
								<button
									type="button"
									class={mode.id === language ? 'tab tab-active' : 'tab'}
									onclick={() => selectLanguage(mode.id)}
								>
									{mode.label}
								</button>
							{/each}
						</div>
						<p class="text-base-content/55 font-serif text-sm">
							{indexSummaryLabel}
						</p>
						{#if catalogError}
							<p class="text-error text-sm">{catalogError}</p>
						{/if}
					</div>
				</div>

				<div class="mt-5">
					{#if showAddressLookup}
						<form
							class="orion-reader-address-lookup"
							onsubmit={(event) => {
								event.preventDefault();
								void openAddress('push');
							}}
						>
							<label class="input input-bordered flex min-w-0 items-center gap-2">
								<ScrollText size={16} class="text-base-content/45" />
								<input
									class="font-serif"
									bind:value={addressInput}
									placeholder={language === 'grc' ? 'Od. 3.74' : 'Reader address'}
									autocomplete="off"
								/>
							</label>
							<button class="btn btn-neutral" disabled={segmentLoading || !catalogId}>
								<ScrollText size={16} />
								{segmentLoading ? 'Opening' : 'Open'}
							</button>
							<button type="button" class="btn btn-ghost" onclick={closeAddressLookup}>
								Close
							</button>
						</form>
					{:else}
						<button
							type="button"
							class="btn btn-sm btn-ghost"
							onclick={() => {
								showAddressLookup = true;
							}}
						>
							<ScrollText size={15} />
							Open reference
						</button>
					{/if}
				</div>
			</div>

			<article class="orion-reader-desk-passage orion-manuscript-panel">
				<div class="orion-reader-desk-head">
					<div class="min-w-0">
						<div class="orion-reader-desk-kicker">
							{readerLanguageLabel(language)} index
						</div>
						<h2>
							{#if selectedWork}
								<span class="orion-reader-work-heading">
									<button
										type="button"
										class="orion-reader-desk-author"
										disabled={!(
											selectedWork.canonical_author_id ||
											selectedWork.source_author_id ||
											selectedWork.author_id
										)}
										onclick={openSelectedWorkAuthor}
									>
										{selectedWorkAuthorLabel()}
									</button>
									<span>{selectedWorkTitleLabel()}</span>
									{#if selectedWorkDiscriminator()}
										<small>{selectedWorkDiscriminator()}</small>
									{/if}
									{#if selectedWorkContributorLine()}
										<small>{selectedWorkContributorLine()}</small>
									{/if}
								</span>
							{:else if selectedSegment}
								{selectedSegment.work_id}
							{:else}
								Library
							{/if}
						</h2>
					</div>
					{#if selectedSegment}
						<div class="orion-reader-desk-actions">
							<button
								type="button"
								class={showTransliteration ? 'btn btn-xs btn-secondary' : 'btn btn-xs'}
								aria-pressed={showTransliteration}
								onclick={toggleTransliteration}
							>
								<Feather size={13} />
								Transliteration
							</button>
							<button type="button" class="btn btn-xs" onclick={showLibrary}>
								<Database size={13} />
								Library
							</button>
							<div class="orion-reader-desk-citation">
								<span>page</span>
								<strong>{pageRangeLabel}</strong>
							</div>
						</div>
					{/if}
				</div>

				{#if segmentError}
					<div class="m-5">
						{@render readerErrorPanel(
							'Passage failed to load',
							segmentError,
							'Try opening again',
							retrySegmentLoad
						)}
					</div>
				{:else if segmentLoading && !selectedSegment}
					{@render readerSkeletonRows('Opening passage', 'segment', 'passage', 5)}
				{:else if selectedSegment}
					{#if segmentLoading}
						{@render readerLoadingStrip('Updating passage', 'segment')}
					{/if}
					<div class="orion-reader-page-nav">
						<button
							type="button"
							class="btn btn-sm"
							disabled={!pagePrevCursor || segmentLoading || contentsLoading}
							onclick={() => showPageCursor(pagePrevCursor)}
						>
							Previous page
						</button>
						<div>
							<span>page</span>
							<strong>{pageRangeLabel}</strong>
						</div>
						<button
							type="button"
							class="btn btn-sm"
							disabled={!pageNextCursor || segmentLoading || contentsLoading}
							onclick={() => showPageCursor(pageNextCursor)}
						>
							Next page
						</button>
					</div>

					<div
						class="orion-reader-leaf"
						lang={language === 'grc' ? 'grc' : language === 'san' ? 'sa' : 'la'}
					>
						{#each pageSegments as segment}
							<section class="orion-reader-leaf-line">
								<button
									type="button"
									class="orion-reader-leaf-ref"
									onclick={() => showSelectedWorkSegment(segment)}
								>
									{segment.citation_path}
								</button>
								<p class:interlinear={showTransliteration} class="orion-reader-desk-text">
									{#each segmentParts(segment) as part}
										{#if part.isWord}
											<button
												type="button"
												class:selected={selectedWord === part.word}
												class:interlinear={Boolean(showTransliteration && part.transliteration)}
												class="orion-reader-token"
												onclick={() => selectToken(part.text)}
											>
												<span class="orion-reader-token-native">{part.text}</span>
												{#if showTransliteration && part.transliteration}
													<span class="orion-reader-token-translit">{part.transliteration}</span>
												{/if}
											</button>
										{:else}
											<span>{part.text}</span>
										{/if}
									{/each}
								</p>
							</section>
						{/each}
					</div>

					<div class="orion-reader-page-nav orion-reader-page-nav-bottom">
						<button
							type="button"
							class="btn btn-sm"
							disabled={!pagePrevCursor || segmentLoading || contentsLoading}
							onclick={() => showPageCursor(pagePrevCursor)}
						>
							Previous page
						</button>
						<div>
							<span class="orion-reader-page-work-label">
								{selectedWork ? selectedWorkTitleLabel() : 'reader page'}
								{#if selectedWorkDiscriminator()}
									<small>{selectedWorkDiscriminator()}</small>
								{/if}
							</span>
							<strong>{pageRangeLabel}</strong>
						</div>
						<button
							type="button"
							class="btn btn-sm"
							disabled={!pageNextCursor || segmentLoading || contentsLoading}
							onclick={() => showPageCursor(pageNextCursor)}
						>
							Next page
						</button>
					</div>

					{#if selectedSegment.source_text || selectedSegment.transliteration}
						<details class="orion-reader-desk-source">
							<summary>Source / transliteration</summary>
							{#if selectedSegment.transliteration}
								<p>{selectedSegment.transliteration}</p>
							{/if}
							{#if selectedSegment.source_text}
								<p>{selectedSegment.source_text}</p>
							{/if}
						</details>
					{/if}
				{:else}
					<div class="orion-reader-discovery">
						<div class="orion-reader-discovery-topline">
							<div class="min-w-0">
								<div class="orion-reader-desk-kicker">Library discovery</div>
								<h3>
									{readerView === 'choose'
										? 'Choose a library view'
										: readerView === 'shelves'
											? activeDiscoverySummary
											: readerView === 'search'
												? textQuery.trim()
													? `Text matches for "${textQuery.trim()}"`
													: `${readerLanguageLabel(language)} text search`
												: activeAuthorSection
													? `${readerLanguageLabel(language)} author section ${activeAuthorSection}`
													: workQuery.trim()
														? `Authors matching "${workQuery.trim()}"`
														: `${readerLanguageLabel(language)} authors`}
								</h3>
							</div>
							<div class="join">
								<button
									type="button"
									class="btn join-item btn-sm"
									class:btn-neutral={readerView === 'shelves'}
									aria-pressed={readerView === 'shelves'}
									onclick={() => selectReaderView('shelves')}
								>
									<Telescope size={15} />
									Shelves
								</button>
								<button
									type="button"
									class="btn join-item btn-sm"
									class:btn-neutral={readerView === 'authors'}
									aria-pressed={readerView === 'authors'}
									onclick={() => selectReaderView('authors')}
								>
									<BookOpen size={15} />
									Top authors
								</button>
								<button
									type="button"
									class="btn join-item btn-sm"
									class:btn-neutral={readerView === 'search'}
									aria-pressed={readerView === 'search'}
									onclick={() => selectReaderView('search')}
								>
									<FileSearch size={15} />
									Text search
								</button>
							</div>
						</div>

						{#if readerView === 'choose'}
							<div class="orion-reader-shelf-grid">
								<button
									type="button"
									class="orion-reader-shelf-card"
									onclick={() => selectReaderView('shelves')}
								>
									<span>Browse</span>
									<strong>Shelves</strong>
									<small>{readerLanguageLabel(language)} works by art, subject, and genre</small>
									<p>
										Enter the library by discipline and use, then narrow from broad learning to a
										particular work.
									</p>
								</button>
								<button
									type="button"
									class="orion-reader-shelf-card"
									onclick={() => selectReaderView('authors')}
								>
									<span>Browse</span>
									<strong>Authors</strong>
									<small>{readerLanguageLabel(language)} author index</small>
									<p>
										Begin with teachers, poets, historians, and witnesses, then open the works
										attached to their names.
									</p>
								</button>
								<button
									type="button"
									class="orion-reader-shelf-card"
									onclick={() => selectReaderView('search')}
								>
									<span>Search</span>
									<strong>Text search</strong>
									<small>Trace words and phrases inside {readerLanguageLabel(language)} texts</small
									>
									<p>
										Follow a form through its passages, with enough nearby context to turn a match
										into a lesson.
									</p>
								</button>
							</div>
						{:else if readerView === 'search'}
							<form
								class="orion-reader-discovery-search"
								onsubmit={(event) => {
									event.preventDefault();
									submitTextSearch();
								}}
							>
								<label class="input input-bordered flex min-w-0 items-center gap-2">
									<FileSearch size={16} class="text-base-content/45" />
									<input
										bind:value={textQuery}
										type="search"
										placeholder="Search inside texts"
										autocomplete="off"
									/>
								</label>
								<select
									class="select select-bordered"
									bind:value={textSearchMode}
									onchange={applyTextSearchMode}
								>
									<option value="fuzzy">Fuzzy</option>
									<option value="keyword">Keyword</option>
									<option value="phrase">Phrase</option>
									<option value="exact">Exact</option>
								</select>
								<button class="btn btn-neutral" disabled={textSearchLoading || !catalogId}>
									<Search size={16} />
									{textSearchLoading ? 'Searching' : 'Search'}
								</button>
								<button
									type="button"
									class="btn btn-ghost"
									disabled={textSearchLoading || (!textQuery.trim() && !textSearchResults.length)}
									onclick={clearTextSearch}
								>
									Clear
								</button>
							</form>

							{#if textSearchError}
								{@render readerErrorPanel(
									'Text search failed',
									textSearchError,
									'Search again',
									retryTextSearch
								)}
							{:else if textSearchLoading && !textSearchResults.length}
								{@render readerSkeletonRows('Searching texts', 'textSearch', 'search', 5)}
							{:else if textSearchResults.length}
								{#if textSearchLoading}
									{@render readerLoadingStrip('Updating text matches', 'textSearch')}
								{/if}
								<div class="orion-reader-discovery-summary">
									<span>{textSearchResults.length} matches on this page</span>
									<span
										>{textSearchMode === 'fuzzy'
											? 'Fuzzy text search'
											: `${textSearchMode} search`}</span
									>
								</div>
								{#if visibleTextSearchCandidates(textSearchQueryCandidates).length}
									<div class="orion-reader-work-meta">
										{#each visibleTextSearchCandidates(textSearchQueryCandidates) as candidate}
											<small title={candidate.explanation || candidate.kind}
												>{candidate.kind.replace(/_/g, ' ')} · {textSearchCandidateLabel(
													candidate
												)}</small
											>
										{/each}
									</div>
								{/if}
								<div class="orion-reader-work-list orion-reader-work-list-discovery">
									{#each textSearchResults as result}
										<article class="orion-reader-work-row">
											<div class="orion-reader-work-row-main">
												<button
													type="button"
													class="orion-reader-work-open"
													onclick={() => openSearchResult(result)}
												>
													<strong>
														{result.title || result.work_id}
														<small>{result.citation_path}</small>
													</strong>
												</button>
												<button
													type="button"
													class="orion-reader-work-author"
													disabled={!result.canonical_author_id}
													onclick={() => {
														if (!result.canonical_author_id) return;
														readerView = 'authors';
														routeAuthorId = result.canonical_author_id;
														routeAuthorName = result.canonical_author_name || result.author;
														selectedAuthor = syntheticAuthorFromRoute(
															result.canonical_author_id,
															routeAuthorName
														);
														void searchWorks(
															null,
															result.canonical_author_id,
															'push',
															routeAuthorName
														);
													}}
												>
													{result.author || result.canonical_author_name || 'Unknown'}
												</button>
											</div>
											<span>{result.snippet || result.text}</span>
											<div class="orion-reader-work-meta">
												{#if result.match_type}
													<small>{result.match_type.replace(/_/g, ' ')}</small>
												{/if}
												{#if result.matched_query}
													<small>matched {result.matched_query}</small>
												{/if}
												{#if result.score}
													<small>{result.score.toFixed(2)} score</small>
												{/if}
											</div>
										</article>
									{/each}
								</div>
								{#if textSearchPrevCursor || textSearchNextCursor}
									<div class="orion-reader-discovery-pager">
										<button
											type="button"
											class="btn btn-sm"
											disabled={!textSearchPrevCursor || textSearchLoading}
											onclick={() => void searchReaderText(textSearchPrevCursor, 'push')}
										>
											Previous matches
										</button>
										<button
											type="button"
											class="btn btn-sm btn-neutral"
											disabled={!textSearchNextCursor || textSearchLoading}
											onclick={() => void searchReaderText(textSearchNextCursor, 'push')}
										>
											Next matches
										</button>
									</div>
								{/if}
							{:else if textQuery.trim()}
								<div class="orion-reader-desk-empty">
									<FileSearch size={24} />
									<span>No text matches found for "{textQuery.trim()}".</span>
								</div>
							{/if}
						{:else if readerView === 'shelves'}
							{#if discoveryShelves.length}
								<div class="orion-reader-shelf-grid">
									{#each discoveryShelves as shelf}
										<button
											type="button"
											class="orion-reader-shelf-card"
											class:active={shelfIsActive(shelf)}
											aria-pressed={shelfIsActive(shelf)}
											onclick={() => selectDiscoveryShelf(shelf)}
										>
											<span>{shelf.query.tag ? 'Tag' : 'Shelf'}</span>
											<strong>{shelf.label}</strong>
											<small>{shelfMetaLabel(shelf)}</small>
											{#if shelf.description}
												<p>{shelf.description}</p>
											{/if}
										</button>
									{/each}
								</div>
							{:else if shelvesLoading}
								{@render readerSkeletonRows('Loading shelves', 'shelves', 'work', 4)}
							{/if}
							<form
								class="orion-reader-discovery-search"
								onsubmit={(event) => {
									event.preventDefault();
									submitDiscoverySearch();
								}}
							>
								<label class="input input-bordered flex min-w-0 items-center gap-2">
									<Search size={16} class="text-base-content/45" />
									<input
										bind:value={workQuery}
										type="search"
										placeholder="Search titles or authors"
										autocomplete="off"
									/>
								</label>
								<select
									class="select select-bordered"
									bind:value={discoveryGroup}
									onchange={applyDiscoveryFilters}
								>
									<option value="">All groups</option>
									{#each discoveryGroups as group}
										<option value={group.id}>{group.label}</option>
									{/each}
								</select>
								<select
									class="select select-bordered"
									bind:value={discoveryTag}
									onchange={applyDiscoveryFilters}
								>
									<option value="">All tags</option>
									{#each discoveryTags as tag}
										<option value={tag.id}>{tag.label}</option>
									{/each}
								</select>
								<select
									class="select select-bordered"
									bind:value={discoverySort}
									onchange={applyDiscoveryFilters}
								>
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
								<button class="btn btn-neutral" disabled={libraryLoading || !catalogId}>
									<Search size={16} />
									{libraryLoading ? 'Searching' : 'Search'}
								</button>
								<button
									type="button"
									class="btn btn-ghost"
									disabled={libraryLoading ||
										(!workQuery.trim() &&
											!discoveryGroup &&
											!discoveryTag &&
											!discoveryAuthorId &&
											discoverySort === 'global-popularity')}
									onclick={clearDiscoveryFilters}
								>
									Clear
								</button>
							</form>

							{#if libraryError}
								{@render readerErrorPanel(
									'Works failed to load',
									libraryError,
									'Load works again',
									retryLibrarySearch
								)}
							{:else if !hasActiveDiscoveryQuery}
								<!-- Shelf cards are the default discovery surface; raw works appear after a choice. -->
							{:else if libraryLoading && !works.length}
								{@render readerSkeletonRows('Loading works', 'library', 'work', 5)}
							{:else if works.length}
								{#if libraryLoading}
									{@render readerLoadingStrip('Updating works', 'library')}
								{/if}
								<div bind:this={readerResultsRegion} class="orion-reader-discovery-summary">
									<span>{works.length} works</span>
									<span
										>{facetValueLabel(discoverySorts, discoverySort ?? 'global-popularity')}</span
									>
								</div>
								<div class="orion-reader-work-list orion-reader-work-list-discovery">
									{#if discoveryAuthorId}
										<div class="orion-reader-active-filter">
											<span>{discoveryAuthorLabel || 'Author'}</span>
											<button
												type="button"
												class="btn btn-xs btn-ghost"
												onclick={clearDiscoveryAuthor}
											>
												Clear author
											</button>
										</div>
									{/if}
									{#each works as work}
										<article
											class:selected={selectedWork?.work_id === work.work_id}
											class="orion-reader-work-row"
										>
											<div class="orion-reader-work-row-main">
												<button
													type="button"
													class="orion-reader-work-open"
													onclick={() => void openWork(work)}
												>
													<strong>
														{workListLabel(work)}
														{#if workListDiscriminator(work)}
															<small>{workListDiscriminator(work)}</small>
														{/if}
													</strong>
												</button>
												<button
													type="button"
													class="orion-reader-work-author"
													disabled={!(
														work.canonical_author_id ||
														work.source_author_id ||
														work.author_id
													)}
													onclick={() => filterDiscoveryByAuthor(work)}
												>
													{readerWorkDisplayAuthor(work)}
												</button>
											</div>
											{#if workMetaLine(work)}
												<span>{workMetaLine(work)}</span>
											{/if}
											<div class="orion-reader-work-meta">
												{#if work.classification_discovery_group_id}
													<small>
														{facetValueLabel(
															discoveryGroups,
															work.classification_discovery_group_id
														)}
													</small>
												{/if}
												{#each readerWorkDiscoveryTags(work).slice(0, 4) as tag}
													<small>{facetValueLabel(discoveryTags, tag)}</small>
												{/each}
												{#if readerPopularityLabel(work)}
													<small>{readerPopularityLabel(work)}</small>
												{/if}
											</div>
										</article>
									{/each}
								</div>
								{#if worksPrevCursor || worksNextCursor}
									<div class="orion-reader-discovery-pager">
										<button
											type="button"
											class="btn btn-sm"
											disabled={!worksPrevCursor || libraryLoading}
											onclick={() => void searchWorks(worksPrevCursor, undefined, 'push')}
										>
											Previous works
										</button>
										<button
											type="button"
											class="btn btn-sm btn-neutral"
											disabled={!worksNextCursor || libraryLoading}
											onclick={() => void searchWorks(worksNextCursor, undefined, 'push')}
										>
											Next works
										</button>
									</div>
								{/if}
							{:else if hasActiveDiscoveryQuery && !libraryLoading}
								<div class="orion-reader-desk-empty">
									<Telescope size={24} />
									<span>No works found for this selection.</span>
								</div>
							{/if}
						{:else}
							<form
								class="orion-reader-discovery-search orion-reader-author-search"
								onsubmit={(event) => {
									event.preventDefault();
									submitAuthorSearch();
								}}
							>
								<label class="input input-bordered flex min-w-0 items-center gap-2">
									<Search size={16} class="text-base-content/45" />
									<input
										bind:value={workQuery}
										type="search"
										placeholder="Search authors"
										autocomplete="off"
									/>
								</label>
								<select
									class="select select-bordered"
									bind:value={authorAgentKind}
									onchange={applyAuthorFilters}
								>
									<option value="">All author kinds</option>
									{#each authorAgentKinds as kind}
										<option value={kind.id}>{kind.label}</option>
									{/each}
								</select>
								<select
									class="select select-bordered"
									bind:value={authorHistoricity}
									onchange={applyAuthorFilters}
								>
									<option value="">All historicity</option>
									{#each authorHistoricityStatuses as status}
										<option value={status.id}>{status.label}</option>
									{/each}
								</select>
								<button class="btn btn-neutral" disabled={authorsLoading || !catalogId}>
									<Search size={16} />
									{authorsLoading ? 'Searching' : 'Search'}
								</button>
							</form>

							<div class="orion-reader-author-toc" aria-label="Author sections">
								<div>
									<span>{readerLanguageLabel(language)} author index</span>
									{#if activeAuthorSection}
										<button type="button" class="btn btn-xs btn-ghost" onclick={clearAuthorSection}>
											All
										</button>
									{/if}
								</div>
								<div class="orion-reader-author-toc-grid">
									{#each authorSections as section}
										{@const nativeLabel = section.native_label || section.label || section.key}
										{@const romanHint = authorSectionRomanHint(language, section.key)}
										<button
											type="button"
											class:active={activeAuthorSection === section.key}
											onclick={() => jumpToAuthorSection(section.key)}
											title={`${section.author_count} authors, ${section.work_count} works`}
										>
											<span class="orion-reader-author-section-native">{nativeLabel}</span>
											{#if romanHint && romanHint !== nativeLabel}
												<span class="orion-reader-author-section-roman">{romanHint}</span>
											{/if}
										</button>
									{/each}
								</div>
							</div>

							{#if authorsError || libraryError}
								{@render readerErrorPanel(
									authorsError ? 'Authors failed to load' : 'Author works failed to load',
									authorsError || libraryError,
									authorsError ? 'Search authors again' : 'Load works again',
									authorsError ? retryAuthorSearch : retryLibrarySearch
								)}
							{:else if authorsLoading && !authors.length}
								{@render readerSkeletonRows('Searching authors', 'authors', 'author', 5)}
							{:else if authors.length}
								{#if authorsLoading}
									{@render readerLoadingStrip('Updating authors', 'authors')}
								{/if}
								<div class="orion-reader-discovery-summary">
									<span>{authors.length} authors</span>
									<span>{indexSummaryLabel}</span>
								</div>
								<div class="orion-reader-author-list">
									{#each authors as author}
										<section class="orion-reader-author-group">
											<div class="orion-reader-author-heading">
												<button
													type="button"
													class="orion-reader-author-button"
													onclick={() => openAuthor(author)}
												>
													<h3>{author.display_name || author.author}</h3>
													{#if author.index_name && author.index_name !== author.display_name}
														<small>{author.index_name}</small>
													{/if}
												</button>
												<span>{author.work_count} {author.work_count === 1 ? 'work' : 'works'}</span
												>
											</div>
											{#if selectedAuthor?.author_id === author.author_id}
												{#if libraryLoading}
													{@render readerSkeletonRows('Loading author works', 'library', 'work', 3)}
												{:else if works.length}
													<div class="orion-reader-work-list">
														{#each works as work}
															<button
																type="button"
																class:selected={selectedWork?.work_id === work.work_id}
																class="orion-reader-work-row"
																onclick={() => void openWork(work)}
															>
																<strong>
																	{workListLabel(work)}
																	{#if workListDiscriminator(work)}
																		<small>{workListDiscriminator(work)}</small>
																	{/if}
																</strong>
																<span>{workMetaLine(work) || 'First page'}</span>
															</button>
														{/each}
													</div>
												{/if}
											{/if}
										</section>
									{/each}
								</div>
								{#if authorsPrevCursor || authorsNextCursor}
									<div class="orion-reader-discovery-pager">
										<button
											type="button"
											class="btn btn-sm"
											disabled={!authorsPrevCursor || authorsLoading}
											onclick={() => void loadAuthors(authorsPrevCursor, 'push')}
										>
											Previous authors
										</button>
										<button
											type="button"
											class="btn btn-sm btn-neutral"
											disabled={!authorsNextCursor || authorsLoading}
											onclick={() => void loadAuthors(authorsNextCursor, 'push')}
										>
											Next authors
										</button>
									</div>
								{/if}
							{:else}
								<div class="orion-reader-desk-empty">
									<Feather size={24} />
									<span>
										{activeAuthorSection
											? `No authors found in section ${activeAuthorSection}.`
											: 'No authors found for this selection.'}
									</span>
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			</article>
		</section>

		<aside class="orion-reader-sidebar space-y-4">
			<section class="orion-manuscript-panel p-4">
				<div class="mb-3 flex items-start justify-between gap-3">
					<div>
						<h2 class="font-serif text-lg font-semibold">Book contents</h2>
					</div>
					<ScrollText class="text-base-content/45 mt-1" size={18} />
				</div>
				{#if contentsLoading}
					{@render readerSkeletonRows('Loading contents', 'contents', 'contents', 4)}
				{:else if contentsError}
					{@render readerErrorPanel(
						'Contents failed to load',
						contentsError,
						'Load contents again',
						retryContentsLoad
					)}
				{:else if contents.length && selectedWork}
					<div class="orion-reader-contents-list">
						{#each contents as segment}
							<button
								type="button"
								class:active={segmentIsActive(segment)}
								onclick={() => showSelectedWorkSegment(segment)}
							>
								<span>{segment.citation_path}</span>
								<small>{readerSegmentDisplayText(segment)}</small>
							</button>
						{/each}
					</div>
				{:else}
					<p class="text-base-content/55 text-sm">No book selected.</p>
				{/if}
			</section>

			<section class="orion-manuscript-panel p-4">
				<div class="mb-3 flex items-start justify-between gap-3">
					<div>
						<h2 class="font-serif text-lg font-semibold">Encounter</h2>
						<p class="text-base-content/60 text-sm">Word study</p>
					</div>
					<BookOpen class="text-base-content/45 mt-1" size={18} />
				</div>
				{#if selectedWord}
					<div class="orion-reader-selected-word">
						<strong>{selectedWord}</strong>
						{#if selectedWordRomanization}
							<span>{selectedWordRomanization.label}: {selectedWordRomanization.value}</span>
						{/if}
						<a class="btn btn-sm btn-secondary mt-3" href={selectedWordHref}>
							<Search size={15} />
							Study word
						</a>
					</div>
				{:else}
					<p class="text-base-content/55 text-sm">
						Click a word in the passage to prepare a lookup.
					</p>
				{/if}
			</section>
		</aside>
	</div>
</main>
