import type { EncounterResult, LanguageMode } from './search-data';

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
