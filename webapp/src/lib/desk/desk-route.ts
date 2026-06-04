import {
	languageModes,
	isSingleWord,
	toolsForLanguage,
	type EncounterResult,
	type LanguageMode,
	type SearchBackend,
	type ToolId,
	type TranslationMode,
	type WordRecommendationItem
} from '../search-data';
import {
	wordIndexItemLookupTarget,
	wordIndexSectionLookupTarget,
	type WordIndexItem,
	type WordIndexSection
} from '../word-index';

export type DeskRouteKeyState = {
	language: LanguageMode;
	query: string;
	backendMode: string;
	translationMode: string;
	lookupTools: string[];
};

export type ClearDeskRouteState = {
	includeLoad: boolean;
	language: LanguageMode;
	query: string;
	backendMode: string;
	translationMode: string;
	theme: string;
	lookupTools: ToolId[];
	defaultTools: ToolId[];
	hasEncounter: boolean;
	visibleTools: ToolId[];
	textLayers: Record<string, unknown>;
	expandedSections: Record<string, unknown>;
	collapsedBranches: Record<string, unknown>;
	pendingVisibleTools: ToolId[];
	pendingSourceLayers: string[];
	pendingExpandedSections: string[];
	pendingCollapsedBranches: string[];
};

export type DeskAppRouteUrlState = ClearDeskRouteState & {
	routePrefillOnly: boolean;
	allLookupSelected: boolean;
	encounterMatchesQuery: boolean;
	returnedToolIds: ToolId[];
};

export type DeskLinkOptions = {
	theme: string;
	translationMode: TranslationMode;
};

export type DeskMotdHrefOptions = {
	theme: string;
	motdLinksLoad: boolean;
};

export const validDeskTranslationModes = new Set<TranslationMode>([
	'off',
	'cache',
	'populate',
	'auto',
	'do-it-all'
]);
export const validDeskBackends = new Set<SearchBackend>(['sample', 'cli']);
export const validDeskThemes = new Set(['manuscript', 'vespers'] as const);

export type DeskTheme = (typeof validDeskThemes extends Set<infer T> ? T : never) & string;

export type DeskRouteHydrationInput = {
	params: URLSearchParams;
	currentLanguage: LanguageMode;
	currentQuery: string;
	encounter: EncounterResult | null;
};

export type DeskRouteHydration = {
	nextLanguage: LanguageMode;
	nextQuery: string;
	validTools: ToolId[];
	requestedTools: ToolId[] | null;
	requestedVisibleTools: ToolId[] | null;
	requestedTheme: DeskTheme | null;
	requestedBackend: SearchBackend | null;
	requestedTranslation: TranslationMode | null;
	shouldPrefillOnly: boolean;
	routeLoadRequested: boolean;
	routeMatchesCurrentEncounter: boolean;
	shouldResetEncounter: boolean;
	shouldPreserveEncounter: boolean;
	routeVisibleTools: ToolId[];
	routeSourceLayers: string[];
	routeExpandedSections: string[];
	routeCollapsedBranches: string[];
	shouldRestoreFromSession: boolean;
};

export function normalizedDeskQuery(value: string) {
	return value.trim().toLowerCase();
}

export function routeMatchesEncounter(
	encounter: EncounterResult | null | undefined,
	language: LanguageMode,
	query: string
) {
	return Boolean(
		encounter &&
		encounter.language === language &&
		normalizedDeskQuery(encounter.query) === normalizedDeskQuery(query)
	);
}

export function shouldResetEncounterForRoute({
	currentLanguage,
	currentQuery,
	nextLanguage,
	nextQuery
}: {
	currentLanguage: LanguageMode;
	currentQuery: string;
	nextLanguage: LanguageMode;
	nextQuery: string;
}) {
	return (
		currentLanguage !== nextLanguage ||
		normalizedDeskQuery(currentQuery) !== normalizedDeskQuery(nextQuery)
	);
}

export function shouldLoadEncounterForRoute({
	routeWantsLoad,
	routeExplicitlyRequestsLoad,
	hasLoadableQuery,
	routeMatchesCurrentEncounter
}: {
	routeWantsLoad: boolean;
	routeExplicitlyRequestsLoad: boolean;
	hasLoadableQuery: boolean;
	routeMatchesCurrentEncounter: boolean;
}) {
	if (!routeWantsLoad || !hasLoadableQuery) return false;
	if (routeExplicitlyRequestsLoad) return true;
	return !routeMatchesCurrentEncounter;
}

export function shouldPersistDeskRouteListParam(key: string) {
	return key !== 'expand' && key !== 'collapse';
}

