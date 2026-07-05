<script lang="ts">
	import { browser } from '$app/environment';
	import { pushState, replaceState } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import {
		createDeskLoadingTimers,
		deskActivityItems,
		syncDeskActivityTimer,
		type DeskActivityKey
	} from '$lib/desk/desk-activity';
	import { createDeskMotdController } from '$lib/desk/desk-motd-controller';
	import { createDeskParadigmController } from '$lib/desk/desk-paradigm-controller';
	import { createDeskTranslationArrivalController } from '$lib/desk/desk-translation-arrival-controller';
	import {
		branchToggleLabel as branchToggleLabelForState,
		componentAwaitsReaderTranslation as componentAwaitsReaderTranslationForState,
		componentCanSwitchTextLayer,
		componentHasTranslationToggle,
		componentHeadwordDisplay as componentHeadwordDisplayForLanguage,
		componentLayerIsSource,
		componentLookupLine,
		componentMeaningCanToggle,
		componentMeaningKey,
		componentMeaningSegments,
		componentMeaningSourceLabel,
		componentMeaningToggleLabel,
		componentPrimaryTool,
		componentSourceLayerLabel,
		componentToolIds,
		componentTranslationModel,
		countLabel,
		dedupeStrings,
		groupAwaitsReaderTranslation as groupAwaitsReaderTranslationForState,
		groupBuckets,
		groupCanSwitchTextLayer,
		groupHasReaderTranslation,
		groupHasTranslationToggle,
		groupHeadwordDisplay as groupHeadwordDisplayForLanguage,
		groupLayerIsSource,
		groupLead,
		groupSourceLayerLabel,
		groupToolIds,
		groupTranslationModel,
		groupTranslationRetrying as groupTranslationRetryingForState,
		groupTranslationRetryKey,
		groupWitnesses,
		languageLabel,
		primaryTool,
		readerEntryLabel,
		readerSectionClass,
		readerSectionStyle,
		retryableGroupTranslation,
		sectionCanToggle,
		sectionExpansionKey,
		sectionHasTreeChildren,
		sectionId,
		sectionSegments,
		sectionShowsReturnedEndingNote,
		sectionToggleLabel,
		toolMeta,
		toolMnemonic,
		toolStyle,
		translationModelLabel,
		visibleGroupBuckets as visibleGroupBucketsForState,
		type BucketGroup
	} from '$lib/desk/desk-entry';
	import { createDeskWordIndexController } from '$lib/desk/desk-word-index';
	import { createDeskRouteStorageController } from '$lib/desk/desk-route-storage-controller';
	import {
		deskEncounterViewState,
		fetchDeskEncounter,
		firstPassTranslationMode,
		manualDeskQueryChanged,
		shouldProgressivelyEnrichLookup,
		retryDeskTranslation,
		validateDeskLookupWord
	} from '$lib/desk/desk-lookup';
	import {
		deskCacheSummary,
		deskCurrentStatusDetail,
		deskCurrentStatusLabel,
		deskReaderLayerStatus
	} from '$lib/desk/desk-status';
	import {
		allAvailableToolIds,
		liveVisibleToolsForLookupTools,
		nextLookupTools,
		nextVisibleTools
	} from '$lib/desk/desk-tool-filters';
	import {
		nextBranchCollapseState,
		nextComponentMeaningExpansionState,
		nextComponentTextLayerState,
		nextGroupTextLayerState,
		nextSectionExpansionState
	} from '$lib/desk/desk-view-state';
	import {
		refreshDeskSearchTranslations,
		retryDeskGroupTranslation
	} from '$lib/desk/desk-workflows';
	import { fetchPayload } from '$lib/msgpack';
	import {
		isPresentableMotdItem,
		motdDisplayGloss,
		motdDisplayLookup,
		motdDisplayNote,
		motdDisplayWord,
		motdVisibleWarnings as motdVisibleWarningsForResult,
		motdWordClass,
		motdWordLang,
		normalizeMotdResult
	} from '$lib/desk/desk-motd';
	import {
		hasMissingSourceReaderTranslations,
		isTranslatedSourceTool,
		returnedToolsForEncounter
	} from '$lib/desk/desk-session';
	import {
		readDeskMotdFromBrowserStorage,
		readDeskWordIndexEarmarksFromBrowserStorage,
		writeDeskMotdToBrowserStorage
	} from '$lib/desk/desk-route-workspace';
	import {
		deskAppRouteUrl,
		deskMotdHref,
		deskRouteHydration,
		deskWordIndexHref,
		deskWordIndexSectionHref,
		type DeskTheme
	} from '$lib/desk/desk-route';
	import {
		clearDeskEncounterPatch,
		clearDeskSearchPatch,
		clearPendingDeskRouteStatePatch,
		resetDeskAppPatch,
		selectDeskLanguagePatch,
		type DeskRouteStatePatch
	} from '$lib/desk/desk-route-state-actions';
	import type { ParadigmPayload } from '$lib/paradigm';
	import { curateParadigmCandidates } from '$lib/paradigm-ui';
	import {
		searchEndpointUrl,
	} from '$lib/desk/desk-endpoints';
	import {
		languageModes,
		tools,
		toolsForLanguage,
		type EncounterBucket,
		type EncounterComponent,
		type EncounterComponentMeaning,
		type EncounterResult,
		type LanguageMode,
		type SearchBackend,
		type ToolId,
		type ToolMeta,
		type ToolRequest,
		type TranslationMode,
		type WordRecommendationItem,
		type WordRecommendationResult
	} from '$lib/search-data';
	import { romanizeSearchTerm } from '$lib/search-romanization';
	import { uiCopy } from '$lib/ui-copy';
	import { wordIndexCandidateQueries } from '$lib/word-index-fallbacks';
	import {
		encounterWordIndexMatchKeys,
		wordIndexActiveSection,
		wordIndexAvailableSections,
		wordIndexBrowseGroups,
		wordIndexDisplay,
		wordIndexDisplayOrderLabel,
		wordIndexEntryCountLabel,
		wordIndexLookup,
		wordIndexMergedRowsFromResponse,
		wordIndexPrimaryItem,
		wordIndexRowMatched as wordIndexRowMatchedWithQuery,
		wordIndexRowPosition,
		wordIndexRowSources as wordIndexRowSourcesForLanguage,
		wordIndexSectionLookupTarget
	} from '$lib/word-index';
	import DeskHeroSearch from '$lib/desk/DeskHeroSearch.svelte';
	import DeskMotdFolio from '$lib/desk/DeskMotdFolio.svelte';
	import DeskLookupResults from '$lib/desk/DeskLookupResults.svelte';
	import DeskPageShell from '$lib/desk/DeskPageShell.svelte';
	import DeskSidebar from '$lib/desk/DeskSidebar.svelte';
	import DeskTopbar from '$lib/desk/DeskTopbar.svelte';
	import type {
		WordIndexItem,
		WordIndexMergedRow,
		WordIndexResponse,
		WordIndexSection,
		WordIndexSectionsResponse
	} from '$lib/word-index';
	import DeskActivityLedger from '$lib/desk/DeskActivityLedger.svelte';

	const simulatedLookupDelayMs = 900;
	const motdSkeletonRows = [0, 1, 2];
	const wordIndexRadius = 5;
	let theme = $state<DeskTheme>('manuscript');
	let language = $state<LanguageMode>('san');
	let query = $state('');
	let backendMode = $state<SearchBackend>('cli');
	let translationMode = $state<TranslationMode>('auto');
	let lookupTools = $state<ToolId[]>(toolsForLanguage('san').map(({ id }) => id));
	let visibleTools = $state<ToolId[]>([]);
	let encounter = $state<EncounterResult | null>(null);
	let loading = $state(false);
	let enrichingTranslations = $state(false);
	let errorMessage = $state('');
	let enrichmentError = $state('');
	let translationArrived = $state(false);
	let translationRetrying = $state<Record<string, boolean>>({});
	const initialMotd = readDeskMotdFromBrowserStorage(
		browser ? localStorage : null,
		normalizeMotdResult
	);
	let motd: WordRecommendationResult | null = $state(initialMotd.result);
	let motdStale = $state(initialMotd.stale);
	let motdLoading = $state(false);
	let motdRefreshing = $state(false);
	let motdError = $state('');
	let motdLinksLoad = $state(true);
	let wordIndex = $state<WordIndexResponse | null>(null);
	let wordIndexSections = $state<WordIndexSectionsResponse | null>(null);
	let wordIndexLoading = $state(false);
	let wordIndexSectionsLoading = $state(false);
	let wordIndexSectionsError = $state('');
	let wordIndexError = $state('');
	let wordIndexEarmarks = $state<WordIndexItem[]>(
		readDeskWordIndexEarmarksFromBrowserStorage(browser ? localStorage : null)
	);
	let paradigmPayloads = $state<Record<string, ParadigmPayload>>({});
	let paradigmLoading = $state<Record<string, boolean>>({});
	let paradigmErrors = $state<Record<string, string>>({});
	let textLayers = $state<Record<string, 'reader' | 'source'>>({});
	let expandedSections = $state<Record<string, boolean>>({});
	let collapsedBranches = $state<Record<string, boolean>>({});
	let sidebarFullHeight = $state(false);
	let deskActivityElapsed = $state<Partial<Record<DeskActivityKey, number>>>({});
	let routeLoadRequested = $state(false);
	let routePrefillOnly = $state(false);
	let activeSearchId = 0;
	let routeStateReady = $state(false);
	let routeSyncQueued = false;
	let pendingVisibleToolsFromRoute: ToolId[] | null = null;
	let pendingSourceLayersFromRoute: string[] = [];
	let pendingExpandedSectionsFromRoute: string[] = [];
	let pendingCollapsedBranchesFromRoute: string[] = [];
	let pendingQueryFromRoute = '';
	let wordIndexRequestId = 0;
	let dictionaryWitnessesSection: HTMLElement | null = null;
	let translationArrivalTimer: ReturnType<typeof setTimeout> | null = null;
	const deskLoadingTimers = createDeskLoadingTimers((kind, seconds) => {
		deskActivityElapsed = { ...deskActivityElapsed, [kind]: seconds };
	});
	const translationArrivalController = createDeskTranslationArrivalController(
		{
			get translationArrived() {
				return translationArrived;
			},
			set translationArrived(value) {
				translationArrived = value;
			},
			get translationArrivalTimer() {
				return translationArrivalTimer;
			},
			set translationArrivalTimer(value) {
				translationArrivalTimer = value;
			}
		},
		{ browser }
	);

	const wordIndexController = createDeskWordIndexController(
		{
			get language() {
				return language;
			},
			get wordIndex() {
				return wordIndex;
			},
			set wordIndex(value) {
				wordIndex = value;
			},
			get wordIndexSections() {
				return wordIndexSections;
			},
			set wordIndexSections(value) {
				wordIndexSections = value;
			},
			get wordIndexLoading() {
				return wordIndexLoading;
			},
			set wordIndexLoading(value) {
				wordIndexLoading = value;
			},
			get wordIndexSectionsLoading() {
				return wordIndexSectionsLoading;
			},
			set wordIndexSectionsLoading(value) {
				wordIndexSectionsLoading = value;
			},
			get wordIndexSectionsError() {
				return wordIndexSectionsError;
			},
			set wordIndexSectionsError(value) {
				wordIndexSectionsError = value;
			},
			get wordIndexError() {
				return wordIndexError;
			},
			set wordIndexError(value) {
				wordIndexError = value;
			},
			get wordIndexRequestId() {
				return wordIndexRequestId;
			},
			set wordIndexRequestId(value) {
				wordIndexRequestId = value;
			},
			get wordIndexEarmarks() {
				return wordIndexEarmarks;
			},
			set wordIndexEarmarks(value) {
				wordIndexEarmarks = value;
			}
		},
		{
			fetchPayload,
			errors: {
				indexFailed: uiCopy.errors.indexFailed
			}
		},
		{ wordIndexRadius }
	);

	const motdController = createDeskMotdController(
		{
			get motd() {
				return motd;
			},
			set motd(value) {
				motd = value;
			},
			get motdStale() {
				return motdStale;
			},
			set motdStale(value) {
				motdStale = value;
			},
			get motdLoading() {
				return motdLoading;
			},
			set motdLoading(value) {
				motdLoading = value;
			},
			get motdRefreshing() {
				return motdRefreshing;
			},
			set motdRefreshing(value) {
				motdRefreshing = value;
			},
			get motdError() {
				return motdError;
			},
			set motdError(value) {
				motdError = value;
			}
		},
		{
			fetchPayload,
			saveMotd: (result) => {
				writeDeskMotdToBrowserStorage(browser ? localStorage : null, result);
			},
			recommendationsFailedMessage: uiCopy.errors.recommendationsFailed
		}
	);

	const paradigmController = createDeskParadigmController(
		{
			get paradigmPayloads() {
				return paradigmPayloads;
			},
			set paradigmPayloads(value) {
				paradigmPayloads = value;
			},
			get paradigmLoading() {
				return paradigmLoading;
			},
			set paradigmLoading(value) {
				paradigmLoading = value;
			},
			get paradigmErrors() {
				return paradigmErrors;
			},
			set paradigmErrors(value) {
				paradigmErrors = value;
			}
		},
		{
			fetchPayload,
			indexFailedMessage: uiCopy.errors.indexFailed
		}
	);

	const storageController = createDeskRouteStorageController(
		{
			get language() { return language; },
			set language(value) { language = value; },
			get query() { return query; },
			set query(value) { query = value; },
			get backendMode() { return backendMode; },
			set backendMode(value) { backendMode = value; },
			get translationMode() { return translationMode; },
			set translationMode(value) { translationMode = value; },
			get theme() { return theme; },
			set theme(value) { theme = value; },
			get lookupTools() { return lookupTools; },
			set lookupTools(value) { lookupTools = value; },
			get visibleTools() { return visibleTools; },
			set visibleTools(value) { visibleTools = value; },
			get encounter() { return encounter; },
			set encounter(value) { encounter = value; },
			get textLayers() { return textLayers; },
			set textLayers(value) { textLayers = value; },
			get expandedSections() { return expandedSections; },
			set expandedSections(value) { expandedSections = value; },
			get collapsedBranches() { return collapsedBranches; },
			set collapsedBranches(value) { collapsedBranches = value; },
			get wordIndex() { return wordIndex; },
			set wordIndex(value) { wordIndex = value; },
			get wordIndexSections() { return wordIndexSections; },
			set wordIndexSections(value) { wordIndexSections = value; },
			get wordIndexEarmarks() { return wordIndexEarmarks; },
			set wordIndexEarmarks(value) { wordIndexEarmarks = value; },
			get loading() { return loading; },
			set loading(value) { loading = value; },
			get enrichingTranslations() { return enrichingTranslations; },
			set enrichingTranslations(value) { enrichingTranslations = value; },
			get errorMessage() { return errorMessage; },
			set errorMessage(value) { errorMessage = value; },
			get enrichmentError() { return enrichmentError; },
			set enrichmentError(value) { enrichmentError = value; }
		},
		{
			browser,
			localStorage: browser ? localStorage : null,
			sessionStorage: browser ? sessionStorage : null,
			setDocumentTheme: (nextTheme) => {
				document.documentElement.dataset.theme = nextTheme;
			}
		}
	);

	let availableTools = $derived(toolsForLanguage(language));
	let returnedToolIds = $derived(
		encounter
			? [...new Set(encounter.buckets.flatMap((bucket) => bucket.source_tools))]
			: ([] as ToolId[])
	);
	let returnedToolOptions = $derived(
		returnedToolIds.map((toolId) => toolMeta(toolId, encounter?.language ?? language))
	);
	let visibleBuckets = $derived(
		encounter
			? encounter.buckets.filter((bucket) =>
					bucket.source_tools.some((tool) => visibleTools.includes(tool))
				)
			: ([] as EncounterBucket[])
	);
	let visibleBucketGroups = $derived(groupBuckets(visibleBuckets, encounter?.query ?? query));
	let visibleComponents = $derived(
		encounter
			? encounter.components.filter((component) =>
					componentToolIds(component).some((tool) => visibleTools.includes(tool))
				)
			: ([] as EncounterComponent[])
	);
	let isAllLookupSelected = $derived(lookupTools.length === availableTools.length);
	let motdPending = $derived(motdLoading && !motd && !motdError);
	let hasTranslationActivity = $derived(
		enrichingTranslations || Object.values(translationRetrying).some(Boolean)
	);
	let hasParadigmActivity = $derived(Object.values(paradigmLoading).some(Boolean));
	let deskActivityRows = $derived(
		deskActivityItems({
			active: {
				lookup: loading,
				translation: hasTranslationActivity,
				wordIndex: wordIndexLoading,
				wordIndexSections: wordIndexSectionsLoading,
				motd: motdLoading || motdRefreshing,
				paradigm: hasParadigmActivity
			},
			elapsed: deskActivityElapsed
		})
	);
	let motdItems = $derived(motd?.items.filter(isPresentableMotdItem) ?? []);
	let motdVisibleWarnings = $derived(motdVisibleWarningsForResult(motd));
	let currentWordIndex = $derived(wordIndexMatchesQuery() ? wordIndex : null);
	let wordIndexGroups = $derived(currentWordIndex?.neighborhood?.groups ?? []);
	let wordIndexBrowseGroupItems = $derived(wordIndexBrowseGroups(currentWordIndex));
	let wordIndexMergedRows = $derived(wordIndexMergedRowsFromResponse(currentWordIndex));
	let wordIndexHasRows = $derived(wordIndexMergedRows.length > 0);
	let wordIndexSourceSetCount = $derived(
		wordIndexBrowseGroupItems.length || wordIndexGroups.length
	);
	let wordIndexInitialLoading = $derived(wordIndexLoading && !currentWordIndex);
	let wordIndexEncounterMatchKeys = $derived(encounterWordIndexMatchKeys(encounter));
	let wordIndexWarnings = $derived(currentWordIndex?.warnings ?? []);
	let wordIndexOrderTitle = $derived(
		wordIndexDisplayOrderLabel(currentWordIndex, uiCopy.wordIndex.orderTitle)
	);
	let wordIndexSectionItems = $derived(wordIndexAvailableSections(wordIndexSections));
	let wordIndexSectionsTitle = $derived(
		wordIndexDisplayOrderLabel(wordIndexSections, uiCopy.wordIndex.sectionsTitle)
	);
	let activeWordIndexSection = $derived(
		wordIndexActiveSection(currentWordIndex, wordIndexSections)
	);
	let searchRomanization = $derived(romanizeSearchTerm(language, query));
	let paradigmCandidateCuration = $derived(
		curateParadigmCandidates(
			encounter?.paradigm_resolution?.candidates ?? [],
			encounter?.paradigm_resolution?.normalized_form || encounter?.query || query
		)
	);
	let paradigmCandidates = $derived(paradigmCandidateCuration.visible);

	const componentLedgerHelpers = {
		countLabel,
		componentPrimaryTool,
		componentToolIds,
		componentHeadwordDisplay: (component: EncounterComponent) =>
			componentHeadwordDisplayForLanguage(component, encounter?.language ?? language),
		componentLookupLine,
		componentCanSwitchTextLayer,
		componentLayerIsSource,
		setComponentTextLayer,
		componentSourceLayerLabel,
		componentHasTranslationToggle,
		componentAwaitsReaderTranslation: (component: EncounterComponent) =>
			componentAwaitsReaderTranslationForState(component, enrichingTranslations),
		componentTranslationModel,
		componentMeaningSegments,
		componentMeaningCanToggle,
		componentMeaningToggleLabel,
		componentMeaningKey,
		componentMeaningSourceLabel,
		toggleComponentMeaning,
		toolMeta,
		toolMnemonic,
		translationModelLabel
	};

	const dictionaryGroupHelpers = {
		countLabel,
		groupHeadwordDisplay: (group: BucketGroup) =>
			groupHeadwordDisplayForLanguage(
				group,
				encounter?.language ?? language,
				encounter?.word_index?.anchors ?? []
			),
		groupLead,
		groupToolIds,
		groupWitnesses,
		readerEntryLabel,
		groupCanSwitchTextLayer,
		groupLayerIsSource,
		groupHasReaderTranslation,
		setGroupTextLayer,
		groupSourceLayerLabel,
		groupTranslationModel,
		groupHasTranslationToggle,
		groupAwaitsReaderTranslation: (group: BucketGroup) =>
			groupAwaitsReaderTranslationForState(group, enrichingTranslations),
		retryableGroupTranslation,
		groupTranslationRetrying: (group: BucketGroup) =>
			groupTranslationRetryingForState(group, translationRetrying),
		retryGroupTranslation,
		visibleGroupBuckets: (group: BucketGroup) =>
			visibleGroupBucketsForState(group, collapsedBranches),
		sectionSegments,
		sectionHasTreeChildren,
		sectionId,
		readerSectionClass,
		readerSectionStyle,
		branchToggleLabel: (bucket: EncounterBucket) =>
			branchToggleLabelForState(bucket, collapsedBranches),
		toggleBranchCollapse,
		sectionExpansionKey,
		sectionCanToggle,
		sectionToggleLabel,
		toggleSectionExpansion,
		sectionShowsReturnedEndingNote,
		toolMeta,
		toolMnemonic,
		translationModelLabel
	};

	$effect(() => {
		if (!browser || !routeStateReady) return;

		theme;
		language;
		query;
		backendMode;
		translationMode;
		lookupTools;
		visibleTools;
		encounter;
		textLayers;
		expandedSections;
		collapsedBranches;
		routeLoadRequested;
		routePrefillOnly;

		queueRouteStateSync();
		storageController.saveDeskState();
	});

	$effect(() => {
		wordIndexEarmarks;
		storageController.saveWordIndexEarmarks();
	});

	$effect(() => {
		if (!browser || !routeStateReady) return;
		void wordIndexController.loadSections(language);
	});

	$effect(() => {
		if (!browser || !routeStateReady) return;
		if (motdLoading || motdRefreshing || motdError) return;
		if (motdStale && motdItems.length) void motdController.load(false);
		if (!motdItems.length) void motdController.load(false);
	});

	function endpointUrl(translationOverride: TranslationMode = translationMode) {
		return searchEndpointUrl({
			language,
			query,
			backendMode,
			translationMode: translationOverride,
			lookupTools,
			allLookupSelected: isAllLookupSelected
		});
	}

	function motdHref(item: WordRecommendationItem) {
		return deskMotdHref(item, { theme, motdLinksLoad });
	}

	function handleMotdNavigation(event: MouseEvent, item: WordRecommendationItem) {
		if (event.defaultPrevented || event.button !== 0) return;
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

		event.preventDefault();
		navigateInsideDesk(motdHref(item));
	}

	function navigateInsideDesk(href: string) {
		if (!browser) return;

		const url = new URL(href, window.location.origin);
		pushState(`${url.pathname}${url.search}`, {});
		hydrateRouteStateFromUrl();
	}

	function isActiveMotd(item: WordRecommendationItem) {
		return language === item.language && query.trim().toLowerCase() === item.query.toLowerCase();
	}

	function wordIndexHref(item: WordIndexItem, includeLoad = false) {
		return deskWordIndexHref(item, { translationMode, theme, includeLoad });
	}

	function wordIndexSectionHref(section: WordIndexSection) {
		return deskWordIndexSectionHref(section, { translationMode, theme });
	}

	function handleWordIndexNavigation(event: MouseEvent, item: WordIndexItem) {
		if (event.defaultPrevented || event.button !== 0) return;
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

		event.preventDefault();
		navigateInsideDesk(wordIndexHref(item));
	}

	function openWordIndexSection(section: WordIndexSection) {
		const href = wordIndexSectionHref(section);
		if (!href) return;
		navigateInsideDesk(href);
	}

	function browseWordIndexSection(section: WordIndexSection) {
		const anchor = section.anchor;
		if (!anchor?.query) return;
		void wordIndexController.loadBrowseWordIndex(anchor.query, anchor.language);
	}

	function wordIndexRowMatched(row: WordIndexMergedRow) {
		return wordIndexRowMatchedWithQuery(row, {
			query,
			encounterMatchKeys: wordIndexEncounterMatchKeys
		});
	}

	function wordIndexRowSources(row: WordIndexMergedRow) {
		return wordIndexRowSourcesForLanguage(row, language);
	}

	function wordIndexMatchesQuery() {
		if (!wordIndex) return false;
		return wordIndex.request.language === language;
	}

	function appRouteUrl(includeLoad = false) {
		return deskAppRouteUrl({
			includeLoad,
			language,
			query,
			backendMode,
			translationMode,
			theme,
			lookupTools,
			defaultTools: toolsForLanguage('san').map(({ id }) => id),
			hasEncounter: Boolean(encounter),
			visibleTools,
			textLayers,
			expandedSections,
			collapsedBranches,
			pendingVisibleTools: pendingVisibleToolsFromRoute ?? [],
			pendingSourceLayers: pendingSourceLayersFromRoute,
			pendingExpandedSections: pendingExpandedSectionsFromRoute,
			pendingCollapsedBranches: pendingCollapsedBranchesFromRoute,
			routePrefillOnly,
			allLookupSelected: isAllLookupSelected,
			encounterMatchesQuery: encounterMatchesQuery(),
			returnedToolIds
		});
	}

	function queueRouteStateSync() {
		if (routeSyncQueued) return;
		routeSyncQueued = true;

		queueMicrotask(() => {
			routeSyncQueued = false;
			const nextUrl = appRouteUrl();
			if (nextUrl !== `${window.location.pathname}${window.location.search}`) {
				replaceState(nextUrl, {});
			}
		});
	}

	function encounterMatchesQuery() {
		return Boolean(
			encounter &&
			encounter.language === language &&
			encounter.query.trim().toLowerCase() === query.trim().toLowerCase()
		);
	}

	function hydrateRouteStateFromUrl() {
		const params = new URL(window.location.href).searchParams;
		const routeIntent = deskRouteHydration({
			params,
			currentLanguage: language,
			currentQuery: query,
			encounter
		});

		if (routeIntent.shouldResetEncounter) {
			clearEncounterState();
		}

		language = routeIntent.nextLanguage;
		query = routeIntent.nextQuery;
		routePrefillOnly = routeIntent.shouldPrefillOnly;
		routeLoadRequested = routeIntent.routeLoadRequested;
		lookupTools = routeIntent.requestedTools?.length
			? routeIntent.requestedTools
			: routeIntent.validTools;

		if (routeIntent.shouldPreserveEncounter && encounter) {
			const returnedTools = returnedToolsForEncounter(encounter);
			visibleTools = routeIntent.routeVisibleTools.length
				? routeIntent.routeVisibleTools.filter((tool) => returnedTools.includes(tool))
				: visibleTools.length
					? visibleTools
					: returnedTools;
			textLayers = Object.fromEntries(
				routeIntent.routeSourceLayers.map((bucketId) => [bucketId, 'source'])
			);
			expandedSections = Object.fromEntries(
				routeIntent.routeExpandedSections.map((key) => [key, true])
			);
			collapsedBranches = Object.fromEntries(
				routeIntent.routeCollapsedBranches.map((key) => [key, true])
			);
			pendingVisibleToolsFromRoute = null;
			pendingSourceLayersFromRoute = [];
			pendingExpandedSectionsFromRoute = [];
			pendingCollapsedBranchesFromRoute = [];
		} else {
			visibleTools = [];
			pendingVisibleToolsFromRoute = routeIntent.requestedVisibleTools;
			pendingSourceLayersFromRoute = routeIntent.routeSourceLayers;
			pendingExpandedSectionsFromRoute = routeIntent.routeExpandedSections;
			pendingCollapsedBranchesFromRoute = routeIntent.routeCollapsedBranches;
		}
		pendingQueryFromRoute = query.trim();

		if (routeIntent.requestedTheme) {
			theme = routeIntent.requestedTheme;
		}

		if (routeIntent.requestedBackend) {
			backendMode = routeIntent.requestedBackend;
		}

		if (routeIntent.requestedTranslation) {
			translationMode = routeIntent.requestedTranslation;
		}

		const restoredFromSession =
			routeIntent.shouldRestoreFromSession && storageController.restoreDeskState(params);
		if (restoredFromSession) routeLoadRequested = false;

		routeStateReady = true;

		if (routeLoadRequested) {
			void runSearch();
		} else {
			queueRouteStateSync();
		}
	}

	function clearPendingRouteState() {
		applyDeskRouteStatePatch(clearPendingDeskRouteStatePatch());
	}

	function applyDeskRouteStatePatch(patch: DeskRouteStatePatch) {
		if (patch.activeSearchIdDelta) activeSearchId += patch.activeSearchIdDelta;
		if (patch.routeLoadRequested !== undefined) routeLoadRequested = patch.routeLoadRequested;
		if (patch.routePrefillOnly !== undefined) routePrefillOnly = patch.routePrefillOnly;
		if (patch.language !== undefined) language = patch.language;
		if (patch.query !== undefined) query = patch.query;
		if (patch.backendMode !== undefined) backendMode = patch.backendMode;
		if (patch.translationMode !== undefined) translationMode = patch.translationMode;
		if (patch.theme !== undefined) theme = patch.theme;
		if (patch.lookupTools !== undefined) lookupTools = patch.lookupTools;
		if (patch.wordIndexEarmarks !== undefined) wordIndexEarmarks = patch.wordIndexEarmarks;
		if (patch.encounter !== undefined) encounter = patch.encounter;
		if (patch.visibleTools !== undefined) visibleTools = patch.visibleTools;
		if (patch.loading !== undefined) loading = patch.loading;
		if (patch.enrichingTranslations !== undefined) {
			enrichingTranslations = patch.enrichingTranslations;
		}
		if (patch.errorMessage !== undefined) errorMessage = patch.errorMessage;
		if (patch.enrichmentError !== undefined) enrichmentError = patch.enrichmentError;
		if (patch.textLayers !== undefined) textLayers = patch.textLayers;
		if (patch.expandedSections !== undefined) expandedSections = patch.expandedSections;
		if (patch.collapsedBranches !== undefined) collapsedBranches = patch.collapsedBranches;
		if (patch.pendingVisibleToolsFromRoute !== undefined) {
			pendingVisibleToolsFromRoute = patch.pendingVisibleToolsFromRoute;
		}
		if (patch.pendingSourceLayersFromRoute !== undefined) {
			pendingSourceLayersFromRoute = patch.pendingSourceLayersFromRoute;
		}
		if (patch.pendingExpandedSectionsFromRoute !== undefined) {
			pendingExpandedSectionsFromRoute = patch.pendingExpandedSectionsFromRoute;
		}
		if (patch.pendingCollapsedBranchesFromRoute !== undefined) {
			pendingCollapsedBranchesFromRoute = patch.pendingCollapsedBranchesFromRoute;
		}
		if (patch.pendingQueryFromRoute !== undefined) pendingQueryFromRoute = patch.pendingQueryFromRoute;
	}

	function clearEncounterState() {
		translationArrivalController.clear();
		applyDeskRouteStatePatch(clearDeskEncounterPatch());
		clearWordIndexState();
		paradigmController.clear();
	}

	function clearWordIndexState() {
		wordIndexController.clearSearchState();
	}

	async function runSearch() {
		motdController.abort();
		translationArrivalController.clear();
		routePrefillOnly = false;
		const lookupValidation = validateDeskLookupWord(query);
		let renderedSearch = false;
		let wordIndexSearchStarted = false;

		if (!lookupValidation.ok) {
			activeSearchId += 1;
			routeLoadRequested = false;
			errorMessage =
				lookupValidation.reason === 'empty'
					? uiCopy.errors.enterOneWord
					: uiCopy.errors.oneWordOnly;
			encounter = null;
			visibleTools = [];
			enrichingTranslations = false;
			collapsedBranches = {};
			clearWordIndexState();
			return;
		}

		const word = lookupValidation.word;

		if (manualDeskQueryChanged(pendingQueryFromRoute, word)) {
			clearPendingRouteState();
		}

		wordIndexController.clearSearchState();

		loading = true;
		routeLoadRequested = false;
		enrichingTranslations = false;
		errorMessage = '';
		enrichmentError = '';
		const searchId = (activeSearchId += 1);
		const requestedTranslationMode = translationMode;
		const firstPassMode = firstPassTranslationMode(backendMode, requestedTranslationMode);

		try {
			const data = await fetchEncounter(firstPassMode);
			if (searchId !== activeSearchId) return;

			applyEncounter(data, true);
			const indexCandidates = wordIndexCandidateQueries(data, word);
			void wordIndexController.loadNearbyWordIndex(
				indexCandidates[0] ?? word,
				language,
				indexCandidates.slice(1)
			);
			wordIndexSearchStarted = true;
			renderedSearch = true;

			if (data.error) {
				errorMessage = uiCopy.errors.liveFallback(data.error);
			}

			if (
				shouldProgressivelyEnrichLookup(backendMode, requestedTranslationMode) &&
				hasMissingSourceReaderTranslations(data)
			) {
				void enrichSearch(searchId, requestedTranslationMode);
			}
		} catch (error) {
			if (searchId !== activeSearchId) return;
			errorMessage = error instanceof Error ? error.message : uiCopy.errors.searchFailed;
			encounter = null;
			visibleTools = [];
			const indexCandidates = wordIndexCandidateQueries(null, word);
			void wordIndexController.loadNearbyWordIndex(
				indexCandidates[0] ?? word,
				language,
				indexCandidates.slice(1)
			);
			wordIndexSearchStarted = true;
		} finally {
			if (searchId === activeSearchId) {
				loading = false;
				if (!wordIndexSearchStarted) wordIndexLoading = false;
				if (renderedSearch) {
					await tick();
					scrollToDictionaryWitnesses();
				}
			}
		}
	}

	async function fetchEncounter(mode: TranslationMode) {
		return fetchDeskEncounter({
			url: endpointUrl(mode),
			delayMs: simulatedLookupDelayMs,
			fetchPayload,
			searchFailedMessage: uiCopy.errors.searchFailed
		});
	}

	function applyEncounter(data: EncounterResult, resetReaderState: boolean) {
		const viewState = deskEncounterViewState({
			result: data,
			resetReaderState,
			previousVisibleTools: visibleTools,
			pendingVisibleTools: pendingVisibleToolsFromRoute,
			pendingSourceLayers: pendingSourceLayersFromRoute,
			pendingExpandedSections: pendingExpandedSectionsFromRoute,
			pendingCollapsedBranches: pendingCollapsedBranchesFromRoute
		});

		encounter = data;
		paradigmController.clear();
		visibleTools = viewState.visibleTools;

		if (viewState.shouldClearPendingRouteState) {
			textLayers = viewState.textLayers;
			expandedSections = viewState.expandedSections;
			collapsedBranches = viewState.collapsedBranches;
			pendingVisibleToolsFromRoute = null;
			pendingSourceLayersFromRoute = [];
			pendingExpandedSectionsFromRoute = [];
			pendingCollapsedBranchesFromRoute = [];
			pendingQueryFromRoute = '';
		}
	}

	async function enrichSearch(searchId: number, mode: TranslationMode) {
		await refreshDeskSearchTranslations({
			searchId,
			isSearchCurrent: (candidate) => candidate === activeSearchId,
			fetchEncounter,
			applyEncounter,
			setEnrichingTranslations: (value) => {
				enrichingTranslations = value;
			},
			setEnrichmentError: (message) => {
				enrichmentError = message;
			},
			tick,
			triggerTranslationArrival: translationArrivalController.trigger,
			translationFailedMessage: uiCopy.errors.translationFailed,
			enrichmentMode: mode
		});
	}

	async function retryGroupTranslation(group: BucketGroup) {
		const translation = retryableGroupTranslation(group);
		if (!translation) return;
		const retryKey = groupTranslationRetryKey(group);
		translationRetrying = { ...translationRetrying, [retryKey]: true };
		enrichmentError = '';

		await retryDeskGroupTranslation({
			searchId: activeSearchId,
			isSearchCurrent: (candidate) => candidate === activeSearchId,
			translation,
			retryKey,
			fetchPayload,
			setTranslationRetrying: (key, value) => {
				translationRetrying = { ...translationRetrying, [key]: value };
			},
			setEnrichmentError: (message) => {
				enrichmentError = message;
			},
			tick,
			fetchEncounter,
			applyEncounter,
			triggerTranslationArrival: translationArrivalController.trigger,
			retryDeskTranslation,
			translationFailedMessage: uiCopy.errors.translationFailed
		});
	}

	function scrollToDictionaryWitnesses() {
		if (!browser || !dictionaryWitnessesSection) return;

		const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		dictionaryWitnessesSection.scrollIntoView({
			behavior: prefersReducedMotion ? 'auto' : 'smooth',
			block: 'start'
		});
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		clearPendingRouteState();
		void runSearch();
	}

	function handleQueryInput() {
		routeLoadRequested = false;
		routePrefillOnly = false;
		clearPendingRouteState();
		clearWordIndexState();
	}

	function handleHeroQueryInput(value: string) {
		query = value;
		handleQueryInput();
	}

	function clearSearchDesk() {
		applyDeskRouteStatePatch(clearDeskSearchPatch());
	}

	function resetAppState() {
		motdController.reset();
		translationArrivalController.clear();
		applyDeskRouteStatePatch(resetDeskAppPatch());
		clearWordIndexState();
		paradigmController.clear();
		storageController.clearAppStorage();
	}

	function clearRouteState() {
		resetAppState();
		if (browser) {
			replaceState('/', {});
		}
	}

	function handleHomeNavigation(event: MouseEvent) {
		if (event.defaultPrevented || event.button !== 0) return;
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

		event.preventDefault();
		clearRouteState();
	}

	function selectLanguage(nextLanguage: LanguageMode) {
		applyDeskRouteStatePatch(selectDeskLanguagePatch(nextLanguage));
	}

	function applyLiveResultFilter(nextTools: ToolId[]) {
		if (!encounter) return;
		visibleTools = liveVisibleToolsForLookupTools(nextTools, returnedToolIds);
	}

	function toggleLookupTool(tool: ToolId) {
		routeLoadRequested = false;
		routePrefillOnly = false;
		const nextTools = nextLookupTools(lookupTools, tool);
		lookupTools = nextTools;
		applyLiveResultFilter(nextTools);
	}

	function toggleVisibleTool(tool: ToolId) {
		visibleTools = nextVisibleTools(visibleTools, tool);
	}

	function showAllLookupTools() {
		routeLoadRequested = false;
		routePrefillOnly = false;
		lookupTools = allAvailableToolIds(availableTools);
		visibleTools = returnedToolIds;
	}

	function showAllReturnedTools() {
		visibleTools = returnedToolIds;
	}

	function toggleSectionExpansion(bucket: EncounterBucket) {
		expandedSections = nextSectionExpansionState(expandedSections, bucket);
	}

	function toggleBranchCollapse(bucket: EncounterBucket) {
		collapsedBranches = nextBranchCollapseState(collapsedBranches, bucket);
	}

	function setComponentTextLayer(component: EncounterComponent, layer: 'reader' | 'source') {
		textLayers = nextComponentTextLayerState(textLayers, component, layer);
	}

	function toggleComponentMeaning(meaning: EncounterComponentMeaning) {
		expandedSections = nextComponentMeaningExpansionState(expandedSections, meaning);
	}

	function setGroupTextLayer(group: BucketGroup, layer: 'reader' | 'source') {
		textLayers = nextGroupTextLayerState(textLayers, group, layer);
	}

	function currentStatusLabel() {
		return deskCurrentStatusLabel({
			loading,
			enrichingTranslations,
			hasAttention: Boolean(errorMessage || enrichmentError),
			hasEncounter: Boolean(encounter)
		});
	}

	function currentStatusDetail() {
		return deskCurrentStatusDetail({
			loading,
			enrichingTranslations,
			lookupToolCount: lookupTools.length,
			encounter,
			visibleBucketCount: visibleBuckets.length,
			query
		});
	}

	function setTheme(nextTheme: 'manuscript' | 'vespers') {
		theme = nextTheme;
		document.documentElement.dataset.theme = nextTheme;
		localStorage.setItem('orion-theme', nextTheme);
	}

	function setTranslationMode(nextMode: TranslationMode) {
		translationMode = nextMode;
	}

	function handleSidebarWheel(event: WheelEvent) {
		if (!window.matchMedia('(min-width: 64rem)').matches) return;

		const sidebar = event.currentTarget as HTMLElement;
		const canScroll = sidebar.scrollHeight > sidebar.clientHeight + 1;
		const atTop = sidebar.scrollTop <= 0;
		const atBottom = sidebar.scrollTop + sidebar.clientHeight >= sidebar.scrollHeight - 1;
		const scrollingPastTop = event.deltaY < 0 && atTop;
		const scrollingPastBottom = event.deltaY > 0 && atBottom;

		event.stopPropagation();

		if (!canScroll || scrollingPastTop || scrollingPastBottom) {
			event.preventDefault();
		}
	}

	function setDictionaryWitnessesSection(element: HTMLElement | null) {
		dictionaryWitnessesSection = element;
	}

	$effect(() => {
		syncDeskActivityTimer(deskLoadingTimers, 'lookup', loading);
		syncDeskActivityTimer(deskLoadingTimers, 'translation', hasTranslationActivity);
		syncDeskActivityTimer(deskLoadingTimers, 'wordIndex', wordIndexLoading);
		syncDeskActivityTimer(deskLoadingTimers, 'wordIndexSections', wordIndexSectionsLoading);
		syncDeskActivityTimer(deskLoadingTimers, 'motd', motdLoading || motdRefreshing);
		syncDeskActivityTimer(deskLoadingTimers, 'paradigm', hasParadigmActivity);
	});

	onMount(() => {
		const savedTheme = localStorage.getItem('orion-theme');

		if (savedTheme === 'manuscript' || savedTheme === 'vespers') {
			theme = savedTheme;
			document.documentElement.dataset.theme = savedTheme;
		}

		hydrateRouteStateFromUrl();

		const syncSidebarHeight = () => {
			sidebarFullHeight = window.scrollY > 72;
		};

		syncSidebarHeight();
		window.addEventListener('scroll', syncSidebarHeight, { passive: true });
		window.addEventListener('popstate', hydrateRouteStateFromUrl);

		return () => {
			motdController.abort();
			translationArrivalController.clear();
			deskLoadingTimers.stopAll();
			window.removeEventListener('scroll', syncSidebarHeight);
			window.removeEventListener('popstate', hydrateRouteStateFromUrl);
		};
	});
