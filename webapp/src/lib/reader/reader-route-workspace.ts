import { browser } from '$app/environment';
import { parseReaderRouteState, type ReaderRouteState } from '$lib/reader';
import {
	buildCurrentReaderRouteState,
	buildReaderRouteUrlUpdate,
	defaultReaderAddressForLanguage,
	type ReaderRouteOverrides
} from '$lib/reader/page-routing';
import {
	buildStoredReaderIndexState,
	readStoredReaderIndexState,
	writeStoredReaderIndexState
} from '$lib/reader/index-storage';

export type ReaderHistoryMode = 'push' | 'replace' | 'none';

export type ReaderRouteWorkspaceState = {
	[key: string]: any;
};

type ReaderRouteWorkspaceDeps = {
	loadCatalogs: () => Promise<void>;
	loadChosenReaderView: (historyMode?: ReaderHistoryMode) => Promise<void>;
	onHydrateSelectedWord?: (word: string) => void;
	applyReaderRouteContent: (
		route: Partial<ReaderRouteState>,
		historyMode: ReaderHistoryMode
	) => Promise<void>;
	loadAllReaderIndexStats: () => Promise<void>;
};

export type ReaderRouteWorkspaceMethods = {
	initializeReaderFromUrl: () => Promise<void>;
	rehydrateReaderFromUrl: () => Promise<void>;
	loadChosenReaderView: (historyMode?: ReaderHistoryMode) => Promise<void>;
	setTheme: (nextTheme: 'manuscript' | 'vespers', sync?: boolean) => void;
	hydrateFromUrl: () => Partial<ReaderRouteState>;
	applyReaderRouteState: (route: Partial<ReaderRouteState>) => void;
	updateReaderUrl: (overrides?: ReaderRouteOverrides, historyMode?: ReaderHistoryMode) => void;
	currentReaderRouteState: () => Partial<ReaderRouteState>;
	restoreReaderIndexState: () => boolean;
	saveReaderIndexState: () => void;
	applyReaderRouteContent: (
		route: Partial<ReaderRouteState>,
		historyMode: ReaderHistoryMode
	) => Promise<void>;
};

