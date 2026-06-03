import type { EncounterResult, SearchBackend, TranslationMode } from '../search-data';
import { uiCopy } from '../ui-copy';
import { shouldProgressivelyEnrichLookup } from './desk-lookup';

export type DeskStatusLabelInput = {
	loading: boolean;
	enrichingTranslations: boolean;
	hasAttention: boolean;
	hasEncounter: boolean;
};

export type DeskStatusDetailInput = {
	loading: boolean;
	enrichingTranslations: boolean;
	lookupToolCount: number;
	encounter: EncounterResult | null;
	visibleBucketCount: number;
	query: string;
};

export type DeskReaderLayerStatusInput = {
	enrichingTranslations: boolean;
	translationMode: TranslationMode;
	backendMode: SearchBackend;
	encounter: EncounterResult | null;
};

export function deskCacheSummary(encounterResult: EncounterResult) {
	const { translation_cache } = encounterResult;

	if (!translation_cache.cache_available) return uiCopy.status.cacheUnavailable;
	if (translation_cache.after.missing === 0) return uiCopy.status.cacheWarm;
	if (translation_cache.written > 0)
		return uiCopy.status.newTranslations(translation_cache.written);
	return uiCopy.status.missingTranslations(translation_cache.after.missing);
}

export function deskCurrentStatusLabel({
	loading,
	enrichingTranslations,
	hasAttention,
	hasEncounter
}: DeskStatusLabelInput) {
	if (loading) return uiCopy.status.searching;
	if (enrichingTranslations) return uiCopy.status.awaitingReader;
	if (hasAttention) return uiCopy.status.attention;
	if (hasEncounter) return uiCopy.status.reading;
	return uiCopy.status.ready;
}

export function deskCurrentStatusDetail({
	loading,
	enrichingTranslations,
	lookupToolCount,
	encounter,
	visibleBucketCount,
	query
}: DeskStatusDetailInput) {
	if (loading) return uiCopy.status.askingSources(lookupToolCount);
	if (enrichingTranslations) return uiCopy.status.awaitingReaderDetail;
	if (encounter) {
		return uiCopy.status.showingSections(
			visibleBucketCount,
			encounter.buckets.length,
			encounter.query
		);
	}
	if (query.trim()) return uiCopy.status.readyForWord;
	return uiCopy.status.chooseWord;
}

export function deskReaderLayerStatus({
	enrichingTranslations,
	translationMode,
	backendMode,
	encounter
}: DeskReaderLayerStatusInput) {
	if (enrichingTranslations) return uiCopy.readerLayer.awaiting(translationMode);
	if (!encounter) return uiCopy.readerLayer.unsearched;
	if (
		shouldProgressivelyEnrichLookup(backendMode, translationMode) &&
		encounter.request.translation_mode === 'cache'
	) {
		return uiCopy.readerLayer.cacheSupplied(translationMode);
	}
	return uiCopy.readerLayer.served(encounter.request.translation_mode);
}