</script>

<svelte:head>
	<title>{uiCopy.app.title}</title>
	<meta name="description" content={uiCopy.app.description} />
</svelte:head>

<DeskPageShell {theme}>
	<DeskHeroSearch
		{language}
		{query}
		{loading}
		{searchRomanization}
		{languageLabel}
		statusDetail={currentStatusDetail()}
		onSelectLanguage={selectLanguage}
		onQueryInput={handleHeroQueryInput}
		onSubmit={handleSubmit}
		onClear={clearSearchDesk}
	/>

	<DeskActivityLedger items={deskActivityRows} />

	<DeskMotdFolio
		{motd}
		items={motdItems}
		visibleWarnings={motdVisibleWarnings}
		pending={motdPending}
		refreshing={motdRefreshing}
		error={motdError}
		linksLoad={motdLinksLoad}
		skeletonRows={motdSkeletonRows}
		{languageLabel}
		{isActiveMotd}
		{motdHref}
		{motdWordClass}
		{motdWordLang}
		{motdDisplayWord}
		{motdDisplayLookup}
		{motdDisplayGloss}
		{motdDisplayNote}
		onToggleLinksLoad={() => {
			motdLinksLoad = !motdLinksLoad;
		}}
		onRefresh={() => void motdController.load(true)}
		onNavigate={handleMotdNavigation}
	/>

	<DeskLookupResults
		{errorMessage}
		{enrichmentError}
		{enrichingTranslations}
		{encounter}
		{loading}
		{translationArrived}
		{visibleComponents}
		{visibleBucketGroups}
		{textLayers}
		{expandedSections}
		{collapsedBranches}
		{toolStyle}
		{componentLedgerHelpers}
		{dictionaryGroupHelpers}
		{query}
		languageName={languageLabel(language)}
		allSourcesSelected={isAllLookupSelected}
		lookupElapsedSeconds={deskActivityElapsed.lookup ?? 0}
		{paradigmCandidates}
		paradigmHiddenCount={paradigmCandidateCuration.hiddenCount}
		{paradigmPayloads}
		{paradigmLoading}
		{paradigmErrors}
		{countLabel}
		onShowAllReturnedTools={showAllReturnedTools}
		onLoadParadigm={paradigmController.load}
		onWitnessesElement={setDictionaryWitnessesSection}
	/>

	{#snippet topbar()}
		<DeskTopbar
			{theme}
			{language}
			{translationMode}
			{enrichingTranslations}
			{languageLabel}
			statusLabel={currentStatusLabel()}
			onHomeNavigation={handleHomeNavigation}
			onTranslationModeChange={setTranslationMode}
			onSetTheme={setTheme}
		/>
	{/snippet}

	{#snippet sidebar()}
		<DeskSidebar
			fullHeight={sidebarFullHeight}
			onWheel={handleSidebarWheel}
			wordIndex={{
				query,
				sections: wordIndexSectionItems,
				activeSection: activeWordIndexSection,
				sectionsTitle: wordIndexSectionsTitle,
				sectionsLoading: wordIndexSectionsLoading,
				sectionsError: wordIndexSectionsError,
				loading: wordIndexLoading,
				initialLoading: wordIndexInitialLoading,
				rows: wordIndexMergedRows,
				hasRows: wordIndexHasRows,
				sourceSetCount: wordIndexSourceSetCount,
				orderTitle: wordIndexOrderTitle,
				error: wordIndexError,
					emptyMessage: wordIndexWarnings[0]?.message || uiCopy.wordIndex.empty,
					hasResponse: Boolean(wordIndex),
					earmarks: wordIndexEarmarks,
					canOpenSection: (section) => Boolean(wordIndexSectionLookupTarget(section)),
					wordIndexPrimaryItem,
					wordIndexRowPosition,
					wordIndexRowMatched,
					wordIndexRowSources,
					wordIndexHref,
					wordIndexDisplay,
					wordIndexLookup,
					wordIndexEntryCountLabel,
					isEarmarked: wordIndexController.isEarmarked,
					languageLabel,
					onBrowseSection: browseWordIndexSection,
					onOpenSection: openWordIndexSection,
					onNavigate: handleWordIndexNavigation,
					onToggleEarmark: wordIndexController.toggleEarmark,
					onClearEarmarks: wordIndexController.clearEarmarks
				}}
			sourceControls={{
				availableTools,
				lookupTools,
				isAllLookupSelected,
				returnedTools: returnedToolOptions,
				visibleTools,
				toolMnemonic,
				onShowAllLookupTools: showAllLookupTools,
				onToggleLookupTool: toggleLookupTool,
				onShowAllReturnedTools: showAllReturnedTools,
				onToggleVisibleTool: toggleVisibleTool
			}}
			colophon={encounter
				? {
						encounter,
						cacheAccount: deskCacheSummary(encounter),
						readerLayerStatus: deskReaderLayerStatus({
							enrichingTranslations,
							translationMode,
							backendMode,
							encounter
						})
					}
				: null}
			pageMarks={{
				pageLink: appRouteUrl(encounterMatchesQuery()),
				endpoint: endpointUrl(),
				onClear: clearRouteState
			}}
		/>
	{/snippet}
</DeskPageShell>
