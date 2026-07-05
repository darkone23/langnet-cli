import type { DeskTheme } from './desk-route';
import {
	toolsForLanguage,
	type EncounterResult,
	type LanguageMode,
	type SearchBackend,
	type ToolId,
	type TranslationMode
} from '../search-data';
import type { WordIndexItem } from '../word-index';

type EmptyRecord = Record<string, never>;

export type DeskRouteStatePatch = Partial<{
	activeSearchIdDelta: number;
	routeLoadRequested: boolean;
	routePrefillOnly: boolean;
	language: LanguageMode;
	query: string;
	backendMode: SearchBackend;
	translationMode: TranslationMode;
	theme: DeskTheme;
	lookupTools: ToolId[];
	wordIndexEarmarks: WordIndexItem[];
	encounter: EncounterResult | null;
	visibleTools: ToolId[];
	loading: boolean;
	enrichingTranslations: boolean;
	errorMessage: string;
	enrichmentError: string;
	textLayers: Record<string, 'reader' | 'source'>;
	expandedSections: Record<string, boolean>;
	collapsedBranches: Record<string, boolean>;
	pendingVisibleToolsFromRoute: ToolId[] | null;
	pendingSourceLayersFromRoute: string[];
	pendingExpandedSectionsFromRoute: string[];
	pendingCollapsedBranchesFromRoute: string[];
	pendingQueryFromRoute: string;
}>;

export type DeskPendingRouteStatePatch = {
	pendingVisibleToolsFromRoute: null;
	pendingSourceLayersFromRoute: string[];
	pendingExpandedSectionsFromRoute: string[];
	pendingCollapsedBranchesFromRoute: string[];
	pendingQueryFromRoute: string;
};

export type DeskEncounterClearPatch = {
	activeSearchIdDelta: 1;
	encounter: null;
	visibleTools: [];
	loading: false;
	enrichingTranslations: false;
	errorMessage: '';
	enrichmentError: '';
	textLayers: EmptyRecord;
	expandedSections: EmptyRecord;
	collapsedBranches: EmptyRecord;
};

export type DeskSearchClearPatch = {
	activeSearchIdDelta: 1;
	query: '';
	encounter: null;
	visibleTools: [];
	errorMessage: '';
	enrichmentError: '';
	enrichingTranslations: false;
	textLayers: EmptyRecord;
	expandedSections: EmptyRecord;
	collapsedBranches: EmptyRecord;
} & DeskPendingRouteStatePatch;

export type DeskAppResetPatch = {
	activeSearchIdDelta: 1;
	routeLoadRequested: false;
	routePrefillOnly: false;
	language: 'san';
	query: '';
	backendMode: SearchBackend;
	translationMode: TranslationMode;
	theme: DeskTheme;
	lookupTools: ReturnType<typeof toolsForLanguage>[number]['id'][];
	wordIndexEarmarks: [];
} & Omit<DeskEncounterClearPatch, 'activeSearchIdDelta'> &
	DeskPendingRouteStatePatch;

export type DeskLanguageSelectPatch = {
	activeSearchIdDelta: 1;
	routeLoadRequested: false;
	routePrefillOnly: false;
	language: LanguageMode;
	query: '';
	lookupTools: ReturnType<typeof toolsForLanguage>[number]['id'][];
	visibleTools: [];
	encounter: null;
	errorMessage: '';
	enrichmentError: '';
	enrichingTranslations: false;
	textLayers: EmptyRecord;
	expandedSections: EmptyRecord;
	collapsedBranches: EmptyRecord;
} & DeskPendingRouteStatePatch;

export function clearPendingDeskRouteStatePatch(): DeskPendingRouteStatePatch {
	return {
		pendingVisibleToolsFromRoute: null,
		pendingSourceLayersFromRoute: [],
		pendingExpandedSectionsFromRoute: [],
		pendingCollapsedBranchesFromRoute: [],
		pendingQueryFromRoute: ''
	};
}

export function clearDeskEncounterPatch(): DeskEncounterClearPatch {
	return {
		activeSearchIdDelta: 1,
		encounter: null,
		visibleTools: [],
		loading: false,
		enrichingTranslations: false,
		errorMessage: '',
		enrichmentError: '',
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {}
	};
}

export function clearDeskSearchPatch(): DeskSearchClearPatch {
	return {
		activeSearchIdDelta: 1,
		query: '',
		encounter: null,
		visibleTools: [],
		errorMessage: '',
		enrichmentError: '',
		enrichingTranslations: false,
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {},
		...clearPendingDeskRouteStatePatch()
	};
}

export function resetDeskAppPatch(): DeskAppResetPatch {
	const { activeSearchIdDelta: _activeSearchIdDelta, ...encounterPatch } = clearDeskEncounterPatch();

	return {
		activeSearchIdDelta: 1,
		routeLoadRequested: false,
		routePrefillOnly: false,
		language: 'san',
		query: '',
		backendMode: 'cli',
		translationMode: 'auto',
		theme: 'manuscript',
		lookupTools: toolsForLanguage('san').map(({ id }) => id),
		wordIndexEarmarks: [],
		...encounterPatch,
		...clearPendingDeskRouteStatePatch()
	};
}

export function selectDeskLanguagePatch(language: LanguageMode): DeskLanguageSelectPatch {
	return {
		activeSearchIdDelta: 1,
		routeLoadRequested: false,
		routePrefillOnly: false,
		language,
		query: '',
		lookupTools: toolsForLanguage(language).map(({ id }) => id),
		visibleTools: [],
		encounter: null,
		errorMessage: '',
		enrichmentError: '',
		enrichingTranslations: false,
		textLayers: {},
		expandedSections: {},
		collapsedBranches: {},
		...clearPendingDeskRouteStatePatch()
	};
}
