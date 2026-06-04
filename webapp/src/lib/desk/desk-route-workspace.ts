import { currentDeskRouteKey, type DeskTheme } from './desk-route';
import {
	readStoredDeskState,
	readStoredMotd,
	readStoredWordIndexEarmarks,
	saveStoredDeskState,
	saveStoredMotd,
	saveStoredWordIndexEarmarks,
	type StoredDeskState
} from './desk-storage';
import {
	type EncounterResult,
	type LanguageMode,
	type SearchBackend,
	type ToolId,
	type TranslationMode,
	type WordRecommendationResult
} from '../search-data';
import {
	encounterMatchesStoredRoute,
	encounterNeedsFreshReaderLayer,
	returnedToolsForEncounter,
	validStoredTools
} from './desk-session';
import type { WordIndexItem, WordIndexResponse, WordIndexSectionsResponse } from '../word-index';

export const MOTD_STORAGE_KEY = 'orion-motd-cache:v5';
export const DESK_STATE_STORAGE_KEY = 'orion-desk-state:v5';
export const WORD_INDEX_EARMARK_STORAGE_KEY = 'orion-word-index-earmarks:v1';
export const DESK_SESSION_STORAGE_TTL_MS = 2 * 60 * 60 * 1000;

const legacyMotdStorageKeys = [
	'orion-motd-cache:v4',
	'orion-motd-cache:v3',
	'orion-motd-cache:v2',
	'orion-motd-cache:v1'
] as const;
const legacyDeskStorageKeys = [
	'orion-desk-state:v4',
	'orion-desk-state:v3',
	'orion-desk-state:v2',
	'orion-desk-state:v1'
] as const;
const legacyThemeStorageKey = 'orion-theme';
type OptionalStorage = Storage | null | undefined;

export function readDeskMotdFromBrowserStorage(
	storage: OptionalStorage,
	normalize: (result: WordRecommendationResult) => WordRecommendationResult
) {
	if (!storage) return { result: null, stale: false };
	return readDeskMotdFromStorage(storage, normalize);
}

export function writeDeskMotdToBrowserStorage(
	storage: OptionalStorage,
	result: WordRecommendationResult
) {
	if (!storage) return;
	return writeDeskMotdToStorage(storage, result);
}

export function readDeskWordIndexEarmarksFromBrowserStorage(storage: OptionalStorage) {
	if (!storage) return [];
	return readDeskWordIndexEarmarksFromStorage(storage);
}

export function writeDeskWordIndexEarmarksToBrowserStorage(
	storage: OptionalStorage,
	items: WordIndexItem[]
) {
	if (!storage) return;
	return writeDeskWordIndexEarmarksToStorage(storage, items);
}

export function readDeskStateFromBrowserStorage(storage: OptionalStorage) {
	if (!storage) return null;
	return readDeskStateFromStorage(storage);
}

export function writeDeskStateToBrowserStorage(
	storage: OptionalStorage,
	input: Parameters<typeof writeDeskStateToStorage>[1]
) {
	if (!storage) return;
	return writeDeskStateToStorage(storage, input);
}

export function clearDeskBrowserStorage(storage: {
	localStorage: OptionalStorage;
	sessionStorage: OptionalStorage;
}) {
	if (storage.sessionStorage) clearDeskStateStorage(storage.sessionStorage);
	if (storage.localStorage) {
		clearDeskMotdState(storage.localStorage);
		clearDeskWordIndexState(storage.localStorage);
		clearDeskThemeStorage(storage.localStorage);
	}
}

export function readDeskMotdFromStorage(
	storage: Storage,
	normalize: (result: WordRecommendationResult) => WordRecommendationResult
) {
	return readStoredMotd(storage, MOTD_STORAGE_KEY, normalize);
}

export function writeDeskMotdToStorage(storage: Storage, result: WordRecommendationResult) {
	return saveStoredMotd(storage, MOTD_STORAGE_KEY, result);
}

export function clearDeskMotdState(storage: Storage) {
	storage.removeItem(MOTD_STORAGE_KEY);
	for (const key of legacyMotdStorageKeys) storage.removeItem(key);
}

