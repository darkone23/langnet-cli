import { languageModes, type EncounterResult, type LanguageMode, type ToolId } from './search-data';

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