export function createReaderRouteWorkspace(
	state: ReaderRouteWorkspaceState,
	deps: ReaderRouteWorkspaceDeps
): ReaderRouteWorkspaceMethods {
	async function initializeReaderFromUrl() {
		const route = hydrateFromUrl();
		const restored = restoreReaderIndexState();
		applyReaderRouteState(route);
		if (!restored || !state.catalogId || !state.catalogs.length) await deps.loadCatalogs();
		else {
			void deps.loadAllReaderIndexStats();
			await deps.loadChosenReaderView('replace');
		}
		await deps.applyReaderRouteContent(route, 'replace');
		updateReaderUrl({}, 'replace');
	}

	async function rehydrateReaderFromUrl() {
		const route = hydrateFromUrl();
		applyReaderRouteState(route);
		if (!state.catalogId || !state.catalogs.length) await deps.loadCatalogs();
		else await deps.loadChosenReaderView('replace');
		await deps.applyReaderRouteContent(route, 'replace');
	}

	function loadChosenReaderView(historyMode: ReaderHistoryMode = 'replace') {
		return deps.loadChosenReaderView(historyMode);
	}

	function setTheme(nextTheme: 'manuscript' | 'vespers', sync = true) {
		state.theme = nextTheme;
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
		if (route.language) state.language = route.language;
		if (route.catalogId) state.catalogId = route.catalogId;
		if (route.theme) setTheme(route.theme, false);
		const hasTextSearchRoute = Boolean(
			route.readerView === 'search' || route.textQuery || route.textSearchCursor
		);
		const hasShelfRoute =
			Boolean(route.readerView === 'shelves') ||
			Boolean(route.query || route.discoveryGroup || route.discoveryTag || route.worksCursor);
		state.readerView =
			route.discoveryAuthorId || route.authorId || route.authorSection
				? 'authors'
				: route.readerView === 'authors'
					? 'authors'
					: hasTextSearchRoute
						? 'search'
						: hasShelfRoute
							? 'shelves'
							: 'choose';

		state.showTransliteration = route.transliteration ?? false;
		state.workQuery = route.query ?? '';
		state.textQuery = route.textQuery ?? '';
		state.textSearchMode = route.textSearchMode ?? 'fuzzy';
		state.discoveryGroup = route.discoveryGroup ?? '';
		state.discoveryTag = route.discoveryTag ?? '';
		state.discoveryAuthorId = route.discoveryAuthorId ?? '';
		state.discoveryAuthorLabel = route.discoveryAuthorLabel ?? '';
		state.discoverySort = route.discoverySort ?? 'global-popularity';
		state.authorAgentKind = route.authorAgentKind ?? '';
		state.authorHistoricity = route.authorHistoricity ?? '';
		state.activeAuthorSection = route.authorSection ?? '';
		state.routeAuthorId = route.authorId ?? '';
		state.routeAuthorName = route.authorName ?? '';
		if (!route.authorId) state.selectedAuthor = null;
		state.authorsCursorParam = route.authorsCursor ?? null;
		state.textSearchCursorParam = route.textSearchCursor ?? null;
		state.worksCursorParam = route.worksCursor ?? null;
		state.contentsCursorParam = route.contentsCursor ?? null;
		state.pageCursorParam = route.pageCursor ?? null;
		state.activeCollection = route.collection ?? 'all';
		state.selectedWord = route.selectedWord ?? '';
		state.selectedWordBriefing = null;
		state.selectedWordBriefingError = '';
		state.selectedWordBriefingGenerating = false;
		if (state.selectedWord && deps.onHydrateSelectedWord) {
			deps.onHydrateSelectedWord(state.selectedWord);
		}

		if (route.address) {
			state.addressInput = route.address;
			state.showAddressLookup = true;
		} else if (!route.work && !route.segment) {
			state.addressInput = defaultReaderAddressForLanguage(state.language);
		}

		if (!route.work && !route.segment) {
			state.selectedWork = null;
			state.selectedSegment = null;
			state.contents = [];
			state.structure = [];
			state.workDossier = null;
			state.pageSegments = [];
			state.navigation = { previous: null, next: null };
			state.pageNextCursor = null;
			state.pagePrevCursor = null;
		}
	}

	function updateReaderUrl(
		overrides: ReaderRouteOverrides = {},
		historyMode: ReaderHistoryMode = 'replace'
	) {
		if (!browser || historyMode === 'none') return;
		const currentUrl = `${window.location.pathname}${window.location.search}`;
		const nextUrl = buildReaderRouteUrlUpdate({
			currentUrl,
			state: currentReaderRouteState(),
			overrides
		});
		if (!nextUrl) return;
		if (historyMode === 'push') window.history.pushState({}, '', nextUrl);
		else window.history.replaceState({}, '', nextUrl);
	}

	function currentReaderRouteState(): Partial<ReaderRouteState> {
		const work = state.selectedWork ? state.selectedWork.work_id : state.selectedSegment?.work_id || undefined;
		const segment = state.selectedSegment?.citation_path || undefined;
		return buildCurrentReaderRouteState({
			language: state.language,
			catalogId: state.catalogId,
			readerView: state.readerView,
			selectedWork: state.selectedWork,
			selectedSegment: state.selectedSegment,
			addressInput: state.addressInput,
			showAddressLookup: state.showAddressLookup,
			workQuery: state.workQuery,
			textQuery: state.textQuery,
			textSearchMode: state.textSearchMode,
			textSearchCursorParam: state.textSearchCursorParam,
			discoveryGroup: state.discoveryGroup,
			discoveryTag: state.discoveryTag,
			discoveryAuthorId: state.discoveryAuthorId,
			discoveryAuthorLabel: state.discoveryAuthorLabel,
			discoverySort: state.discoverySort,
			authorAgentKind: state.authorAgentKind,
			authorHistoricity: state.authorHistoricity,
			activeAuthorSection: state.activeAuthorSection,
			routeAuthorId: state.routeAuthorId,
			routeAuthorName: state.routeAuthorName,
			authorsCursorParam: state.authorsCursorParam,
			worksCursorParam: state.worksCursorParam,
			contentsCursorParam: state.contentsCursorParam,
			pageCursorParam: state.pageCursorParam,
			activeCollection: state.activeCollection,
			selectedWord: state.selectedWord,
			theme: state.theme,
			showTransliteration: state.showTransliteration,
			selectedAuthorId: state.selectedAuthor?.author_id
		});
	}

	function restoreReaderIndexState() {
		if (!browser) return false;
		const stored = readStoredReaderIndexState(sessionStorage, {
			language: state.language,
			catalogId: state.catalogId
		});
		if (!stored) return false;

		state.catalogId = stored.catalogId;
		state.readerView = stored.readerView;
		state.activeAuthorSection = stored.activeAuthorSection;
		state.workQuery = stored.workQuery;
		state.textQuery = stored.textQuery;
		state.textSearchMode = stored.textSearchMode;
		state.discoveryGroup = stored.discoveryGroup;
		state.discoveryTag = stored.discoveryTag;
		state.discoveryAuthorId = stored.discoveryAuthorId;
		state.discoveryAuthorLabel = stored.discoveryAuthorLabel;
		state.discoverySort = stored.discoverySort;
		state.authorAgentKind = stored.authorAgentKind;
		state.authorHistoricity = stored.authorHistoricity;
		state.worksNextCursor = stored.worksNextCursor ?? null;
		state.worksPrevCursor = stored.worksPrevCursor ?? null;
		state.authorsNextCursor = stored.authorsNextCursor ?? null;
		state.authorsPrevCursor = stored.authorsPrevCursor ?? null;
		state.textSearchNextCursor = stored.textSearchNextCursor ?? null;
		state.textSearchPrevCursor = stored.textSearchPrevCursor ?? null;
		state.libraryLoading = false;
		state.authorsLoading = false;
		state.textSearchLoading = false;
		state.catalogError = '';
		state.authorsError = '';
		state.textSearchError = '';
		return true;
	}

	function saveReaderIndexState() {
		if (!browser || !state.catalogId || !state.catalogs.length) return;
		const stored = buildStoredReaderIndexState({
			language: state.language,
			catalogId: state.catalogId,
			readerView: state.readerView,
			activeAuthorSection: state.activeAuthorSection,
			workQuery: state.workQuery,
			textQuery: state.textQuery,
			textSearchMode: state.textSearchMode,
			discoveryGroup: state.discoveryGroup,
			discoveryTag: state.discoveryTag,
			discoveryAuthorId: state.discoveryAuthorId,
			discoveryAuthorLabel: state.discoveryAuthorLabel,
			discoverySort: state.discoverySort,
			authorAgentKind: state.authorAgentKind,
			authorHistoricity: state.authorHistoricity,
			worksNextCursor: state.worksNextCursor,
			worksPrevCursor: state.worksPrevCursor,
			authorsNextCursor: state.authorsNextCursor,
			authorsPrevCursor: state.authorsPrevCursor,
			textSearchNextCursor: state.textSearchNextCursor,
			textSearchPrevCursor: state.textSearchPrevCursor
		});
		writeStoredReaderIndexState(sessionStorage, stored);
	}

	async function applyReaderRouteContent(
		route: Partial<ReaderRouteState>,
		historyMode: ReaderHistoryMode
	) {
		return deps.applyReaderRouteContent(route, historyMode);
	}

	return {
		initializeReaderFromUrl,
		rehydrateReaderFromUrl,
		loadChosenReaderView,
		setTheme,
		hydrateFromUrl,
		applyReaderRouteState,
		applyReaderRouteContent,
		updateReaderUrl,
		currentReaderRouteState,
		restoreReaderIndexState,
		saveReaderIndexState
	};
}