export function readDeskWordIndexEarmarksFromStorage(storage: Storage) {
	return readStoredWordIndexEarmarks(storage, WORD_INDEX_EARMARK_STORAGE_KEY);
}

export function writeDeskWordIndexEarmarksToStorage(storage: Storage, items: WordIndexItem[]) {
	return saveStoredWordIndexEarmarks(storage, WORD_INDEX_EARMARK_STORAGE_KEY, items);
}

export function clearDeskWordIndexState(storage: Storage) {
	storage.removeItem(WORD_INDEX_EARMARK_STORAGE_KEY);
}

export function readDeskStateFromStorage(storage: Storage) {
	return readStoredDeskState(storage, DESK_STATE_STORAGE_KEY);
}

export function writeDeskStateToStorage(
	storage: Storage,
	input: {
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
	}
) {
	const state: StoredDeskState = {
		version: 5,
		expiresAt: Date.now() + DESK_SESSION_STORAGE_TTL_MS,
		routeKey: currentDeskRouteKey({
			language: input.language,
			query: input.query,
			backendMode: input.backendMode,
			translationMode: input.translationMode,
			lookupTools: input.lookupTools
		}),
		language: input.language,
		query: input.query,
		backendMode: input.backendMode,
		translationMode: input.translationMode,
		theme: input.theme,
		lookupTools: input.lookupTools,
		visibleTools: input.visibleTools,
		encounter: input.encounter,
		textLayers: input.textLayers,
		expandedSections: input.expandedSections,
		collapsedBranches: input.collapsedBranches,
		wordIndex: input.wordIndex,
		wordIndexSections: input.wordIndexSections
	};
	return saveStoredDeskState(storage, DESK_STATE_STORAGE_KEY, state);
}

export function clearDeskStateStorage(storage: Storage) {
	storage.removeItem(DESK_STATE_STORAGE_KEY);
	for (const key of legacyDeskStorageKeys) storage.removeItem(key);
}

export function clearDeskThemeStorage(storage: Storage) {
	storage.removeItem(legacyThemeStorageKey);
}

export function restoreDeskStateFromStorage(args: {
	stored: StoredDeskState | null;
	params: URLSearchParams;
	language: LanguageMode;
	query: string;
	backendMode: SearchBackend;
	translationMode: TranslationMode;
	lookupTools: ToolId[];
}) {
	const { stored, params, language, query, backendMode, translationMode, lookupTools } = args;

	if (!stored?.query || !params.has('q')) return null;
	if (
		stored.routeKey &&
		stored.routeKey !==
			currentDeskRouteKey({ language, query, backendMode, translationMode, lookupTools })
	) {
		return null;
	}
	if (stored.language !== language) return null;
	if (stored.query.trim().toLowerCase() !== query.trim().toLowerCase()) return null;
	if (stored.backendMode && stored.backendMode !== backendMode) return null;
	if (stored.translationMode && stored.translationMode !== translationMode) return null;

	const restoredLookupTools = validStoredTools(stored.lookupTools, language) || lookupTools;
	const restoredEncounter =
		encounterMatchesStoredRoute(stored.encounter, language, query) &&
		stored.encounter &&
		!encounterNeedsFreshReaderLayer(stored.encounter)
			? stored.encounter
			: null;
	const visibleTools = restoredEncounter
		? validStoredTools(stored.visibleTools, language) ||
			returnedToolsForEncounter(restoredEncounter)
		: [];

	return {
		theme:
			stored.theme === 'manuscript' || stored.theme === 'vespers'
				? (stored.theme as DeskTheme)
				: null,
		lookupTools: restoredLookupTools,
		encounter: restoredEncounter,
		visibleTools,
		textLayers: stored.textLayers ?? {},
		expandedSections: stored.expandedSections ?? {},
		collapsedBranches: stored.collapsedBranches ?? {},
		wordIndex: stored.wordIndex?.request.language === language ? stored.wordIndex : null,
		wordIndexSections:
			stored.wordIndexSections?.request.language === language ? stored.wordIndexSections : null
	};
}
