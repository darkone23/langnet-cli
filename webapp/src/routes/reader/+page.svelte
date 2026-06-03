<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount, tick } from 'svelte';
	import { fetchPayload } from '$lib/msgpack';
	import ReaderApparatusSheet from '$lib/ReaderApparatusSheet.svelte';
	import ReaderApparatusTabs from '$lib/ReaderApparatusTabs.svelte';
	import ReaderContextSidebar from '$lib/ReaderContextSidebar.svelte';
	import ReaderDeskChrome from '$lib/ReaderDeskChrome.svelte';
	import ReaderDeskHeader from '$lib/ReaderDeskHeader.svelte';
	import ReaderDiscoveryView from '$lib/ReaderDiscoveryView.svelte';
	import ReaderErrorPanel from '$lib/ReaderErrorPanel.svelte';
	import ReaderLoadingRows from '$lib/ReaderLoadingRows.svelte';
	import ReaderLoadingStrip from '$lib/ReaderLoadingStrip.svelte';
	import ReaderPassageView from '$lib/ReaderPassageView.svelte';
	import ReaderSelectedWorkDesk from '$lib/ReaderSelectedWorkDesk.svelte';
	import ReaderShell from '$lib/ReaderShell.svelte';
	import {
		buildStoredReaderIndexState,
		readStoredReaderIndexState,
		writeStoredReaderIndexState,
		type ReaderIndexView
	} from '$lib/reader-index-storage';
	import { createReaderLoadingTimers, type ReaderLoadingKey } from '$lib/reader-loading-timers';
	import {
		buildReaderIndexStatsTargets,
		findReaderIndexStatsInList,
		readerIndexStatsFromSections,
		upsertReaderIndexStatsList
	} from '$lib/reader-index-stats';
	import {
		readerFacetValueLabel,
		readerFacetValues as facetValues,
		readerSelectedWorkAuthorLabel,
		readerSelectedWorkContributorLine,
		readerSelectedWorkDiscriminator,
		readerSelectedWorkTitleLabel,
		readerSyntheticAuthorFromRoute,
		readerSyntheticAuthorFromWork,
		upsertReaderAuthor
	} from '$lib/reader-page-authors';
	import {
		deriveReaderPagePagination,
		readerAuthorSectionRomanHint as authorSectionRomanHint,
		readerCitationRangeLabel,
		readerDiscoverySummaryLabel,
		readerDiscoveryTitleLabel,
		readerShelfMetaLabel as shelfMetaLabel,
		readerTextSearchCandidateLabel as textSearchCandidateLabel,
		readerVisibleTextSearchCandidates as visibleTextSearchCandidates,
		readerWorkMetaLine as workMetaLine
	} from '$lib/reader-page-formatting';
	import {
		readerCurrentReadingWorkRef,
		readerSearchResultWorkRef,
		readerSegmentIsActive,
		readerShelfIsActive
	} from '$lib/reader-page-navigation';
	import {
		encounterBriefingCanGenerate,
		encounterBriefingIsGenerated,
		encounterBriefingModelLabel,
		encounterBriefingOutput,
		type EncounterBriefingFlow,
		type EncounterBriefingSummary
	} from '$lib/encounter-briefing';
	import {
		buildReaderTokenParts,
		buildReaderRouteSearch,
		cleanReaderToken,
		parseReaderRouteState,
		readerAuthorMatchesId,
		readerAuthorRouteStateFromWork,
		readerDiscoverySortValues,
		readerFacetValuesForLanguage,
		readerHasIndexStats,
		readerIndexSummaryLabel,
		readerIndexStatsKey,
		readerLanguageLabel,
		readerLoadingStatusLabel,
		readerShelfRouteState,
		readerWorkListDiscriminator,
		readerWorkListLabel,
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
		type ReaderWorkDossierResponse,
		type ReaderWorkResponse,
		type ReaderStructureNode,
		type ReaderStructureResponse,
		type ReaderWorksResponse
	} from '$lib/reader';
	import {
		buildCurrentReaderRouteState,
		defaultReaderAddressForLanguage,
		formatReaderAddress,
		readerIsCanonicalRef,
		readerWorkHasContributorMetadata,
		type ReaderRouteOverrides
	} from '$lib/reader-page-routing';
	import { romanizeSearchTerm } from '$lib/search-romanization';
	import { languageModes, type LanguageMode } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

	type ReaderHistoryMode = 'push' | 'replace' | 'none';

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
	let structure = $state<ReaderStructureNode[]>([]);
	let workDossier = $state<ReaderWorkDossierResponse | null>(null);
	let selectedSegment = $state<ReaderSegment | null>(null);
	let pageSegments = $state<ReaderSegment[]>([]);
	let navigation = $state<{
		previous: ReaderNavigationTarget | null;
		next: ReaderNavigationTarget | null;
	}>({ previous: null, next: null });
	let addressInput = $state('Od. 3.74');
	let showAddressLookup = $state(false);
	let selectedWord = $state('');
	let selectedWordBriefing = $state<EncounterBriefingFlow | null>(null);
	let selectedWordBriefingLoading = $state(false);
	let selectedWordBriefingGenerating = $state(false);
	let selectedWordBriefingError = $state('');
	let activeApparatusPanel = $state<'structure' | 'word' | 'oracle' | 'evidence' | ''>('');
	let shelvesLoading = $state(false);
	let libraryLoading = $state(false);
	let contentsLoading = $state(false);
	let structureLoading = $state(false);
	let dossierLoading = $state(false);
	let segmentLoading = $state(false);
	let libraryError = $state('');
	let authorsLoading = $state(false);
	let textSearchLoading = $state(false);
	let shelvesLoadingElapsedSeconds = $state(0);
	let libraryLoadingElapsedSeconds = $state(0);
	let authorsLoadingElapsedSeconds = $state(0);
	let textSearchElapsedSeconds = $state(0);
	let contentsLoadingElapsedSeconds = $state(0);
	let structureLoadingElapsedSeconds = $state(0);
	let dossierLoadingElapsedSeconds = $state(0);
	let segmentLoadingElapsedSeconds = $state(0);
	let authorsError = $state('');
	let textSearchError = $state('');
	let contentsError = $state('');
	let structureError = $state('');
	let dossierError = $state('');
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
	const readerLoadingTimers = createReaderLoadingTimers(setReaderLoadingElapsedSeconds);
	const readerIndexStatsInFlight = new Set<string>();
	let selectedWordBriefingController: AbortController | null = null;

	let selectedWordRomanization = $derived(
		selectedWord ? romanizeSearchTerm(language, selectedWord) : null
	);
	let selectedWordHref = $derived(
		selectedWord
			? `/?language=${language}&q=${encodeURIComponent(selectedWord)}&load=yes&backend=cli`
			: '/'
	);
	let selectedWordBriefingOutput = $derived(encounterBriefingOutput(selectedWordBriefing));
	let selectedWordBriefingGenerated = $derived(encounterBriefingIsGenerated(selectedWordBriefing));
	let selectedWordBriefingCanGenerate = $derived(
		encounterBriefingCanGenerate(selectedWordBriefing)
	);
	let selectedWordBriefingModel = $derived(encounterBriefingModelLabel(selectedWordBriefing));
	let selectedWordBriefingBadge = $derived(
		selectedWordBriefingGenerated
			? selectedWordBriefingModel
				? uiCopy.encounterBriefing.provenanceGenerated(selectedWordBriefingModel)
				: uiCopy.encounterBriefing.statusGenerated
			: uiCopy.encounterBriefing.statusDraft
	);
	let currentDivisionTrail = $derived(selectedSegment?.current_divisions ?? []);
	let currentDivisionNode = $derived(
		currentDivisionTrail.length ? currentDivisionTrail[currentDivisionTrail.length - 1] : null
	);
	let activeReaderIndexStats = $derived(findReaderIndexStats(language, catalogId));
	let indexSummaryLabel = $derived(
		readerIndexSummaryLabel(language, catalogId, activeReaderIndexStats)
	);
	let pageRangeLabel = $derived(readerCitationRangeLabel(pageSegments, selectedSegment));
	let discoveryGroups = $derived(facetValues(facets, 'discovery_groups'));
	let discoveryTags = $derived(
		readerFacetValuesForLanguage(facetValues(facets, 'discovery_tags'), language)
	);
	let discoverySorts = $derived(readerDiscoverySortValues(facetValues(facets, 'sorts')));
	let authorAgentKinds = $derived(facetValues(facets, 'author_agent_kinds'));
	let authorHistoricityStatuses = $derived(facetValues(facets, 'author_historicity_statuses'));
	let activeDiscoverySummary = $derived(
		readerDiscoverySummaryLabel({
			discoveryGroup,
			discoveryTag,
			workQuery,
			discoveryAuthorLabel,
			discoveryGroups,
			discoveryTags,
			languageLabel: readerLanguageLabel(language)
		})
	);
	let activeDiscoveryTitle = $derived(
		readerDiscoveryTitleLabel({
			readerView,
			activeDiscoverySummary,
			textQuery,
			activeAuthorSection,
			workQuery,
			languageLabel: readerLanguageLabel(language)
		})
	);
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
		selectedWordBriefing = null;
		selectedWordBriefingError = '';
		selectedWordBriefingGenerating = false;
		if (selectedWord) void fetchEncounterBriefing(selectedWord);
		if (route.theme) setTheme(route.theme, false);
		if (route.address) {
			addressInput = route.address;
			showAddressLookup = true;
		} else if (!route.work && !route.segment)
			addressInput = defaultReaderAddressForLanguage(language);
		if (!route.work && !route.segment) {
			selectedWork = null;
			selectedSegment = null;
			contents = [];
			structure = [];
			workDossier = null;
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
			await loadStructure(route.work);
			await loadWorkDossier(route.work);
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
			selectedAuthor = readerSyntheticAuthorFromRoute(
				route.discoveryAuthorId,
				route.discoveryAuthorLabel ?? route.discoveryAuthorId,
				language
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

	async function fetchEncounterBriefing(word: string, generate = false) {
		const token = cleanReaderToken(word);
		if (!token) return;
		selectedWordBriefingController?.abort();
		const controller = new AbortController();
		selectedWordBriefingController = controller;
		selectedWordBriefingLoading = true;
		selectedWordBriefingGenerating = generate;
		selectedWordBriefingError = '';
		if (!generate) selectedWordBriefing = null;
		try {
			const params = new URLSearchParams({
				language,
				q: token,
				translation: 'cache',
				timeout_ms: generate ? '300000' : '180000'
			});
			if (generate) params.set('generate', '1');
			const { response, data } = await fetchPayload<EncounterBriefingFlow & { error?: string }>(
				`/api/encounter-briefing?${params.toString()}`,
				{ signal: controller.signal }
			);
			if (!response.ok) throw new Error(data.error || 'Encounter briefing failed.');
			if (selectedWord === token) selectedWordBriefing = data;
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			if (selectedWord === token) {
				selectedWordBriefingError =
					error instanceof Error ? error.message : 'Encounter briefing failed.';
			}
		} finally {
			if (selectedWordBriefingController === controller) {
				selectedWordBriefingController = null;
				selectedWordBriefingLoading = false;
				selectedWordBriefingGenerating = false;
			}
		}
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
		addressInput = defaultReaderAddressForLanguage(nextLanguage);
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
		selectedWordBriefingController?.abort();
		selectedWordBriefingController = null;
		selectedWordBriefing = null;
		selectedWordBriefingError = '';
		selectedWordBriefingLoading = false;
		selectedWordBriefingGenerating = false;
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

	function findReaderIndexStats(targetLanguage: LanguageMode, targetCatalogId: string) {
		return findReaderIndexStatsInList(readerIndexStats, targetLanguage, targetCatalogId);
	}

	function upsertReaderIndexStats(stats: ReaderIndexStats) {
		readerIndexStats = upsertReaderIndexStatsList(readerIndexStats, stats);
		saveReaderIndexState();
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
		const targets = buildReaderIndexStatsTargets({
			catalogs,
			catalogDefaults,
			languageModes,
			activeLanguage: language,
			activeCatalogId: catalogId
		});

		await Promise.all(
			targets.map((target) => loadReaderIndexStatsFor(target.language, target.catalogId))
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

	function upsertAuthor(author: ReaderAuthor) {
		authors = upsertReaderAuthor(authors, author);
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
		const synthetic = readerSyntheticAuthorFromRoute(authorId, authorName, language);
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
		structure = [];
		workDossier = null;
		navigation = { previous: null, next: null };
		pageNextCursor = null;
		pagePrevCursor = null;
		selectedWord = '';
		contentsCursorParam = null;
		pageCursorParam = null;
		showAddressLookup = false;
		addressInput = defaultReaderAddressForLanguage(language);
		updateReaderUrl({}, 'push');
		if (readerView === 'shelves' && hasActiveDiscoveryQuery && !works.length)
			void searchWorks(null, routeAuthorId || undefined, 'replace');
	}

	async function openWork(work: ReaderWork) {
		selectedWork = work;
		selectedSegment = null;
		selectedWord = '';
		contents = [];
		structure = [];
		workDossier = null;
		contentsError = '';
		structureError = '';
		dossierError = '';
		contentsCursorParam = null;
		pageCursorParam = null;
		await loadStructure(readerWorkRef(work));
		await loadWorkDossier(readerWorkRef(work));
		await loadContentsPage(readerWorkRef(work), null, 'push');
	}

	async function loadStructure(work: string) {
		if (!work || !catalogId) return;
		structureLoading = true;
		structureError = '';
		startReaderLoadingTimer('structure');
		try {
			const params = new URLSearchParams({
				mode: 'structure',
				catalog: catalogId,
				language,
				work,
				timeout_ms: '120000'
			});
			const { response, data } = await fetchReaderApi<ReaderStructureResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader structure failed.');
			structure = data.items ?? [];
		} catch (error) {
			structureError = error instanceof Error ? error.message : 'Reader structure failed.';
		} finally {
			structureLoading = false;
			stopReaderLoadingTimer('structure');
		}
	}

	async function loadWorkDossier(work: string) {
		if (!work || !catalogId) return;
		dossierLoading = true;
		dossierError = '';
		startReaderLoadingTimer('dossier');
		try {
			const params = new URLSearchParams({
				mode: 'about',
				catalog: catalogId,
				language,
				work,
				timeout_ms: '120000'
			});
			const { response, data } = await fetchReaderApi<ReaderWorkDossierResponse>(
				`/api/reader?${params.toString()}`
			);
			if (!response.ok) throw new Error(data.error || 'Reader work dossier failed.');
			workDossier = data;
		} catch (error) {
			dossierError = error instanceof Error ? error.message : 'Reader work dossier failed.';
		} finally {
			dossierLoading = false;
			stopReaderLoadingTimer('dossier');
		}
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
			if (selectedWork && !structure.some((node) => node.work_id === selectedWork?.work_id)) {
				await loadStructure(readerWorkRef(selectedWork));
			}
			if (selectedWork && workDossier?.work?.work_id !== selectedWork.work_id) {
				await loadWorkDossier(readerWorkRef(selectedWork));
			}
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
		if (workSegment && readerIsCanonicalRef(workSegment[1])) {
			await showSegment(workSegment[1], workSegment[2], 'replace');
			return;
		}
		if (readerIsCanonicalRef(address)) {
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
			selectedSegment = data.segment
				? {
						...data.segment,
						current_divisions: data.current_divisions ?? data.segment.current_divisions
					}
				: null;
			navigation = data.navigation ?? { previous: null, next: null };
			if (data.segment) {
				const resolvedWork = data.structure_node?.work_id || data.segment.work_id;
				await ensureSelectedWork(resolvedWork);
				if (data.structure_node && !structure.some((node) => node.work_id === resolvedWork)) {
					await loadStructure(resolvedWork);
				}
				if (selectedWork && workDossier?.work?.work_id !== selectedWork.work_id) {
					await loadWorkDossier(readerWorkRef(selectedWork));
				}
				await loadPageWindow(resolvedWork, data.segment.citation_path);
				contentsCursorParam = null;
				pageCursorParam = null;
				syncUrl(resolvedWork, data.segment.citation_path, historyMode);
			}
		} catch (error) {
			segmentError = error instanceof Error ? error.message : 'Reference lookup failed.';
		} finally {
			segmentLoading = false;
			stopReaderLoadingTimer('segment');
		}
	}

	async function ensureSelectedWork(work: string) {
		if (
			selectedWork &&
			(selectedWork.work_id === work ||
				selectedWork.cts_work_urn === work ||
				selectedWork.canonical_text_id === work ||
				selectedWork.canonical_address === work) &&
			readerWorkHasContributorMetadata(selectedWork)
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
			const derivedPagination = deriveReaderPagePagination(pageSegments, pageLimit);
			pageNextCursor = data.pagination?.next_cursor ?? derivedPagination.next;
			pagePrevCursor = data.pagination?.prev_cursor ?? derivedPagination.previous;
		} catch {
			pageSegments = selectedSegment ? [selectedSegment] : [];
			pageNextCursor = null;
			pagePrevCursor = null;
		}
	}

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
		return buildCurrentReaderRouteState({
			language,
			catalogId,
			readerView,
			selectedWork,
			selectedSegment,
			addressInput,
			showAddressLookup,
			workQuery,
			textQuery,
			textSearchMode,
			textSearchCursorParam,
			discoveryGroup,
			discoveryTag,
			discoveryAuthorId,
			discoveryAuthorLabel,
			discoverySort,
			authorAgentKind,
			authorHistoricity,
			activeAuthorSection,
			selectedAuthorId: selectedAuthor?.author_id,
			routeAuthorId,
			routeAuthorName,
			authorsCursorParam,
			worksCursorParam,
			contentsCursorParam,
			pageCursorParam,
			activeCollection,
			selectedWord,
			theme,
			showTransliteration
		});
	}

	function selectToken(text: string) {
		const token = cleanReaderToken(text);
		if (!token) return;
		selectedWord = token;
		selectedWordBriefing = null;
		selectedWordBriefingError = '';
		selectedWordBriefingGenerating = false;
		updateReaderUrl({ selectedWord: token }, 'replace');
		void fetchEncounterBriefing(token);
	}

	function segmentIsActive(segment: ReaderSegment) {
		return readerSegmentIsActive(selectedSegment, segment);
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
			addressInput = defaultReaderAddressForLanguage(language);
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
		return readerShelfIsActive(shelf, { discoveryGroup, discoveryTag });
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

	function startReaderLoadingTimer(kind: ReaderLoadingKey) {
		readerLoadingTimers.start(kind);
	}

	function stopReaderLoadingTimer(kind: ReaderLoadingKey) {
		readerLoadingTimers.stop(kind);
	}

	function stopAllReaderLoadingTimers() {
		readerLoadingTimers.stopAll();
	}

	function setReaderLoadingElapsedSeconds(kind: ReaderLoadingKey, seconds: number) {
		if (kind === 'shelves') shelvesLoadingElapsedSeconds = seconds;
		else if (kind === 'library') libraryLoadingElapsedSeconds = seconds;
		else if (kind === 'authors') authorsLoadingElapsedSeconds = seconds;
		else if (kind === 'textSearch') textSearchElapsedSeconds = seconds;
		else if (kind === 'contents') contentsLoadingElapsedSeconds = seconds;
		else if (kind === 'structure') structureLoadingElapsedSeconds = seconds;
		else if (kind === 'dossier') dossierLoadingElapsedSeconds = seconds;
		else segmentLoadingElapsedSeconds = seconds;
	}

	function readerLoadingElapsedSeconds(kind: ReaderLoadingKey) {
		if (kind === 'shelves') return shelvesLoadingElapsedSeconds;
		if (kind === 'library') return libraryLoadingElapsedSeconds;
		if (kind === 'authors') return authorsLoadingElapsedSeconds;
		if (kind === 'textSearch') return textSearchElapsedSeconds;
		if (kind === 'contents') return contentsLoadingElapsedSeconds;
		if (kind === 'structure') return structureLoadingElapsedSeconds;
		if (kind === 'dossier') return dossierLoadingElapsedSeconds;
		return segmentLoadingElapsedSeconds;
	}

	function readerLoadingElapsed(kind: ReaderLoadingKey) {
		return readerLoadingElapsedSeconds(kind);
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
		const work = readerSearchResultWorkRef(result);
		if (!work || !result.citation_path) return;
		void showSegment(work, result.citation_path, 'push');
	}

	function openSearchResultAuthor(result: ReaderSearchResult) {
		if (!result.canonical_author_id) return;
		readerView = 'authors';
		routeAuthorId = result.canonical_author_id;
		routeAuthorName = result.canonical_author_name || result.author;
		selectedAuthor = readerSyntheticAuthorFromRoute(
			result.canonical_author_id,
			routeAuthorName,
			language
		);
		void searchWorks(null, result.canonical_author_id, 'push', routeAuthorName);
	}

	function filterDiscoveryByAuthor(work: ReaderWork) {
		const route = readerAuthorRouteStateFromWork(work);
		if (!route?.authorId) return;
		const author = readerSyntheticAuthorFromWork(work, route.authorId);
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
		const work = readerCurrentReadingWorkRef(selectedWork, selectedSegment);
		if (!work) return;
		void loadContentsPage(work, cursor, 'push');
	}

	function showNavigationTarget(target: ReaderNavigationTarget | null) {
		if (!target) return;
		const work = readerCurrentReadingWorkRef(selectedWork, selectedSegment);
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

	function facetValueLabel(values: ReaderFacetValue[], id: string) {
		return readerFacetValueLabel(values, id);
	}

	function workListLabel(work: ReaderWork) {
		return readerWorkListLabel(work, works);
	}

	function workListDiscriminator(work: ReaderWork) {
		return readerWorkListDiscriminator(work, works);
	}

	function selectedWorkTitleLabel() {
		return readerSelectedWorkTitleLabel(selectedWork, works);
	}

	function selectedWorkDiscriminator() {
		return readerSelectedWorkDiscriminator(selectedWork, works);
	}

	function selectedWorkContributorLine() {
		return readerSelectedWorkContributorLine(selectedWork);
	}

	function selectedWorkAuthorLabel() {
		return readerSelectedWorkAuthorLabel(selectedWork);
	}

	function openSelectedWorkAuthor() {
		if (!selectedWork) return;
		filterDiscoveryByAuthor(selectedWork);
	}

	function restoreReaderIndexState() {
		if (!browser) return false;

		const stored = readStoredReaderIndexState(sessionStorage, { language, catalogId });
		if (!stored) return false;

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
	}

	function saveReaderIndexState() {
		if (!browser || !catalogId || !catalogs.length) return;

		const stored = buildStoredReaderIndexState({
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
		});

		writeStoredReaderIndexState(sessionStorage, stored);
	}
</script>

<svelte:window onkeydown={handleReaderKeydown} />

<svelte:head>
	<title>Reader Desk | {uiCopy.app.name}</title>
	<meta
		name="description"
		content="A didactic reader for Sanskrit, Greek, and Latin: search, read, and follow words through the sources."
	/>
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen" data-theme={theme}>
	<ReaderDeskChrome
		{theme}
		{language}
		{indexSummaryLabel}
		{catalogError}
		{showAddressLookup}
		{addressInput}
		{segmentLoading}
		catalogReady={Boolean(catalogId)}
		onThemeSelect={setTheme}
		onLanguageSelect={selectLanguage}
		onAddressInput={(value) => {
			addressInput = value;
		}}
		onOpenAddress={() => void openAddress('push')}
		onCloseLookup={closeAddressLookup}
		onShowLookup={() => {
			showAddressLookup = true;
		}}
	/>

	<ReaderShell>
		{#if selectedWork}
			<ReaderSelectedWorkDesk
				workTitle={selectedWorkTitleLabel()}
				workSubtitle={selectedWorkContributorLine() || selectedWorkDiscriminator()}
				classificationConfidence={selectedWork.classification_confidence}
				dossier={workDossier}
				{dossierLoading}
				dossierLoadingLabel={readerLoadingStatus(uiCopy.workDossier.loading, 'dossier')}
				{dossierError}
				{currentDivisionNode}
				onOpenDivision={(workId, citation) => showSegment(workId, citation, 'push')}
				onRetry={() => selectedWork && void loadWorkDossier(readerWorkRef(selectedWork))}
			/>
		{/if}

		<article class="orion-reader-desk-passage orion-manuscript-panel">
			<ReaderDeskHeader
				languageLabel={readerLanguageLabel(language)}
				workAuthorLabel={selectedWork ? selectedWorkAuthorLabel() : null}
				workTitle={selectedWork ? selectedWorkTitleLabel() : null}
				workDiscriminator={selectedWorkDiscriminator()}
				workContributorLine={selectedWorkContributorLine()}
				canOpenAuthor={Boolean(
					selectedWork?.canonical_author_id ||
					selectedWork?.source_author_id ||
					selectedWork?.author_id
				)}
				segmentWorkId={selectedSegment?.work_id}
				hasSelectedSegment={Boolean(selectedSegment)}
				{showTransliteration}
				{pageRangeLabel}
				onOpenAuthor={openSelectedWorkAuthor}
				onToggleTransliteration={toggleTransliteration}
				onShowLibrary={showLibrary}
			/>

			{#if segmentError || segmentLoading || selectedSegment}
				<ReaderPassageView
					{segmentError}
					{segmentLoading}
					{selectedSegment}
					{pagePrevCursor}
					{pageNextCursor}
					{contentsLoading}
					{pageRangeLabel}
					{currentDivisionTrail}
					{currentDivisionNode}
					{pageSegments}
					{language}
					{selectedWord}
					{showTransliteration}
					selectedWorkLabel={selectedWork ? selectedWorkTitleLabel() : 'reader page'}
					selectedWorkDetail={selectedWorkDiscriminator()}
					openingStatusLabel={readerLoadingStatus('Opening passage', 'segment')}
					openingElapsedLabel={readerLoadingElapsed('segment')}
					updatingStatusLabel={readerLoadingStatus('Updating passage', 'segment')}
					updatingElapsedLabel={readerLoadingElapsed('segment')}
					{segmentParts}
					onRetrySegment={retrySegmentLoad}
					onOpenPage={showPageCursor}
					onOpenDivision={(workId, citation) => showSegment(workId, citation, 'push')}
					onOpenSegment={showSelectedWorkSegment}
					onSelectToken={selectToken}
				/>
			{:else}
				<ReaderDiscoveryView
					{activeDiscoveryTitle}
					{readerView}
					languageLabel={readerLanguageLabel(language)}
					catalogReady={Boolean(catalogId)}
					{textQuery}
					{textSearchMode}
					{textSearchLoading}
					{textSearchError}
					{textSearchResults}
					textSearchQueryCandidates={visibleTextSearchCandidates(textSearchQueryCandidates)}
					{textSearchCandidateLabel}
					{textSearchPrevCursor}
					{textSearchNextCursor}
					textSearchingStatusLabel={readerLoadingStatus('Searching texts', 'textSearch')}
					textSearchingElapsedLabel={readerLoadingElapsed('textSearch')}
					textUpdatingStatusLabel={readerLoadingStatus('Updating text matches', 'textSearch')}
					textUpdatingElapsedLabel={readerLoadingElapsed('textSearch')}
					{discoveryShelves}
					{shelvesLoading}
					{workQuery}
					{discoveryGroup}
					{discoveryTag}
					{discoveryAuthorId}
					{discoveryAuthorLabel}
					discoverySort={discoverySort ?? 'global-popularity'}
					{discoveryGroups}
					{discoveryTags}
					{discoverySorts}
					{libraryLoading}
					{libraryError}
					{hasActiveDiscoveryQuery}
					{works}
					selectedWorkId={selectedWork?.work_id}
					{worksPrevCursor}
					{worksNextCursor}
					shelvesStatusLabel={readerLoadingStatus('Loading shelves', 'shelves')}
					shelvesElapsedLabel={readerLoadingElapsed('shelves')}
					loadingWorksStatusLabel={readerLoadingStatus('Loading works', 'library')}
					loadingWorksElapsedLabel={readerLoadingElapsed('library')}
					updatingWorksStatusLabel={readerLoadingStatus('Updating works', 'library')}
					updatingWorksElapsedLabel={readerLoadingElapsed('library')}
					{authorAgentKind}
					{authorHistoricity}
					{authorAgentKinds}
					{authorHistoricityStatuses}
					{authorsLoading}
					{authorsError}
					{authors}
					selectedAuthorId={selectedAuthor?.author_id}
					{authorSections}
					{activeAuthorSection}
					{indexSummaryLabel}
					{authorsPrevCursor}
					{authorsNextCursor}
					searchingAuthorsStatusLabel={readerLoadingStatus('Searching authors', 'authors')}
					searchingAuthorsElapsedLabel={readerLoadingElapsed('authors')}
					updatingAuthorsStatusLabel={readerLoadingStatus('Updating authors', 'authors')}
					updatingAuthorsElapsedLabel={readerLoadingElapsed('authors')}
					loadingAuthorWorksStatusLabel={readerLoadingStatus('Loading author works', 'library')}
					loadingAuthorWorksElapsedLabel={readerLoadingElapsed('library')}
					{facetValueLabel}
					{workListLabel}
					{workListDiscriminator}
					{workMetaLine}
					{shelfIsActive}
					{shelfMetaLabel}
					romanHintForSection={(sectionKey) => authorSectionRomanHint(language, sectionKey)}
					onSelectView={selectReaderView}
					onTextQueryInput={(value) => {
						textQuery = value;
					}}
					onTextSearchModeChange={(mode) => {
						textSearchMode = mode;
						applyTextSearchMode();
					}}
					onSubmitTextSearch={submitTextSearch}
					onClearTextSearch={clearTextSearch}
					onRetryTextSearch={retryTextSearch}
					onOpenTextResult={openSearchResult}
					onOpenTextAuthor={openSearchResultAuthor}
					onOpenPreviousText={(cursor) => void searchReaderText(cursor, 'push')}
					onOpenNextText={(cursor) => void searchReaderText(cursor, 'push')}
					onSelectShelf={selectDiscoveryShelf}
					onWorkQueryInput={(value) => {
						workQuery = value;
					}}
					onDiscoveryGroupChange={(value) => {
						discoveryGroup = value;
					}}
					onDiscoveryTagChange={(value) => {
						discoveryTag = value;
					}}
					onDiscoverySortChange={(value) => {
						discoverySort = value;
					}}
					onApplyDiscoveryFilters={applyDiscoveryFilters}
					onSubmitDiscoverySearch={submitDiscoverySearch}
					onClearDiscoveryFilters={clearDiscoveryFilters}
					onRetryLibrary={retryLibrarySearch}
					onSummaryElement={(element) => {
						readerResultsRegion = element;
					}}
					onOpenWork={(work) => void openWork(work)}
					onFilterByAuthor={filterDiscoveryByAuthor}
					onClearAuthorFilter={clearDiscoveryAuthor}
					onOpenPreviousWorks={(cursor) => void searchWorks(cursor, undefined, 'push')}
					onOpenNextWorks={(cursor) => void searchWorks(cursor, undefined, 'push')}
					onAuthorAgentKindChange={(value) => {
						authorAgentKind = value;
					}}
					onAuthorHistoricityChange={(value) => {
						authorHistoricity = value;
					}}
					onApplyAuthorFilters={applyAuthorFilters}
					onSubmitAuthorSearch={submitAuthorSearch}
					onJumpToAuthorSection={jumpToAuthorSection}
					onClearAuthorSection={clearAuthorSection}
					onRetryAuthors={retryAuthorSearch}
					onOpenAuthor={openAuthor}
					onOpenAuthorWork={(work) => void openWork(work)}
					onOpenPreviousAuthors={(cursor) => void loadAuthors(cursor, 'push')}
					onOpenNextAuthors={(cursor) => void loadAuthors(cursor, 'push')}
				/>
			{/if}
		</article>

		{#snippet sidebar()}
			<ReaderContextSidebar
				{structure}
				{structureLoading}
				{structureError}
				structureStatusLabel={readerLoadingStatus(uiCopy.readerStructure.loading, 'structure')}
				structureElapsedLabel={readerLoadingElapsed('structure')}
				hasSelectedWork={Boolean(selectedWork)}
				{contents}
				{contentsLoading}
				{contentsError}
				contentsStatusLabel={readerLoadingStatus('Loading contents', 'contents')}
				contentsElapsedLabel={readerLoadingElapsed('contents')}
				{selectedWord}
				{selectedWordRomanization}
				{selectedWordHref}
				{selectedWordBriefingOutput}
				{selectedWordBriefingBadge}
				{selectedWordBriefingCanGenerate}
				{selectedWordBriefingLoading}
				{selectedWordBriefingGenerating}
				{selectedWordBriefingError}
				{segmentIsActive}
				onRetryStructure={() => selectedWork && void loadStructure(readerWorkRef(selectedWork))}
				onRetryContents={retryContentsLoad}
				onOpenDivision={(workId, citation) => showSegment(workId, citation, 'push')}
				onOpenSegment={showSelectedWorkSegment}
				onGenerateBriefing={() => void fetchEncounterBriefing(selectedWord, true)}
			/>
		{/snippet}
	</ReaderShell>

	<ReaderApparatusTabs
		showing={Boolean(selectedWork || selectedSegment || selectedWord)}
		onOpenPanel={(panel) => {
			activeApparatusPanel = panel;
		}}
	/>

	<ReaderApparatusSheet
		activePanel={activeApparatusPanel}
		{structure}
		{selectedWord}
		{selectedWordRomanization}
		{selectedWordHref}
		{selectedWordBriefingOutput}
		{selectedWordBriefingBadge}
		{selectedWordBriefingCanGenerate}
		{selectedWordBriefingLoading}
		{selectedWordBriefingGenerating}
		{selectedWordBriefingError}
		{currentDivisionTrail}
		{currentDivisionNode}
		{selectedSegment}
		selectedWorkTitle={selectedWorkTitleLabel()}
		selectedWorkAddress={selectedWork?.canonical_address || ''}
		onClose={() => (activeApparatusPanel = '')}
		onOpenDivision={(workId, citation) => showSegment(workId, citation, 'push')}
		onGenerateBriefing={() => selectedWord && void fetchEncounterBriefing(selectedWord, true)}
	/>
</main>
