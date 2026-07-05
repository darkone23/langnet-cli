import {
	clearDeskBrowserStorage,
	clearDeskStateStorage,
	clearDeskThemeStorage,
	readDeskStateFromBrowserStorage,
	restoreDeskStateFromStorage,
	writeDeskStateToBrowserStorage,
	writeDeskWordIndexEarmarksToBrowserStorage
} from './desk-route-workspace';
import type { DeskTheme } from './desk-route';
import type {
	EncounterResult,
	LanguageMode,
	SearchBackend,
	ToolId,
	TranslationMode
} from '../search-data';
import type { WordIndexItem, WordIndexResponse, WordIndexSectionsResponse } from '../word-index';

type OptionalStorage = Storage | null | undefined;

export type DeskRouteStorageState = {
	language: LanguageMode;
	query: string;
	backendMode: SearchBackend;
	translationMode: TranslationMode;
	theme: DeskTheme;
	lookupTools: ToolId[];
	visibleTools: ToolId[];
	encounter: EncounterResult | null;
	textLayers: Record<string, 'reader' | 'source'>;
	expandedSections: Record<string, boolean>;
	collapsedBranches: Record<string, boolean>;
	wordIndex: WordIndexResponse | null;
	wordIndexSections: WordIndexSectionsResponse | null;
	wordIndexEarmarks: WordIndexItem[];
	loading: boolean;
	enrichingTranslations: boolean;
	errorMessage: string;
	enrichmentError: string;
};

type DeskRouteStorageControllerDeps = {
	browser: boolean;
	localStorage: OptionalStorage;
	sessionStorage: OptionalStorage;
	setDocumentTheme?: (theme: DeskTheme) => void;
};

export function createDeskRouteStorageController(
	state: DeskRouteStorageState,
	deps: DeskRouteStorageControllerDeps
) {
	function saveWordIndexEarmarks() {
		writeDeskWordIndexEarmarksToBrowserStorage(deps.browser ? deps.localStorage : null, state.wordIndexEarmarks);
	}

	function saveDeskState() {
		if (!deps.browser || !deps.sessionStorage) return;

		if (!state.query.trim() && !state.encounter) {
			clearDeskStateStorage(deps.sessionStorage);
			return;
		}

		writeDeskStateToBrowserStorage(deps.sessionStorage, {
			language: state.language,
			query: state.query,
			backendMode: state.backendMode,
			translationMode: state.translationMode,
			theme: state.theme,
			lookupTools: state.lookupTools,
			visibleTools: state.visibleTools,
			encounter: state.encounter,
			textLayers: state.textLayers,
			expandedSections: state.expandedSections,
			collapsedBranches: state.collapsedBranches,
			wordIndex: state.wordIndex,
			wordIndexSections: state.wordIndexSections
		});
	}

	function clearStoredThemeState() {
		if (!deps.browser || !deps.localStorage) return;

		try {
			clearDeskThemeStorage(deps.localStorage);
			deps.setDocumentTheme?.('manuscript');
		} catch {
			// Ignore storage failures.
		}
	}

	function clearAppStorage() {
		if (!deps.browser) return;
		clearDeskBrowserStorage({
			localStorage: deps.localStorage,
			sessionStorage: deps.sessionStorage
		});
		clearStoredThemeState();
	}

	function restoreDeskState(params: URLSearchParams) {
		const stored = readDeskStateFromBrowserStorage(deps.browser ? deps.sessionStorage : null);
		const restored = restoreDeskStateFromStorage({
			params,
			stored,
			language: state.language,
			query: state.query,
			backendMode: state.backendMode,
			translationMode: state.translationMode,
			lookupTools: state.lookupTools
		});
		if (!restored) return false;

		state.theme = restored.theme ?? state.theme;
		state.lookupTools = restored.lookupTools;
		state.encounter = restored.encounter;
		state.visibleTools = restored.visibleTools;
		state.textLayers = restored.textLayers;
		state.expandedSections = restored.expandedSections;
		state.collapsedBranches = restored.collapsedBranches;
		state.loading = false;
		state.enrichingTranslations = false;
		state.errorMessage = '';
		state.enrichmentError = '';
		state.wordIndex = restored.wordIndex;
		state.wordIndexSections = restored.wordIndexSections;
		return Boolean(state.encounter);
	}

	return {
		clearAppStorage,
		restoreDeskState,
		saveDeskState,
		saveWordIndexEarmarks
	};
}
