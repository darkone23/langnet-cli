<script lang="ts">
	import { browser } from '$app/environment';
	import { pushState, replaceState } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import {
		createDeskLoadingTimers,
		deskActivityItems,
		type DeskActivityKey
	} from '$lib/desk/desk-activity';
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
		clearDeskBrowserStorage,
		readDeskMotdFromBrowserStorage,
		readDeskStateFromBrowserStorage,
		readDeskWordIndexEarmarksFromBrowserStorage,
		restoreDeskStateFromStorage,
		writeDeskMotdToBrowserStorage,
		writeDeskStateToBrowserStorage,
		writeDeskWordIndexEarmarksToBrowserStorage,
		clearDeskStateStorage,
		clearDeskThemeStorage
	} from '$lib/desk/desk-route-workspace';
	import {
		currentDeskRouteKey,
		deskAppRouteUrl,
		deskMotdHref,
		deskRouteHydration,
		deskWordIndexHref,
		deskWordIndexSectionHref,
		type DeskTheme
	} from '$lib/desk/desk-route';
	import { motdItemKeys } from '$lib/motd-cache';
	import { normalizeParadigmPayload, type ParadigmPayload } from '$lib/paradigm';
	import {
		curateParadigmCandidates,
		paradigmPayloadHasForms,
		paradigmUnavailableMessage
	} from '$lib/paradigm-ui';
	import type { ParadigmResolutionCandidate } from '$lib/paradigm-resolution';
	import { paradigmCandidateKey, paradigmRequestUrl } from '$lib/desk/desk-paradigm';
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
	let motdAbortController: AbortController | null = null;
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
	let motdRequestId = 0;
	let wordIndexRequestId = 0;
	let dictionaryWitnessesSection: HTMLElement | null = null;
	let translationArrivalTimer: ReturnType<typeof setTimeout> | null = null;
	const deskLoadingTimers = createDeskLoadingTimers((kind, seconds) => {
		deskActivityElapsed = { ...deskActivityElapsed, [kind]: seconds };
	});

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
		saveDeskStateToSessionStorage();
	});

	$effect(() => {
		wordIndexEarmarks;
		saveWordIndexEarmarks();
	});

	$effect(() => {
		if (!browser || !routeStateReady) return;
		void wordIndexController.loadSections(language);
	});

	$effect(() => {
		if (!browser || !routeStateReady) return;
		if (motdLoading || motdRefreshing || motdError) return;
		if (motdStale && motdItems.length) void loadMotd(false);
		if (!motdItems.length) void loadMotd(false);
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

	async function loadMotd(refresh = false) {
		const requestId = ++motdRequestId;
		const showRefreshState = Boolean(motd);
		motdAbortController?.abort();
		const controller = new AbortController();
		motdAbortController = controller;
		motdLoading = !showRefreshState;
		motdRefreshing = showRefreshState;
		motdError = '';

		try {
			const params = new URLSearchParams({
				language: 'all',
				count: '1',
				translation: 'cache',
				candidate_source: 'pool',
				timeout_ms: '3000'
			});
			if (refresh || motdStale) {
				params.set('refresh', '1');
				const avoid = motdItemKeys(motd);
				if (avoid.length) params.set('avoid', avoid.join(','));
			}
			const { response, data: motdPayload } = await fetchPayload<WordRecommendationResult>(
				`/api/motd?${params.toString()}`,
				{
					signal: controller.signal
				}
			);
			const data = normalizeMotdResult(motdPayload);

			if (!response.ok) {
				throw new Error(data.error ?? uiCopy.errors.recommendationsFailed);
			}
			if (!data.items.length) {
				throw new Error(data.error ?? uiCopy.errors.recommendationsFailed);
			}

			if (requestId !== motdRequestId) return;
			motd = data;
			motdStale = false;
			saveMotdToLocalStorage(data);
		} catch (error) {
			if (requestId !== motdRequestId) return;
			if (isAbortError(error)) return;
			motdError = error instanceof Error ? error.message : uiCopy.errors.recommendationsFailed;
		} finally {
			if (requestId === motdRequestId) {
				motdLoading = false;
				motdRefreshing = false;
				if (motdAbortController === controller) motdAbortController = null;
			}
		}
	}

	function abortMotdRequest() {
		motdRequestId += 1;
		motdAbortController?.abort();
		motdAbortController = null;
		motdLoading = false;
		motdRefreshing = false;
	}

	function isAbortError(error: unknown) {
		return error instanceof DOMException
			? error.name === 'AbortError'
			: error instanceof Error && error.name === 'AbortError';
	}

	function saveMotdToLocalStorage(result: WordRecommendationResult) {
		writeDeskMotdToBrowserStorage(browser ? localStorage : null, result);
	}

	function saveWordIndexEarmarks() {
		writeDeskWordIndexEarmarksToBrowserStorage(browser ? localStorage : null, wordIndexEarmarks);
	}

	function saveDeskStateToSessionStorage() {
		if (!browser) return;

		if (!query.trim() && !encounter) {
			clearDeskStateStorage(sessionStorage);
			return;
		}

		writeDeskStateToBrowserStorage(sessionStorage, {
			language,
			query,
			backendMode,
			translationMode,
			theme,
			lookupTools,
			visibleTools,
			encounter,
			textLayers,
			expandedSections,
			collapsedBranches,
			wordIndex,
			wordIndexSections
		});
	}

	function clearStoredThemeState() {
		if (!browser) return;

		try {
			clearDeskThemeStorage(localStorage);
			document.documentElement.dataset.theme = 'manuscript';
		} catch {
			// Ignore storage failures.
		}
	}

	function clearAppBrowserStorage() {
		if (!browser) return;
		clearDeskBrowserStorage({
			localStorage,
			sessionStorage
		});
		clearStoredThemeState();
	}

	function currentRouteKey() {
		return currentDeskRouteKey({
			language,
			query,
			backendMode,
			translationMode,
			lookupTools
		});
	}

	function restoreDeskStateFromSessionStorage(params: URLSearchParams) {
		const stored = readDeskStateFromBrowserStorage(browser ? sessionStorage : null);
		const restored = restoreDeskStateFromStorage({
			params,
			stored,
			language,
			query,
			backendMode,
			translationMode,
			lookupTools
		});
		if (!restored) return false;

		theme = restored.theme ?? theme;
		lookupTools = restored.lookupTools;
		encounter = restored.encounter;
		visibleTools = restored.visibleTools;
		textLayers = restored.textLayers;
		expandedSections = restored.expandedSections;
		collapsedBranches = restored.collapsedBranches;
		loading = false;
		enrichingTranslations = false;
		errorMessage = '';
		enrichmentError = '';
		wordIndex = restored.wordIndex;
		wordIndexSections = restored.wordIndexSections;
		return Boolean(encounter);
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

	async function loadParadigm(candidate: ParadigmResolutionCandidate) {
		const key = paradigmCandidateKey(candidate);
		if (!candidate.paradigm_request || paradigmPayloads[key] || paradigmLoading[key]) return;

		paradigmLoading = { ...paradigmLoading, [key]: true };
		paradigmErrors = { ...paradigmErrors, [key]: '' };

		try {
			const { response, data } = await fetchPayload<ParadigmPayload>(paradigmRequestUrl(candidate));
			const payload = normalizeParadigmPayload(data);
			if (!response.ok || payload?.error) {
				throw new Error(payload?.error ?? uiCopy.errors.indexFailed);
			}
			if (!payload) throw new Error('Paradigm lookup did not return a table.');
			if (!paradigmPayloadHasForms(payload)) throw new Error(paradigmUnavailableMessage(payload));
			paradigmPayloads = { ...paradigmPayloads, [key]: payload };
		} catch (error) {
			paradigmErrors = {
				...paradigmErrors,
				[key]: error instanceof Error ? error.message : 'Paradigm lookup failed.'
			};
		} finally {
			paradigmLoading = { ...paradigmLoading, [key]: false };
		}
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
			routeIntent.shouldRestoreFromSession && restoreDeskStateFromSessionStorage(params);
		if (restoredFromSession) routeLoadRequested = false;

		routeStateReady = true;

		if (routeLoadRequested) {
			void runSearch();
		} else {
			queueRouteStateSync();
		}
	}

	function clearPendingRouteState() {
		pendingVisibleToolsFromRoute = null;
		pendingSourceLayersFromRoute = [];
		pendingExpandedSectionsFromRoute = [];
		pendingCollapsedBranchesFromRoute = [];
		pendingQueryFromRoute = '';
	}

	function clearEncounterState() {
		activeSearchId += 1;
		clearTranslationArrival();
		encounter = null;
		visibleTools = [];
		loading = false;
		enrichingTranslations = false;
		errorMessage = '';
		enrichmentError = '';
		textLayers = {};
		expandedSections = {};
		collapsedBranches = {};
		clearWordIndexState();
		clearParadigmState();
	}

	function clearWordIndexState() {
		wordIndexController.clearSearchState();
	}

	function clearParadigmState() {
		paradigmPayloads = {};
		paradigmLoading = {};
		paradigmErrors = {};
	}

	async function runSearch() {
		abortMotdRequest();
		clearTranslationArrival();
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
		clearParadigmState();
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
			triggerTranslationArrival,
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
			triggerTranslationArrival,
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

	function triggerTranslationArrival() {
		if (!browser) return;
		clearTranslationArrival();
		translationArrived = true;
		translationArrivalTimer = setTimeout(() => {
			translationArrived = false;
			translationArrivalTimer = null;
		}, 1800);
	}

	function clearTranslationArrival() {
		translationArrived = false;
		if (translationArrivalTimer) {
			clearTimeout(translationArrivalTimer);
			translationArrivalTimer = null;
		}
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
		activeSearchId += 1;
		query = '';
		encounter = null;
		visibleTools = [];
		errorMessage = '';
		enrichmentError = '';
		enrichingTranslations = false;
		textLayers = {};
		expandedSections = {};
		collapsedBranches = {};
		clearPendingRouteState();
	}

	function resetAppState() {
		abortMotdRequest();
		clearTranslationArrival();
		routeLoadRequested = false;
		routePrefillOnly = false;
		language = 'san';
		query = '';
		backendMode = 'cli';
		translationMode = 'auto';
		theme = 'manuscript';
		lookupTools = toolsForLanguage('san').map(({ id }) => id);
		motd = null;
		motdStale = false;
		motdError = '';
		motdLoading = false;
		motdRefreshing = false;
		wordIndexEarmarks = [];
		clearEncounterState();
		clearPendingRouteState();
		clearAppBrowserStorage();
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
		routeLoadRequested = false;
		routePrefillOnly = false;
		language = nextLanguage;
		query = '';
		lookupTools = toolsForLanguage(nextLanguage).map(({ id }) => id);
		visibleTools = [];
		encounter = null;
		errorMessage = '';
		enrichmentError = '';
		enrichingTranslations = false;
		activeSearchId += 1;
		textLayers = {};
		expandedSections = {};
		collapsedBranches = {};
		clearPendingRouteState();
	}

	function applyLiveResultFilter(nextTools: ToolId[]) {
		if (!encounter) return;
		visibleTools = returnedToolIds.filter((tool) => nextTools.includes(tool));
	}

	function toggleLookupTool(tool: ToolId) {
		routeLoadRequested = false;
		routePrefillOnly = false;
		let nextTools: ToolId[];

		if (lookupTools.includes(tool)) {
			if (lookupTools.length === 1) return;
			nextTools = lookupTools.filter((candidate) => candidate !== tool);
		} else {
			nextTools = [...lookupTools, tool];
		}

		lookupTools = nextTools;
		applyLiveResultFilter(nextTools);
	}

	function toggleVisibleTool(tool: ToolId) {
		if (visibleTools.includes(tool)) {
			if (visibleTools.length === 1) return;
			visibleTools = visibleTools.filter((candidate) => candidate !== tool);
		} else {
			visibleTools = [...visibleTools, tool];
		}
	}

	function showAllLookupTools() {
		routeLoadRequested = false;
		routePrefillOnly = false;
		lookupTools = availableTools.map(({ id }) => id);
		visibleTools = returnedToolIds;
	}

	function showAllReturnedTools() {
		visibleTools = returnedToolIds;
	}

	function toggleSectionExpansion(bucket: EncounterBucket) {
		const key = sectionExpansionKey(bucket);
		expandedSections = {
			...expandedSections,
			[key]: !expandedSections[key]
		};
	}

	function toggleBranchCollapse(bucket: EncounterBucket) {
		const key = sectionExpansionKey(bucket);
		collapsedBranches = {
			...collapsedBranches,
			[key]: !collapsedBranches[key]
		};
	}

	function setComponentTextLayer(component: EncounterComponent, layer: 'reader' | 'source') {
		textLayers = {
			...textLayers,
			...Object.fromEntries(
				component.evidence.meanings.map((meaning) => [componentMeaningKey(meaning), layer])
			)
		};
	}

	function toggleComponentMeaning(meaning: EncounterComponentMeaning) {
		const key = componentMeaningKey(meaning);
		expandedSections = {
			...expandedSections,
			[key]: !expandedSections[key]
		};
	}

	function setGroupTextLayer(group: BucketGroup, layer: 'reader' | 'source') {
		textLayers = {
			...textLayers,
			...Object.fromEntries(group.buckets.map((bucket) => [bucket.bucket_id, layer]))
		};
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

	function syncDeskActivityTimer(kind: DeskActivityKey, active: boolean) {
		if (active) {
			if (!deskLoadingTimers.isRunning(kind)) deskLoadingTimers.start(kind);
			return;
		}

		deskLoadingTimers.stop(kind);
	}

	$effect(() => {
		syncDeskActivityTimer('lookup', loading);
		syncDeskActivityTimer('translation', hasTranslationActivity);
		syncDeskActivityTimer('wordIndex', wordIndexLoading);
		syncDeskActivityTimer('wordIndexSections', wordIndexSectionsLoading);
		syncDeskActivityTimer('motd', motdLoading || motdRefreshing);
		syncDeskActivityTimer('paradigm', hasParadigmActivity);
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
			abortMotdRequest();
			clearTranslationArrival();
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
		onRefresh={() => void loadMotd(true)}
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
		onLoadParadigm={loadParadigm}
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
