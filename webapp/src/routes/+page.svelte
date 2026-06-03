<script lang="ts">
	import { browser } from '$app/environment';
	import { pushState, replaceState } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import {
		Bird,
		BookmarkCheck,
		BookOpen,
		Bug,
		Cat,
		Dog,
		Fish,
		Shell,
		Snail,
		Squirrel,
		ScrollText,
		Turtle
	} from 'lucide-svelte';
	import { buildComponentHeadwordDisplay, buildHeadwordDisplay } from '$lib/headword-display';
	import {
		createDeskLoadingTimers,
		deskActivityItems,
		type DeskActivityKey
	} from '$lib/desk-activity';
	import { fetchPayload } from '$lib/msgpack';
	import {
		currentDeskRouteKey,
		isClearDeskRouteState,
		readLanguageParam,
		readRouteList,
		readToolParams,
		routeMatchesEncounter,
		routeExplicitlyRequestsLoad,
		routePrefillOnlyRequested,
		routeShouldLoad,
		shouldLoadEncounterForRoute,
		shouldPersistDeskRouteListParam,
		shouldResetEncounterForRoute
	} from '$lib/desk-route';
	import { motdItemKeys } from '$lib/motd-cache';
	import {
		clearStorageKeys,
		readStoredDeskState as readStoredDeskStateFromStorage,
		readStoredMotd as readStoredMotdFromStorage,
		readStoredWordIndexEarmarks as readStoredWordIndexEarmarksFromStorage,
		saveStoredDeskState,
		saveStoredMotd,
		saveStoredWordIndexEarmarks,
		type StoredDeskState
	} from '$lib/desk-storage';
	import { normalizeParadigmPayload, type ParadigmPayload } from '$lib/paradigm';
	import {
		curateParadigmCandidates,
		paradigmPayloadHasForms,
		paradigmUnavailableMessage
	} from '$lib/paradigm-ui';
	import type { ParadigmResolutionCandidate } from '$lib/paradigm-resolution';
	import { paradigmCandidateKey, paradigmRequestUrl } from '$lib/desk-paradigm';
	import {
		isSingleWord,
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
	import {
		isCompactOutlinedDictionaryText,
		isOutlinedDictionaryHeading,
		isOutlinedDictionaryTool,
		sourceOutlineDepth
	} from '$lib/source-outline';
	import { uiCopy } from '$lib/ui-copy';
	import { wordIndexCandidateQueries } from '$lib/word-index-fallbacks';
	import {
		wordIndexActiveSection,
		wordIndexAvailableSections,
		wordIndexBrowseGroups,
		wordIndexBrowseItems,
		wordIndexDisplayOrderLabel,
		wordIndexItemEntryCount,
		wordIndexItemLookupTarget,
		wordIndexSectionLookupTarget
	} from '$lib/word-index';
	import DeskHeroSearch from '$lib/DeskHeroSearch.svelte';
	import DeskMotdFolio from '$lib/DeskMotdFolio.svelte';
	import DeskLookupResults from '$lib/DeskLookupResults.svelte';
	import DeskPageShell from '$lib/DeskPageShell.svelte';
	import DeskSidebar from '$lib/DeskSidebar.svelte';
	import DeskTopbar from '$lib/DeskTopbar.svelte';
	import type {
		WordIndexItem,
		WordIndexNeighborhoodGroup,
		WordIndexResponse,
		WordIndexSection,
		WordIndexSectionsResponse
	} from '$lib/word-index';
	import DeskActivityLedger from '$lib/DeskActivityLedger.svelte';

	const toolStyle: Record<ToolId, { accent: string; badge: string }> = {
		cdsl: { accent: 'border-l-secondary', badge: 'badge-secondary' },
		heritage: { accent: 'border-l-accent', badge: 'badge-accent' },
		dico: { accent: 'border-l-success', badge: 'badge-success' },
		diogenes: { accent: 'border-l-info', badge: 'badge-info' },
		bailly: { accent: 'border-l-success', badge: 'badge-success' },
		strongs_greek: { accent: 'border-l-warning', badge: 'badge-warning' },
		cts_index: { accent: 'border-l-accent', badge: 'badge-accent' },
		spacy: { accent: 'border-l-neutral', badge: 'badge-neutral' },
		cltk: { accent: 'border-l-success', badge: 'badge-success' },
		whitakers: { accent: 'border-l-secondary', badge: 'badge-secondary' },
		gaffiot: { accent: 'border-l-accent', badge: 'badge-accent' },
		lewis_1890: { accent: 'border-l-info', badge: 'badge-info' }
	};

	const simulatedLookupDelayMs = 900;
	const motdSkeletonRows = [0, 1, 2];
	const motdStorageKey = 'orion-motd-cache:v5';
	const deskStorageKey = 'orion-desk-state:v5';
	const deskStorageTtlMs = 2 * 60 * 60 * 1000;
	const wordIndexStorageKey = 'orion-word-index-earmarks:v1';
	const wordIndexRadius = 5;
	const validTranslationModes = new Set<TranslationMode>([
		'off',
		'cache',
		'populate',
		'auto',
		'do-it-all'
	]);
	const validBackends = new Set<SearchBackend>(['sample', 'cli']);
	const validThemes = new Set(['manuscript', 'vespers']);

	type BucketGroup = {
		id: string;
		toolId: ToolId;
		dictionary: string;
		lexeme: string;
		buckets: EncounterBucket[];
		witnessCount: number;
		sourceRefCount: number;
		reasons: string[];
	};

	type Mnemonic = {
		Icon: typeof Bird;
		name: string;
	};

	type WordIndexRow = {
		item: WordIndexItem;
		position: 'before' | 'anchor' | 'after';
	};

	type WordIndexMergedPosition = WordIndexRow['position'] | 'nearby' | 'browse';

	type WordIndexMergedRow = {
		key: string;
		items: WordIndexItem[];
		positions: WordIndexMergedPosition[];
		sortKey: string;
	};

	type LooseWordRecommendationItem = Partial<WordRecommendationItem> & {
		canonical_name?: string;
		canonical?: {
			name?: string;
			display?: string;
			script?: string;
			transliteration?: string;
			roman?: string;
			iast?: string;
		};
		display_forms?: Partial<WordRecommendationItem['display_forms']> & {
			devanagari?: string;
			greek?: string;
			iast?: string;
			transliteration?: string;
		};
		forms?: Partial<WordRecommendationItem['display_forms']> & {
			devanagari?: string;
			greek?: string;
			iast?: string;
			transliteration?: string;
		};
	};

	let theme = $state<'manuscript' | 'vespers'>('manuscript');
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
	const initialMotd = readStoredMotd();
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
	let wordIndexEarmarks = $state<WordIndexItem[]>(readStoredWordIndexEarmarks());
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
	let visibleBucketGroups = $derived(groupBuckets(visibleBuckets));
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
	let motdVisibleWarnings = $derived(
		motd?.warnings.filter((warning) => shouldShowMotdWarning(warning.message)) ?? []
	);
	let currentWordIndex = $derived(wordIndexMatchesQuery() ? wordIndex : null);
	let wordIndexGroups = $derived(currentWordIndex?.neighborhood?.groups ?? []);
	let wordIndexBrowseGroupItems = $derived(wordIndexBrowseGroups(currentWordIndex));
	let wordIndexMergedRows = $derived(mergedWordIndexRowsFromResponse(currentWordIndex));
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
		componentHeadwordDisplay,
		componentLookupLine,
		componentCanSwitchTextLayer,
		componentLayerIsSource,
		setComponentTextLayer,
		componentSourceLayerLabel,
		componentHasTranslationToggle,
		componentAwaitsReaderTranslation,
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
		groupHeadwordDisplay,
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
		groupAwaitsReaderTranslation,
		retryableGroupTranslation,
		groupTranslationRetrying,
		retryGroupTranslation,
		visibleGroupBuckets,
		sectionSegments,
		sectionHasTreeChildren,
		sectionId,
		readerSectionClass,
		readerSectionStyle,
		branchToggleLabel,
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
		void loadWordIndexSections(language);
	});

	$effect(() => {
		if (!browser || !routeStateReady) return;
		if (motdLoading || motdRefreshing || motdError) return;
		if (motdStale && motdItems.length) void loadMotd(false);
		if (!motdItems.length) void loadMotd(false);
	});

	function endpointUrl(translationOverride: TranslationMode = translationMode) {
		const params = new URLSearchParams();
		params.set('language', language);

		if (query.trim()) {
			params.set('q', query.trim());
		}

		params.set('backend', backendMode);
		if (backendMode === 'cli') {
			params.set('translation', translationOverride);
			params.set('max_buckets', '54321');
			params.set('max_gloss_chars', '54321');
			params.set('source_layer_version', '3');
		}

		if (isAllLookupSelected) {
			params.set('dictionary', 'all');
		} else {
			for (const tool of lookupTools) {
				params.append('dictionary', tool);
			}
		}

		return `/api/search?${params.toString()}`;
	}

	function wordIndexEndpointUrl(targetQuery = query.trim(), targetLanguage = language) {
		const params = new URLSearchParams({
			mode: 'nearby',
			language: targetLanguage,
			q: targetQuery,
			source: 'all',
			radius: String(wordIndexRadius)
		});

		return `/api/word-index?${params.toString()}`;
	}

	function wordIndexSectionsEndpointUrl(targetLanguage = language) {
		const params = new URLSearchParams({
			mode: 'sections',
			language: targetLanguage,
			source: 'all'
		});

		return `/api/word-index?${params.toString()}`;
	}

	function wordIndexBrowseEndpointUrl(prefix: string, targetLanguage = language) {
		const params = new URLSearchParams({
			mode: 'browse',
			language: targetLanguage,
			prefix,
			source: 'all',
			count: '12'
		});

		return `/api/word-index?${params.toString()}`;
	}

	async function loadWordIndexSections(targetLanguage = language) {
		if (wordIndexSections?.request.language === targetLanguage) return;

		wordIndexSectionsLoading = true;
		wordIndexSectionsError = '';

		try {
			const { response, data } = await fetchPayload<WordIndexSectionsResponse>(
				wordIndexSectionsEndpointUrl(targetLanguage)
			);

			if (!response.ok) {
				throw new Error(data.error ?? uiCopy.errors.indexFailed);
			}

			if (targetLanguage !== language) return;
			wordIndexSections = data;
		} catch (error) {
			if (targetLanguage !== language) return;
			wordIndexSections = null;
			wordIndexSectionsError = error instanceof Error ? error.message : uiCopy.errors.indexFailed;
		} finally {
			if (targetLanguage === language) {
				wordIndexSectionsLoading = false;
			}
		}
	}

	async function loadNearbyWordIndex(
		targetQuery = query.trim(),
		targetLanguage = language,
		fallbackQueries: string[] = []
	) {
		const candidates = dedupeStrings([targetQuery, ...fallbackQueries])
			.map((candidate) => candidate.trim())
			.filter((candidate) => candidate && isSingleWord(candidate));
		const word = candidates[0] ?? '';
		const requestId = ++wordIndexRequestId;

		if (!word) {
			wordIndex = null;
			wordIndexLoading = false;
			wordIndexError = '';
			return;
		}

		wordIndexLoading = true;
		wordIndexError = '';

		try {
			let data: WordIndexResponse | null = null;

			for (const candidate of candidates) {
				const result = await fetchPayload<WordIndexResponse>(
					wordIndexEndpointUrl(candidate, targetLanguage)
				);
				const { response } = result;
				data = result.data;

				if (!response.ok) {
					throw new Error(data.error ?? uiCopy.errors.indexFailed);
				}

				if (requestId !== wordIndexRequestId) return;
				if (wordIndexResponseHasRows(data) || candidate === candidates[candidates.length - 1]) {
					break;
				}
			}

			if (requestId !== wordIndexRequestId) return;
			wordIndex = data;
		} catch (error) {
			if (requestId !== wordIndexRequestId) return;
			wordIndex = null;
			wordIndexError = error instanceof Error ? error.message : uiCopy.errors.indexFailed;
		} finally {
			if (requestId === wordIndexRequestId) {
				wordIndexLoading = false;
			}
		}
	}

	async function loadBrowseWordIndex(prefix: string, targetLanguage = language) {
		const normalizedPrefix = prefix.trim();
		const requestId = ++wordIndexRequestId;

		if (!normalizedPrefix) {
			wordIndex = null;
			wordIndexLoading = false;
			wordIndexError = '';
			return;
		}

		wordIndexLoading = true;
		wordIndexError = '';

		try {
			const { response, data } = await fetchPayload<WordIndexResponse>(
				wordIndexBrowseEndpointUrl(normalizedPrefix, targetLanguage)
			);

			if (!response.ok) {
				throw new Error(data.error ?? uiCopy.errors.indexFailed);
			}

			if (requestId !== wordIndexRequestId) return;
			wordIndex = data;
		} catch (error) {
			if (requestId !== wordIndexRequestId) return;
			wordIndex = null;
			wordIndexError = error instanceof Error ? error.message : uiCopy.errors.indexFailed;
		} finally {
			if (requestId === wordIndexRequestId) {
				wordIndexLoading = false;
			}
		}
	}

	function wordIndexResponseHasRows(result: WordIndexResponse | null) {
		if (!result) return false;
		if (wordIndexBrowseItems(result).length) return true;
		if (wordIndexBrowseGroups(result).some((group) => group.items.length)) return true;
		if (result.neighborhood?.items?.length) return true;
		if (result.neighborhood?.anchor) return true;
		return (result.neighborhood?.groups ?? []).some(
			(group) => group.anchor || group.before.length || group.after.length
		);
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

	function readStoredMotd(): { result: WordRecommendationResult | null; stale: boolean } {
		if (!browser) return { result: null, stale: false };
		return readStoredMotdFromStorage(localStorage, motdStorageKey, normalizeMotdResult);
	}

	function saveMotdToLocalStorage(result: WordRecommendationResult) {
		if (!browser) return;
		saveStoredMotd(localStorage, motdStorageKey, result);
	}

	function readStoredWordIndexEarmarks() {
		if (!browser) return [];
		return readStoredWordIndexEarmarksFromStorage(localStorage, wordIndexStorageKey);
	}

	function saveWordIndexEarmarks() {
		if (!browser) return;
		saveStoredWordIndexEarmarks(localStorage, wordIndexStorageKey, wordIndexEarmarks);
	}

	function readStoredDeskState() {
		if (!browser) return null;
		return readStoredDeskStateFromStorage(sessionStorage, deskStorageKey);
	}

	function saveDeskStateToSessionStorage() {
		if (!browser) return;

		if (!query.trim() && !encounter) {
			clearStoredDeskState();
			return;
		}

		const stored: StoredDeskState = {
			version: 5,
			expiresAt: Date.now() + deskStorageTtlMs,
			routeKey: currentRouteKey(),
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
		};

		saveStoredDeskState(sessionStorage, deskStorageKey, stored);
	}

	function clearStoredDeskState() {
		if (!browser) return;
		clearStorageKeys(sessionStorage, [
			deskStorageKey,
			'orion-desk-state:v4',
			'orion-desk-state:v3',
			'orion-desk-state:v2',
			'orion-desk-state:v1'
		]);
	}

	function clearStoredMotdState() {
		if (!browser) return;
		clearStorageKeys(localStorage, [
			motdStorageKey,
			'orion-motd-cache:v4',
			'orion-motd-cache:v3',
			'orion-motd-cache:v2',
			'orion-motd-cache:v1'
		]);
	}

	function clearStoredWordIndexState() {
		if (!browser) return;
		clearStorageKeys(localStorage, [wordIndexStorageKey]);
	}

	function clearStoredThemeState() {
		if (!browser) return;

		try {
			localStorage.removeItem('orion-theme');
			document.documentElement.dataset.theme = 'manuscript';
		} catch {
			// Ignore storage failures.
		}
	}

	function clearAppBrowserStorage() {
		clearStoredDeskState();
		clearStoredMotdState();
		clearStoredWordIndexState();
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
		const stored = readStoredDeskState();
		if (!stored?.query || !params.has('q')) return false;
		if (stored.routeKey && stored.routeKey !== currentRouteKey()) return false;
		if (stored.language !== language) return false;
		if (stored.query.trim().toLowerCase() !== query.trim().toLowerCase()) return false;
		if (stored.backendMode && stored.backendMode !== backendMode) return false;
		if (stored.translationMode && stored.translationMode !== translationMode) return false;

		theme = stored.theme === 'vespers' || stored.theme === 'manuscript' ? stored.theme : theme;
		lookupTools = validStoredTools(stored.lookupTools, language) || lookupTools;
		encounter =
			encounterMatchesStoredRoute(stored.encounter) &&
			stored.encounter &&
			!encounterNeedsFreshReaderLayer(stored.encounter)
				? stored.encounter
				: null;
		visibleTools = encounter
			? validStoredTools(stored.visibleTools, language) || returnedToolsForEncounter(encounter)
			: [];
		textLayers = stored.textLayers ?? {};
		expandedSections = stored.expandedSections ?? {};
		collapsedBranches = stored.collapsedBranches ?? {};
		loading = false;
		enrichingTranslations = false;
		errorMessage = '';
		enrichmentError = '';
		wordIndex = stored.wordIndex?.request.language === language ? stored.wordIndex : null;
		wordIndexSections =
			stored.wordIndexSections?.request.language === language ? stored.wordIndexSections : null;
		return Boolean(encounter);
	}

	function encounterNeedsFreshReaderLayer(result: EncounterResult) {
		const after = result.translation_cache?.after;
		if ((after?.missing ?? 0) > 0 || (after?.errors ?? 0) > 0 || (after?.empty ?? 0) > 0) {
			return true;
		}

		return hasMissingSourceReaderTranslations(result) || hasStaleTranslatedSourceLayer(result);
	}

	function hasStaleTranslatedSourceLayer(result: EncounterResult) {
		return result.buckets.some((bucket) => {
			const translation = bucket.translation;
			if (!translation?.available) return false;
			if (translation.source_lang !== 'fr') return false;
			if (!isTranslatedSourceTool(translation.source_tool)) return false;
			return sourceLayerLooksLikeReaderEnglish(translation.source_text, translation.target_text);
		});
	}

	function sourceLayerLooksLikeReaderEnglish(sourceText: string, targetText: string) {
		const source = sourceText.replace(/\s+/g, ' ').trim().toLowerCase();
		const target = targetText.replace(/\s+/g, ' ').trim().toLowerCase();
		if (!source || !target) return true;
		if (source === target) return true;
		return source.length > 80 && target.length > 80 && source.slice(0, 80) === target.slice(0, 80);
	}

	function encounterMatchesStoredRoute(storedEncounter: EncounterResult | null | undefined) {
		return Boolean(
			storedEncounter &&
			storedEncounter.language === language &&
			storedEncounter.query.trim().toLowerCase() === query.trim().toLowerCase()
		);
	}

	function validStoredTools(values: ToolId[] | undefined, mode: LanguageMode) {
		if (!values?.length) return null;
		const validToolSet = new Set(toolsForLanguage(mode).map(({ id }) => id));
		const parsed = values.filter((tool): tool is ToolId => validToolSet.has(tool));
		return parsed.length ? [...new Set(parsed)] : null;
	}

	function returnedToolsForEncounter(result: EncounterResult) {
		return [
			...new Set([
				...result.source_tools,
				...result.buckets.flatMap((bucket) => bucket.source_tools)
			])
		];
	}

	function normalizeMotdResult(result: WordRecommendationResult): WordRecommendationResult {
		return {
			schema_version: result.schema_version || 'langnet.word_of_day.v1',
			generated_at: result.generated_at || new Date().toISOString(),
			suggested_ttl_seconds: result.suggested_ttl_seconds || 3600,
			items: Array.isArray(result.items)
				? result.items.map((item) => normalizeMotdItem(item)).filter(isPresentableMotdItem)
				: [],
			exhaustion: result.exhaustion,
			warnings: Array.isArray(result.warnings) ? result.warnings : [],
			error: result.error
		};
	}

	function normalizeMotdItem(input: WordRecommendationItem): WordRecommendationItem {
		const item = input as LooseWordRecommendationItem;
		const language = item.language ?? 'san';
		const query = item.query || item.primary_lexeme || item.display || 'word';
		const canonical = item.canonical;
		const forms = item.display_forms ?? item.forms ?? {};
		const native =
			forms.native ||
			forms.devanagari ||
			forms.greek ||
			canonical?.name ||
			canonical?.display ||
			item.canonical_name ||
			item.display ||
			query;
		const roman =
			forms.roman ||
			forms.iast ||
			forms.transliteration ||
			canonical?.transliteration ||
			canonical?.roman ||
			canonical?.iast ||
			item.display ||
			query;
		const canonicalDisplay =
			forms.canonical || canonical?.display || canonical?.name || item.canonical_name || native;

		return {
			language,
			query,
			key: item.key || `${language}:${query}`,
			display: item.display || query,
			primary_lexeme: item.primary_lexeme || query,
			lexeme_anchors: item.lexeme_anchors ?? [],
			summary: item.summary ?? '',
			learner_note: item.learner_note ?? '',
			mnemonic: item.mnemonic ?? '',
			difficulty: item.difficulty ?? 'beginner',
			confidence: item.confidence ?? 'unknown',
			ambiguity: {
				has_multiple_lexemes: Boolean(item.ambiguity?.has_multiple_lexemes),
				lexeme_count: item.ambiguity?.lexeme_count ?? 0,
				note: item.ambiguity?.note ?? ''
			},
			recommended_request: {
				language: item.recommended_request?.language ?? language,
				q: item.recommended_request?.q ?? query,
				dictionary: item.recommended_request?.dictionary ?? 'all',
				translation: item.recommended_request?.translation ?? 'auto',
				backend: item.recommended_request?.backend ?? 'cli'
			},
			source_basis: item.source_basis ?? [],
			display_forms: {
				native,
				roman,
				canonical: canonicalDisplay,
				script: forms.script || canonical?.script || ''
			},
			ui: {
				href_query: item.ui?.href_query ?? '',
				badge: item.ui?.badge ?? '',
				short_gloss: item.ui?.short_gloss ?? ''
			},
			novelty: item.novelty
		};
	}

	function motdHref(item: WordRecommendationItem) {
		const request = item.recommended_request;
		const params = new URLSearchParams({
			lang: request.language || item.language,
			q: request.q || item.query,
			dictionary: request.dictionary || 'all',
			translation: request.translation || 'auto'
		});
		params.set('backend', request.backend || 'cli');
		params.set('theme', theme);
		if (motdLinksLoad) {
			params.set('load', 'yes');
		} else {
			params.set('load', 'no');
		}
		return `/?${params.toString()}`;
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

	function isPresentableMotdItem(item: WordRecommendationItem) {
		return Boolean(
			(
				item.display ||
				item.query ||
				item.primary_lexeme ||
				item.ui?.short_gloss ||
				item.summary ||
				item.learner_note ||
				item.mnemonic
			).trim()
		);
	}

	function motdDisplayWord(item: WordRecommendationItem) {
		const display = item.display || item.query || item.primary_lexeme || 'word';
		const preferred = item.display_forms.native || item.display_forms.canonical || display;
		const cleaned =
			item.language === 'lat'
				? stripLatinMotdTags(preferred)
				: item.language === 'grc'
					? stripGreekMotdEncoding(preferred)
					: item.language === 'san'
						? stripSanskritMotdEncoding(preferred)
						: preferred;
		return cleaned.normalize('NFC');
	}

	function stripLatinMotdTags(value: string) {
		return value.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '').trim() || value;
	}

	function stripGreekMotdEncoding(value: string) {
		const cleaned = value
			.normalize('NFC')
			.replace(/_\d+\b/g, '')
			.replace(/[_]+/g, '')
			.replace(/(?:^|[\s([{])[-]+/g, (match) => match.replace(/-/g, ''))
			.replace(/[-]+(?=$|[\s)\]}])/g, '')
			.replace(/-/g, '')
			.replace(/\s+/g, ' ')
			.trim();

		return cleaned || value;
	}

	function motdWordClass(item: WordRecommendationItem) {
		if (item.language === 'grc') return 'orion-motd-word orion-motd-word-grc';
		if (item.language === 'san') return 'orion-motd-word orion-motd-word-san';
		return 'orion-motd-word';
	}

	function motdWordLang(item: WordRecommendationItem) {
		if (item.language === 'grc') return 'grc';
		if (item.language === 'san') {
			const script = item.display_forms.script.toLowerCase();
			if (script.includes('deva') || /[\u0900-\u097F]/u.test(motdDisplayWord(item)))
				return 'sa-Deva';
			return 'sa-Latn';
		}
		return 'la';
	}

	function motdDisplayLookup(item: WordRecommendationItem) {
		if (item.language !== 'grc' && item.language !== 'san') return '';
		const display = motdDisplayWord(item).toLowerCase();
		const lookup =
			item.language === 'grc'
				? greekMotdRomanLookup(item)
				: stripSanskritMotdEncoding(
						item.display_forms.roman || item.query || item.primary_lexeme || item.display
					);
		if (!lookup || lookup.toLowerCase() === display) return '';
		return lookup;
	}

	function greekMotdRomanLookup(item: WordRecommendationItem) {
		const provided = stripGreekMotdLookup(
			item.display_forms.roman || item.primary_lexeme || item.query || item.display
		);
		if (provided && !/[\u0370-\u03ff]/u.test(provided)) return provided;
		return transliterateGreekMotd(motdDisplayWord(item));
	}

	function stripGreekMotdLookup(value: string) {
		return stripGreekMotdEncoding(value).replace(/-/g, '').trim();
	}

	function transliterateGreekMotd(value: string) {
		const table: Record<string, string> = {
			α: 'a',
			β: 'b',
			γ: 'g',
			δ: 'd',
			ε: 'e',
			ζ: 'z',
			η: 'e',
			θ: 'th',
			ι: 'i',
			κ: 'k',
			λ: 'l',
			μ: 'm',
			ν: 'n',
			ξ: 'x',
			ο: 'o',
			π: 'p',
			ρ: 'r',
			σ: 's',
			ς: 's',
			τ: 't',
			υ: 'u',
			φ: 'ph',
			χ: 'ch',
			ψ: 'ps',
			ω: 'o'
		};
		const normalized = stripGreekMotdEncoding(value)
			.normalize('NFD')
			.replace(/[\u0300-\u036f]/g, '')
			.toLowerCase();
		return normalized
			.split('')
			.map((char) => table[char] ?? char)
			.join('')
			.replace(/\s+/g, ' ')
			.trim();
	}

	function stripSanskritMotdEncoding(value: string) {
		return value
			.normalize('NFC')
			.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '')
			.replace(/_\d+\b/g, '')
			.replace(/[_-]+/g, '')
			.replace(/\s+/g, ' ')
			.trim();
	}

	function motdDisplayGloss(item: WordRecommendationItem) {
		return (
			item.ui?.short_gloss || item.summary || item.learner_note || item.mnemonic || 'Learner word.'
		);
	}

	function motdDisplayNote(item: WordRecommendationItem) {
		const note = item.mnemonic || item.ui?.short_gloss || item.summary || item.learner_note || '';
		return note
			.replace(/^Query\s+`[^`]+`\s+is backed by source evidence for\s+[^.]+\.?\s*/i, '')
			.replace(/^Query\s+`[^`]+`\s+opens\s+[^,]+,\s*/i, '')
			.trim();
	}

	function wordIndexRows(group: WordIndexNeighborhoodGroup): WordIndexRow[] {
		return [
			...group.before.map((item) => ({ item, position: 'before' as const })),
			...(group.anchor ? [{ item: group.anchor, position: 'anchor' as const }] : []),
			...group.after.map((item) => ({ item, position: 'after' as const }))
		];
	}

	function mergeWordIndexRows(groups: WordIndexNeighborhoodGroup[]): WordIndexMergedRow[] {
		const merged = new Map<string, WordIndexMergedRow>();

		for (const row of groups.flatMap(wordIndexRows)) {
			const key = wordIndexMergeKey(row.item);
			const existing = merged.get(key);

			if (existing) {
				if (!existing.items.some((item) => wordIndexItemKey(item) === wordIndexItemKey(row.item))) {
					existing.items.push(row.item);
				}
				if (!existing.positions.includes(row.position)) existing.positions.push(row.position);
				if (wordIndexSortKey(row.item) < existing.sortKey)
					existing.sortKey = wordIndexSortKey(row.item);
			} else {
				merged.set(key, {
					key,
					items: [row.item],
					positions: [row.position],
					sortKey: wordIndexSortKey(row.item)
				});
			}
		}

		return [...merged.values()];
	}

	function mergedWordIndexRowsFromResponse(result: WordIndexResponse | null): WordIndexMergedRow[] {
		const browseRows = mergedWordIndexRowsFromBrowseItems(wordIndexBrowseItems(result));
		if (browseRows.length) return browseRows;

		const mergedItemRows = mergedWordIndexRowsFromItems(result?.neighborhood?.items ?? []);
		const groupedRows = mergeWordIndexRows(result?.neighborhood?.groups ?? []);

		if (preferMergedWordIndexItems(mergedItemRows, groupedRows)) return mergedItemRows;
		if (groupedRows.length) return groupedRows;
		if (mergedItemRows.length) return mergedItemRows;

		const anchor = result?.neighborhood?.anchor;
		if (!anchor) return [];

		return [
			{
				key: wordIndexMergeKey(anchor),
				items: [anchor],
				positions: ['anchor'],
				sortKey: wordIndexSortKey(anchor)
			}
		];
	}

	function mergedWordIndexRowsFromItems(items: WordIndexItem[]): WordIndexMergedRow[] {
		return items.map((item) => ({
			key: wordIndexMergeKey(item),
			items: [item],
			positions: [item.position ?? 'anchor'],
			sortKey: wordIndexSortKey(item)
		}));
	}

	function mergedWordIndexRowsFromBrowseItems(items: WordIndexItem[]): WordIndexMergedRow[] {
		return items.map((item) => ({
			key: `browse:${wordIndexItemKey(item)}`,
			items: [item],
			positions: ['browse' as const],
			sortKey: wordIndexSortKey(item)
		}));
	}

	function mergedWordIndexRowsFromBrowseGroups(
		groups: ReturnType<typeof wordIndexBrowseGroups>
	): WordIndexMergedRow[] {
		return groups.flatMap((group) =>
			group.items.map((item) => ({
				key: `${group.source}:${group.dictionary}:${wordIndexItemKey(item)}`,
				items: [item],
				positions: ['browse' as const],
				sortKey: wordIndexSortKey(item)
			}))
		);
	}

	function preferMergedWordIndexItems(
		mergedItemRows: WordIndexMergedRow[],
		groupedRows: WordIndexMergedRow[]
	) {
		if (!mergedItemRows.length) return false;
		if (!groupedRows.length) return true;

		const mergedBefore = mergedItemRows.filter((row) => row.positions.includes('before')).length;
		const groupedBefore = groupedRows.filter((row) => row.positions.includes('before')).length;
		const mergedHasAnchor = mergedItemRows.some((row) => row.positions.includes('anchor'));
		const groupedHasAnchor = groupedRows.some((row) => row.positions.includes('anchor'));
		const mergedHasAfter = mergedItemRows.some((row) => row.positions.includes('after'));

		return mergedHasAnchor && mergedHasAfter && (!groupedHasAnchor || mergedBefore > groupedBefore);
	}

	function wordIndexMergeKey(item: WordIndexItem) {
		return (
			item.wheel_id ||
			item.lexeme_id ||
			`${item.language}:${item.canonical_key || item.lookup || item.encounter.q}`
		);
	}

	function wordIndexSortKey(item: WordIndexItem) {
		return item.wheel_order_key || item.canonical_key || item.lookup || item.encounter.q;
	}

	function wordIndexPrimaryItem(row: WordIndexMergedRow) {
		return (
			row.items.find((item) => item.encounter.dictionary === 'all') ??
			row.items.find((item) => isTranslatedSourceTool(sourceToolFromWordIndex(item.source))) ??
			row.items[0]
		);
	}

	function wordIndexHref(item: WordIndexItem, includeLoad = false) {
		const target = wordIndexItemLookupTarget(item);
		const params = new URLSearchParams({
			lang: target.language,
			q: target.query,
			translation: translationMode,
			theme
		});
		const validTools = new Set(toolsForLanguage(target.language).map(({ id }) => id));
		params.set(
			'dictionary',
			validTools.has(target.dictionary as ToolId) ? target.dictionary : 'all'
		);
		if (includeLoad) params.set('load', 'yes');
		return `/?${params.toString()}`;
	}

	function wordIndexSectionHref(section: WordIndexSection) {
		const target = wordIndexSectionLookupTarget(section);
		if (!target) return '';

		const params = new URLSearchParams({
			lang: target.language,
			q: target.query,
			translation: translationMode,
			theme,
			load: 'yes'
		});
		const validTools = new Set(toolsForLanguage(target.language).map(({ id }) => id));
		params.set(
			'dictionary',
			validTools.has(target.dictionary as ToolId) ? target.dictionary : 'all'
		);
		return `/?${params.toString()}`;
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
		void loadBrowseWordIndex(anchor.query, anchor.language);
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

	function wordIndexDisplay(item: WordIndexItem) {
		const display = item.display.primary || item.canonical_name || item.source_name;
		const cleanDisplay = stripSourceVariantNumber(display);
		const normalizedLookup = item.lookup || item.canonical_key || item.encounter.q;

		if (display !== cleanDisplay && normalizedLookup) return normalizedLookup.normalize('NFC');
		return (cleanDisplay || normalizedLookup).normalize('NFC');
	}

	function wordIndexLookup(item: WordIndexItem) {
		const display = wordIndexDisplay(item).toLowerCase();
		const lookup = item.display.transliteration || item.lookup || item.canonical_key;
		if (!lookup || lookup.toLowerCase() === display) return '';
		return lookup.normalize('NFC');
	}

	function wordIndexEntryCountLabel(item: WordIndexItem) {
		const count = wordIndexItemEntryCount(item);
		if (count <= 1) return '';
		return `${count} entries`;
	}

	function wordIndexRowSources(row: WordIndexMergedRow) {
		return [
			...new Set(
				row.items.flatMap((item) => {
					if (item.source_counts?.length) {
						return item.source_counts.map((source) =>
							source.count > 1
								? `${wordIndexSourceLabelFromParts(source)} ${source.count}`
								: wordIndexSourceLabelFromParts(source)
						);
					}
					if (item.sources?.length) {
						return item.sources.map((source) => wordIndexSourceLabelFromParts(source));
					}
					if (item.source_entries.length) {
						return item.source_entries.map((entry) => wordIndexSourceLabelFromParts(entry));
					}
					return [wordIndexSourceLabel(item)];
				})
			)
		];
	}

	function wordIndexSourceLabel(item: WordIndexItem) {
		return wordIndexSourceLabelFromParts({
			source: item.source,
			dictionary: item.dictionary,
			language: item.language
		});
	}

	function wordIndexSourceLabelFromParts({
		source,
		dictionary,
		language: sourceLanguage = language
	}: {
		source: string;
		dictionary: string;
		language?: LanguageMode;
	}) {
		const tool = toolMeta(sourceToolFromWordIndex(source), sourceLanguage);
		return dictionary && dictionary !== source
			? `${tool.shortLabel}/${dictionary}`
			: tool.shortLabel;
	}

	function wordIndexRowPosition(row: WordIndexMergedRow): WordIndexMergedPosition {
		const directPosition = row.items.find((item) => item.position)?.position;
		if (directPosition) return directPosition;
		if (row.positions.includes('anchor')) return 'anchor';
		if (row.positions.includes('before') && row.positions.includes('after')) return 'nearby';
		return row.positions[0] ?? 'anchor';
	}

	function wordIndexRowMatched(row: WordIndexMergedRow) {
		if (row.items.some((item) => item.match)) return true;

		const queryKeys = queryEquivalentKeys(query);
		for (const key of wordIndexEncounterMatchKeys) queryKeys.add(key);
		if (!queryKeys.size) return false;

		return row.items.some((item) =>
			wordIndexItemLexemeKeys(item).some((key) => queryKeys.has(key))
		);
	}

	function encounterWordIndexMatchKeys(result: EncounterResult | null) {
		const keys = new Set<string>();
		if (!result) return keys;

		for (const anchor of result.lexeme_anchors) addWordIndexMatchKey(keys, anchor);
		for (const bucket of result.buckets) {
			for (const lemma of bucket.bucket_lemmas) addWordIndexMatchKey(keys, lemma);
			for (const witness of bucket.witnesses) {
				addWordIndexMatchKey(keys, witness.headword);
				addWordIndexMatchKey(keys, witness.lexeme_anchor);
			}
		}

		return keys;
	}

	function queryEquivalentKeys(value: string) {
		const keys = new Set<string>();
		addWordIndexMatchKey(keys, value);
		return keys;
	}

	function wordIndexItemLexemeKeys(item: WordIndexItem) {
		const keys = new Set<string>();
		addWordIndexMatchKey(keys, item.lookup);
		addWordIndexMatchKey(keys, item.canonical_key);
		addWordIndexMatchKey(keys, item.canonical_name);
		addWordIndexMatchKey(keys, item.source_name);
		addWordIndexMatchKey(keys, item.display.primary);
		addWordIndexMatchKey(keys, item.display.transliteration);
		addWordIndexMatchKey(keys, item.encounter.q);
		for (const entry of item.source_entries) {
			addWordIndexMatchKey(keys, entry.source_name);
			addWordIndexMatchKey(keys, entry.source_display);
		}
		return [...keys];
	}

	function addWordIndexMatchKey(keys: Set<string>, value: string | undefined) {
		const key = strictStudyKey(value);
		if (key) keys.add(key);
		const sanskritKey = sanskritSourceStudyKey(value);
		if (sanskritKey) keys.add(sanskritKey);
	}

	function strictStudyKey(value: string | undefined) {
		return (value ?? '')
			.replace(/^lex:/, '')
			.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '')
			.normalize('NFC')
			.toLowerCase()
			.replace(/[^a-z0-9.\-āīūṛṝḷḹṃḥṅñṭḍṇśṣ\u0370-\u03ff\u0900-\u097f]+/gu, '')
			.trim();
	}

	function sanskritSourceStudyKey(value: string | undefined) {
		return strictStudyKey(value)
			.replace(/\.n/g, 'ṇ')
			.replace(/\.s/g, 'ṣ')
			.replace(/aa/g, 'ā')
			.replace(/ii/g, 'ī')
			.replace(/uu/g, 'ū')
			.replace(/[^a-z0-9āīūṛṝḷḹṃḥṅñṭḍṇśṣ\u0900-\u097f]+/gu, '')
			.trim();
	}

	function stripSourceVariantNumber(value: string) {
		return value.replace(/^\s*\d+\s+/u, '').trim();
	}

	function wordIndexMatchesQuery() {
		if (!wordIndex) return false;
		return wordIndex.request.language === language;
	}

	function wordIndexItemKey(item: WordIndexItem) {
		return (
			item.ids.index_entry ||
			item.index_entry_id ||
			item.source_ref ||
			`${item.language}:${item.source}:${item.dictionary}:${item.lookup || item.encounter.q}`
		);
	}

	function isEarmarked(item: WordIndexItem) {
		const key = wordIndexItemKey(item);
		return wordIndexEarmarks.some((earmark) => wordIndexItemKey(earmark) === key);
	}

	function toggleWordIndexEarmark(item: WordIndexItem) {
		const key = wordIndexItemKey(item);

		if (isEarmarked(item)) {
			wordIndexEarmarks = wordIndexEarmarks.filter((earmark) => wordIndexItemKey(earmark) !== key);
			return;
		}

		wordIndexEarmarks = [item, ...wordIndexEarmarks].slice(0, 18);
	}

	function clearWordIndexEarmarks() {
		wordIndexEarmarks = [];
	}

	function sourceToolFromWordIndex(source: string): ToolId {
		if (source === 'gaffiot') return 'gaffiot';
		if (source === 'lewis_1890') return 'lewis_1890';
		if (source === 'bailly') return 'bailly';
		if (source === 'dico') return 'dico';
		if (source === 'cdsl') return 'cdsl';
		if (source === 'heritage') return 'heritage';
		if (source === 'whitakers') return 'whitakers';
		if (source === 'cltk') return 'cltk';
		if (source === 'spacy') return 'spacy';
		if (source === 'cts_index') return 'cts_index';
		return 'diogenes';
	}

	function shouldShowMotdWarning(message: string) {
		if (!motdItems.length) return true;
		return !isRecoverableMotdWarning(message);
	}

	function isRecoverableMotdWarning(message: string) {
		return (
			/encounter returned no usable source-backed buckets/i.test(message) ||
			/LLM card finalization unavailable/i.test(message) ||
			/Precomputed learner pool fell back to curated words/i.test(message) ||
			/Precomputed learner pool returned no cards/i.test(message) ||
			/MOTD pool database does not exist/i.test(message) ||
			/live LLM recommendations warm in the background/i.test(message)
		);
	}

	function appRouteUrl(includeLoad = false) {
		if (isClearRouteState(includeLoad)) return '/';

		const routeHasMatchingEncounter = encounterMatchesQuery();
		const params = new URLSearchParams();
		params.set('lang', language);
		if (query.trim()) params.set('q', query.trim());
		params.set('backend', backendMode);
		params.set('translation', translationMode);
		params.set('theme', theme);
		if (includeLoad && query.trim()) params.set('load', 'yes');
		if (!includeLoad && routePrefillOnly && query.trim() && !encounter) params.set('load', 'no');

		if (isAllLookupSelected) {
			params.set('dictionary', 'all');
		} else {
			for (const tool of lookupTools) params.append('dictionary', tool);
		}

		if (
			routeHasMatchingEncounter &&
			visibleTools.length &&
			visibleTools.length !== returnedToolIds.length
		) {
			for (const tool of visibleTools) params.append('visible', tool);
		} else if (!encounter && pendingVisibleToolsFromRoute?.length) {
			for (const tool of pendingVisibleToolsFromRoute) params.append('visible', tool);
		}

		const sourceLayerIds = new Set(!encounter ? pendingSourceLayersFromRoute : []);
		if (routeHasMatchingEncounter) {
			for (const [bucketId, layer] of Object.entries(textLayers)) {
				if (layer === 'source') sourceLayerIds.add(bucketId);
			}
		}
		for (const bucketId of sourceLayerIds) params.append('source', bucketId);

		const queryString = params.toString();
		return queryString ? `/?${queryString}` : '/';
	}

	function isClearRouteState(includeLoad = false) {
		return isClearDeskRouteState({
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
			pendingCollapsedBranches: pendingCollapsedBranchesFromRoute
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
		const nextLanguage = readLanguageParam(params) ?? language;
		const nextQuery = params.get('q') ?? '';
		const validTools = toolsForLanguage(nextLanguage).map(({ id }) => id);
		const requestedTools = readToolParams(params, 'dictionary', validTools);
		const requestedVisibleTools = readToolParams(params, 'visible', validTools);
		const requestedTheme = params.get('theme');
		const requestedBackend = params.get('backend');
		const requestedTranslation = params.get('translation');
		const shouldPrefillOnly = routePrefillOnlyRequested(params);
		const shouldLoad = routeShouldLoad(params);

		const routeMatchesCurrentEncounter = routeMatchesEncounter(encounter, nextLanguage, nextQuery);
		const shouldResetEncounter = shouldResetEncounterForRoute({
			currentLanguage: language,
			currentQuery: query,
			nextLanguage,
			nextQuery
		});
		const shouldPreserveEncounter = routeMatchesCurrentEncounter && !shouldResetEncounter;

		if (shouldResetEncounter) {
			clearEncounterState();
		}

		language = nextLanguage;
		query = nextQuery;
		routePrefillOnly = shouldPrefillOnly;
		routeLoadRequested = shouldLoadEncounterForRoute({
			routeWantsLoad: shouldLoad,
			routeExplicitlyRequestsLoad: routeExplicitlyRequestsLoad(params),
			hasLoadableQuery: Boolean(query.trim()) && isSingleWord(query.trim()),
			routeMatchesCurrentEncounter
		});
		lookupTools = requestedTools?.length ? requestedTools : validTools;
		const routeVisibleTools = requestedVisibleTools ?? [];
		const routeSourceLayers = readRouteList(params, 'source');
		const routeExpandedSections = shouldPersistDeskRouteListParam('expand')
			? readRouteList(params, 'expand')
			: [];
		const routeCollapsedBranches = shouldPersistDeskRouteListParam('collapse')
			? readRouteList(params, 'collapse')
			: [];

		if (shouldPreserveEncounter && encounter) {
			const returnedTools = returnedToolsForEncounter(encounter);
			visibleTools = routeVisibleTools.length
				? routeVisibleTools.filter((tool) => returnedTools.includes(tool))
				: visibleTools.length
					? visibleTools
					: returnedTools;
			textLayers = Object.fromEntries(routeSourceLayers.map((bucketId) => [bucketId, 'source']));
			expandedSections = Object.fromEntries(routeExpandedSections.map((key) => [key, true]));
			collapsedBranches = Object.fromEntries(routeCollapsedBranches.map((key) => [key, true]));
			pendingVisibleToolsFromRoute = null;
			pendingSourceLayersFromRoute = [];
			pendingExpandedSectionsFromRoute = [];
			pendingCollapsedBranchesFromRoute = [];
		} else {
			visibleTools = [];
			pendingVisibleToolsFromRoute = requestedVisibleTools;
			pendingSourceLayersFromRoute = routeSourceLayers;
			pendingExpandedSectionsFromRoute = routeExpandedSections;
			pendingCollapsedBranchesFromRoute = routeCollapsedBranches;
		}
		pendingQueryFromRoute = query.trim();

		if (requestedTheme && validThemes.has(requestedTheme)) {
			theme = requestedTheme as 'manuscript' | 'vespers';
		}

		if (requestedBackend && validBackends.has(requestedBackend as SearchBackend)) {
			backendMode = requestedBackend as SearchBackend;
		}

		if (
			requestedTranslation &&
			validTranslationModes.has(requestedTranslation as TranslationMode)
		) {
			translationMode = requestedTranslation as TranslationMode;
		}

		const restoredFromSession =
			!routePrefillOnlyRequested(params) &&
			!routeExplicitlyRequestsLoad(params) &&
			restoreDeskStateFromSessionStorage(params);
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
		wordIndexRequestId += 1;
		wordIndex = null;
		wordIndexLoading = false;
		wordIndexError = '';
	}

	function clearParadigmState() {
		paradigmPayloads = {};
		paradigmLoading = {};
		paradigmErrors = {};
	}

	function delay(milliseconds: number) {
		return new Promise((resolve) => setTimeout(resolve, milliseconds));
	}

	async function runSearch() {
		abortMotdRequest();
		clearTranslationArrival();
		routePrefillOnly = false;
		const word = query.trim();
		const manualQueryChanged = pendingQueryFromRoute && pendingQueryFromRoute !== word;
		let renderedSearch = false;
		let wordIndexSearchStarted = false;

		if (!word) {
			activeSearchId += 1;
			routeLoadRequested = false;
			errorMessage = uiCopy.errors.enterOneWord;
			encounter = null;
			visibleTools = [];
			enrichingTranslations = false;
			collapsedBranches = {};
			clearWordIndexState();
			return;
		}

		if (!isSingleWord(word)) {
			activeSearchId += 1;
			routeLoadRequested = false;
			errorMessage = uiCopy.errors.oneWordOnly;
			encounter = null;
			visibleTools = [];
			enrichingTranslations = false;
			collapsedBranches = {};
			clearWordIndexState();
			return;
		}

		if (manualQueryChanged) {
			clearPendingRouteState();
		}

		wordIndexRequestId += 1;
		wordIndex = null;
		wordIndexError = '';
		wordIndexLoading = true;

		loading = true;
		routeLoadRequested = false;
		enrichingTranslations = false;
		errorMessage = '';
		enrichmentError = '';
		const searchId = (activeSearchId += 1);
		const requestedTranslationMode = translationMode;
		const firstPassTranslationMode = shouldProgressivelyEnrich(requestedTranslationMode)
			? 'cache'
			: requestedTranslationMode;

		try {
			const data = await fetchEncounter(firstPassTranslationMode);
			if (searchId !== activeSearchId) return;

			applyEncounter(data, true);
			const indexCandidates = wordIndexCandidateQueries(data, word);
			void loadNearbyWordIndex(indexCandidates[0] ?? word, language, indexCandidates.slice(1));
			wordIndexSearchStarted = true;
			renderedSearch = true;

			if (data.error) {
				errorMessage = uiCopy.errors.liveFallback(data.error);
			}

			if (
				shouldProgressivelyEnrich(requestedTranslationMode) &&
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
			void loadNearbyWordIndex(indexCandidates[0] ?? word, language, indexCandidates.slice(1));
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
		const [{ response, data }] = await Promise.all([
			fetchPayload<EncounterResult>(endpointUrl(mode)),
			delay(simulatedLookupDelayMs)
		]);

		if (!response.ok) {
			throw new Error(data.error ?? uiCopy.errors.searchFailed);
		}

		return data;
	}

	function applyEncounter(data: EncounterResult, resetReaderState: boolean) {
		const previousVisibleTools = visibleTools;
		const nextReturnedTools = [
			...new Set([...data.source_tools, ...data.buckets.flatMap((bucket) => bucket.source_tools)])
		];
		const routedVisibleTools = pendingVisibleToolsFromRoute
			? nextReturnedTools.filter((tool) => pendingVisibleToolsFromRoute?.includes(tool))
			: [];

		encounter = data;
		clearParadigmState();
		visibleTools = resetReaderState
			? routedVisibleTools.length
				? routedVisibleTools
				: nextReturnedTools
			: nextReturnedTools.filter((tool) => previousVisibleTools.includes(tool));

		if (!visibleTools.length) {
			visibleTools = nextReturnedTools;
		}

		if (resetReaderState) {
			textLayers = Object.fromEntries(
				data.buckets
					.filter((bucket) => pendingSourceLayersFromRoute.includes(bucket.bucket_id))
					.map((bucket) => [bucket.bucket_id, 'source' as const])
			);
			expandedSections = Object.fromEntries(
				data.buckets
					.map((bucket) => sectionExpansionKey(bucket))
					.filter((key) => pendingExpandedSectionsFromRoute.includes(key))
					.map((key) => [key, true])
			);
			collapsedBranches = Object.fromEntries(
				data.buckets
					.map((bucket) => sectionExpansionKey(bucket))
					.filter((key) => pendingCollapsedBranchesFromRoute.includes(key))
					.map((key) => [key, true])
			);
			pendingVisibleToolsFromRoute = null;
			pendingSourceLayersFromRoute = [];
			pendingExpandedSectionsFromRoute = [];
			pendingCollapsedBranchesFromRoute = [];
			pendingQueryFromRoute = '';
		}
	}

	async function enrichSearch(searchId: number, mode: TranslationMode) {
		enrichingTranslations = true;

		try {
			const data = await fetchEncounter(mode);
			if (searchId !== activeSearchId) return;
			applyEncounter(data, false);
			enrichmentError = '';
			await tick();
			if (searchId === activeSearchId) triggerTranslationArrival();
		} catch (error) {
			if (searchId !== activeSearchId) return;
			enrichmentError = error instanceof Error ? error.message : uiCopy.errors.translationFailed;
		} finally {
			if (searchId === activeSearchId) {
				enrichingTranslations = false;
			}
		}
	}

	async function retryGroupTranslation(group: BucketGroup) {
		const translation = retryableGroupTranslation(group);
		if (!translation) return;
		const retryKey = groupTranslationRetryKey(group);
		translationRetrying = { ...translationRetrying, [retryKey]: true };
		enrichmentError = '';

		try {
			const { response, data } = await fetchPayload<{ error?: string; limit_reached?: boolean }>(
				'/api/translation-cache',
				{
					method: 'POST',
					headers: { 'content-type': 'application/json' },
					body: JSON.stringify({
						translation_id: translation.translation_id,
						source_lexicon: translation.source_lexicon ?? translation.source_tool,
						entry_id: translation.entry_id,
						occurrence: translation.occurrence,
						headword_norm: translation.headword_norm,
						source_text_hash: translation.source_text_hash,
						max_retries: 3
					})
				}
			);
			if (!response.ok) {
				throw new Error(
					data.error ??
						(data.limit_reached
							? 'This translation has reached its retry limit.'
							: uiCopy.errors.translationFailed)
				);
			}
			const searchId = activeSearchId;
			const refreshed = await fetchEncounter('auto');
			if (searchId !== activeSearchId) return;
			applyEncounter(refreshed, false);
			await tick();
			triggerTranslationArrival();
		} catch (error) {
			enrichmentError = error instanceof Error ? error.message : uiCopy.errors.translationFailed;
		} finally {
			translationRetrying = { ...translationRetrying, [retryKey]: false };
		}
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

	function shouldProgressivelyEnrich(mode: TranslationMode) {
		return (
			backendMode === 'cli' && (mode === 'auto' || mode === 'populate' || mode === 'do-it-all')
		);
	}

	function hasMissingSourceReaderTranslations(result: EncounterResult) {
		const missingBucketTranslation = result.buckets.some((bucket) => {
			const translation = bucket.translation;
			if (!translation || translation.available) return false;
			if (translation.source_lang !== 'fr') return false;
			return isTranslatedSourceTool(translation.source_tool);
		});

		const missingComponentTranslation = result.components.some((component) =>
			component.evidence.meanings.some((meaning) => {
				const translation = meaning.translation;
				if (!translation || translation.available) return false;
				if (translation.source_lang !== 'fr') return false;
				return isTranslatedSourceTool(translation.source_tool);
			})
		);

		return missingBucketTranslation || missingComponentTranslation;
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

	function primaryTool(bucket: EncounterBucket): ToolId {
		return (
			bucket.translation?.source_tool ??
			bucket.witnesses[0]?.tool ??
			bucket.source_tools[0] ??
			'diogenes'
		);
	}

	function primaryLexeme(bucket: EncounterBucket) {
		return bucket.witnesses[0]?.headword ?? bucket.bucket_lemmas[0] ?? encounter?.query ?? query;
	}

	function primaryDictionary(bucket: EncounterBucket) {
		return bucket.witnesses[0]?.dictionary ?? primaryTool(bucket);
	}

	function groupHeadwordDisplay(group: BucketGroup) {
		return buildHeadwordDisplay({
			language: encounter?.language ?? language,
			lexeme: group.lexeme,
			source: group.toolId,
			dictionary: group.dictionary,
			groupValues: groupHeadwordValues(group),
			anchors: encounter?.word_index?.anchors ?? []
		});
	}

	function groupHeadwordValues(group: BucketGroup) {
		return [
			group.lexeme,
			...group.buckets.flatMap((bucket) => [
				...bucket.bucket_lemmas,
				...bucket.witnesses.flatMap((witness) => [witness.headword, witness.lexeme_anchor])
			])
		].filter((value): value is string => Boolean(value));
	}

	function groupBuckets(buckets: EncounterBucket[]): BucketGroup[] {
		const groups = new Map<string, BucketGroup>();

		for (const bucket of buckets) {
			const toolId = primaryTool(bucket);
			const dictionary = primaryDictionary(bucket);
			const lexeme = primaryLexeme(bucket);
			const id = `${toolId}:${dictionary}:${lexeme}`;
			const existing = groups.get(id);

			if (existing) {
				existing.buckets.push(bucket);
				existing.witnessCount += bucket.witness_count;
				existing.sourceRefCount += bucket.source_refs.length;
				existing.reasons = dedupeStrings([...existing.reasons, ...bucket.reasons]);
			} else {
				groups.set(id, {
					id,
					toolId,
					dictionary,
					lexeme,
					buckets: [bucket],
					witnessCount: bucket.witness_count,
					sourceRefCount: bucket.source_refs.length,
					reasons: dedupeStrings(bucket.reasons)
				});
			}
		}

		return [...groups.values()]
			.map((group) => ({
				...group,
				buckets: [...group.buckets].sort(compareBucketsBySourceOrder)
			}))
			.sort(compareGroupsBySourceOrder);
	}

	function compareGroupsBySourceOrder(a: BucketGroup, b: BucketGroup) {
		return (
			compareBucketsBySourceOrder(a.buckets[0], b.buckets[0]) || a.lexeme.localeCompare(b.lexeme)
		);
	}

	function compareBucketsBySourceOrder(a: EncounterBucket, b: EncounterBucket) {
		return (
			compareSourceRefs(primarySourceRef(a), primarySourceRef(b)) ||
			a.learner_quality_order - b.learner_quality_order ||
			a.bucket_id.localeCompare(b.bucket_id)
		);
	}

	function primarySourceRef(bucket: EncounterBucket) {
		const tool = primaryTool(bucket);
		return (
			bucket.source_refs.find((sourceRef) => sourceRef.startsWith(`${tool}:`)) ??
			bucket.source_refs[0] ??
			bucket.witnesses[0]?.source_ref ??
			''
		);
	}

	function compareSourceRefs(a: string, b: string) {
		const aParts = sourceRefParts(a);
		const bParts = sourceRefParts(b);
		const length = Math.max(aParts.length, bParts.length);

		for (let index = 0; index < length; index += 1) {
			const aPart = aParts[index];
			const bPart = bParts[index];

			if (aPart === undefined) return -1;
			if (bPart === undefined) return 1;
			if (typeof aPart === 'number' && typeof bPart === 'number' && aPart !== bPart) {
				return aPart - bPart;
			}
			if (aPart !== bPart)
				return String(aPart).localeCompare(String(bPart), undefined, { numeric: true });
		}

		return 0;
	}

	function sourceRefParts(sourceRef: string) {
		const [, rest = sourceRef] = sourceRef.split(/:(.*)/s);
		return rest
			.split(/[:_]/)
			.filter(Boolean)
			.map((part) => (/^\d+$/.test(part) ? Number(part) : part));
	}

	function dedupeStrings(values: string[]) {
		return [...new Set(values.filter(Boolean))];
	}

	function languageLabel(mode: LanguageMode) {
		return languageModes.find((candidate) => candidate.id === mode)?.label ?? mode;
	}

	function countLabel(count: number, singular: string, plural = `${singular}s`) {
		return `${count} ${count === 1 ? singular : plural}`;
	}

	function glossSegments(gloss: string) {
		const segments = gloss
			.split('|')
			.map((segment) => segment.trim())
			.filter(Boolean);
		return segments.length ? segments : [uiCopy.errors.noGloss];
	}

	function activeGloss(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		const text =
			bucket.translation &&
			(!bucket.translation.available || layerState[bucket.bucket_id] === 'source')
				? bucket.translation.source_text
				: (bucket.translation?.target_text ?? bucket.display_gloss);

		return postProcessDisplayText(bucket, text);
	}

	function postProcessDisplayText(bucket: EncounterBucket, value: string) {
		if (primaryTool(bucket) !== 'dico') return value;
		return value.replace(/_\d+\b/g, '');
	}

	function activeGlossSegments(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return glossSegments(activeGloss(bucket, layerState));
	}

	function sectionText(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		if (expansionState[sectionExpansionKey(bucket)] && sectionHasSourceDetail(bucket, layerState)) {
			return sourceDetailText(bucket);
		}

		if (
			shouldCollapseReaderSection(bucket, layerState) &&
			!expansionState[sectionExpansionKey(bucket)]
		) {
			return truncateText(activeGloss(bucket, layerState), sectionPreviewLength(bucket));
		}

		return activeGloss(bucket, layerState);
	}

	function sectionSegments(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		return glossSegments(sectionText(bucket, layerState, expansionState));
	}

	function sectionHasSourceDetail(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		if (bucket.translation?.available && isTranslatedSourceTool(bucket.translation.source_tool)) {
			return false;
		}

		const detail = sourceDetailText(bucket);
		if (!detail) return false;
		if (detail.length <= activeGloss(bucket, layerState).length + 24) return false;
		return isSectionTruncated(bucket, layerState);
	}

	function sourceDetailText(bucket: EncounterBucket) {
		return postProcessDisplayText(
			bucket,
			bucket.evidence_note
				.replace(/^examples:\s*/i, '')
				.replace(/^cross refs:\s*/i, 'Cross refs: ')
				.trim()
		);
	}

	function isSectionTruncated(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return /(?:…|\.\.\.)\s*$/u.test(activeGloss(bucket, layerState).trim());
	}

	function sectionIsClippedWithoutDetail(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return isSectionTruncated(bucket, layerState) && !sectionHasSourceDetail(bucket, layerState);
	}

	function sectionShowsReturnedEndingNote(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		return (
			sectionIsClippedWithoutDetail(bucket, layerState) &&
			(!sectionCanToggle(bucket, layerState) || expansionState[sectionExpansionKey(bucket)])
		);
	}

	function sectionCanToggle(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return (
			sectionHasSourceDetail(bucket, layerState) || shouldCollapseReaderSection(bucket, layerState)
		);
	}

	function shouldCollapseReaderSection(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		const tool = primaryTool(bucket);
		const text = activeGloss(bucket, layerState);
		const segments = activeGlossSegments(bucket, layerState);

		if (isOutlinedDictionaryTool(tool)) {
			if (isCompactOutlineHeading(bucket, layerState)) return false;
			return text.length > sectionPreviewLength(bucket) || segments.length > 1;
		}

		if (isTranslatedSourceTool(tool)) {
			return text.length > sectionPreviewLength(bucket) || segments.length > 3;
		}

		return false;
	}

	function sectionPreviewLength(bucket: EncounterBucket) {
		const tool = primaryTool(bucket);
		if (isTranslatedSourceTool(tool)) return 420;
		return 260;
	}

	function sectionToggleLabel(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		if (expansionState[sectionExpansionKey(bucket)]) return uiCopy.readerText.closePassage;
		return sectionHasSourceDetail(bucket, layerState)
			? uiCopy.passage.openSource
			: uiCopy.passage.openFull;
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

	function branchToggleLabel(bucket: EncounterBucket) {
		return collapsedBranches[sectionExpansionKey(bucket)]
			? uiCopy.passage.openNested
			: uiCopy.passage.closeNested;
	}

	function sectionExpansionKey(bucket: EncounterBucket) {
		return `${bucket.bucket_id}:${primarySourceRef(bucket)}`;
	}

	function groupToolIds(group: BucketGroup): ToolId[] {
		return [...new Set(group.buckets.flatMap((bucket) => bucket.source_tools))];
	}

	function componentToolIds(component: EncounterComponent): ToolId[] {
		const meaningTools = component.evidence.meanings.flatMap((meaning) => meaning.source_tools);
		return meaningTools.length ? [...new Set(meaningTools)] : [component.source_tool];
	}

	function componentPrimaryTool(component: EncounterComponent): ToolId {
		return componentToolIds(component)[0] ?? component.source_tool;
	}

	function componentLabel(component: EncounterComponent) {
		return component.display || component.surface || component.lemma || 'compound member';
	}

	function componentHeadwordDisplay(component: EncounterComponent) {
		return buildComponentHeadwordDisplay({
			language: encounter?.language ?? language,
			label: componentLabel(component)
		});
	}

	function componentLookupLine(component: EncounterComponent) {
		const terms = component.lookup_terms.length
			? component.lookup_terms.join(', ')
			: component.lemma;
		const role = component.role ? `${component.role} member` : 'compound member';
		return `${role}${terms ? `; lookup terms: ${terms}` : ''}`;
	}

	function componentMeaningSegments(
		meaning: EncounterComponentMeaning,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		return glossSegments(componentMeaningText(meaning, layerState, expansionState));
	}

	function componentMeaningActiveGloss(
		meaning: EncounterComponentMeaning,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		const key = componentMeaningKey(meaning);
		const text =
			meaning.translation && (!meaning.translation.available || layerState[key] === 'source')
				? meaning.translation.source_text
				: (meaning.translation?.target_text ?? meaning.display_gloss);
		return postProcessComponentText(meaning, text);
	}

	function postProcessComponentText(meaning: EncounterComponentMeaning, value: string) {
		const tool = meaning.translation?.source_tool ?? meaning.source_tools[0];
		if (tool !== 'dico') return value;
		return value.replace(/_\d+\b/g, '');
	}

	function componentMeaningText(
		meaning: EncounterComponentMeaning,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		const text = componentMeaningActiveGloss(meaning, layerState);
		if (expansionState[componentMeaningKey(meaning)]) return text;
		if (componentMeaningCanToggle(meaning, layerState)) return truncateText(text, 420);
		return text;
	}

	function componentMeaningCanToggle(
		meaning: EncounterComponentMeaning,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		const text = componentMeaningActiveGloss(meaning, layerState);
		return text.length > 420 || glossSegments(text).length > 3;
	}

	function componentMeaningKey(meaning: EncounterComponentMeaning) {
		return `component:${meaning.bucket_id}:${meaning.source_refs[0] ?? ''}`;
	}

	function componentMeaningToggleLabel(
		meaning: EncounterComponentMeaning,
		expansionState: Record<string, boolean> = expandedSections
	) {
		return expansionState[componentMeaningKey(meaning)]
			? uiCopy.passage.closeComponent
			: uiCopy.passage.openComponent;
	}

	function toggleComponentMeaning(meaning: EncounterComponentMeaning) {
		const key = componentMeaningKey(meaning);
		expandedSections = {
			...expandedSections,
			[key]: !expandedSections[key]
		};
	}

	function componentHasTranslationToggle(component: EncounterComponent) {
		return component.evidence.meanings.some((meaning) =>
			isTranslatedSourceTool(meaning.translation?.source_tool)
		);
	}

	function componentHasReaderTranslation(component: EncounterComponent) {
		return component.evidence.meanings.some((meaning) => meaning.translation?.available === true);
	}

	function componentAwaitsReaderTranslation(component: EncounterComponent) {
		return (
			enrichingTranslations &&
			component.evidence.meanings.some((meaning) => meaningAwaitsReaderTranslation(meaning))
		);
	}

	function meaningAwaitsReaderTranslation(meaning: EncounterComponentMeaning) {
		const translation = meaning.translation;
		if (!translation || translation.available) return false;
		if (translation.source_lang !== 'fr') return false;
		return isTranslatedSourceTool(translation.source_tool);
	}

	function componentCanSwitchTextLayer(component: EncounterComponent) {
		return componentHasTranslationToggle(component) && componentHasReaderTranslation(component);
	}

	function componentLayerIsSource(
		component: EncounterComponent,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return component.evidence.meanings.some(
			(meaning) => layerState[componentMeaningKey(meaning)] === 'source'
		);
	}

	function setComponentTextLayer(component: EncounterComponent, layer: 'reader' | 'source') {
		textLayers = {
			...textLayers,
			...Object.fromEntries(
				component.evidence.meanings.map((meaning) => [componentMeaningKey(meaning), layer])
			)
		};
	}

	function componentSourceLayerLabel(component: EncounterComponent) {
		const meaning =
			component.evidence.meanings.find((candidate) => candidate.translation) ??
			component.evidence.meanings[0];
		return meaning?.translation?.source_label ?? 'Source';
	}

	function componentTranslationModel(component: EncounterComponent) {
		return component.evidence.meanings.find((meaning) => meaning.translation?.model)?.translation
			?.model;
	}

	function componentMeaningSourceLabel(meaning: EncounterComponentMeaning) {
		const tools = meaning.source_tools.length
			? meaning.source_tools.map((tool) => toolMeta(tool).shortLabel).join(', ')
			: 'source';
		const refs = meaning.source_refs.slice(0, 2).join(', ');
		return refs ? `${tools}; ${refs}` : tools;
	}

	function groupWitnesses(group: BucketGroup) {
		const seen = new Set<string>();
		return group.buckets
			.flatMap((bucket) => bucket.witnesses)
			.filter((witness) => {
				const key = `${witness.tool}:${witness.source_ref ?? ''}:${witness.headword ?? ''}:${witness.label}`;
				if (seen.has(key)) return false;
				seen.add(key);
				return true;
			});
	}

	function visibleGroupBuckets(group: BucketGroup) {
		if (!isOutlinedDictionaryTool(group.toolId)) return group.buckets;

		const buckets: EncounterBucket[] = [];
		let hiddenDepth: number | null = null;

		for (const bucket of group.buckets) {
			const depth = sourceRefDepth(bucket);

			if (hiddenDepth !== null) {
				if (depth > hiddenDepth) continue;
				hiddenDepth = null;
			}

			buckets.push(bucket);

			if (sectionHasTreeChildren(group, bucket) && collapsedBranches[sectionExpansionKey(bucket)]) {
				hiddenDepth = depth;
			}
		}

		return buckets;
	}

	function sectionHasTreeChildren(group: BucketGroup, bucket: EncounterBucket) {
		if (!isOutlinedDictionaryTool(primaryTool(bucket))) return false;
		const index = group.buckets.indexOf(bucket);
		if (index === -1) return false;
		const nextBucket = group.buckets[index + 1];
		if (!nextBucket) return false;
		return sourceRefDepth(nextBucket) > sourceRefDepth(bucket);
	}

	function sourceRefDepth(bucket: EncounterBucket) {
		return sourceOutlineDepth(primarySourceRef(bucket));
	}

	function readerSectionClass(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		const tool = primaryTool(bucket);
		const classes = ['orion-reader-section', `orion-reader-section-${tool}`];

		if (isOutlinedDictionaryTool(tool)) {
			classes.push('orion-reader-section-outline');

			if (sourceRefDepth(bucket) === 0) classes.push('orion-reader-section-root');
			if (sourceRefDepth(bucket) === 0 && isCompactOutlineHeading(bucket, layerState)) {
				classes.push('orion-reader-section-root-compact');
			}
			if (isOutlineHeading(bucket, layerState)) classes.push('orion-reader-section-heading');
		}

		return classes.join(' ');
	}

	function readerSectionStyle(bucket: EncounterBucket) {
		const depth = sourceRefDepth(bucket);
		const isOutlined = isOutlinedDictionaryTool(primaryTool(bucket));
		const indent = isOutlined ? Math.min(depth * 1.25, 5) : 0;
		const ruleWidth = isOutlined ? Math.min(depth, 4) : 0;
		const fontSize = Math.max(0.98, 1.08 - depth * 0.025);

		return `--orion-indent: ${indent}rem; --orion-rule-width: ${ruleWidth}rem; --orion-section-font: ${fontSize}rem;`;
	}

	function isOutlineHeading(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return isOutlinedDictionaryHeading(primaryTool(bucket), activeGloss(bucket, layerState));
	}

	function isCompactOutlineHeading(
		bucket: EncounterBucket,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		if (!isOutlinedDictionaryTool(primaryTool(bucket))) return false;
		return isCompactOutlinedDictionaryText(activeGloss(bucket, layerState));
	}

	function groupLead(
		group: BucketGroup,
		layerState: Record<string, 'reader' | 'source'> = textLayers,
		expansionState: Record<string, boolean> = expandedSections
	) {
		const root = group.buckets.find((bucket) => sourceRefDepth(bucket) === 0) ?? group.buckets[0];
		if (!root) return '';
		const firstSegment = activeGlossSegments(root, layerState)[0] ?? activeGloss(root, layerState);
		const lead = truncateText(firstSegment, 220);
		const firstRenderedSegment =
			sectionSegments(root, layerState, expansionState)[0] ??
			sectionText(root, layerState, expansionState);

		if (
			firstSegment.replace(/\s+/g, ' ').trim().length <= 220 &&
			lead === firstRenderedSegment.replace(/\s+/g, ' ').trim()
		) {
			return '';
		}

		return lead;
	}

	function sectionId(group: BucketGroup, bucket: EncounterBucket) {
		return `entry-${safeDomId(group.id)}-${safeDomId(primarySourceRef(bucket) || bucket.bucket_id)}`;
	}

	function truncateText(value: string, maxLength: number) {
		const normalized = value.replace(/\s+/g, ' ').trim();
		if (normalized.length <= maxLength) return normalized;
		return `${normalized.slice(0, maxLength - 1).trim()}...`;
	}

	function safeDomId(value: string) {
		return value.replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'section';
	}

	function groupHasTranslationToggle(group: BucketGroup) {
		return group.buckets.some(showTranslationToggle);
	}

	function groupHasReaderTranslation(group: BucketGroup) {
		return group.buckets.some(hasReaderTranslation);
	}

	function groupAwaitsReaderTranslation(group: BucketGroup) {
		return enrichingTranslations && group.buckets.some(bucketAwaitsReaderTranslation);
	}

	function bucketAwaitsReaderTranslation(bucket: EncounterBucket) {
		const translation = bucket.translation;
		if (!translation || translation.available) return false;
		if (translation.source_lang !== 'fr') return false;
		return isTranslatedSourceTool(translation.source_tool);
	}

	function groupCanSwitchTextLayer(group: BucketGroup) {
		return groupHasTranslationToggle(group) && groupHasReaderTranslation(group);
	}

	function groupSourceLayerLabel(group: BucketGroup) {
		const bucket = group.buckets.find((candidate) => candidate.translation) ?? group.buckets[0];
		return sourceLayerLabel(bucket);
	}

	function groupTranslationModel(group: BucketGroup) {
		return group.buckets.find((bucket) => bucket.translation?.model)?.translation?.model;
	}

	function retryableGroupTranslation(group: BucketGroup) {
		return group.buckets.find((bucket) => {
			const translation = bucket.translation;
			if (!translation) return false;
			if (!isTranslatedSourceTool(translation.source_tool)) return false;
			return Boolean(
				translation.translation_id ||
				(translation.source_lexicon &&
					translation.entry_id &&
					translation.occurrence !== undefined &&
					translation.source_text_hash)
			);
		})?.translation;
	}

	function groupTranslationRetryKey(group: BucketGroup) {
		const translation = retryableGroupTranslation(group);
		return (
			translation?.translation_id ||
			[
				translation?.source_lexicon ?? translation?.source_tool ?? group.toolId,
				translation?.entry_id ?? group.lexeme,
				translation?.occurrence ?? 0,
				translation?.source_text_hash ?? group.id
			].join(':')
		);
	}

	function groupTranslationRetrying(group: BucketGroup) {
		return Boolean(translationRetrying[groupTranslationRetryKey(group)]);
	}

	function setGroupTextLayer(group: BucketGroup, layer: 'reader' | 'source') {
		textLayers = {
			...textLayers,
			...Object.fromEntries(group.buckets.map((bucket) => [bucket.bucket_id, layer]))
		};
	}

	function groupLayerIsSource(
		group: BucketGroup,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		return group.buckets.some((bucket) => layerState[bucket.bucket_id] === 'source');
	}

	function readerEntryLabel(
		group: BucketGroup,
		layerState: Record<string, 'reader' | 'source'> = textLayers
	) {
		if (!group.buckets.length) return uiCopy.readerText.label;
		if (groupHasTranslationToggle(group)) {
			const bucket = group.buckets.find((candidate) => candidate.translation) ?? group.buckets[0];
			return groupLayerIsSource(group, layerState) || !groupHasReaderTranslation(group)
				? sourceLayerLabel(bucket)
				: readerLayerLabel(bucket);
		}
		return uiCopy.readerText.label;
	}

	function toolMeta(
		toolId: ToolId,
		mode: LanguageMode = encounter?.language ?? language
	): ToolMeta {
		return (
			tools.find((tool) => tool.id === toolId && tool.language === mode) ??
			tools.find((tool) => tool.id === toolId) ?? {
				id: toolId,
				language: mode,
				label: toolId,
				shortLabel: toolId,
				kind: 'tool',
				description: 'Source entry evidence.'
			}
		);
	}

	function toolMnemonic(toolId: ToolId): Mnemonic {
		const mnemonics: Record<ToolId, Mnemonic> = {
			cdsl: { Icon: Turtle, name: 'Long-form Sanskrit dictionaries' },
			heritage: { Icon: Shell, name: 'Inherited-form analysis' },
			dico: { Icon: Fish, name: 'Sanskrit source with reader English' },
			diogenes: { Icon: Bird, name: 'Greek and Latin dictionary entries' },
			bailly: { Icon: BookOpen, name: 'Bailly source entries' },
			strongs_greek: { Icon: BookmarkCheck, name: "Strong's Greek source entries" },
			cts_index: { Icon: Squirrel, name: 'Citation index' },
			spacy: { Icon: Bug, name: 'Grammar probe' },
			cltk: { Icon: Cat, name: 'Supplemental lexicon' },
			whitakers: { Icon: Dog, name: 'Latin morphology' },
			gaffiot: { Icon: Snail, name: 'Gaffiot source entries' },
			lewis_1890: { Icon: ScrollText, name: 'Lewis 1890 source entries' }
		};

		return mnemonics[toolId];
	}

	function readerLayerLabel(bucket: EncounterBucket) {
		return bucket.translation?.available
			? `Reader ${bucket.reader_lang.toUpperCase()}`
			: uiCopy.readerText.pending;
	}

	function sourceLayerLabel(bucket: EncounterBucket) {
		return bucket.translation?.source_label ?? 'Source';
	}

	function showTranslationToggle(bucket: EncounterBucket) {
		return isTranslatedSourceTool(bucket.translation?.source_tool);
	}

	function hasReaderTranslation(bucket: EncounterBucket) {
		return bucket.translation?.available === true;
	}

	function translationModelLabel(model: string | undefined) {
		if (!model) return '';
		const withoutProvider = model.replace(/^openai:/, '');
		const labels: Record<string, string> = {
			'google/gemini-2.5-flash': 'Gemini 2.5 Flash',
			'deepseek/deepseek-v4-flash': 'DeepSeek V4 Flash'
		};
		return labels[withoutProvider] ?? withoutProvider;
	}

	function isTranslatedSourceTool(tool: ToolId | undefined) {
		return tool === 'dico' || tool === 'gaffiot' || tool === 'bailly';
	}

	function cacheSummary(encounterResult: EncounterResult) {
		const { translation_cache } = encounterResult;

		if (!translation_cache.cache_available) return uiCopy.status.cacheUnavailable;
		if (translation_cache.after.missing === 0) return uiCopy.status.cacheWarm;
		if (translation_cache.written > 0)
			return uiCopy.status.newTranslations(translation_cache.written);
		return uiCopy.status.missingTranslations(translation_cache.after.missing);
	}

	function currentStatusLabel() {
		if (loading) return uiCopy.status.searching;
		if (enrichingTranslations) return uiCopy.status.awaitingReader;
		if (errorMessage || enrichmentError) return uiCopy.status.attention;
		if (encounter) return uiCopy.status.reading;
		return uiCopy.status.ready;
	}

	function currentStatusDetail() {
		if (loading) {
			return uiCopy.status.askingSources(lookupTools.length);
		}

		if (enrichingTranslations) {
			return uiCopy.status.awaitingReaderDetail;
		}

		if (encounter) {
			return uiCopy.status.showingSections(
				visibleBuckets.length,
				encounter.buckets.length,
				encounter.query
			);
		}

		if (query.trim()) return uiCopy.status.readyForWord;
		return uiCopy.status.chooseWord;
	}

	function readerLayerStatus() {
		if (enrichingTranslations) return uiCopy.readerLayer.awaiting(translationMode);
		if (!encounter) return uiCopy.readerLayer.unsearched;
		if (
			shouldProgressivelyEnrich(translationMode) &&
			encounter.request.translation_mode === 'cache'
		) {
			return uiCopy.readerLayer.cacheSupplied(translationMode);
		}
		return uiCopy.readerLayer.served(encounter.request.translation_mode);
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
				isEarmarked,
				languageLabel,
				onBrowseSection: browseWordIndexSection,
				onOpenSection: openWordIndexSection,
				onNavigate: handleWordIndexNavigation,
				onToggleEarmark: toggleWordIndexEarmark,
				onClearEarmarks: clearWordIndexEarmarks
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
						cacheAccount: cacheSummary(encounter),
						readerLayerStatus: readerLayerStatus()
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
