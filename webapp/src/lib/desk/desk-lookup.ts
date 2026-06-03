import type {
	EncounterBucket,
	EncounterResult,
	SearchBackend,
	ToolId,
	TranslationMode
} from '../search-data';
import { isSingleWord } from '../search-data';
import { returnedToolsForEncounter } from './desk-session';
import { sectionExpansionKey } from './desk-entry';

export type DeskLookupValidation =
	| {
			ok: true;
			word: string;
	  }
	| {
			ok: false;
			reason: 'empty' | 'multiword';
	  };

export type DeskEncounterViewStateInput = {
	result: EncounterResult;
	resetReaderState: boolean;
	previousVisibleTools: ToolId[];
	pendingVisibleTools: ToolId[] | null;
	pendingSourceLayers: string[];
	pendingExpandedSections: string[];
	pendingCollapsedBranches: string[];
};

export type DeskEncounterViewState = {
	visibleTools: ToolId[];
	textLayers: Record<string, 'source'>;
	expandedSections: Record<string, true>;
	collapsedBranches: Record<string, true>;
	shouldClearPendingRouteState: boolean;
};

type FetchPayload = <T = unknown>(
	input: RequestInfo | URL,
	init?: RequestInit
) => Promise<{ response: Response; data: T }>;

type Delay = (milliseconds: number) => Promise<unknown>;

export type FetchDeskEncounterInput = {
	url: string;
	delayMs: number;
	fetchPayload: FetchPayload;
	searchFailedMessage: string;
	delay?: Delay;
};

export type RetryDeskTranslationInput = {
	translation: NonNullable<EncounterBucket['translation']>;
	fetchPayload: FetchPayload;
	translationFailedMessage: string;
	endpoint?: string;
	maxRetries?: number;
	limitReachedMessage?: string;
};

export function validateDeskLookupWord(query: string): DeskLookupValidation {
	const word = query.trim();
	if (!word) return { ok: false, reason: 'empty' };
	if (!isSingleWord(word)) return { ok: false, reason: 'multiword' };
	return { ok: true, word };
}

export function shouldProgressivelyEnrichLookup(backendMode: SearchBackend, mode: TranslationMode) {
	return backendMode === 'cli' && (mode === 'auto' || mode === 'populate' || mode === 'do-it-all');
}

export function firstPassTranslationMode(
	backendMode: SearchBackend,
	mode: TranslationMode
): TranslationMode {
	return shouldProgressivelyEnrichLookup(backendMode, mode) ? 'cache' : mode;
}

export function manualDeskQueryChanged(pendingQuery: string, word: string) {
	return Boolean(pendingQuery && pendingQuery !== word);
}

export function deskEncounterViewState({
	result,
	resetReaderState,
	previousVisibleTools,
	pendingVisibleTools,
	pendingSourceLayers,
	pendingExpandedSections,
	pendingCollapsedBranches
}: DeskEncounterViewStateInput): DeskEncounterViewState {
	const nextReturnedTools = returnedToolsForEncounter(result);
	const routedVisibleTools = pendingVisibleTools
		? nextReturnedTools.filter((tool) => pendingVisibleTools.includes(tool))
		: [];
	let visibleTools = resetReaderState
		? routedVisibleTools.length
			? routedVisibleTools
			: nextReturnedTools
		: nextReturnedTools.filter((tool) => previousVisibleTools.includes(tool));

	if (!visibleTools.length) {
		visibleTools = nextReturnedTools;
	}

	if (!resetReaderState) {
		return {
			visibleTools,
			textLayers: {},
			expandedSections: {},
			collapsedBranches: {},
			shouldClearPendingRouteState: false
		};
	}

	return {
		visibleTools,
		textLayers: Object.fromEntries(
			result.buckets
				.filter((bucket) => pendingSourceLayers.includes(bucket.bucket_id))
				.map((bucket) => [bucket.bucket_id, 'source' as const])
		),
		expandedSections: Object.fromEntries(
			result.buckets
				.map((bucket) => sectionExpansionKey(bucket))
				.filter((key) => pendingExpandedSections.includes(key))
				.map((key) => [key, true as const])
		),
		collapsedBranches: Object.fromEntries(
			result.buckets
				.map((bucket) => sectionExpansionKey(bucket))
				.filter((key) => pendingCollapsedBranches.includes(key))
				.map((key) => [key, true as const])
		),
		shouldClearPendingRouteState: true
	};
}

export async function fetchDeskEncounter({
	url,
	delayMs,
	fetchPayload,
	searchFailedMessage,
	delay = wait
}: FetchDeskEncounterInput) {
	const [{ response, data }] = await Promise.all([
		fetchPayload<EncounterResult>(url),
		delay(delayMs)
	]);

	if (!response.ok) {
		throw new Error(data.error ?? searchFailedMessage);
	}

	return data;
}

export async function retryDeskTranslation({
	translation,
	fetchPayload,
	translationFailedMessage,
	endpoint = '/api/translation-cache',
	maxRetries = 3,
	limitReachedMessage = 'This translation has reached its retry limit.'
}: RetryDeskTranslationInput) {
	const { response, data } = await fetchPayload<{ error?: string; limit_reached?: boolean }>(
		endpoint,
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
				max_retries: maxRetries
			})
		}
	);

	if (!response.ok) {
		throw new Error(
			data.error ?? (data.limit_reached ? limitReachedMessage : translationFailedMessage)
		);
	}

	return data;
}

function wait(milliseconds: number) {
	return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
