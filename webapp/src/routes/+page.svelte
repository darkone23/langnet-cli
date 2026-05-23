<script lang="ts">
	import { browser } from '$app/environment';
	import { pushState, replaceState } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import {
		Asterisk,
		Bird,
		BookmarkCheck,
		BookmarkPlus,
		BookOpen,
		Bug,
		Cat,
		ChevronDown,
		CheckCircle2,
		Compass,
		Database,
		Dog,
		Eraser,
		Feather,
		Fish,
		Flower2,
		Moon,
		Omega,
		RefreshCw,
		Search,
		Shell,
		SlidersHorizontal,
		Snail,
		Sparkles,
		Squirrel,
		ScrollText,
		Sun,
		Telescope,
		Turtle
	} from 'lucide-svelte';
	import {
		buildComponentHeadwordDisplay,
		buildHeadwordDisplay,
		type HeadwordDisplay
	} from '$lib/headword-display';
	import { fetchPayload } from '$lib/msgpack';
	import {
		routeMatchesEncounter,
		shouldLoadEncounterForRoute,
		shouldPersistDeskRouteListParam,
		shouldResetEncounterForRoute
	} from '$lib/desk-route';
	import { motdItemKeys, motdTtlMs, storedMotdStatus, type StoredMotd } from '$lib/motd-cache';
	import {
		normalizeParadigmPayload,
		paradigmRequestKey,
		type ParadigmBlock,
		type ParadigmPayload
	} from '$lib/paradigm';
	import {
		curateParadigmCandidates,
		learnerDisplayForm,
		paradigmPayloadHasForms,
		paradigmSlotMatchesCandidate,
		paradigmSlotGroups,
		paradigmUnavailableMessage
	} from '$lib/paradigm-ui';
	import type {
		LearningConcept,
		LearningFosterBridge,
		LearningNativeGateway,
		ParadigmResolutionCandidate
	} from '$lib/paradigm-resolution';
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
		wordIndexSectionLookupTarget
	} from '$lib/word-index';
	import type {
		WordIndexItem,
		WordIndexNeighborhoodGroup,
		WordIndexResponse,
		WordIndexSection,
		WordIndexSectionsResponse
	} from '$lib/word-index';

	const toolStyle: Record<ToolId, { accent: string; badge: string }> = {
		cdsl: { accent: 'border-l-secondary', badge: 'badge-secondary' },
		heritage: { accent: 'border-l-accent', badge: 'badge-accent' },
		dico: { accent: 'border-l-success', badge: 'badge-success' },
		diogenes: { accent: 'border-l-info', badge: 'badge-info' },
		bailly: { accent: 'border-l-success', badge: 'badge-success' },
		cts_index: { accent: 'border-l-accent', badge: 'badge-accent' },
		spacy: { accent: 'border-l-neutral', badge: 'badge-neutral' },
		cltk: { accent: 'border-l-success', badge: 'badge-success' },
		whitakers: { accent: 'border-l-secondary', badge: 'badge-secondary' },
		gaffiot: { accent: 'border-l-accent', badge: 'badge-accent' },
		lewis_1890: { accent: 'border-l-info', badge: 'badge-info' }
	};

	const simulatedLookupDelayMs = 900;
	const loadingSteps = uiCopy.search.loadingSteps;
	const motdSkeletonRows = [0, 1, 2];
	const motdStorageKey = 'orion-motd-cache:v4';
	const deskStorageKey = 'orion-desk-state:v3';
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

	type StoredDeskState = {
		version: 3;
		expiresAt: number;
		routeKey: string;
		language: LanguageMode;
		query: string;
		backendMode: SearchBackend;
		translationMode: TranslationMode;
		theme: 'manuscript' | 'vespers';
		lookupTools: ToolId[];
		visibleTools: ToolId[];
		encounter: EncounterResult | null;
		textLayers: Record<string, 'reader' | 'source'>;
		expandedSections: Record<string, boolean>;
		collapsedBranches: Record<string, boolean>;
		wordIndex?: WordIndexResponse | null;
		wordIndexSections?: WordIndexSectionsResponse | null;
	};

	type StoredWordIndexEarmarks = {
		version: 1;
		items: WordIndexItem[];
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

	let availableTools = $derived(toolsForLanguage(language));
	let returnedToolIds = $derived(
		encounter
			? [...new Set(encounter.buckets.flatMap((bucket) => bucket.source_tools))]
			: ([] as ToolId[])
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
	let hasParadigmCandidates = $derived(paradigmCandidates.length > 0);

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
				candidate_source: 'llm',
				timeout_ms: '12000'
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

		try {
			const raw = localStorage.getItem(motdStorageKey);
			if (!raw) return { result: null, stale: false };

			const stored = JSON.parse(raw) as Partial<StoredMotd>;
			const status = storedMotdStatus(stored);
			if (status === 'invalid') {
				localStorage.removeItem(motdStorageKey);
				return { result: null, stale: false };
			}

			if (!stored.result) return { result: null, stale: false };
			const result = normalizeMotdResult(stored.result);
			if (!result.items.length) {
				localStorage.removeItem(motdStorageKey);
				return { result: null, stale: false };
			}
			return { result, stale: status === 'stale' };
		} catch {
			localStorage.removeItem(motdStorageKey);
			return { result: null, stale: false };
		}
	}

	function saveMotdToLocalStorage(result: WordRecommendationResult) {
		if (!browser || !result.items.length) return;

		const ttlMs = motdTtlMs(result.suggested_ttl_seconds);
		const stored: StoredMotd = {
			version: 3,
			savedAt: Date.now(),
			expiresAt: Date.now() + ttlMs,
			kind: 'current',
			result
		};

		try {
			localStorage.setItem(motdStorageKey, JSON.stringify(stored));
		} catch {
			// localStorage may be unavailable or full; the app can still use the API path.
		}
	}

	function readStoredWordIndexEarmarks() {
		if (!browser) return [];

		try {
			const raw = localStorage.getItem(wordIndexStorageKey);
			if (!raw) return [];

			const stored = JSON.parse(raw) as Partial<StoredWordIndexEarmarks>;
			if (stored.version !== 1 || !Array.isArray(stored.items)) {
				localStorage.removeItem(wordIndexStorageKey);
				return [];
			}

			return stored.items.filter((item) => Boolean(item?.encounter?.q)).slice(0, 18);
		} catch {
			localStorage.removeItem(wordIndexStorageKey);
			return [];
		}
	}

	function saveWordIndexEarmarks() {
		if (!browser) return;

		try {
			localStorage.setItem(
				wordIndexStorageKey,
				JSON.stringify({ version: 1, items: wordIndexEarmarks } satisfies StoredWordIndexEarmarks)
			);
		} catch {
			// Earmarks are a reader convenience; failure must not affect lookup.
		}
	}

	function readStoredDeskState() {
		if (!browser) return null;

		try {
			const raw = sessionStorage.getItem(deskStorageKey);
			if (!raw) return null;

			const stored = JSON.parse(raw) as Partial<StoredDeskState>;
			if (stored.version !== 3 || !stored.expiresAt || stored.expiresAt <= Date.now()) {
				sessionStorage.removeItem(deskStorageKey);
				return null;
			}

			return stored;
		} catch {
			sessionStorage.removeItem(deskStorageKey);
			return null;
		}
	}

	function saveDeskStateToSessionStorage() {
		if (!browser) return;

		if (!query.trim() && !encounter) {
			clearStoredDeskState();
			return;
		}

		const stored: StoredDeskState = {
			version: 3,
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

		try {
			sessionStorage.setItem(deskStorageKey, JSON.stringify(stored));
		} catch {
			// Long dictionary entries can exceed browser storage limits; hard links still work.
		}
	}

	function clearStoredDeskState() {
		if (!browser) return;

		try {
			sessionStorage.removeItem(deskStorageKey);
			sessionStorage.removeItem('orion-desk-state:v2');
			sessionStorage.removeItem('orion-desk-state:v1');
		} catch {
			// Ignore storage failures.
		}
	}

	function clearStoredMotdState() {
		if (!browser) return;

		try {
			localStorage.removeItem(motdStorageKey);
			localStorage.removeItem('orion-motd-cache:v3');
			localStorage.removeItem('orion-motd-cache:v2');
			localStorage.removeItem('orion-motd-cache:v1');
		} catch {
			// Ignore storage failures.
		}
	}

	function clearStoredWordIndexState() {
		if (!browser) return;

		try {
			localStorage.removeItem(wordIndexStorageKey);
		} catch {
			// Ignore storage failures.
		}
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
		return JSON.stringify({
			language,
			query: query.trim().toLowerCase(),
			backendMode,
			translationMode,
			lookupTools: [...lookupTools].sort()
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

		return hasMissingSourceReaderTranslations(result);
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
		const targetLanguage = item.encounter.language;
		const params = new URLSearchParams({
			lang: targetLanguage,
			q: item.encounter.q || item.lookup || item.canonical_key,
			translation: translationMode,
			theme
		});
		appendCurrentDictionaryParams(params, targetLanguage);
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

	function appendCurrentDictionaryParams(params: URLSearchParams, targetLanguage: LanguageMode) {
		const validTools = new Set(toolsForLanguage(targetLanguage).map(({ id }) => id));
		const toolsToCarry =
			targetLanguage === language ? lookupTools.filter((tool) => validTools.has(tool)) : [];
		const carriesAll =
			toolsToCarry.length === 0 || toolsToCarry.length === toolsForLanguage(targetLanguage).length;

		if (carriesAll) {
			params.set('dictionary', 'all');
			return;
		}

		for (const tool of toolsToCarry) params.append('dictionary', tool);
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

	function paradigmCandidateKey(candidate: ParadigmResolutionCandidate) {
		if (candidate.paradigm_request) return paradigmRequestKey(candidate.paradigm_request);
		return [
			candidate.lemma,
			candidate.entry_type,
			candidate.part_of_speech,
			candidate.paradigm_kind,
			candidate.unresolved_reason ?? 'unresolved'
		].join(':');
	}

	function paradigmCandidateTitle(candidate: ParadigmResolutionCandidate) {
		const kind =
			candidate.paradigm_kind && candidate.paradigm_kind !== 'unknown'
				? candidate.paradigm_kind
				: 'form';
		const label = learnerDisplayForm(candidate.lemma || encounter?.query || 'form');
		return `${label || 'form'} ${kind}`;
	}

	function paradigmCandidateSubtitle(candidate: ParadigmResolutionCandidate) {
		return [
			candidate.observed_form ? `form ${learnerDisplayForm(candidate.observed_form)}` : '',
			candidate.part_of_speech && candidate.part_of_speech !== 'unknown'
				? candidate.part_of_speech
				: '',
			candidate.entry_type && candidate.entry_type !== 'unknown' ? candidate.entry_type : '',
			candidate.foster_display,
			candidate.ranking_reasons.includes('ambiguous-analysis') ? 'ambiguous analysis' : '',
			candidate.confidence ? `${candidate.confidence} confidence` : ''
		]
			.filter(Boolean)
			.join(' · ');
	}

	function paradigmFeatureEntries(candidate: ParadigmResolutionCandidate) {
		const seen = new Set<string>();
		const entries: { key: string; value: string }[] = [];

		for (const analysis of candidate.native_analyses) {
			for (const [key, value] of Object.entries(analysis.features)) {
				const label = paradigmFeatureLabel(key);
				const display = paradigmFeatureValue(value);
				const entryKey = `${label}:${display}`;
				if (!display || display === 'unknown' || seen.has(entryKey)) continue;
				seen.add(entryKey);
				entries.push({ key: label, value: display });
			}
		}

		return entries;
	}

	function paradigmFunctionalLabels(candidate: ParadigmResolutionCandidate) {
		return [
			...new Set(
				candidate.functional_analyses
					.map((analysis) => paradigmRelationLabel(analysis.relation))
					.filter((label) => label && label !== 'unknown')
			)
		];
	}

	function learningConcepts(candidate: ParadigmResolutionCandidate) {
		return candidate.learning_overlay?.concepts ?? [];
	}

	function learningPrimarySummary(candidate: ParadigmResolutionCandidate) {
		const overlay = candidate.learning_overlay;
		const caseConcept =
			overlay?.concepts.find((concept) => concept.kind === 'case') ?? overlay?.concepts[0];
		if (candidate.display_summary) return learnerDisplayForm(candidate.display_summary);
		if (caseConcept?.plain_english) return caseConcept.plain_english;
		return candidate.foster_display || '';
	}

	function learningGatewayTitle(concepts: LearningConcept[]) {
		return learningPrimaryConcept(concepts)?.foster_gateway || '';
	}

	function learningPrimaryConcept(concepts: LearningConcept[]) {
		const priority = ['case', 'person', 'tense', 'mood', 'voice', 'number', 'gender', 'process'];
		return (
			[...concepts].sort(
				(left, right) =>
					conceptPriority(left.kind, priority) - conceptPriority(right.kind, priority)
			)[0] ?? null
		);
	}

	function conceptPriority(kind: string, priority: string[]) {
		const index = priority.indexOf(kind);
		return index === -1 ? priority.length : index;
	}

	function learningNativeGateways(
		concepts: LearningConcept[],
		targetLanguage: LanguageMode = language
	) {
		const seen = new Set<string>();
		const gateways: LearningNativeGateway[] = [];
		const primaryConcept = learningPrimaryConcept(concepts);
		for (const concept of primaryConcept ? [primaryConcept] : concepts) {
			const nativeGateways = concept.native_gateways.length
				? concept.native_gateways
				: derivedNativeGateways(concept, targetLanguage);
			for (const gateway of nativeGateways) {
				if (gateway.language !== targetLanguage) continue;
				if (!gateway.term) continue;
				const key = `${gateway.language}:${gateway.term}:${gateway.role}`;
				if (seen.has(key)) continue;
				seen.add(key);
				gateways.push(gateway);
			}
		}
		return gateways.slice(0, 1);
	}

	function candidateLearningLanguage(candidate: ParadigmResolutionCandidate): LanguageMode {
		return (
			candidate.paradigm_request?.language ??
			candidate.native_analyses.find((analysis) => analysis.language)?.language ??
			encounter?.language ??
			language
		);
	}

	function derivedNativeGateways(
		concept: LearningConcept,
		targetLanguage: LanguageMode
	): LearningNativeGateway[] {
		const labels = {
			grc: 'Greek',
			lat: 'Latin',
			san: 'Sanskrit'
		} as const;
		return [targetLanguage]
			.map((language) => {
				const term = concept.traditional[language] ?? '';
				const role =
					language === 'san'
						? (concept.traditional.san_role ?? concept.traditional.san_process ?? '')
						: '';
				return {
					language,
					label: labels[language],
					term,
					role,
					foster_gateway: concept.foster_gateway,
					explanation: `${labels[language]} gateway: ${term}; LangNet uses ${concept.foster_gateway} as the learner gateway.`
				};
			})
			.filter((gateway) => gateway.term);
	}

	function learningFosterBridges(concepts: LearningConcept[]) {
		const primaryConcept = learningPrimaryConcept(concepts);
		const byId = new Map<string, LearningFosterBridge>();
		for (const concept of primaryConcept ? [primaryConcept] : concepts) {
			for (const bridge of concept.foster_bridges) {
				if (bridge.id) byId.set(bridge.id, bridge);
			}
		}
		return [...byId.values()]
			.sort(
				(left, right) =>
					Number(right.status !== 'aggregate_candidate') -
					Number(left.status !== 'aggregate_candidate')
			)
			.slice(0, 1);
	}

	function paradigmFeatureLabel(value: string) {
		return value.replace(/_/g, ' ');
	}

	function paradigmFeatureValue(value: unknown) {
		if (value === null || value === undefined || value === '') return '';
		return String(value).replace(/_/g, ' ');
	}

	function paradigmRelationLabel(value: string) {
		return value.replace(/_/g, ' ');
	}

	function paradigmRequestUrl(candidate: ParadigmResolutionCandidate) {
		const request = candidate.paradigm_request;
		if (!request) return '';
		const params = new URLSearchParams({
			language: request.language,
			lemma: request.lemma,
			kind: request.kind,
			timeout_ms: '120000'
		});
		const gender = request.options.gender;
		const presentClass = request.options.class;
		if (typeof gender === 'string' && gender) params.set('gender', gender);
		if (typeof presentClass === 'string' && presentClass) params.set('class', presentClass);
		return `/api/paradigm?${params.toString()}`;
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

	function paradigmSlotFeatureSummary(features: Record<string, unknown>) {
		return Object.entries(features)
			.map(([key, value]) => `${paradigmFeatureLabel(key)} ${paradigmFeatureValue(value)}`.trim())
			.filter(Boolean)
			.join(' · ');
	}

	function paradigmTableLearningTitle(candidate: ParadigmResolutionCandidate) {
		if (candidate.paradigm_kind === 'declension') return 'Reading a declension table';
		if (candidate.paradigm_kind === 'conjugation') return 'Reading a conjugation table';
		return 'Reading a form table';
	}

	function paradigmTableLearningSummary(
		candidate: ParadigmResolutionCandidate,
		block: ParadigmBlock
	) {
		const dimensionText = block.dimensions.map(paradigmFeatureLabel).join(', ');
		if (candidate.paradigm_kind === 'declension') {
			return `This table maps noun-form jobs. ${dimensionText || 'The listed features'} tell what role, count, and agreement shape a form can carry.`;
		}
		if (candidate.paradigm_kind === 'conjugation') {
			return `This table maps verb-form jobs. ${dimensionText || 'The listed features'} tell who acts, when or how the action is framed, and how the action relates to its subject.`;
		}
		return `This table maps possible forms by ${dimensionText || 'their grammatical features'}.`;
	}

	function paradigmTableAxisNotes(block: ParadigmBlock) {
		return block.dimensions.map((dimension) => ({
			label: paradigmFeatureLabel(dimension),
			note: paradigmDimensionNote(dimension)
		}));
	}

	function paradigmDimensionNote(dimension: string) {
		const notes: Record<string, string> = {
			case: 'job in the expression',
			number: 'one, two, or many',
			gender: 'agreement class',
			person: 'speaker, addressee, or other',
			tense: 'time or verbal frame',
			mood: 'mode of statement',
			voice: 'action relation',
			degree: 'comparison level'
		};
		return notes[dimension] ?? 'form feature';
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
		if (!result || result.language !== 'lat') return keys;

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
		return (
			!includeLoad &&
			language === 'san' &&
			!query.trim() &&
			backendMode === 'cli' &&
			translationMode === 'auto' &&
			theme === 'manuscript' &&
			lookupTools.length === toolsForLanguage('san').length &&
			lookupTools.every((tool) => toolsForLanguage('san').some(({ id }) => id === tool)) &&
			!encounter &&
			!visibleTools.length &&
			!Object.keys(textLayers).length &&
			!Object.keys(expandedSections).length &&
			!Object.keys(collapsedBranches).length &&
			!pendingVisibleToolsFromRoute?.length &&
			!pendingSourceLayersFromRoute.length &&
			!pendingExpandedSectionsFromRoute.length &&
			!pendingCollapsedBranchesFromRoute.length
		);
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

	function routeShouldLoad(params: URLSearchParams) {
		const value = params.get('load')?.toLowerCase();
		if (routePrefillOnlyRequested(params)) return false;
		if (value === 'yes' || value === 'true' || value === '1') return true;
		return Boolean(params.get('q')?.trim());
	}

	function routeExplicitlyRequestsLoad(params: URLSearchParams) {
		const value = params.get('load')?.toLowerCase();
		return value === 'yes' || value === 'true' || value === '1';
	}

	function routePrefillOnlyRequested(params: URLSearchParams) {
		const loadValue = params.get('load')?.toLowerCase();
		const prefillValue = params.get('prefill')?.toLowerCase();
		return (
			loadValue === 'no' ||
			loadValue === 'false' ||
			loadValue === '0' ||
			prefillValue === 'yes' ||
			prefillValue === 'true' ||
			prefillValue === '1'
		);
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

	function readLanguageParam(params: URLSearchParams) {
		const requestedLanguage = params.get('lang') ?? params.get('language');
		return languageModes.some((mode) => mode.id === requestedLanguage)
			? (requestedLanguage as LanguageMode)
			: null;
	}

	function readToolParams(params: URLSearchParams, name: string, validTools: ToolId[]) {
		const values = readRouteList(params, name);
		if (!values.length) return null;
		if (values.includes('all')) return validTools;

		const validToolSet = new Set(validTools);
		const parsed = values.filter((value): value is ToolId => validToolSet.has(value as ToolId));
		return parsed.length ? [...new Set(parsed)] : null;
	}

	function readRouteList(params: URLSearchParams, name: string) {
		return params
			.getAll(name)
			.flatMap((value) => value.split(','))
			.map((value) => value.trim())
			.filter(Boolean);
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

	function activeGloss(bucket: EncounterBucket) {
		const text =
			bucket.translation &&
			(!bucket.translation.available || textLayers[bucket.bucket_id] === 'source')
				? bucket.translation.source_text
				: (bucket.translation?.target_text ?? bucket.display_gloss);

		return postProcessDisplayText(bucket, text);
	}

	function postProcessDisplayText(bucket: EncounterBucket, value: string) {
		if (primaryTool(bucket) !== 'dico') return value;
		return value.replace(/_\d+\b/g, '');
	}

	function activeGlossSegments(bucket: EncounterBucket) {
		return glossSegments(activeGloss(bucket));
	}

	function sectionText(bucket: EncounterBucket) {
		if (expandedSections[sectionExpansionKey(bucket)] && sectionHasSourceDetail(bucket)) {
			return sourceDetailText(bucket);
		}

		if (shouldCollapseReaderSection(bucket) && !expandedSections[sectionExpansionKey(bucket)]) {
			return truncateText(activeGloss(bucket), sectionPreviewLength(bucket));
		}

		return activeGloss(bucket);
	}

	function sectionSegments(bucket: EncounterBucket) {
		return glossSegments(sectionText(bucket));
	}

	function sectionHasSourceDetail(bucket: EncounterBucket) {
		if (bucket.translation?.available && isTranslatedSourceTool(bucket.translation.source_tool)) {
			return false;
		}

		const detail = sourceDetailText(bucket);
		if (!detail) return false;
		if (detail.length <= activeGloss(bucket).length + 24) return false;
		return isSectionTruncated(bucket);
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

	function isSectionTruncated(bucket: EncounterBucket) {
		return /(?:…|\.\.\.)\s*$/u.test(activeGloss(bucket).trim());
	}

	function sectionIsClippedWithoutDetail(bucket: EncounterBucket) {
		return isSectionTruncated(bucket) && !sectionHasSourceDetail(bucket);
	}

	function sectionShowsReturnedEndingNote(bucket: EncounterBucket) {
		return (
			sectionIsClippedWithoutDetail(bucket) &&
			(!sectionCanToggle(bucket) || expandedSections[sectionExpansionKey(bucket)])
		);
	}

	function sectionCanToggle(bucket: EncounterBucket) {
		return sectionHasSourceDetail(bucket) || shouldCollapseReaderSection(bucket);
	}

	function shouldCollapseReaderSection(bucket: EncounterBucket) {
		const tool = primaryTool(bucket);
		const text = activeGloss(bucket);
		const segments = activeGlossSegments(bucket);

		if (isOutlinedDictionaryTool(tool)) {
			if (isCompactOutlineHeading(bucket)) return false;
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

	function sectionToggleLabel(bucket: EncounterBucket) {
		if (expandedSections[sectionExpansionKey(bucket)]) return uiCopy.readerText.closePassage;
		return sectionHasSourceDetail(bucket) ? uiCopy.passage.openSource : uiCopy.passage.openFull;
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

	function illuminatedTitleClass(title: HeadwordDisplay['title']) {
		const base = 'orion-illuminated-title font-serif text-3xl leading-tight';
		if (!title) return base;
		if (title.script === 'devanagari') {
			return `${base} orion-illuminated-title-explicit orion-illuminated-title-devanagari`;
		}
		return `${base} orion-illuminated-title-explicit`;
	}

	function componentLookupLine(component: EncounterComponent) {
		const terms = component.lookup_terms.length
			? component.lookup_terms.join(', ')
			: component.lemma;
		const role = component.role ? `${component.role} member` : 'compound member';
		return `${role}${terms ? `; lookup terms: ${terms}` : ''}`;
	}

	function componentMeaningSegments(meaning: EncounterComponentMeaning) {
		return glossSegments(componentMeaningText(meaning));
	}

	function componentMeaningActiveGloss(meaning: EncounterComponentMeaning) {
		const key = componentMeaningKey(meaning);
		const text =
			meaning.translation && (!meaning.translation.available || textLayers[key] === 'source')
				? meaning.translation.source_text
				: (meaning.translation?.target_text ?? meaning.display_gloss);
		return postProcessComponentText(meaning, text);
	}

	function postProcessComponentText(meaning: EncounterComponentMeaning, value: string) {
		const tool = meaning.translation?.source_tool ?? meaning.source_tools[0];
		if (tool !== 'dico') return value;
		return value.replace(/_\d+\b/g, '');
	}

	function componentMeaningText(meaning: EncounterComponentMeaning) {
		const text = componentMeaningActiveGloss(meaning);
		if (expandedSections[componentMeaningKey(meaning)]) return text;
		if (componentMeaningCanToggle(meaning)) return truncateText(text, 420);
		return text;
	}

	function componentMeaningCanToggle(meaning: EncounterComponentMeaning) {
		const text = componentMeaningActiveGloss(meaning);
		return text.length > 420 || glossSegments(text).length > 3;
	}

	function componentMeaningKey(meaning: EncounterComponentMeaning) {
		return `component:${meaning.bucket_id}:${meaning.source_refs[0] ?? ''}`;
	}

	function componentMeaningToggleLabel(meaning: EncounterComponentMeaning) {
		return expandedSections[componentMeaningKey(meaning)]
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

	function componentLayerIsSource(component: EncounterComponent) {
		return component.evidence.meanings.some(
			(meaning) => textLayers[componentMeaningKey(meaning)] === 'source'
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

	function readerSectionClass(bucket: EncounterBucket) {
		const tool = primaryTool(bucket);
		const classes = ['orion-reader-section', `orion-reader-section-${tool}`];

		if (isOutlinedDictionaryTool(tool)) {
			classes.push('orion-reader-section-outline');

			if (sourceRefDepth(bucket) === 0) classes.push('orion-reader-section-root');
			if (sourceRefDepth(bucket) === 0 && isCompactOutlineHeading(bucket)) {
				classes.push('orion-reader-section-root-compact');
			}
			if (isOutlineHeading(bucket)) classes.push('orion-reader-section-heading');
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

	function isOutlineHeading(bucket: EncounterBucket) {
		return isOutlinedDictionaryHeading(primaryTool(bucket), activeGloss(bucket));
	}

	function isCompactOutlineHeading(bucket: EncounterBucket) {
		if (!isOutlinedDictionaryTool(primaryTool(bucket))) return false;
		return isCompactOutlinedDictionaryText(activeGloss(bucket));
	}

	function groupLead(group: BucketGroup) {
		const root = group.buckets.find((bucket) => sourceRefDepth(bucket) === 0) ?? group.buckets[0];
		if (!root) return '';
		const firstSegment = activeGlossSegments(root)[0] ?? activeGloss(root);
		const lead = truncateText(firstSegment, 220);
		const firstRenderedSegment = sectionSegments(root)[0] ?? sectionText(root);

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

	function groupLayerIsSource(group: BucketGroup) {
		return group.buckets.some((bucket) => textLayers[bucket.bucket_id] === 'source');
	}

	function readerEntryLabel(group: BucketGroup) {
		if (!group.buckets.length) return uiCopy.readerText.label;
		if (groupHasTranslationToggle(group)) {
			const bucket = group.buckets.find((candidate) => candidate.translation) ?? group.buckets[0];
			return groupLayerIsSource(group) || !groupHasReaderTranslation(group)
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
			cts_index: { Icon: Squirrel, name: 'Citation index' },
			spacy: { Icon: Bug, name: 'Grammar probe' },
			cltk: { Icon: Cat, name: 'Supplemental lexicon' },
			whitakers: { Icon: Dog, name: 'Latin morphology' },
			gaffiot: { Icon: Snail, name: 'Gaffiot source entries' },
			lewis_1890: { Icon: ScrollText, name: 'Lewis 1890 source entries' }
		};

		return mnemonics[toolId];
	}

	function languageModeIcon(mode: LanguageMode) {
		const icons = {
			san: Flower2,
			grc: Omega,
			lat: ScrollText
		};

		return icons[mode];
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
			window.removeEventListener('scroll', syncSidebarHeight);
			window.removeEventListener('popstate', hydrateRouteStateFromUrl);
		};
	});
</script>

<svelte:head>
	<title>{uiCopy.app.title}</title>
	<meta name="description" content={uiCopy.app.description} />
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen" data-theme={theme}>
	<header class="navbar border-base-300 bg-base-100 border-b px-4 lg:px-8">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-3">
				<a
					href="/"
					class="orion-home-seal grid h-10 w-10 place-items-center rounded transition-opacity hover:opacity-85"
					aria-label={uiCopy.nav.homeAria}
					onclick={handleHomeNavigation}
				>
					<Telescope size={21} />
				</a>
				<div class="min-w-0">
					<div class="truncate text-base font-semibold">{uiCopy.app.name}</div>
					<div class="text-base-content/60 truncate text-sm">
						{uiCopy.app.motto}
					</div>
				</div>
			</div>
		</div>

		<div class="hidden items-center gap-3 md:flex">
			<a class="btn btn-sm btn-ghost" href="/reader">
				<BookOpen size={15} />
				Reader
			</a>
			<a class="btn btn-sm btn-ghost" href="/learn">
				<Sparkles size={15} />
				Learn
			</a>

			<label class="orion-topbar-control">
				<span>{uiCopy.readerLayer.label}</span>
				<select
					class="select select-xs border-base-300 bg-base-100"
					aria-label={uiCopy.readerLayer.modeAria}
					bind:value={translationMode}
				>
					<option value="auto">auto</option>
					<option value="cache">cache</option>
					<option value="off">off</option>
					<option value="populate">populate</option>
				</select>
				{#if enrichingTranslations}
					<span
						class="loading loading-spinner loading-xs"
						aria-label={uiCopy.readerLayer.loadingAria}
					></span>
				{/if}
			</label>

			<div class="stats stats-horizontal border-base-300 bg-base-100 border shadow-none">
				<div class="stat px-4 py-2">
					<div class="stat-title text-xs">{uiCopy.nav.languageStat}</div>
					<div class="stat-value text-lg">{languageLabel(language)}</div>
				</div>
				<div class="stat px-4 py-2">
					<div class="stat-title text-xs">{uiCopy.nav.statusStat}</div>
					<div class="stat-value text-lg">{currentStatusLabel()}</div>
				</div>
			</div>

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
					<span class="hidden lg:inline">{uiCopy.theme.reader}</span>
				</button>
				<button
					type="button"
					class={theme === 'vespers' ? 'btn btn-sm join-item btn-primary' : 'btn btn-sm join-item'}
					aria-label={uiCopy.theme.nightAria}
					onclick={() => setTheme('vespers')}
				>
					<Moon size={16} />
					<span class="hidden lg:inline">{uiCopy.theme.night}</span>
				</button>
			</div>
		</div>
	</header>

	<div
		class="orion-page-shell mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,48rem)_21rem] lg:px-8"
	>
		<article class="min-w-0 space-y-6">
			<section class="hero orion-manuscript-panel">
				<div class="hero-content block w-full p-6 lg:p-8">
					<div class="max-w-3xl">
						<div class="badge badge-secondary badge-outline mb-4 gap-2">
							<Feather size={14} />
							{uiCopy.hero.badge}
						</div>
						<h1 class="font-serif text-4xl leading-tight md:text-5xl">
							{uiCopy.hero.title(language)}
						</h1>
						<p class="text-base-content/70 mt-4 max-w-2xl font-serif text-xl leading-8">
							{uiCopy.hero.intro}
						</p>
					</div>

					<div class="mt-6">
						<div class="tabs tabs-box w-full md:w-auto">
							{#each languageModes as mode}
								{@const ModeIcon = languageModeIcon(mode.id)}
								<button
									type="button"
									class={mode.id === language ? 'tab tab-active gap-2' : 'tab gap-2'}
									title={`Set the desk for ${mode.label}`}
									onclick={() => selectLanguage(mode.id)}
								>
									<ModeIcon size={15} />
									{mode.label}
								</button>
							{/each}
						</div>
					</div>

					<form class="mt-6" onsubmit={handleSubmit}>
						<div class="join w-full">
							<label class="input input-lg join-item flex-1">
								<Search size={20} class="text-base-content/50" />
								<input
									bind:value={query}
									type="search"
									placeholder={uiCopy.search.placeholder(languageLabel(language))}
									aria-label={uiCopy.search.inputAria}
									autocomplete="off"
									disabled={loading}
									oninput={handleQueryInput}
								/>
							</label>
							<button class="btn btn-neutral btn-lg join-item" disabled={loading}>
								{#if loading}
									<span class="loading loading-spinner loading-sm"></span>
								{:else}
									<Search size={17} />
								{/if}
								<span class="hidden sm:inline">{uiCopy.search.button(loading)}</span>
							</button>
						</div>
						{#if searchRomanization}
							<div class="orion-search-reading" aria-live="polite">
								<span>{searchRomanization.label}</span>
								<code>{searchRomanization.value}</code>
							</div>
						{/if}

						<div class="mt-4 flex flex-wrap items-center gap-3">
							<button
								type="button"
								class="btn btn-ghost btn-sm"
								disabled={loading}
								onclick={() => {
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
								}}
							>
								{uiCopy.search.clear}
							</button>
							<span class={loading ? 'loading loading-spinner loading-sm' : 'hidden'}></span>
							<span class="text-base-content/60 text-sm" role="status" aria-live="polite">
								{currentStatusDetail()}
							</span>
						</div>
					</form>
				</div>
			</section>

			<section class="card orion-manuscript-panel orion-motd-folio">
				<div class="card-body gap-5 p-5 lg:p-6">
					<div class="orion-motd-folio-head">
						<div class="orion-motd-folio-title">
							<span class="orion-motd-emblem" aria-hidden="true">
								<BookOpen size={18} />
								<Sparkles size={12} />
							</span>
							<div>
								<h2 class="card-title text-lg">{uiCopy.margin.title}</h2>
								<p class="text-base-content/65 font-serif text-sm leading-6">
									{uiCopy.margin.intro}
									{#if !motdPending}
										{uiCopy.margin.linkMode(motdLinksLoad)}
									{/if}
								</p>
							</div>
						</div>

						<div class="orion-motd-actions">
							{#if motdPending}
								<span
									class="orion-motd-control-skeleton orion-motd-control-skeleton-load"
									aria-hidden="true"
								></span>
								<span
									class="orion-motd-control-skeleton orion-motd-control-skeleton-refresh"
									aria-hidden="true"
								></span>
							{:else}
								<button
									type="button"
									class={motdLinksLoad ? 'btn btn-xs btn-secondary' : 'btn btn-xs'}
									disabled={motdRefreshing}
									title={uiCopy.margin.loadTitle}
									onclick={() => {
										motdLinksLoad = !motdLinksLoad;
									}}
								>
									<Search size={13} />
									{uiCopy.margin.linkToggle(motdLinksLoad)}
								</button>
								<button
									type="button"
									class="btn btn-xs"
									disabled={motdRefreshing}
									title={uiCopy.margin.refreshTitle}
									onclick={() => void loadMotd(true)}
								>
									{#if motdRefreshing}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<RefreshCw size={13} />
									{/if}
									{uiCopy.margin.refresh}
								</button>
							{/if}
						</div>
					</div>

					{#if motdPending}
						<div class="orion-motd-list" aria-busy="true" aria-label={uiCopy.margin.prepareAria}>
							{#each motdSkeletonRows as _}
								<div class="orion-motd-link orion-motd-skeleton-card">
									<span class="orion-motd-skeleton-block orion-motd-skeleton-heading"></span>
									<span class="orion-motd-skeleton-block orion-motd-skeleton-gloss"></span>
									<span class="orion-motd-skeleton-block orion-motd-skeleton-foot"></span>
								</div>
							{/each}
							<span class="sr-only">{uiCopy.margin.prepareAria}</span>
						</div>
					{:else if motd}
						{#if motdItems.length}
							<div
								class={motdRefreshing
									? 'orion-motd-list orion-motd-list-refreshing'
									: 'orion-motd-list'}
								aria-busy={motdRefreshing}
							>
								{#each motdItems as item}
									{@const activeMotd = isActiveMotd(item)}
									<a
										class={activeMotd
											? 'orion-motd-link orion-motd-link-active'
											: 'orion-motd-link'}
										href={motdHref(item)}
										aria-current={activeMotd ? 'page' : undefined}
										onclick={(event) => handleMotdNavigation(event, item)}
									>
										<span class="orion-motd-lang">{languageLabel(item.language)}</span>
										<span class={motdWordClass(item)} lang={motdWordLang(item)}>
											<span>{motdDisplayWord(item)}</span>
											{#if motdDisplayLookup(item)}
												<span class="orion-motd-lookup">{motdDisplayLookup(item)}</span>
											{/if}
										</span>
										<span class="orion-motd-gloss">{motdDisplayGloss(item)}</span>
										<span class="orion-motd-note">{motdDisplayNote(item)}</span>
										<span class="orion-motd-action">
											{uiCopy.margin.cardAction(item.language, motdLinksLoad)}
										</span>
										{#if item.ambiguity.has_multiple_lexemes}
											<span class="orion-motd-caveat">{uiCopy.margin.multipleAnchors}</span>
										{/if}
										{#if item.novelty?.is_repeat}
											<span class="orion-motd-caveat">{uiCopy.margin.repeat}</span>
										{/if}
										{#if activeMotd}
											<span class="orion-motd-active-label">{uiCopy.margin.active}</span>
										{/if}
									</a>
								{/each}
							</div>
						{/if}

						{#if motdError}
							<div class="orion-motd-warning">
								{motdError}
							</div>
						{/if}
						{#if motdRefreshing}
							<div class="orion-motd-warning">
								{uiCopy.margin.refreshingPrevious}
							</div>
						{/if}
						{#if motdVisibleWarnings.length}
							<div class="orion-motd-warning">
								{motdVisibleWarnings[0].message}
							</div>
						{/if}
						{#if motd.exhaustion?.fresh_requested && !motd.exhaustion.fresh_satisfied}
							<div class="orion-motd-warning">
								{motd.exhaustion.reason || uiCopy.margin.noFreshWord}
							</div>
						{/if}
					{:else if motdError}
						<div class="alert alert-warning text-sm">{motdError}</div>
					{/if}
				</div>
			</section>

			{#if errorMessage}
				<div class="alert alert-warning">
					<Search size={18} />
					<span>{errorMessage}</span>
				</div>
			{/if}

			{#if enrichingTranslations && encounter}
				<div class="alert alert-info">
					<span class="loading loading-spinner loading-sm"></span>
					<span>{uiCopy.translator.alert}</span>
				</div>
			{/if}

			{#if enrichmentError}
				<div class="alert alert-warning">
					<Search size={18} />
					<span>{uiCopy.translator.failed(enrichmentError)}</span>
				</div>
			{/if}

			{#if !loading && encounter && visibleComponents.length}
				<section class="orion-component-ledger">
					<div class="orion-component-ledger-head">
						<div>
							<h2 class="font-serif text-2xl">{uiCopy.components.title}</h2>
							<p>{uiCopy.components.intro}</p>
						</div>
						<span class="orion-component-count">
							<span>{visibleComponents.length}</span>
							<span>{visibleComponents.length === 1 ? 'member' : 'members'}</span>
						</span>
					</div>

					<div class="orion-component-list">
						{#each visibleComponents as component}
							{@const componentTool = componentPrimaryTool(component)}
							{@const ComponentIcon = toolMnemonic(componentTool).Icon}
							{@const componentDisplay = componentHeadwordDisplay(component)}
							<article class="orion-result-group orion-component-group">
								<header class="orion-result-group-head">
									<div class="min-w-0">
										<div class="mb-2 flex flex-wrap items-center gap-2">
											<span class="orion-source-beast" title={toolMnemonic(componentTool).name}>
												<ComponentIcon size={16} />
											</span>
											<span class={`badge ${toolStyle[componentTool].badge}`}>
												{toolMeta(componentTool).shortLabel}
											</span>
											<span class="badge badge-outline">member</span>
										</div>
										<div class="orion-entry-bookplate">
											<h3
												class={illuminatedTitleClass(componentDisplay.title)}
												lang={componentDisplay.primaryLang}
												aria-label={componentDisplay.title ? componentDisplay.primary : undefined}
											>
												{#if componentDisplay.title?.script === 'devanagari'}
													<span class="orion-devanagari-title" aria-hidden="true">
														<span class="orion-devanagari-initial">
															<span class="orion-devanagari-initial-glyph">
																{componentDisplay.title.initial}
															</span>
														</span>
														{#if componentDisplay.title.rest}
															<span class="orion-devanagari-connector"></span>
															<span class="orion-devanagari-rest"
																>{componentDisplay.title.rest}</span
															>
														{/if}
													</span>
												{:else if componentDisplay.title}
													<span class="orion-plain-title" aria-hidden="true">
														<span class="orion-plain-initial">
															<span class="orion-plain-initial-glyph">
																{componentDisplay.title.initial}
															</span>
														</span>
														{#if componentDisplay.title.rest}
															<span class="orion-plain-rest">{componentDisplay.title.rest}</span>
														{/if}
													</span>
												{:else}
													{componentDisplay.primary}
												{/if}
											</h3>
											{#if componentDisplay.forms.length}
												<div class="orion-headword-forms" aria-label="Headword forms">
													{#each componentDisplay.forms as form}
														<span class="orion-headword-form">
															<span class="orion-headword-form-label">{form.label}</span>
															{#if form.kind === 'code'}
																<code>{form.value}</code>
															{:else}
																<span>{form.value}</span>
															{/if}
														</span>
													{/each}
												</div>
											{/if}
											<p class="orion-entry-lead">{componentLookupLine(component)}</p>
										</div>
										{#if component.analysis}
											<p class="orion-entry-source-line">{component.analysis}</p>
										{/if}
									</div>
									<div class="orion-entry-chrome">
										<div class="orion-entry-source-strip">
											{#each componentToolIds(component) as tool}
												{@const ToolIcon = toolMnemonic(tool).Icon}
												<span
													class="orion-source-beast orion-source-beast-sm"
													title={toolMnemonic(tool).name}
												>
													<ToolIcon size={14} />
												</span>
											{/each}
											<span>{component.evidence.meanings.length} entries</span>
											<span>{component.evidence.status || 'linked'}</span>
										</div>

										{#if componentCanSwitchTextLayer(component)}
											<div class="flex shrink-0 flex-col items-end gap-1">
												<div class="orion-layer-switch join">
													<button
														type="button"
														class={componentLayerIsSource(component)
															? 'btn btn-xs join-item'
															: 'btn btn-xs join-item btn-secondary'}
														onclick={() => setComponentTextLayer(component, 'reader')}
													>
														Reader English
													</button>
													<button
														type="button"
														class={componentLayerIsSource(component)
															? 'btn btn-xs join-item btn-secondary'
															: 'btn btn-xs join-item'}
														onclick={() => setComponentTextLayer(component, 'source')}
													>
														{componentSourceLayerLabel(component)}
													</button>
												</div>
												{#if translationModelLabel(componentTranslationModel(component))}
													<div class="text-base-content/50 text-[0.68rem] leading-none">
														EN by {translationModelLabel(componentTranslationModel(component))}
													</div>
												{/if}
											</div>
										{:else if componentHasTranslationToggle(component)}
											<span class="badge badge-outline"
												>{componentSourceLayerLabel(component)} only</span
											>
										{/if}
										{#if componentAwaitsReaderTranslation(component)}
											<span class="orion-translator-sigil" title={uiCopy.translator.title}>
												<span>{uiCopy.translator.badge}</span>
												<i></i><i></i><i></i>
											</span>
										{/if}
									</div>
								</header>

								{#if component.evidence.error}
									<div class="alert alert-warning text-sm">{component.evidence.error}</div>
								{:else if component.evidence.meanings.length}
									<div class={`orion-entry-reader ${toolStyle[componentTool].accent}`}>
										<div class="orion-reader-sections">
											{#each component.evidence.meanings as meaning}
												{@const segments = componentMeaningSegments(meaning)}
												<section
													class={`orion-reader-section orion-reader-section-${componentTool} orion-component-meaning`}
												>
													<div class="orion-reader-marker"></div>
													<div>
														<div class="orion-component-source">
															{componentMeaningSourceLabel(meaning)}
														</div>
														<div class="orion-reader-copy">
															{#each segments as gloss, segmentIndex}
																<p>
																	{gloss}
																	{#if segmentIndex === segments.length - 1 && componentMeaningCanToggle(meaning)}
																		<button
																			type="button"
																			class="orion-section-detail-toggle"
																			aria-label={componentMeaningToggleLabel(meaning)}
																			title={componentMeaningToggleLabel(meaning)}
																			onclick={() => toggleComponentMeaning(meaning)}
																		>
																			<ChevronDown
																				size={12}
																				class={expandedSections[componentMeaningKey(meaning)]
																					? 'orion-chevron-open'
																					: ''}
																			/>
																		</button>
																	{/if}
																</p>
															{/each}
														</div>
													</div>
												</section>
											{/each}
										</div>
									</div>
								{:else}
									<div class="orion-component-empty">{uiCopy.components.empty}</div>
								{/if}
							</article>
						{/each}
					</div>
				</section>
			{/if}

			<section
				bind:this={dictionaryWitnessesSection}
				class={translationArrived
					? 'orion-dictionary-witnesses orion-translation-arrived space-y-4'
					: 'orion-dictionary-witnesses space-y-4'}
			>
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<h2 class="font-serif text-3xl">{uiCopy.results.title}</h2>
						<p class="text-base-content/60 text-sm">{uiCopy.results.intro}</p>
					</div>
					<div class="join">
						<button type="button" class="btn btn-sm join-item" onclick={showAllReturnedTools}>
							{uiCopy.results.all}
						</button>
						<button type="button" class="btn btn-sm join-item btn-ghost">
							{countLabel(visibleBucketGroups.length, 'source group')}
						</button>
					</div>
				</div>

				{#if loading}
					<section class="card orion-manuscript-panel">
						<div class="card-body items-center gap-6 p-8 text-center">
							<div class="orion-pulse-widget" aria-hidden="true">
								<div class="orion-pulse-core">
									<BookOpen size={30} />
								</div>
								<span class="orion-pulse-dot orion-pulse-dot-a"></span>
								<span class="orion-pulse-dot orion-pulse-dot-b"></span>
								<span class="orion-pulse-dot orion-pulse-dot-c"></span>
							</div>

							<div class="max-w-xl">
								<h3 class="font-serif text-3xl leading-tight">{uiCopy.search.loadingTitle}</h3>
								<p class="text-base-content/65 mt-3 font-serif text-lg leading-7">
									Looking up <em>{query.trim()}</em> in {languageLabel(language)} with
									<code class="mx-1">dictionary={isAllLookupSelected ? 'all' : 'custom'}</code>.
								</p>
								<p class="text-base-content/60 mt-2 text-sm leading-6">
									{uiCopy.search.coldSources}
								</p>
							</div>

							<ul class="steps steps-vertical md:steps-horizontal w-full max-w-2xl">
								{#each loadingSteps as step}
									<li class="step step-primary">{step}</li>
								{/each}
							</ul>
						</div>
					</section>
				{:else if encounter}
					{#if hasParadigmCandidates}
						<section class="orion-paradigm-panel orion-manuscript-panel">
							<header class="orion-paradigm-head">
								<div>
									<h3>
										<ScrollText size={18} />
										Forms
									</h3>
									<p>
										{learnerDisplayForm(encounter.paradigm_resolution?.searched_form)}
										{#if encounter.paradigm_resolution?.normalized_form && learnerDisplayForm(encounter.paradigm_resolution.normalized_form) !== learnerDisplayForm(encounter.paradigm_resolution.searched_form)}
											<span>
												· {learnerDisplayForm(encounter.paradigm_resolution.normalized_form)}
											</span>
										{/if}
									</p>
								</div>
								<span>{countLabel(paradigmCandidates.length, 'reading')}</span>
							</header>

							<div class="orion-paradigm-candidates">
								{#each paradigmCandidates as candidate}
									{@const candidateKey = paradigmCandidateKey(candidate)}
									{@const features = paradigmFeatureEntries(candidate)}
									{@const relations = paradigmFunctionalLabels(candidate)}
									{@const learning = learningConcepts(candidate)}
									{@const nativeGateways = learningNativeGateways(
										learning,
										candidateLearningLanguage(candidate)
									)}
									{@const fosterBridges = learningFosterBridges(learning)}
									{@const paradigm = paradigmPayloads[candidateKey]}
									<article class="orion-paradigm-card">
										<div class="orion-paradigm-card-head">
											<div>
												<h4>{paradigmCandidateTitle(candidate)}</h4>
												{#if paradigmCandidateSubtitle(candidate)}
													<p>{paradigmCandidateSubtitle(candidate)}</p>
												{/if}
											</div>
											{#if candidate.paradigm_request}
												<button
													type="button"
													class="orion-paradigm-load"
													disabled={Boolean(paradigmLoading[candidateKey] || paradigm)}
													onclick={() => loadParadigm(candidate)}
												>
													{#if paradigmLoading[candidateKey]}
														<span class="loading loading-spinner loading-xs"></span>
													{/if}
													{paradigm ? 'Table loaded' : 'Load table'}
												</button>
											{:else if candidate.unresolved_reason}
												<span class="orion-paradigm-unresolved">
													{paradigmRelationLabel(candidate.unresolved_reason)}
												</span>
											{/if}
										</div>

										{#if features.length || relations.length}
											<div class="orion-paradigm-tags">
												{#each features as feature}
													<span><b>{feature.key}</b>{feature.value}</span>
												{/each}
												{#each relations as relation}
													<span class="orion-paradigm-relation">{relation}</span>
												{/each}
											</div>
										{/if}

										{#if learning.length}
											<section class="orion-learning-strip">
												<div class="orion-learning-head">
													<span>Learn this form</span>
													<strong>{learningGatewayTitle(learning)}</strong>
												</div>
												{#if learningPrimarySummary(candidate)}
													<p>{learningPrimarySummary(candidate)}</p>
												{/if}
												{#if nativeGateways.length}
													<div class="orion-learning-chips">
														{#each nativeGateways as gateway}
															<span title={gateway.explanation}>
																<b>{gateway.label}</b>
																{gateway.term}
																{#if gateway.role}<em>{gateway.role}</em>{/if}
															</span>
														{/each}
													</div>
												{/if}
												{#if fosterBridges.length}
													<div class="orion-learning-bridges">
														{#each fosterBridges as bridge}
															<span
																class={bridge.status === 'aggregate_candidate'
																	? 'orion-learning-bridge orion-learning-bridge-related'
																	: 'orion-learning-bridge'}
															>
																<b>Try this</b>
																{bridge.learner_action || bridge.plain_english}
															</span>
														{/each}
													</div>
												{/if}
												<a class="orion-learning-open" href="/learn">Open the learning path</a>
											</section>
										{/if}

										{#if paradigmErrors[candidateKey]}
											<div class="orion-paradigm-warning">{paradigmErrors[candidateKey]}</div>
										{/if}

										{#if paradigm}
											<div class="orion-paradigm-tables">
												{#each paradigm.paradigms as block}
													{@const slotGroups = paradigmSlotGroups(block)}
													{@const axisNotes = paradigmTableAxisNotes(block)}
													<section class="orion-paradigm-table">
														<div class="orion-paradigm-table-head">
															<span>{block.label}</span>
															<small>{block.dimensions.join(' · ')}</small>
														</div>
														<section class="orion-table-learning">
															<div class="orion-table-learning-head">
																<span>{paradigmTableLearningTitle(candidate)}</span>
																<p>{paradigmTableLearningSummary(candidate, block)}</p>
															</div>
															{#if axisNotes.length}
																<div class="orion-table-axis-notes">
																	{#each axisNotes as axis}
																		<span><b>{axis.label}</b>{axis.note}</span>
																	{/each}
																</div>
															{/if}
														</section>
														<div class="orion-paradigm-slot-groups">
															{#each slotGroups as group}
																<section class="orion-paradigm-slot-group">
																	<h5>{group.label}</h5>
																	<div class="orion-paradigm-slots">
																		{#each group.slots as slot}
																			<div
																				class={paradigmSlotMatchesCandidate(
																					slot,
																					candidate,
																					encounter?.query ?? ''
																				)
																					? 'orion-paradigm-slot orion-paradigm-slot-match'
																					: 'orion-paradigm-slot'}
																			>
																				<span class="orion-paradigm-slot-feature">
																					{paradigmSlotFeatureSummary(slot.features)}
																				</span>
																				<span class="orion-paradigm-slot-forms">
																					{slot.forms.map((form) => form.text).join(', ')}
																				</span>
																			</div>
																		{/each}
																	</div>
																</section>
															{/each}
														</div>
													</section>
												{/each}
											</div>
										{/if}
									</article>
								{/each}
								{#if paradigmCandidateCuration.hiddenCount}
									<p class="orion-paradigm-hidden-note">
										{countLabel(paradigmCandidateCuration.hiddenCount, 'additional reading')}
										held back from the first view.
									</p>
								{/if}
							</div>
						</section>
					{/if}

					{#each visibleBucketGroups as group}
						{@const groupTool = toolMeta(group.toolId, encounter.language)}
						{@const GroupIcon = toolMnemonic(group.toolId).Icon}
						{@const headwordDisplay = groupHeadwordDisplay(group)}

						<section class="orion-result-group">
							<div class="orion-result-group-head">
								<div class="min-w-0">
									<div class="mb-2 flex flex-wrap items-center gap-2">
										<span class="orion-source-beast" title={toolMnemonic(group.toolId).name}>
											<GroupIcon size={16} />
										</span>
										<span class={`badge ${toolStyle[group.toolId].badge}`}>
											{groupTool.shortLabel}
										</span>
									</div>
									<div class="orion-entry-bookplate">
										<h3
											class={illuminatedTitleClass(headwordDisplay.title)}
											lang={headwordDisplay.primaryLang}
											aria-label={headwordDisplay.title ? headwordDisplay.primary : undefined}
										>
											{#if headwordDisplay.title?.script === 'devanagari'}
												<span class="orion-devanagari-title" aria-hidden="true">
													<span class="orion-devanagari-initial">
														<span class="orion-devanagari-initial-glyph">
															{headwordDisplay.title.initial}
														</span>
													</span>
													{#if headwordDisplay.title.rest}
														<span class="orion-devanagari-connector"></span>
														<span class="orion-devanagari-rest">{headwordDisplay.title.rest}</span>
													{/if}
												</span>
											{:else if headwordDisplay.title}
												<span class="orion-plain-title" aria-hidden="true">
													<span class="orion-plain-initial">
														<span class="orion-plain-initial-glyph">
															{headwordDisplay.title.initial}
														</span>
													</span>
													{#if headwordDisplay.title.rest}
														<span class="orion-plain-rest">{headwordDisplay.title.rest}</span>
													{/if}
												</span>
											{:else}
												{headwordDisplay.primary}
											{/if}
										</h3>
										{#if headwordDisplay.forms.length}
											<div class="orion-headword-forms" aria-label="Headword forms">
												{#each headwordDisplay.forms as form}
													<span class="orion-headword-form">
														<span class="orion-headword-form-label">{form.label}</span>
														{#if form.kind === 'code'}
															<code>{form.value}</code>
														{:else}
															<span>{form.value}</span>
														{/if}
													</span>
												{/each}
											</div>
										{/if}
										{#if groupLead(group)}
											<p class="orion-entry-lead">{groupLead(group)}</p>
										{/if}
									</div>
									<p class="orion-entry-source-line">
										{groupTool.label}
										{#if group.dictionary !== group.toolId}
											<span> · {group.dictionary}</span>
										{/if}
									</p>
								</div>
								<div class="orion-entry-chrome">
									<div class="orion-entry-source-strip">
										{#each groupToolIds(group) as tool}
											{@const ToolIcon = toolMnemonic(tool).Icon}
											<span
												class="orion-source-beast orion-source-beast-sm"
												title={toolMnemonic(tool).name}
											>
												<ToolIcon size={14} />
											</span>
										{/each}
										<span>{readerEntryLabel(group)}</span>
										<span>{countLabel(group.buckets.length, 'section')}</span>
										<span>{countLabel(groupWitnesses(group).length, 'source entry')}</span>
									</div>

									{#if groupCanSwitchTextLayer(group)}
										<div class="flex shrink-0 flex-col items-end gap-1">
											<div class="orion-layer-switch join">
												<button
													type="button"
													class={groupLayerIsSource(group)
														? 'btn btn-xs join-item'
														: 'btn btn-xs join-item btn-secondary'}
													onclick={() => setGroupTextLayer(group, 'reader')}
												>
													Reader English
												</button>
												<button
													type="button"
													class={groupLayerIsSource(group) || !groupHasReaderTranslation(group)
														? 'btn btn-xs join-item btn-secondary'
														: 'btn btn-xs join-item'}
													onclick={() => setGroupTextLayer(group, 'source')}
												>
													{groupSourceLayerLabel(group)}
												</button>
											</div>
											{#if translationModelLabel(groupTranslationModel(group))}
												<div
													class="text-base-content/50 flex items-center gap-1 text-[0.68rem] leading-none"
												>
													<span>EN by {translationModelLabel(groupTranslationModel(group))}</span>
													{#if retryableGroupTranslation(group)}
														<button
															type="button"
															class="btn btn-ghost btn-xs h-5 min-h-0 px-1"
															disabled={groupTranslationRetrying(group)}
															aria-label="Retry English translation"
															title="Retry English translation"
															onclick={() => retryGroupTranslation(group)}
														>
															{#if groupTranslationRetrying(group)}
																<span class="loading loading-spinner loading-xs"></span>
															{:else}
																<RefreshCw size={12} />
															{/if}
														</button>
													{/if}
												</div>
											{/if}
										</div>
									{:else if groupHasTranslationToggle(group)}
										<div class="flex shrink-0 items-center gap-1">
											<span class="badge badge-outline">{groupSourceLayerLabel(group)} only</span>
											{#if retryableGroupTranslation(group)}
												<button
													type="button"
													class="btn btn-ghost btn-xs h-5 min-h-0 px-1"
													disabled={groupTranslationRetrying(group)}
													aria-label="Retry English translation"
													title="Retry English translation"
													onclick={() => retryGroupTranslation(group)}
												>
													{#if groupTranslationRetrying(group)}
														<span class="loading loading-spinner loading-xs"></span>
													{:else}
														<RefreshCw size={12} />
													{/if}
												</button>
											{/if}
										</div>
									{/if}
									{#if groupAwaitsReaderTranslation(group)}
										<span class="orion-translator-sigil" title={uiCopy.translator.title}>
											<span>{uiCopy.translator.badge}</span>
											<i></i><i></i><i></i>
										</span>
									{/if}
								</div>
							</div>

							<article class={`orion-entry-reader ${toolStyle[group.toolId].accent}`}>
								<div class="orion-reader-sections">
									{#each visibleGroupBuckets(group) as bucket}
										{@const segments = sectionSegments(bucket)}
										{@const hasTreeChildren = sectionHasTreeChildren(group, bucket)}
										<section
											id={sectionId(group, bucket)}
											class={readerSectionClass(bucket)}
											style={readerSectionStyle(bucket)}
										>
											<div class="orion-reader-marker">
												{#if hasTreeChildren}
													<button
														type="button"
														class="orion-branch-toggle"
														aria-label={branchToggleLabel(bucket)}
														title={branchToggleLabel(bucket)}
														onclick={() => toggleBranchCollapse(bucket)}
													>
														<Asterisk
															size={11}
															strokeWidth={2.2}
															class={collapsedBranches[sectionExpansionKey(bucket)]
																? 'orion-branch-mark-collapsed'
																: ''}
														/>
													</button>
												{/if}
											</div>
											<div class="orion-reader-copy">
												{#each segments as gloss, segmentIndex}
													<p>
														{gloss}
														{#if segmentIndex === segments.length - 1}
															{#if sectionCanToggle(bucket)}
																<button
																	type="button"
																	class="orion-section-detail-toggle"
																	aria-label={sectionToggleLabel(bucket)}
																	title={sectionToggleLabel(bucket)}
																	onclick={() => toggleSectionExpansion(bucket)}
																>
																	<ChevronDown
																		size={12}
																		class={expandedSections[sectionExpansionKey(bucket)]
																			? 'orion-chevron-open'
																			: ''}
																	/>
																</button>
															{/if}
															{#if sectionShowsReturnedEndingNote(bucket)}
																<span class="orion-section-detail-note"
																	>{uiCopy.results.returnedEnding}</span
																>
															{/if}
														{/if}
													</p>
												{/each}
											</div>
										</section>
									{/each}
								</div>
							</article>
						</section>
					{:else}
						<div class="alert alert-info">
							<Database size={18} />
							<span>{uiCopy.results.noFilterMatch}</span>
						</div>
					{/each}
				{/if}
			</section>
		</article>

		<aside
			class={sidebarFullHeight
				? 'orion-sidebar orion-sidebar-full min-w-0 space-y-4'
				: 'orion-sidebar min-w-0 space-y-4'}
			onwheel={handleSidebarWheel}
		>
			{#if query.trim() || wordIndexSectionItems.length || wordIndexEarmarks.length}
				<section class="card orion-manuscript-panel w-full min-w-0">
					<div class="card-body min-w-0 gap-3 p-4">
						<h2 class="card-title text-base">
							<Compass size={17} />
							{uiCopy.wordIndex.title}
							{#if wordIndexLoading && !wordIndexInitialLoading}
								<span class="orion-index-busy" title={uiCopy.wordIndex.loading}>
									<span class="loading loading-spinner loading-xs"></span>
								</span>
							{/if}
						</h2>
						<p class="text-base-content/65 font-serif text-xs leading-5">
							{uiCopy.wordIndex.intro}
						</p>

						{#if wordIndexSectionItems.length}
							<section class="orion-index-section-rail" aria-label={wordIndexSectionsTitle}>
								<div class="orion-index-section-head">
									<span>{wordIndexSectionsTitle}</span>
									<div class="orion-index-section-actions">
										{#if activeWordIndexSection?.anchor?.query}
											<button
												type="button"
												class="orion-index-section-browse"
												onclick={() => browseWordIndexSection(activeWordIndexSection)}
											>
												{uiCopy.wordIndex.browseSection}
											</button>
										{/if}
										{#if wordIndexSectionsLoading}
											<span title={uiCopy.wordIndex.sectionsLoading}>
												<span class="loading loading-spinner loading-xs"></span>
											</span>
										{/if}
									</div>
								</div>
								<div class="orion-index-section-list">
									{#each wordIndexSectionItems as section}
										{@const sectionCanOpen = Boolean(wordIndexSectionLookupTarget(section))}
										<button
											type="button"
											class={activeWordIndexSection?.id === section.id
												? 'orion-index-section-button orion-index-section-button-active'
												: sectionCanOpen
													? 'orion-index-section-button'
													: 'orion-index-section-button orion-index-section-button-unavailable'}
											disabled={!sectionCanOpen}
											title={`${section.label} ${section.transliteration}`}
											aria-current={activeWordIndexSection?.id === section.id ? 'true' : undefined}
											onclick={() => openWordIndexSection(section)}
										>
											<span>{section.label}</span>
											<small>{section.transliteration}</small>
										</button>
									{/each}
								</div>
							</section>
						{:else if wordIndexSectionsError}
							<div class="orion-motd-warning">{wordIndexSectionsError}</div>
						{/if}

						{#if wordIndexInitialLoading}
							<div class="orion-index-skeleton" aria-busy="true">
								<span></span>
								<span></span>
								<span></span>
								<span class="sr-only">{uiCopy.wordIndex.loading}</span>
							</div>
						{:else if wordIndexHasRows}
							<div class="orion-index-groups">
								<section class="orion-index-group">
									<div class="orion-index-group-head">
										<span class="orion-source-beast orion-source-beast-sm">
											<Compass size={13} />
										</span>
										<span>{wordIndexOrderTitle}</span>
										<span>{wordIndexSourceSetCount} source sets</span>
									</div>

									<div class="orion-index-rows">
										{#each wordIndexMergedRows as row}
											{@const item = wordIndexPrimaryItem(row)}
											{@const position = wordIndexRowPosition(row)}
											{@const matched = wordIndexRowMatched(row)}
											<div
												class={matched
													? 'orion-index-row orion-index-row-matched'
													: position === 'anchor'
														? 'orion-index-row orion-index-row-anchor'
														: 'orion-index-row'}
											>
												<a
													class="orion-index-link"
													href={wordIndexHref(item)}
													aria-current={position === 'anchor' ? 'page' : undefined}
													onclick={(event) => handleWordIndexNavigation(event, item)}
												>
													<span class="orion-index-word">{wordIndexDisplay(item)}</span>
													<span class="orion-index-source-list">
														{#each wordIndexRowSources(row) as source}
															<span>{source}</span>
														{/each}
													</span>
													{#if wordIndexLookup(item)}
														<span class="orion-index-lookup">{wordIndexLookup(item)}</span>
													{/if}
													{#if wordIndexEntryCountLabel(item)}
														<span class="orion-index-entry-count">
															{wordIndexEntryCountLabel(item)}
														</span>
													{/if}
													<span class="orion-index-position">
														{matched
															? uiCopy.wordIndex.active
															: uiCopy.wordIndex.position(position)}
													</span>
												</a>
												<button
													type="button"
													class="orion-index-earmark"
													title={isEarmarked(item)
														? uiCopy.wordIndex.removeEarmarkTitle
														: uiCopy.wordIndex.earmarkTitle}
													aria-label={isEarmarked(item)
														? uiCopy.wordIndex.removeEarmarkTitle
														: uiCopy.wordIndex.earmarkTitle}
													onclick={() => toggleWordIndexEarmark(item)}
												>
													{#if isEarmarked(item)}
														<BookmarkCheck size={14} />
													{:else}
														<BookmarkPlus size={14} />
													{/if}
												</button>
											</div>
										{/each}
									</div>
								</section>
							</div>
						{:else if wordIndexError}
							<div class="orion-motd-warning">{wordIndexError}</div>
						{:else if wordIndex}
							<div class="orion-motd-warning">
								{wordIndexWarnings[0]?.message || uiCopy.wordIndex.empty}
							</div>
						{/if}

						{#if wordIndexEarmarks.length}
							<div class="orion-earmarks">
								<div class="orion-earmarks-head">
									<div class="orion-earmarks-title">{uiCopy.wordIndex.earmarks}</div>
									<button
										type="button"
										class="orion-earmarks-clear"
										title={uiCopy.wordIndex.clearEarmarksTitle}
										onclick={clearWordIndexEarmarks}
									>
										<Eraser size={12} />
										{uiCopy.wordIndex.clearEarmarks}
									</button>
								</div>
								<div class="orion-earmark-list">
									{#each wordIndexEarmarks as item}
										<a
											class="orion-earmark-link"
											href={wordIndexHref(item)}
											onclick={(event) => handleWordIndexNavigation(event, item)}
										>
											<span>{wordIndexDisplay(item)}</span>
											<small>{languageLabel(item.encounter.language)}</small>
										</a>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</section>
			{/if}

			<fieldset class="fieldset orion-manuscript-panel w-full min-w-0 p-4">
				<legend class="fieldset-legend gap-2">
					<SlidersHorizontal size={16} />
					{uiCopy.sidebar.sourceTitle}
				</legend>

				<p class="text-base-content/65 mb-3 font-serif text-xs leading-5">
					{uiCopy.sidebar.sourceIntro}
				</p>

				<div class="orion-source-grid">
					<button
						type="button"
						class={isAllLookupSelected
							? 'orion-tool-chip orion-tool-chip-active'
							: 'orion-tool-chip'}
						onclick={showAllLookupTools}
						title={uiCopy.sidebar.generatorAllTitle}
					>
						<span class="orion-tool-icon">
							<BookOpen size={16} />
						</span>
						<span class="orion-tool-chip-label">{uiCopy.sidebar.all}</span>
						{#if isAllLookupSelected}
							<CheckCircle2 size={14} class="orion-tool-check" />
						{/if}
					</button>

					{#each availableTools as tool}
						{@const MnemonicIcon = toolMnemonic(tool.id).Icon}
						<button
							type="button"
							class={lookupTools.includes(tool.id)
								? 'orion-tool-chip orion-tool-chip-active'
								: 'orion-tool-chip'}
							onclick={() => toggleLookupTool(tool.id)}
							title={`${toolMnemonic(tool.id).name}: ${tool.description}`}
						>
							<span class="orion-tool-icon">
								<MnemonicIcon size={16} />
							</span>
							<span class="orion-tool-chip-label">{tool.shortLabel}</span>
							{#if lookupTools.includes(tool.id)}
								<CheckCircle2 size={14} class="orion-tool-check" />
							{/if}
						</button>
					{/each}
				</div>
			</fieldset>

			{#if encounter?.buckets.length}
				<fieldset class="fieldset orion-manuscript-panel w-full min-w-0 p-4">
					<legend class="fieldset-legend gap-2">
						<Database size={16} />
						{uiCopy.sidebar.returnedTitle}
					</legend>

					<div class="orion-source-grid">
						<button
							type="button"
							class={visibleTools.length === returnedToolIds.length
								? 'orion-tool-chip orion-tool-chip-active'
								: 'orion-tool-chip'}
							onclick={showAllReturnedTools}
							title={uiCopy.sidebar.showLoaded}
						>
							<span class="orion-tool-icon">
								<Database size={16} />
							</span>
							<span class="orion-tool-chip-label">{uiCopy.sidebar.all}</span>
						</button>

						{#each returnedToolIds as toolId}
							{@const tool = toolMeta(toolId, encounter.language)}
							{@const MnemonicIcon = toolMnemonic(toolId).Icon}
							<button
								type="button"
								class={visibleTools.includes(toolId)
									? 'orion-tool-chip orion-tool-chip-active'
									: 'orion-tool-chip'}
								onclick={() => toggleVisibleTool(toolId)}
								title={`${toolMnemonic(toolId).name}: ${tool.label}`}
							>
								<span class="orion-tool-icon">
									<MnemonicIcon size={16} />
								</span>
								<span class="orion-tool-chip-label">{tool.shortLabel}</span>
								{#if visibleTools.includes(toolId)}
									<CheckCircle2 size={14} class="orion-tool-check" />
								{/if}
							</button>
						{/each}
					</div>
				</fieldset>
			{/if}

			{#if encounter}
				<section class="card orion-manuscript-panel w-full min-w-0">
					<div class="card-body min-w-0 gap-3 p-4">
						<h2 class="card-title text-base">
							<Sparkles size={17} />
							{uiCopy.colophon.title}
						</h2>
						<div class="flex flex-wrap gap-2">
							{#each encounter.lexeme_anchors as anchor}
								<span class="badge badge-outline">{anchor}</span>
							{/each}
						</div>
						<div class="rounded-box bg-base-200 p-3 text-sm leading-6">
							<div class="font-medium">{uiCopy.colophon.translationAccount}</div>
							<div class="text-base-content/65">
								{encounter.translation_cache.after.hits}/{encounter.translation_cache.after.total} hits,
								{encounter.translation_cache.written} written
							</div>
							<div class="text-base-content/65">Account: {cacheSummary(encounter)}</div>
						</div>
						<div class="rounded-box bg-base-200 p-3 text-sm leading-6">
							<div class="font-medium">{uiCopy.colophon.requestSeal}</div>
							<div class="text-base-content/65">
								backend={encounter.backend}, translation={encounter.request.translation_mode},
								reader={encounter.request.reader_lang}
							</div>
							<div class="text-base-content/65 mt-1">{readerLayerStatus()}</div>
						</div>
						{#if encounter.warnings.length}
							<div class="alert alert-warning text-sm">
								{encounter.warnings[0]}
							</div>
						{/if}
					</div>
				</section>
			{/if}

			<section class="card orion-manuscript-panel w-full min-w-0">
				<div class="card-body min-w-0 gap-3 p-4">
					<h2 class="card-title text-base">
						<span class="flex min-w-0 flex-1 items-center gap-2">
							<Sparkles size={17} />
							{uiCopy.pageMarks.title}
						</span>
						<button
							type="button"
							class="btn btn-ghost btn-xs gap-1"
							onclick={clearRouteState}
							title={uiCopy.pageMarks.clearTitle}
						>
							<Eraser size={14} />
							Clear
						</button>
					</h2>
					<div>
						<div class="text-base-content/50 mb-1 text-xs font-medium uppercase">
							{uiCopy.pageMarks.pageLink}
						</div>
						<div class="mockup-code orion-endpoint-code w-full min-w-0 overflow-x-auto text-xs">
							<pre class="break-all whitespace-pre-wrap"><code
									>{appRouteUrl(encounterMatchesQuery())}</code
								></pre>
						</div>
					</div>
					<div>
						<div class="text-base-content/50 mb-1 text-xs font-medium uppercase">
							{uiCopy.pageMarks.endpoint}
						</div>
						<div class="mockup-code orion-endpoint-code w-full min-w-0 overflow-x-auto text-xs">
							<pre class="break-all whitespace-pre-wrap"><code>{endpointUrl()}</code></pre>
						</div>
					</div>
					<p class="text-base-content/65 font-serif text-sm leading-6">
						{uiCopy.pageMarks.contractPrefix}
						<code>dictionary=all</code>
						{uiCopy.pageMarks.contractSuffix}
					</p>
				</div>
			</section>
		</aside>
	</div>
</main>
