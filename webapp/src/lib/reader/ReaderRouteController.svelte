<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount, tick } from 'svelte';
	import {
		fetchReaderApi,
		fetchReaderEncounterBriefing,
		readerAuthorSectionsUrl,
		readerCatalogsUrl,
		readerWordContextUrl
	} from '$lib/reader/reader-api';
	import ReaderRouteControllerView from './ReaderRouteControllerView.svelte';
	import type { ReaderIndexView } from '$lib/reader/index-storage';
import { createReaderLoadingTimers, type ReaderLoadingKey } from '$lib/reader/loading-timers';
	import {
		buildReaderIndexStatsTargets,
		findReaderIndexStatsInList,
		readerIndexStatsFromSections,
		upsertReaderIndexStatsList
	} from '$lib/reader/index-stats';
	import {
		readerFacetValueLabel,
		readerFacetValues as facetValues,
		readerSelectedWorkAuthorLabel,
		readerSelectedWorkContributorLine,
		readerSelectedWorkDiscriminator,
		readerSelectedWorkTitleLabel,
		readerSyntheticAuthorFromRoute,
		readerSyntheticAuthorFromWork
	} from '$lib/reader/page-authors';
	import {
		readerAuthorSectionRomanHint as authorSectionRomanHint,
		readerCitationRangeLabel,
		readerDiscoverySummaryLabel,
		readerDiscoveryTitleLabel,
		readerShelfMetaLabel as shelfMetaLabel,
		readerTextSearchCandidateLabel as textSearchCandidateLabel,
		readerVisibleTextSearchCandidates as visibleTextSearchCandidates,
		readerWorkMetaLine as workMetaLine
	} from '$lib/reader/page-formatting';
	import {
		readerCurrentReadingWorkRef,
		readerSearchResultWorkRef,
		readerSegmentIsActive,
		readerShelfIsActive
	} from '$lib/reader/page-navigation';
	import {
		encounterBriefingCanGenerate,
		encounterBriefingIsGenerated,
		encounterBriefingModelLabel,
		encounterBriefingOutput,
		type EncounterBriefingFlow
	} from '$lib/encounter-briefing';
	import {
		buildReaderTokenParts,
		cleanReaderToken,
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
		type ReaderCatalog,
		type ReaderCatalogsResponse,
		type ReaderDiscoveryShelf,
		type ReaderFacet,
		type ReaderIndexStats,
		type ReaderNavigationTarget,
		type ReaderRouteState,
		type ReaderSearchMode,
		type ReaderSearchQueryCandidate,
		type ReaderSearchResult,
		type ReaderSegment,
		type ReaderTokenPart,
		type ReaderWork,
		type ReaderWorkDossierResponse,
		type ReaderWordContextResponse,
		type ReaderStructureNode
	} from '$lib/reader';
