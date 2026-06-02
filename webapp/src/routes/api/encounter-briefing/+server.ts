import { encounterBriefingFromCli } from '$lib/server/langnet-cli';
import { payloadResponse } from '$lib/server/msgpack-response';
import {
	isSingleWord,
	languageModes,
	toolsForLanguage,
	type LanguageMode,
	type ToolId,
	type ToolRequest
} from '$lib/search-data';
import { searchErrorMessage } from '$lib/search-route';

const validLanguages = new Set(languageModes.map(({ id }) => id));
const translationModes = new Set(['off', 'cache', 'populate', 'auto', 'do-it-all']);
const cachePolicies = new Set(['read-write', 'read-only', 'off']);

export async function GET({ url, request }) {
	const respond = (payload: unknown, init?: ResponseInit) =>
		payloadResponse(request, payload, init);
	const query = url.searchParams.get('q') ?? '';
	const word = query.trim();
	const requestedLanguage = url.searchParams.get('language') ?? 'san';
	const language = validLanguages.has(requestedLanguage as LanguageMode)
		? (requestedLanguage as LanguageMode)
		: 'san';
	const requestedTranslationMode = url.searchParams.get('translation') ?? 'cache';
	const translationMode = translationModes.has(requestedTranslationMode)
		? requestedTranslationMode
		: 'cache';
	const requestedCachePolicy = url.searchParams.get('cache_policy') ?? 'read-write';
	const cachePolicy = cachePolicies.has(requestedCachePolicy)
		? (requestedCachePolicy as 'read-write' | 'read-only' | 'off')
		: ('read-write' as const);
	const validTools = new Set(toolsForLanguage(language).map(({ id }) => id));
	const requestedDictionaries = url.searchParams.getAll('dictionary');
	const hasAllDictionaryRequest =
		requestedDictionaries.length === 0 || requestedDictionaries.includes('all');
	const requestedToolFilters = requestedDictionaries.filter((dictionary): dictionary is ToolId =>
		validTools.has(dictionary as ToolId)
	);
	const dictionaries: ToolRequest[] =
		hasAllDictionaryRequest || requestedToolFilters.length === 0 ? ['all'] : requestedToolFilters;

	if (!word) {
		return respond(emptyEncounterBriefingResponse(language, word, 'Briefing needs a word.'), {
			status: 400
		});
	}
	if (!isSingleWord(word)) {
		return respond(
			emptyEncounterBriefingResponse(language, word, 'Briefing accepts one word at a time.'),
			{ status: 400 }
		);
	}

	try {
		return respond(
			await encounterBriefingFromCli({
				language,
				query: word,
				dictionaries,
				translationMode,
				maxBuckets: readInteger(url.searchParams.get('max_buckets'), 8, 1, 100),
				maxGlossChars: readInteger(url.searchParams.get('max_gloss_chars'), 1400, 1, 100_000),
				maxMeanings: readInteger(url.searchParams.get('max_meanings'), 5, 1, 12),
				maxReaderUsages: readInteger(url.searchParams.get('max_reader_usages'), 3, 0, 12),
				maxSourceRefs: readInteger(url.searchParams.get('max_source_refs'), 10, 0, 40),
				model: url.searchParams.get('model') ?? 'openai:qwen/qwen3.7-max',
				generate: truthy(url.searchParams.get('generate')),
				cachePolicy,
				timeoutMs: readInteger(url.searchParams.get('timeout_ms'), 300_000, 1_000, 300_000)
			})
		);
	} catch (error) {
		return respond(emptyEncounterBriefingResponse(language, word, searchErrorMessage(error)), {
			status: 502
		});
	}
}

function emptyEncounterBriefingResponse(language: LanguageMode, query: string, error: string) {
	return {
		schema_version: 'langnet.encounter_briefing.web_error.v1',
		digest: { language, query, forms: query ? [query] : [] },
		generation: { status: 'error' },
		error
	};
}

function readInteger(value: string | null, fallback: number, min: number, max: number) {
	if (!value) return fallback;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return fallback;
	return Math.min(max, Math.max(min, parsed));
}

function truthy(value: string | null) {
	return value === '1' || value === 'yes' || value === 'true';
}
