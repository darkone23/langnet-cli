import {
	encounterWord,
	isSingleWord,
	languageModes,
	toolsForLanguage,
	type LanguageMode,
	type SearchBackend,
	type ToolId,
	type ToolRequest,
	type TranslationMode
} from '$lib/search-data';
import { searchErrorMessage, shouldRetrySearchWithoutTranslation } from '$lib/search-route';
import { encounterWordFromCli } from '$lib/server/langnet-cli';
import { payloadResponse } from '$lib/server/msgpack-response';
import {
	canCacheSearchResponse,
	searchCacheKey,
	searchResponseCache
} from '$lib/server/search-cache';

const validLanguages = new Set(languageModes.map(({ id }) => id));
const translationModes = new Set(['off', 'cache', 'populate', 'auto', 'do-it-all']);
const searchBackends = new Set(['sample', 'cli']);

export async function GET({ url, request }) {
	const respond = (payload: unknown, init?: ResponseInit) =>
		payloadResponse(request, payload, init);
	const query = url.searchParams.get('q') ?? '';
	const word = query.trim();
	const requestedLanguage = url.searchParams.get('language') ?? 'san';
	const language = validLanguages.has(requestedLanguage as LanguageMode)
		? (requestedLanguage as LanguageMode)
		: 'san';
	const requestedBackend = url.searchParams.get('backend') ?? 'cli';
	const backend = searchBackends.has(requestedBackend)
		? (requestedBackend as SearchBackend)
		: ('sample' as const);
	const requestedTranslationMode = url.searchParams.get('translation') ?? 'cache';
	const translationMode = translationModes.has(requestedTranslationMode)
		? (requestedTranslationMode as TranslationMode)
		: ('cache' as const);
	const validTools = new Set(toolsForLanguage(language).map(({ id }) => id));
	const requestedDictionaries = url.searchParams.getAll('dictionary');
	const hasAllDictionaryRequest =
		requestedDictionaries.length === 0 || requestedDictionaries.includes('all');
	const requestedToolFilters = requestedDictionaries.filter((dictionary): dictionary is ToolId =>
		validTools.has(dictionary as ToolId)
	);
	const dictionaries: ToolRequest[] =
		hasAllDictionaryRequest || requestedToolFilters.length === 0 ? ['all'] : requestedToolFilters;

	if (word && !isSingleWord(word)) {
		return respond(
			{
				...encounterWord(word, language, dictionaries),
				error: 'Search accepts one word at a time.',
				buckets: []
			},
			{ status: 400 }
		);
	}

	if (backend === 'cli' && word) {
		const maxBuckets = readInteger(url.searchParams.get('max_buckets'), 12, 1, 100_000);
		const maxGlossChars = readInteger(url.searchParams.get('max_gloss_chars'), 1400, 1, 100_000);
		const timeoutMs = readInteger(url.searchParams.get('timeout_ms'), 300_000, 1_000, 300_000);
		const cacheKey = searchCacheKey(url);
		const cached = searchResponseCache.get(cacheKey);
		if (cached) {
			return respond(cached, {
				headers: { 'server-timing': 'search_cache;desc="hit"' }
			});
		}

		try {
			const result = await encounterWordFromCli({
				language,
				query: word,
				dictionaries,
				translationMode,
				maxBuckets,
				maxGlossChars,
				timeoutMs
			});
			if (
				canCacheSearchResponse({
					backend,
					word,
					translationMode,
					payload: result
				})
			) {
				searchResponseCache.set(cacheKey, result);
			}
			return respond(result);
		} catch (error) {
			if (shouldRetrySearchWithoutTranslation(error, translationMode)) {
				try {
					const fallback = await encounterWordFromCli({
						language,
						query: word,
						dictionaries,
						translationMode: 'off',
						maxBuckets,
						maxGlossChars,
						timeoutMs
					});

					const result = {
						...fallback,
						warnings: [
							...fallback.warnings,
							`Translation enrichment skipped after CLI cache failure: ${searchErrorMessage(error)}`
						]
					};
					if (
						canCacheSearchResponse({
							backend,
							word,
							translationMode,
							payload: result
						})
					) {
						searchResponseCache.set(cacheKey, result);
					}
					return respond(result);
				} catch {
					// Preserve the original translation-cache failure; it explains why the retry happened.
				}
			}

			return respond(
				{
					query: word,
					language,
					dictionaries,
					source_tools: [],
					lexeme_anchors: [],
					buckets: [],
					analysis: [],
					components: [],
					translation_cache: {
						mode: translationMode,
						cache_available: false,
						populate: false,
						written: 0,
						before: { total: 0, hits: 0, missing: 0, errors: 1 },
						after: { total: 0, hits: 0, missing: 0, errors: 1 }
					},
					warnings: [],
					request: {
						translation_mode: translationMode,
						tool_filter: dictionaries,
						reader_lang: 'en'
					},
					backend: 'cli',
					error: searchErrorMessage(error)
				},
				{ status: 502 }
			);
		}
	}

	return respond({
		...encounterWord(word, language, dictionaries),
		backend: 'sample'
	});
}

function readInteger(value: string | null, fallback: number, min: number, max: number) {
	if (!value) return fallback;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return fallback;
	return Math.min(max, Math.max(min, parsed));
}