import { defaultReaderAddressForLanguage, formatReaderAddress } from '$lib/reader/page-routing';
import { createReaderRouteContentLoaders } from '$lib/reader/reader-route-content-loaders';
import { createReaderRouteDiscoveryLoaders } from '$lib/reader/reader-route-discovery-loaders';
import {
	createReaderRouteWorkspaceState,
	readerRouteWorkspaceBinding
} from '$lib/reader/reader-route-workspace-state';
import { createReaderRouteWorkspace, type ReaderHistoryMode } from '$lib/reader/reader-route-workspace';
	import { romanizeSearchTerm } from '$lib/search-romanization';
	import { languageModes, type LanguageMode } from '$lib/search-data';
	import { uiCopy } from '$lib/ui-copy';

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
	let selectedWordContext = $state<ReaderWordContextResponse | null>(null);
	let selectedWordContextLoading = $state(false);
	let selectedWordContextError = $state('');
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
	let activeCollection = $state<'all' | 'work' | 'author'>('all');
	let pageRadius = $state(2);
	let pageLimit = $state(14);
	let pageTextBudget = $state(4_500);
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
	let selectedWordContextController: AbortController | null = null;

	let selectedWordRomanization = $derived(
		selectedWord ? romanizeSearchTerm(language, selectedWord) : null
	);
	let selectedWordHref = $derived(
		selectedWord
			? `/q?language=${language}&q=${encodeURIComponent(selectedWord)}&load=yes&backend=cli`
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
	let selectedWorkLabels = $derived({
		title: readerSelectedWorkTitleLabel(selectedWork, works),
		discriminator: readerSelectedWorkDiscriminator(selectedWork, works),
		contributorLine: readerSelectedWorkContributorLine(selectedWork),
		author: readerSelectedWorkAuthorLabel(selectedWork)
	});
	let hasActiveDiscoveryQuery = $derived(
		Boolean(
			workQuery.trim() || discoveryGroup || discoveryTag || discoveryAuthorId || worksCursorParam
		)
	);

	

	const readerRouteWorkspaceState = createReaderRouteWorkspaceState({
		theme: readerRouteWorkspaceBinding(() => theme, (value) => {
			theme = value;
		}),
		language: readerRouteWorkspaceBinding(() => language, (value) => {
			language = value;
		}),
		catalogs: readerRouteWorkspaceBinding(() => catalogs, (value) => {
			catalogs = value;
		}),
		catalogDefaults: readerRouteWorkspaceBinding(() => catalogDefaults, (value) => {
			catalogDefaults = value;
		}),
		catalogId: readerRouteWorkspaceBinding(() => catalogId, (value) => {
			catalogId = value;
		}),
		catalogError: readerRouteWorkspaceBinding(() => catalogError, (value) => {
			catalogError = value;
		}),
		workQuery: readerRouteWorkspaceBinding(() => workQuery, (value) => {
			workQuery = value;
		}),
		textQuery: readerRouteWorkspaceBinding(() => textQuery, (value) => {
			textQuery = value;
		}),
		textSearchMode: readerRouteWorkspaceBinding(() => textSearchMode, (value) => {
			textSearchMode = value;
		}),
		textSearchResults: readerRouteWorkspaceBinding(() => textSearchResults, (value) => {
			textSearchResults = value;
		}),
		textSearchQueryCandidates: readerRouteWorkspaceBinding(
			() => textSearchQueryCandidates,
			(value) => {
				textSearchQueryCandidates = value;
			}
		),
		readerView: readerRouteWorkspaceBinding(() => readerView, (value) => {
			readerView = value;
		}),
		facets: readerRouteWorkspaceBinding(() => facets, (value) => {
			facets = value;
		}),
		discoveryShelves: readerRouteWorkspaceBinding(() => discoveryShelves, (value) => {
			discoveryShelves = value;
		}),
		discoveryGroup: readerRouteWorkspaceBinding(() => discoveryGroup, (value) => {
			discoveryGroup = value;
		}),
		discoveryTag: readerRouteWorkspaceBinding(() => discoveryTag, (value) => {
			discoveryTag = value;
		}),
		discoveryAuthorId: readerRouteWorkspaceBinding(() => discoveryAuthorId, (value) => {
			discoveryAuthorId = value;
		}),
		discoveryAuthorLabel: readerRouteWorkspaceBinding(() => discoveryAuthorLabel, (value) => {
			discoveryAuthorLabel = value;
		}),
		discoverySort: readerRouteWorkspaceBinding(() => discoverySort, (value) => {
			discoverySort = value;
		}),
		authorAgentKind: readerRouteWorkspaceBinding(() => authorAgentKind, (value) => {
			authorAgentKind = value;
		}),
		authorHistoricity: readerRouteWorkspaceBinding(() => authorHistoricity, (value) => {
			authorHistoricity = value;
		}),
		works: readerRouteWorkspaceBinding(() => works, (value) => {
			works = value;
		}),
		authorSections: readerRouteWorkspaceBinding(() => authorSections, (value) => {
			authorSections = value;
		}),
		readerIndexStats: readerRouteWorkspaceBinding(() => readerIndexStats, (value) => {
			readerIndexStats = value;
		}),
		authors: readerRouteWorkspaceBinding(() => authors, (value) => {
			authors = value;
		}),
		selectedAuthor: readerRouteWorkspaceBinding(() => selectedAuthor, (value) => {
			selectedAuthor = value;
		}),
		selectedWork: readerRouteWorkspaceBinding(() => selectedWork, (value) => {
			selectedWork = value;
		}),
		contents: readerRouteWorkspaceBinding(() => contents, (value) => {
			contents = value;
		}),
		structure: readerRouteWorkspaceBinding(() => structure, (value) => {
			structure = value;
		}),
		workDossier: readerRouteWorkspaceBinding(() => workDossier, (value) => {
			workDossier = value;
		}),
		selectedSegment: readerRouteWorkspaceBinding(() => selectedSegment, (value) => {
			selectedSegment = value;
		}),
		pageSegments: readerRouteWorkspaceBinding(() => pageSegments, (value) => {
			pageSegments = value;
		}),
		navigation: readerRouteWorkspaceBinding(() => navigation, (value) => {
			navigation = value;
		}),
		addressInput: readerRouteWorkspaceBinding(() => addressInput, (value) => {
			addressInput = value;
		}),
		showAddressLookup: readerRouteWorkspaceBinding(() => showAddressLookup, (value) => {
			showAddressLookup = value;
		}),
		selectedWord: readerRouteWorkspaceBinding(() => selectedWord, (value) => {
			selectedWord = value;
		}),
		selectedWordBriefing: readerRouteWorkspaceBinding(() => selectedWordBriefing, (value) => {
			selectedWordBriefing = value;
		}),
		selectedWordBriefingLoading: readerRouteWorkspaceBinding(
			() => selectedWordBriefingLoading,
			(value) => {
				selectedWordBriefingLoading = value;
			}
		),
		selectedWordBriefingGenerating: readerRouteWorkspaceBinding(
			() => selectedWordBriefingGenerating,
			(value) => {
				selectedWordBriefingGenerating = value;
			}
		),
		selectedWordBriefingError: readerRouteWorkspaceBinding(() => selectedWordBriefingError, (value) => {
			selectedWordBriefingError = value;
		}),
		selectedWordContext: readerRouteWorkspaceBinding(() => selectedWordContext, (value) => {
			selectedWordContext = value;
		}),
		selectedWordContextLoading: readerRouteWorkspaceBinding(
			() => selectedWordContextLoading,
			(value) => {
				selectedWordContextLoading = value;
			}
		),
		selectedWordContextError: readerRouteWorkspaceBinding(() => selectedWordContextError, (value) => {
			selectedWordContextError = value;
		}),
		activeApparatusPanel: readerRouteWorkspaceBinding(() => activeApparatusPanel, (value) => {
			activeApparatusPanel = value;
		}),
		shelvesLoading: readerRouteWorkspaceBinding(() => shelvesLoading, (value) => {
			shelvesLoading = value;
		}),
		libraryLoading: readerRouteWorkspaceBinding(() => libraryLoading, (value) => {
			libraryLoading = value;
		}),
		contentsLoading: readerRouteWorkspaceBinding(() => contentsLoading, (value) => {
			contentsLoading = value;
		}),
		structureLoading: readerRouteWorkspaceBinding(() => structureLoading, (value) => {
			structureLoading = value;
		}),
		dossierLoading: readerRouteWorkspaceBinding(() => dossierLoading, (value) => {
			dossierLoading = value;
		}),
		segmentLoading: readerRouteWorkspaceBinding(() => segmentLoading, (value) => {
			segmentLoading = value;
		}),
		libraryError: readerRouteWorkspaceBinding(() => libraryError, (value) => {
			libraryError = value;
		}),
		authorsError: readerRouteWorkspaceBinding(() => authorsError, (value) => {
			authorsError = value;
		}),
		textSearchError: readerRouteWorkspaceBinding(() => textSearchError, (value) => {
			textSearchError = value;
		}),
		contentsError: readerRouteWorkspaceBinding(() => contentsError, (value) => {
			contentsError = value;
		}),
		structureError: readerRouteWorkspaceBinding(() => structureError, (value) => {
			structureError = value;
		}),
		dossierError: readerRouteWorkspaceBinding(() => dossierError, (value) => {
			dossierError = value;
		}),
		segmentError: readerRouteWorkspaceBinding(() => segmentError, (value) => {
			segmentError = value;
		}),
		totalFiltered: readerRouteWorkspaceBinding(() => totalFiltered, (value) => {
			totalFiltered = value;
		}),
		worksNextCursor: readerRouteWorkspaceBinding(() => worksNextCursor, (value) => {
			worksNextCursor = value;
		}),
		worksPrevCursor: readerRouteWorkspaceBinding(() => worksPrevCursor, (value) => {
			worksPrevCursor = value;
		}),
		authorsNextCursor: readerRouteWorkspaceBinding(() => authorsNextCursor, (value) => {
			authorsNextCursor = value;
		}),
		authorsPrevCursor: readerRouteWorkspaceBinding(() => authorsPrevCursor, (value) => {
			authorsPrevCursor = value;
		}),
		textSearchNextCursor: readerRouteWorkspaceBinding(() => textSearchNextCursor, (value) => {
			textSearchNextCursor = value;
		}),
		textSearchPrevCursor: readerRouteWorkspaceBinding(() => textSearchPrevCursor, (value) => {
			textSearchPrevCursor = value;
		}),
		activeCollection: readerRouteWorkspaceBinding(() => activeCollection, (value) => {
			activeCollection = value;
		}),
		pageRadius: readerRouteWorkspaceBinding(() => pageRadius, (value) => {
			pageRadius = value;
		}),
		pageLimit: readerRouteWorkspaceBinding(() => pageLimit, (value) => {
			pageLimit = value;
		}),
		pageTextBudget: readerRouteWorkspaceBinding(() => pageTextBudget, (value) => {
			pageTextBudget = value;
		}),
		pageNextCursor: readerRouteWorkspaceBinding(() => pageNextCursor, (value) => {
			pageNextCursor = value;
		}),
		pagePrevCursor: readerRouteWorkspaceBinding(() => pagePrevCursor, (value) => {
			pagePrevCursor = value;
		}),
		activeAuthorSection: readerRouteWorkspaceBinding(() => activeAuthorSection, (value) => {
			activeAuthorSection = value;
		}),
		routeAuthorId: readerRouteWorkspaceBinding(() => routeAuthorId, (value) => {
			routeAuthorId = value;
		}),
		routeAuthorName: readerRouteWorkspaceBinding(() => routeAuthorName, (value) => {
			routeAuthorName = value;
		}),
		authorsCursorParam: readerRouteWorkspaceBinding(() => authorsCursorParam, (value) => {
			authorsCursorParam = value;
		}),
		textSearchCursorParam: readerRouteWorkspaceBinding(() => textSearchCursorParam, (value) => {
			textSearchCursorParam = value;
		}),
		worksCursorParam: readerRouteWorkspaceBinding(() => worksCursorParam, (value) => {
			worksCursorParam = value;
		}),
		contentsCursorParam: readerRouteWorkspaceBinding(() => contentsCursorParam, (value) => {
			contentsCursorParam = value;
		}),
		pageCursorParam: readerRouteWorkspaceBinding(() => pageCursorParam, (value) => {
			pageCursorParam = value;
		}),
		showTransliteration: readerRouteWorkspaceBinding(() => showTransliteration, (value) => {
			showTransliteration = value;
		}),
		shelvesLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => shelvesLoadingElapsedSeconds,
			(value) => {
				shelvesLoadingElapsedSeconds = value;
			}
		),
		libraryLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => libraryLoadingElapsedSeconds,
			(value) => {
				libraryLoadingElapsedSeconds = value;
			}
		),
		authorsLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => authorsLoadingElapsedSeconds,
			(value) => {
				authorsLoadingElapsedSeconds = value;
			}
		),
		textSearchElapsedSeconds: readerRouteWorkspaceBinding(
			() => textSearchElapsedSeconds,
			(value) => {
				textSearchElapsedSeconds = value;
			}
		),
		contentsLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => contentsLoadingElapsedSeconds,
			(value) => {
				contentsLoadingElapsedSeconds = value;
			}
		),
		structureLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => structureLoadingElapsedSeconds,
			(value) => {
				structureLoadingElapsedSeconds = value;
			}
		),
		dossierLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => dossierLoadingElapsedSeconds,
			(value) => {
				dossierLoadingElapsedSeconds = value;
			}
		),
		segmentLoadingElapsedSeconds: readerRouteWorkspaceBinding(
			() => segmentLoadingElapsedSeconds,
			(value) => {
				segmentLoadingElapsedSeconds = value;
			}
		)
	});

	const readerRouteWorkspace = createReaderRouteWorkspace(readerRouteWorkspaceState, {
		loadCatalogs,
		loadChosenReaderView,
		applyReaderRouteContent: applyReaderRouteContentInternal,
		loadAllReaderIndexStats,
		onHydrateSelectedWord: (word) => {
			void fetchEncounterBriefing(word);
		}
	});
	const {
		initializeReaderFromUrl,
		rehydrateReaderFromUrl,
		setTheme,
		hydrateFromUrl,
		applyReaderRouteState,
		applyReaderRouteContent,
		updateReaderUrl,
		currentReaderRouteState,
		restoreReaderIndexState,
		saveReaderIndexState
	} = readerRouteWorkspace;

	function syncReaderAddressUrl(
		work: string,
		segment: string,
		historyMode: ReaderHistoryMode = 'replace'
	) {
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

	const readerRouteContentLoaders = createReaderRouteContentLoaders(readerRouteWorkspaceState, {
		updateReaderUrl,
		readerLoadingTimers,
		syncAddressUrl: syncReaderAddressUrl,
		getPageLimit: () => pageLimit,
		getPageTextBudget: () => pageTextBudget,
		getPageRadius: () => pageRadius
	});
	const {
		openWork,
		loadStructure,
		loadWorkDossier,
		loadContentsPage,
		showSegment,
		openAddress,
		showAddress,
		resolveAddress,
		ensureSelectedWork,
		loadPageWindow
	} = readerRouteContentLoaders;

	const readerRouteDiscoveryLoaders = createReaderRouteDiscoveryLoaders(readerRouteWorkspaceState, {
		readerLoadingTimers,
		updateReaderUrl,
		saveReaderIndexState,
		upsertReaderIndexStats,
		scrollReaderResultsIntoView: scrollReaderResultsIntoView
	});
	const {
		loadFacets,
		loadShelves,
		loadAuthorSections,
		loadAuthors,
		findAuthorById,
		findAuthorByQuery,
		resolveRouteAuthor,
		searchWorks,
		searchReaderText
	} = readerRouteDiscoveryLoaders;

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

	async function loadChosenReaderView(historyMode: ReaderHistoryMode = 'replace') {
		if (readerView === 'shelves' && !discoveryShelves.length) await loadShelves();
		if (readerView === 'authors' && (!authorSections.length || !authors.length)) {
			await loadAuthorSections(historyMode);
		}
		if (readerView === 'search' && textQuery.trim()) {
			await searchReaderText(textSearchCursorParam, historyMode);
		}
	}

	async function applyReaderRouteContentInternal(
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
			const { response, data } = await fetchReaderApi<ReaderCatalogsResponse>(readerCatalogsUrl());
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
			const sections = await loadReaderIndexSections(targetLanguage, targetCatalogId);
			upsertReaderIndexStats(readerIndexStatsFromSections(targetLanguage, targetCatalogId, sections));
		} catch {
			// The active author list still reports its own error; stats fall back to a neutral label.
		} finally {
			readerIndexStatsInFlight.delete(key);
		}
	}

	async function loadReaderIndexSections(targetLanguage: LanguageMode, targetCatalogId: string) {
		const { response, data } = await fetchReaderApi<ReaderAuthorSectionsResponse>(
			readerAuthorSectionsUrl({ catalogId: targetCatalogId, language: targetLanguage })
		);
		if (!response.ok) throw new Error(data.error || 'Reader author sections failed.');
		return data.items;
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
		selectedWordContextController?.abort();
		selectedWordContextController = null;
		selectedWordContext = null;
		selectedWordContextError = '';
		selectedWordContextLoading = false;
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
			const { response, data } = await fetchReaderEncounterBriefing({
				language,
				token,
				generate,
				signal: controller.signal
			});
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

	async function fetchWordContext(word: string) {
		const token = cleanReaderToken(word);
		if (!token || !catalogId) return;
		selectedWordContextController?.abort();
		const controller = new AbortController();
		selectedWordContextController = controller;
		selectedWordContextLoading = true;
		selectedWordContextError = '';
		const work =
			selectedSegment?.work_id ||
			(selectedWork ? readerWorkRef(selectedWork) : readerCurrentReadingWorkRef(selectedWork, selectedSegment));
		const segment = selectedSegment?.citation_path ?? null;
		try {
			const { response, data } = await fetchReaderApi<ReaderWordContextResponse>(
				readerWordContextUrl({
					catalogId,
					language,
					query: token,
					work,
					segment
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader word context failed.');
			if (selectedWord === token) selectedWordContext = data;
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			if (selectedWord === token) {
				selectedWordContextError =
					error instanceof Error ? error.message : 'Reader word context failed.';
			}
		} finally {
			if (selectedWordContextController === controller) {
				selectedWordContextController = null;
				selectedWordContextLoading = false;
			}
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
		selectedWordContextController?.abort();
		selectedWordContextController = null;
		selectedWordContext = null;
		selectedWordContextError = '';
		selectedWordContextLoading = false;
		contentsCursorParam = null;
		pageCursorParam = null;
		showAddressLookup = false;
		addressInput = defaultReaderAddressForLanguage(language);
		updateReaderUrl({}, 'push');
		if (readerView === 'shelves' && hasActiveDiscoveryQuery && !works.length)
			void searchWorks(null, routeAuthorId || undefined, 'replace');
	}

	function selectToken(text: string) {
		const token = cleanReaderToken(text);
		if (!token) return;
		selectedWord = token;
		selectedWordBriefing = null;
		selectedWordBriefingError = '';
		selectedWordBriefingGenerating = false;
		selectedWordContext = null;
		selectedWordContextError = '';
		updateReaderUrl({ selectedWord: token }, 'replace');
		void fetchWordContext(token);
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

	function openSelectedWorkAuthor() {
		if (!selectedWork) return;
		filterDiscoveryByAuthor(selectedWork);
	}

	const readerRouteControllerViewProps = $derived({
		theme,
		language,
		onOpenWindowKeydown: handleReaderKeydown,
		indexSummaryLabel,
		catalogError,
		showAddressLookup,
		addressInput,
		segmentLoading,
		catalogReady: Boolean(catalogId),
		onThemeSelect: setTheme,
		onLanguageSelect: selectLanguage,
		onAddressInput: (value: string) => {
			addressInput = value;
		},
		onOpenAddress: () => {
			void openAddress('push');
		},
		onCloseLookup: closeAddressLookup,
		onShowLookup: () => {
			showAddressLookup = true;
		},
		selectedWork,
		selectedWorkLabels,
		topSection: workDossier,
		dossierLoading,
		dossierLoadingLabel: readerLoadingStatus(uiCopy.workDossier.loading, 'dossier'),
		dossierError,
		currentDivisionNode,
		onOpenWorkDivision: showSegment,
		onRetrySelectedWork: () => selectedWork && void loadWorkDossier(readerWorkRef(selectedWork)),
		headerLanguageLabel: readerLanguageLabel(language),
		canOpenWorkAuthor: Boolean(
			selectedWork?.canonical_author_id || selectedWork?.source_author_id || selectedWork?.author_id
		),
		onOpenWorkAuthor: openSelectedWorkAuthor,
		onToggleTransliteration: toggleTransliteration,
		onShowLibrary: showLibrary,
		selectedSegment,
		segmentError,
		pagePrevCursor,
		pageNextCursor,
		contentsLoading,
		pageRangeLabel,
		currentDivisionTrail,
		pageSegments,
		selectedWord,
		showTransliteration,
		openingStatusLabel: readerLoadingStatus('Opening passage', 'segment'),
		openingElapsedLabel: readerLoadingElapsedSeconds('segment'),
		updatingStatusLabel: readerLoadingStatus('Updating passage', 'segment'),
		updatingElapsedLabel: readerLoadingElapsedSeconds('segment'),
		segmentParts,
		onRetrySegment: retrySegmentLoad,
		onOpenPage: showPageCursor,
		onOpenDivisionFromPassage: showSegment,
		onOpenSegment: showSelectedWorkSegment,
		onSelectToken: selectToken,
		activeDiscoveryTitle,
		readerView,
		textQuery,
		textSearchMode,
		textSearchLoading,
		textSearchError,
		textSearchResults,
		textSearchQueryCandidates: visibleTextSearchCandidates(textSearchQueryCandidates),
		textSearchCandidateLabel,
		textSearchPrevCursor,
		textSearchNextCursor,
		textSearchingStatusLabel: readerLoadingStatus('Searching texts', 'textSearch'),
		textSearchingElapsedLabel: readerLoadingElapsedSeconds('textSearch'),
		textUpdatingStatusLabel: readerLoadingStatus('Updating text matches', 'textSearch'),
		textUpdatingElapsedLabel: readerLoadingElapsedSeconds('textSearch'),
		discoveryShelves,
		shelvesLoading,
		workQuery,
		discoveryGroup,
		discoveryTag,
		discoveryAuthorId,
		discoveryAuthorLabel,
		discoverySort: discoverySort ?? 'global-popularity',
		discoveryGroups,
		discoveryTags,
		discoverySorts,
		libraryLoading,
		libraryError,
		hasActiveDiscoveryQuery,
		works,
		selectedWorkId: selectedWork?.work_id,
		worksPrevCursor,
		worksNextCursor,
		shelvesStatusLabel: readerLoadingStatus('Loading shelves', 'shelves'),
		shelvesElapsedLabel: readerLoadingElapsedSeconds('shelves'),
		loadingWorksStatusLabel: readerLoadingStatus('Loading works', 'library'),
		loadingWorksElapsedLabel: readerLoadingElapsedSeconds('library'),
		updatingWorksStatusLabel: readerLoadingStatus('Updating works', 'library'),
		updatingWorksElapsedLabel: readerLoadingElapsedSeconds('library'),
		authorAgentKind,
		authorHistoricity,
		authorAgentKinds,
		authorHistoricityStatuses,
		authorsLoading,
		authorsError,
		authors,
		selectedAuthorId: selectedAuthor?.author_id,
		authorSections,
		activeAuthorSection,
		authorsPrevCursor,
		authorsNextCursor,
		searchingAuthorsStatusLabel: readerLoadingStatus('Searching authors', 'authors'),
		searchingAuthorsElapsedLabel: readerLoadingElapsedSeconds('authors'),
		updatingAuthorsStatusLabel: readerLoadingStatus('Updating authors', 'authors'),
		updatingAuthorsElapsedLabel: readerLoadingElapsedSeconds('authors'),
		loadingAuthorWorksStatusLabel: readerLoadingStatus('Loading author works', 'library'),
		loadingAuthorWorksElapsedLabel: readerLoadingElapsedSeconds('library'),
		facetValueLabel: readerFacetValueLabel,
		discoveryWorkListLabel: (work: ReaderWork) => readerWorkListLabel(work, works),
		discoveryWorkListDiscriminator: (work: ReaderWork) => readerWorkListDiscriminator(work, works),
		workMetaLine,
		shelfIsActive,
		shelfMetaLabel,
		onSelectView: selectReaderView,
		romanHintForSection: (sectionKey: string) => authorSectionRomanHint(language, sectionKey),
		onTextQueryInput: (value: string) => {
			textQuery = value;
		},
		onTextSearchModeChange: (mode: ReaderSearchMode) => {
			textSearchMode = mode;
			applyTextSearchMode();
		},
		onSubmitTextSearch: submitTextSearch,
		onClearTextSearch: clearTextSearch,
		onRetryTextSearch: retryTextSearch,
		onOpenTextResult: openSearchResult,
		onOpenTextAuthor: openSearchResultAuthor,
		onOpenPreviousText: (cursor: string | null) => void searchReaderText(cursor, 'push'),
		onOpenNextText: (cursor: string | null) => void searchReaderText(cursor, 'push'),
		onSelectShelf: selectDiscoveryShelf,
		onWorkQueryInput: (value: string) => {
			workQuery = value;
		},
		onDiscoveryGroupChange: (value: string) => {
			discoveryGroup = value;
		},
		onDiscoveryTagChange: (value: string) => {
			discoveryTag = value;
		},
		onDiscoverySortChange: (value: ReaderRouteState['discoverySort'] | undefined) => {
			discoverySort = value;
		},
		onApplyDiscoveryFilters: applyDiscoveryFilters,
		onSubmitDiscoverySearch: submitDiscoverySearch,
		onClearDiscoveryFilters: clearDiscoveryFilters,
		onRetryLibrary: retryLibrarySearch,
		onSummaryElement: (element: HTMLElement | null) => {
			readerResultsRegion = element;
		},
		onOpenWork: (work: ReaderWork) => {
			void openWork(work);
		},
		onFilterByAuthor: filterDiscoveryByAuthor,
		onClearDiscoveryAuthor: clearDiscoveryAuthor,
		onOpenPreviousWorks: (cursor: string | null) => void searchWorks(cursor, undefined, 'push'),
		onOpenNextWorks: (cursor: string | null) => void searchWorks(cursor, undefined, 'push'),
		onAuthorAgentKindChange: (value: string) => {
			authorAgentKind = value;
		},
		onAuthorHistoricityChange: (value: string) => {
			authorHistoricity = value;
		},
		onApplyAuthorFilters: applyAuthorFilters,
		onSubmitAuthorSearch: submitAuthorSearch,
		onJumpToAuthorSection: jumpToAuthorSection,
		onClearAuthorSection: clearAuthorSection,
		onRetryAuthors: retryAuthorSearch,
		onOpenAuthor: openAuthor,
		onOpenAuthorWork: (work: ReaderWork) => void openWork(work),
		onOpenPreviousAuthors: (cursor: string | null) => void loadAuthors(cursor, 'push'),
		onOpenNextAuthors: (cursor: string | null) => void loadAuthors(cursor, 'push'),
		sidebarStructure: structure,
		sidebarStructureLoading: structureLoading,
		sidebarStructureError: structureError,
		sidebarStructureStatusLabel: readerLoadingStatus(uiCopy.readerStructure.loading, 'structure'),
		sidebarStructureElapsedLabel: readerLoadingElapsedSeconds('structure'),
		sidebarContents: contents,
		sidebarContentsLoading: contentsLoading,
		sidebarContentsError: contentsError,
		sidebarContentsStatusLabel: readerLoadingStatus('Loading contents', 'contents'),
		sidebarContentsElapsedLabel: readerLoadingElapsedSeconds('contents'),
		selectedWordRomanization,
		selectedWordHref,
		selectedWordBriefingBadge,
		selectedWordBriefingCanGenerate,
		selectedWordBriefingLoading,
		selectedWordBriefingGenerating,
		selectedWordBriefingError,
		selectedWordContext,
		selectedWordContextLoading,
		selectedWordContextError,
		segmentIsActive,
		onRetryStructure: () => selectedWork && void loadStructure(readerWorkRef(selectedWork)),
		onRetryContents: retryContentsLoad,
		onOpenDivision: showSegment,
		onGenerateBriefing: () => selectedWord && void fetchEncounterBriefing(selectedWord, true),
		activeApparatusPanel,
		onCloseApparatus: () => {
			activeApparatusPanel = '';
		},
		onOpenDivisionFromSheet: showSegment,
		onGenerateBriefingFromSheet: () => selectedWord && void fetchEncounterBriefing(selectedWord, true),
		selectedWordBriefingOutput,
		onOpenPanel: (panel: '' | 'structure' | 'word' | 'oracle' | 'evidence') => {
			activeApparatusPanel = panel;
		}
	});

	</script>

<ReaderRouteControllerView {...readerRouteControllerViewProps} />