export function routeShouldLoad(params: URLSearchParams) {
	const value = params.get('load')?.toLowerCase();
	if (routePrefillOnlyRequested(params)) return false;
	if (value === 'yes' || value === 'true' || value === '1') return true;
	return Boolean(params.get('q')?.trim());
}

export function routeExplicitlyRequestsLoad(params: URLSearchParams) {
	const value = params.get('load')?.toLowerCase();
	return value === 'yes' || value === 'true' || value === '1';
}

export function routePrefillOnlyRequested(params: URLSearchParams) {
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

export function readLanguageParam(params: URLSearchParams) {
	const requestedLanguage = params.get('lang') ?? params.get('language');
	return languageModes.some((mode) => mode.id === requestedLanguage)
		? (requestedLanguage as LanguageMode)
		: null;
}

export function readToolParams(params: URLSearchParams, name: string, validTools: ToolId[]) {
	const values = readRouteList(params, name);
	if (!values.length) return null;
	if (values.includes('all')) return validTools;

	const validToolSet = new Set(validTools);
	const parsed = values.filter((value): value is ToolId => validToolSet.has(value as ToolId));
	return parsed.length ? [...new Set(parsed)] : null;
}

export function readRouteList(params: URLSearchParams, name: string) {
	return params
		.getAll(name)
		.flatMap((value) => value.split(','))
		.map((value) => value.trim())
		.filter(Boolean);
}

export function currentDeskRouteKey(state: DeskRouteKeyState) {
	return JSON.stringify({
		language: state.language,
		query: normalizedDeskQuery(state.query),
		backendMode: state.backendMode,
		translationMode: state.translationMode,
		lookupTools: [...state.lookupTools].sort()
	});
}

export function deskRouteHydration({
	params,
	currentLanguage,
	currentQuery,
	encounter
}: DeskRouteHydrationInput): DeskRouteHydration {
	const nextLanguage = readLanguageParam(params) ?? currentLanguage;
	const nextQuery = params.get('q') ?? '';
	const validTools = toolsForLanguage(nextLanguage).map(({ id }) => id);
	const requestedTools = readToolParams(params, 'dictionary', validTools);
	const requestedVisibleTools = readToolParams(params, 'visible', validTools);
	const requestedTheme = readDeskThemeParam(params);
	const requestedBackend = readDeskBackendParam(params);
	const requestedTranslation = readDeskTranslationParam(params);
	const shouldPrefillOnly = routePrefillOnlyRequested(params);
	const shouldLoad = routeShouldLoad(params);
	const routeMatchesCurrentEncounter = routeMatchesEncounter(encounter, nextLanguage, nextQuery);
	const shouldResetEncounter = shouldResetEncounterForRoute({
		currentLanguage,
		currentQuery,
		nextLanguage,
		nextQuery
	});
	const shouldPreserveEncounter = routeMatchesCurrentEncounter && !shouldResetEncounter;
	const routeVisibleTools = requestedVisibleTools ?? [];
	const routeSourceLayers = readRouteList(params, 'source');
	const routeExpandedSections = shouldPersistDeskRouteListParam('expand')
		? readRouteList(params, 'expand')
		: [];
	const routeCollapsedBranches = shouldPersistDeskRouteListParam('collapse')
		? readRouteList(params, 'collapse')
		: [];

	return {
		nextLanguage,
		nextQuery,
		validTools,
		requestedTools,
		requestedVisibleTools,
		requestedTheme,
		requestedBackend,
		requestedTranslation,
		shouldPrefillOnly,
		routeLoadRequested: shouldLoadEncounterForRoute({
			routeWantsLoad: shouldLoad,
			routeExplicitlyRequestsLoad: routeExplicitlyRequestsLoad(params),
			hasLoadableQuery: Boolean(nextQuery.trim()) && isSingleWord(nextQuery.trim()),
			routeMatchesCurrentEncounter
		}),
		routeMatchesCurrentEncounter,
		shouldResetEncounter,
		shouldPreserveEncounter,
		routeVisibleTools,
		routeSourceLayers,
		routeExpandedSections,
		routeCollapsedBranches,
		shouldRestoreFromSession:
			!routePrefillOnlyRequested(params) && !routeExplicitlyRequestsLoad(params)
	};
}

export function readDeskThemeParam(params: URLSearchParams): DeskTheme | null {
	const requestedTheme = params.get('theme');
	return requestedTheme && validDeskThemes.has(requestedTheme as DeskTheme)
		? (requestedTheme as DeskTheme)
		: null;
}

export function readDeskBackendParam(params: URLSearchParams): SearchBackend | null {
	const requestedBackend = params.get('backend');
	return requestedBackend && validDeskBackends.has(requestedBackend as SearchBackend)
		? (requestedBackend as SearchBackend)
		: null;
}

export function readDeskTranslationParam(params: URLSearchParams): TranslationMode | null {
	const requestedTranslation = params.get('translation');
	return requestedTranslation &&
		validDeskTranslationModes.has(requestedTranslation as TranslationMode)
		? (requestedTranslation as TranslationMode)
		: null;
}

export function isClearDeskRouteState(state: ClearDeskRouteState) {
	const defaultToolSet = new Set(state.defaultTools);
	return (
		!state.includeLoad &&
		state.language === 'san' &&
		!state.query.trim() &&
		state.backendMode === 'cli' &&
		state.translationMode === 'auto' &&
		state.theme === 'manuscript' &&
		state.lookupTools.length === state.defaultTools.length &&
		state.lookupTools.every((tool) => defaultToolSet.has(tool)) &&
		!state.hasEncounter &&
		!state.visibleTools.length &&
		!Object.keys(state.textLayers).length &&
		!Object.keys(state.expandedSections).length &&
		!Object.keys(state.collapsedBranches).length &&
		!state.pendingVisibleTools.length &&
		!state.pendingSourceLayers.length &&
		!state.pendingExpandedSections.length &&
		!state.pendingCollapsedBranches.length
	);
}

export function deskAppRouteUrl(state: DeskAppRouteUrlState) {
	if (isClearDeskRouteState(state)) return '/q';

	const params = new URLSearchParams();
	params.set('lang', state.language);
	if (state.query.trim()) params.set('q', state.query.trim());
	params.set('backend', state.backendMode);
	params.set('translation', state.translationMode);
	params.set('theme', state.theme);
	if (state.includeLoad && state.query.trim()) params.set('load', 'yes');
	if (!state.includeLoad && state.routePrefillOnly && state.query.trim() && !state.hasEncounter) {
		params.set('load', 'no');
	}

	if (state.allLookupSelected) {
		params.set('dictionary', 'all');
	} else {
		for (const tool of state.lookupTools) params.append('dictionary', tool);
	}

	if (
		state.encounterMatchesQuery &&
		state.visibleTools.length &&
		state.visibleTools.length !== state.returnedToolIds.length
	) {
		for (const tool of state.visibleTools) params.append('visible', tool);
	} else if (!state.hasEncounter && state.pendingVisibleTools.length) {
		for (const tool of state.pendingVisibleTools) params.append('visible', tool);
	}

const sourceLayerIds = new Set(!state.hasEncounter ? state.pendingSourceLayers : []);
	if (state.encounterMatchesQuery) {
		for (const [bucketId, layer] of Object.entries(state.textLayers)) {
			if (layer === 'source') sourceLayerIds.add(bucketId);
		}
	}
	for (const bucketId of sourceLayerIds) params.append('source', bucketId);

	const queryString = params.toString();
	return queryString ? `/q?${queryString}` : '/q';
}

export function deskMotdHref(item: WordRecommendationItem, options: DeskMotdHrefOptions) {
	const request = item.recommended_request;
	const params = new URLSearchParams({
		lang: request.language || item.language,
		q: request.q || item.query,
		dictionary: request.dictionary || 'all',
		translation: request.translation || 'auto'
	});
	params.set('backend', request.backend || 'cli');
	params.set('theme', options.theme);
	params.set('load', options.motdLinksLoad ? 'yes' : 'no');
	return `/q?${params.toString()}`;
}

export function deskWordIndexHref(
	item: WordIndexItem,
	options: DeskLinkOptions & { includeLoad?: boolean }
) {
	const target = wordIndexItemLookupTarget(item);
	return deskWordIndexTargetHref(target, options);
}

export function deskWordIndexSectionHref(section: WordIndexSection, options: DeskLinkOptions) {
	const target = wordIndexSectionLookupTarget(section);
	if (!target) return '';
	return deskWordIndexTargetHref(target, { ...options, includeLoad: true });
}

function deskWordIndexTargetHref(
	target: { language: LanguageMode; query: string; dictionary: string },
	options: DeskLinkOptions & { includeLoad?: boolean }
) {
	const params = new URLSearchParams({
		lang: target.language,
		q: target.query,
		translation: options.translationMode,
		theme: options.theme
	});
	const validTools = new Set(toolsForLanguage(target.language).map(({ id }) => id));
	params.set('dictionary', validTools.has(target.dictionary as ToolId) ? target.dictionary : 'all');
	if (options.includeLoad) params.set('load', 'yes');
	return `/q?${params.toString()}`;
}
