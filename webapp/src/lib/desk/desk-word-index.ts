import { isSingleWord, type LanguageMode } from '../search-data';
import { fetchPayload } from '../msgpack';
import { wordIndexItemKey } from '../word-index';
import {
	wordIndexBrowseEndpointUrl,
	wordIndexNearbyEndpointUrl,
	wordIndexSectionsEndpointUrl
} from './desk-endpoints';
import type { WordIndexItem, WordIndexResponse, WordIndexSectionsResponse } from '../word-index';

export type DeskWordIndexState = {
	language: LanguageMode;
	wordIndex: WordIndexResponse | null;
	wordIndexSections: WordIndexSectionsResponse | null;
	wordIndexLoading: boolean;
	wordIndexSectionsLoading: boolean;
	wordIndexError: string;
	wordIndexSectionsError: string;
	wordIndexRequestId: number;
	wordIndexEarmarks: WordIndexItem[];
};

export type DeskWordIndexDependencies = {
	fetchPayload: typeof fetchPayload;
	errors: {
		indexFailed: string;
	};
};

export type DeskWordIndexController = {
	loadSections(targetLanguage?: LanguageMode): Promise<void>;
	loadNearbyWordIndex(
		targetQuery?: string,
		targetLanguage?: LanguageMode,
		fallbackQueries?: string[]
	): Promise<void>;
	loadBrowseWordIndex(prefix: string, targetLanguage?: LanguageMode): Promise<void>;
	hasRows(result: WordIndexResponse | null): boolean;
	isEarmarked(item: WordIndexItem): boolean;
	toggleEarmark(item: WordIndexItem): void;
	clearEarmarks(): void;
	clearSearchState(): void;
};

function dedupeStrings(values: string[]) {
	return [...new Set(values)];
}

export function createDeskWordIndexController(
	state: DeskWordIndexState,
	deps: DeskWordIndexDependencies,
	options: { wordIndexRadius: number }
): DeskWordIndexController {
	return {
		loadSections: async (targetLanguage = state.language) => {
			if (state.wordIndexSections?.request.language === targetLanguage) return;

			state.wordIndexSectionsLoading = true;
			state.wordIndexSectionsError = '';

			try {
				const { response, data } = await deps.fetchPayload<WordIndexSectionsResponse>(
					wordIndexSectionsEndpointUrl(targetLanguage)
				);

				if (!response.ok) throw new Error(data.error || deps.errors.indexFailed);
				if (targetLanguage !== state.language) return;
				state.wordIndexSections = data;
			} catch (error) {
				if (targetLanguage !== state.language) return;
				state.wordIndexSections = null;
				state.wordIndexSectionsError =
					error instanceof Error ? error.message : deps.errors.indexFailed;
			} finally {
				if (targetLanguage === state.language) {
					state.wordIndexSectionsLoading = false;
				}
			}
		},

		loadNearbyWordIndex: async (
			targetQuery = '',
			targetLanguage = state.language,
			fallbackQueries: string[] = []
		) => {
			const candidates = dedupeStrings([targetQuery, ...fallbackQueries])
				.map((candidate) => candidate.trim())
				.filter((candidate) => candidate && isSingleWord(candidate));
			const word = candidates[0] ?? '';
			const requestId = state.wordIndexRequestId + 1;
			state.wordIndexRequestId = requestId;

			if (!word) {
				state.wordIndex = null;
				state.wordIndexLoading = false;
				state.wordIndexError = '';
				return;
			}

			state.wordIndexLoading = true;
			state.wordIndexError = '';

			try {
				let data: WordIndexResponse | null = null;

				for (const candidate of candidates) {
					const result = await deps.fetchPayload<WordIndexResponse>(
						wordIndexNearbyEndpointUrl({
							language: targetLanguage,
							query: candidate,
							radius: options.wordIndexRadius
						})
					);
					data = result.data;

					if (!result.response.ok) {
						throw new Error(data.error || deps.errors.indexFailed);
					}
					if (requestId !== state.wordIndexRequestId) return;
					if (wordIndexResponseHasRows(data) || candidate === candidates[candidates.length - 1]) {
						break;
					}
				}

				if (requestId !== state.wordIndexRequestId) return;
				state.wordIndex = data;
			} catch (error) {
				if (requestId !== state.wordIndexRequestId) return;
				state.wordIndex = null;
				state.wordIndexError = error instanceof Error ? error.message : deps.errors.indexFailed;
			} finally {
				if (requestId === state.wordIndexRequestId) {
					state.wordIndexLoading = false;
				}
			}
		},

		loadBrowseWordIndex: async (prefix: string, targetLanguage = state.language) => {
			const normalizedPrefix = prefix.trim();
			const requestId = state.wordIndexRequestId + 1;
			state.wordIndexRequestId = requestId;

			if (!normalizedPrefix) {
				state.wordIndex = null;
				state.wordIndexLoading = false;
				state.wordIndexError = '';
				return;
			}

			state.wordIndexLoading = true;
			state.wordIndexError = '';

			try {
				const { response, data } = await deps.fetchPayload<WordIndexResponse>(
					wordIndexBrowseEndpointUrl({
						language: targetLanguage,
						prefix: normalizedPrefix
					})
				);

				if (!response.ok) {
					throw new Error(data.error || deps.errors.indexFailed);
				}
				if (requestId !== state.wordIndexRequestId) return;
				state.wordIndex = data;
			} catch (error) {
				if (requestId !== state.wordIndexRequestId) return;
				state.wordIndex = null;
				state.wordIndexError = error instanceof Error ? error.message : deps.errors.indexFailed;
			} finally {
				if (requestId === state.wordIndexRequestId) {
					state.wordIndexLoading = false;
				}
			}
		},

		hasRows: (result) => {
			if (!result) return false;
			return (
				Boolean(result.items.length) ||
				Boolean(result.neighborhood?.items?.length) ||
				Boolean(result.neighborhood?.anchor) ||
				(result.neighborhood?.groups ?? []).some(
					(group) => group.anchor || group.before.length || group.after.length
				) ||
				Boolean(result.neighborhood?.window?.source_group_count) ||
				Boolean(result.neighborhood?.window?.lexeme_count)
			);
		},

		isEarmarked: (item) => {
			const key = wordIndexItemKey(item);
			return state.wordIndexEarmarks.some((earmark) => wordIndexItemKey(earmark) === key);
		},

		toggleEarmark: (item) => {
			const key = wordIndexItemKey(item);
			if (state.wordIndexEarmarks.some((earmark) => wordIndexItemKey(earmark) === key)) {
				state.wordIndexEarmarks = state.wordIndexEarmarks.filter(
					(earmark) => wordIndexItemKey(earmark) !== key
				);
				return;
			}

			state.wordIndexEarmarks = [item, ...state.wordIndexEarmarks].slice(0, 18);
		},

		clearEarmarks: () => {
			state.wordIndexEarmarks = [];
		},

		clearSearchState: () => {
			state.wordIndexRequestId += 1;
			state.wordIndex = null;
			state.wordIndexLoading = false;
			state.wordIndexError = '';
		}
	};
}

const neighborhoodsHaveRows = (result: WordIndexResponse | null) => {
	if (!result) return false;
	if (result.neighborhood?.items?.length) return true;
	if (result.neighborhood?.groups.length) return true;
	if (result.neighborhood?.anchor) return true;
	return (
		result.neighborhood?.window?.source_group_count !== undefined ||
		result.neighborhood?.window?.lexeme_count !== undefined
	);
};

function wordIndexResponseHasRows(result: WordIndexResponse | null) {
	return neighborhoodsHaveRows(result) || Boolean(result?.items.length);
}
