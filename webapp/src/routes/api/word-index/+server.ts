import { json } from '@sveltejs/kit';
import { isSingleWord, languageModes, tools, type LanguageMode } from '$lib/search-data';
import { wordIndexFromCli } from '$lib/server/langnet-cli';
import type { WordIndexLanguage, WordIndexMode, WordIndexRequest } from '$lib/word-index';

const validLanguages = new Set<WordIndexLanguage>(['all', ...languageModes.map(({ id }) => id)]);
const validModes = new Set<WordIndexMode>([
	'sources',
	'sections',
	'wheel',
	'list',
	'nearby',
	'browse'
]);

export async function GET({ url }) {
	const requestedMode = url.searchParams.get('mode') ?? 'nearby';
	const mode = validModes.has(requestedMode as WordIndexMode)
		? (requestedMode as WordIndexMode)
		: ('nearby' as const);
	const requestedLanguage =
		url.searchParams.get('language') ?? url.searchParams.get('lang') ?? 'all';
	const language = validLanguages.has(requestedLanguage as WordIndexLanguage)
		? (requestedLanguage as WordIndexLanguage)
		: ('all' as const);
	const source = normalizeSource(url.searchParams.get('source') ?? 'all', language);
	const query = (url.searchParams.get('q') ?? url.searchParams.get('query') ?? '').trim();
	const prefix = (url.searchParams.get('prefix') ?? query).trim();
	const request: WordIndexRequest = {
		mode,
		language,
		source,
		query,
		prefix,
		radius: readInteger(url.searchParams.get('radius'), 5, 1, 20),
		count: readInteger(url.searchParams.get('count'), 12, 1, 50),
		seed: url.searchParams.get('seed') ?? 'daily',
		timeoutMs: readInteger(url.searchParams.get('timeout_ms'), 30_000, 1_000, 120_000)
	};

	if (
		(mode === 'nearby' || mode === 'list' || mode === 'sections' || mode === 'browse') &&
		language === 'all'
	) {
		return json(
			{
				...emptyWordIndexResponse(request),
				error: 'Dictionary index lookup needs one language.'
			},
			{ status: 400 }
		);
	}

	if (mode === 'nearby' && (!query || !isSingleWord(query))) {
		return json(
			{
				...emptyWordIndexResponse(request),
				error: 'Nearby lookup accepts one word at a time.'
			},
			{ status: 400 }
		);
	}

	try {
		return json(await wordIndexFromCli(request));
	} catch (error) {
		return json(
			{
				...emptyWordIndexResponse(request),
				error: friendlyIndexError(error)
			},
			{ status: 502 }
		);
	}
}

function normalizeSource(source: string, language: WordIndexLanguage) {
	if (source === 'all') return 'all';
	if (language === 'all') return source;

	const validSources = new Set([
		...tools.filter((tool) => tool.language === language).map((tool) => tool.id),
		'lewis_short',
		'lsj',
		'mw',
		'ap90'
	]);

	return validSources.has(source) ? source : 'all';
}

function emptyWordIndexResponse(request: WordIndexRequest) {
	return {
		schema_version: 'langnet.word_index.v1',
		request,
		sources: [],
		items: [],
		neighborhood: { groups: [] },
		browse: { groups: [] },
		pagination: { next_cursor: null, prev_cursor: null },
		warnings: []
	};
}

function readInteger(value: string | null, fallback: number, min: number, max: number) {
	if (!value) return fallback;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return fallback;
	return Math.min(max, Math.max(min, parsed));
}

function friendlyIndexError(error: unknown) {
	const message = error instanceof Error ? error.message : '';
	if (/timed out after/i.test(message)) return message;
	if (/Invalid value for '--output'/i.test(message)) {
		return 'Dictionary index command rejected its output mode.';
	}
	if (/no indexed neighborhood found/i.test(message)) return 'No indexed neighbors were found.';
	if (/langnet-cli did not return JSON/i.test(message)) {
		return 'Dictionary index command did not return JSON.';
	}
	return 'Dictionary index lookup failed.';
}
