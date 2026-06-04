import type { EncounterBucket, EncounterResult, TranslationMode } from '../search-data';

import type { RetryDeskTranslationInput } from './desk-lookup';

type DeskFetchPayload = <T = unknown>(
	input: RequestInfo | URL,
	init?: RequestInit
) => Promise<{ response: Response; data: T }>;

export type RefreshSearchInput = {
	searchId: number;
	isSearchCurrent: (searchId: number) => boolean;
	fetchEncounter: (mode: TranslationMode) => Promise<EncounterResult>;
	applyEncounter: (result: EncounterResult, resetReaderState: boolean) => void;
	setEnrichingTranslations: (value: boolean) => void;
	setEnrichmentError: (message: string) => void;
	tick: () => Promise<unknown>;
	triggerTranslationArrival: () => void;
	translationFailedMessage: string;
	enrichmentMode: TranslationMode;
};

export type RetryDeskGroupInput = {
	searchId: number;
	isSearchCurrent: (searchId: number) => boolean;
	translation: NonNullable<EncounterBucket['translation']>;
	retryKey: string;
	setTranslationRetrying: (retryKey: string, value: boolean) => void;
	setEnrichmentError: (message: string) => void;
	tick: () => Promise<unknown>;
	fetchEncounter: (mode: TranslationMode) => Promise<EncounterResult>;
	applyEncounter: (result: EncounterResult, resetReaderState: boolean) => void;
	triggerTranslationArrival: () => void;
	fetchPayload: DeskFetchPayload;
	retryDeskTranslation: (input: RetryDeskTranslationInput) => Promise<unknown>;
	translationFailedMessage: string;
};

export async function refreshDeskSearchTranslations({
	searchId,
	isSearchCurrent,
	fetchEncounter,
	applyEncounter,
	setEnrichingTranslations,
	setEnrichmentError,
	tick,
	triggerTranslationArrival,
	translationFailedMessage,
	enrichmentMode
}: RefreshSearchInput) {
	setEnrichingTranslations(true);

	try {
		const data = await fetchEncounter(enrichmentMode);
		if (!isSearchCurrent(searchId)) return;
		applyEncounter(data, false);
		setEnrichmentError('');
		await tick();
		if (isSearchCurrent(searchId)) {
			triggerTranslationArrival();
		}
	} catch (error) {
		if (!isSearchCurrent(searchId)) return;
		setEnrichmentError(error instanceof Error ? error.message : translationFailedMessage);
	} finally {
		if (isSearchCurrent(searchId)) {
			setEnrichingTranslations(false);
		}
	}
}

export async function retryDeskGroupTranslation({
	searchId,
	isSearchCurrent,
	translation,
	retryKey,
	setTranslationRetrying,
	setEnrichmentError,
	tick,
	fetchEncounter,
	applyEncounter,
	triggerTranslationArrival,
	fetchPayload,
	retryDeskTranslation,
	translationFailedMessage
}: RetryDeskGroupInput) {
	setTranslationRetrying(retryKey, true);
	setEnrichmentError('');
	try {
		await retryDeskTranslation({
			fetchPayload,
			translation,
			translationFailedMessage
		});
		if (!isSearchCurrent(searchId)) return;
		const refreshed = await fetchEncounter('auto');
		if (!isSearchCurrent(searchId)) return;
		applyEncounter(refreshed, false);
		await tick();
		triggerTranslationArrival();
	} catch (error) {
		if (!isSearchCurrent(searchId)) return;
		setEnrichmentError(error instanceof Error ? error.message : translationFailedMessage);
	} finally {
		setTranslationRetrying(retryKey, false);
	}
}
