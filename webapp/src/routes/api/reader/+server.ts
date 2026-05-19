import { payloadResponse } from '$lib/server/msgpack-response';
import {
	canCacheReaderResponse,
	readerCacheKey,
	readerResponseCache
} from '$lib/server/reader-cache';
import { languageModes, type LanguageMode } from '$lib/search-data';
import {
	readerAliases,
	readerAuthorFacets,
	readerAuthorSections,
	readerAuthors,
	readerCatalogs,
	readerCollections,
	readerContents,
	readerFacets,
	readerGroups,
	readerResolveAddress,
	readerSearch,
	readerShow,
	readerShelves,
	readerSummary,
	readerTags,
	readerWork,
	readerWorks
} from '$lib/server/reader-cli';

const validLanguages = new Set(languageModes.map(({ id }) => id));
const validModes = new Set([
	'catalogs',
	'summary',
	'collections',
	'aliases',
	'facets',
	'groups',
	'tags',
	'author-facets',
	'shelves',
	'search',
	'author-sections',
	'authors',
	'work',
	'works',
	'contents',
	'show',
	'resolve-address'
]);

export async function GET({ url, request }) {
	const requestedMode = url.searchParams.get('mode') ?? 'catalogs';
	const mode = validModes.has(requestedMode) ? requestedMode : 'catalogs';
	const catalogId = url.searchParams.get('catalog');
	const language = readLanguage(url.searchParams.get('language') ?? url.searchParams.get('lang'));
	const timeoutMs = readInteger(url.searchParams.get('timeout_ms'), 120_000, 1_000, 300_000);
	const options = { timeoutMs, signal: request.signal };
	const startedAt = performance.now();
	const respond = (payload: unknown, init: ResponseInit = {}) => {
		const headers = new Headers(init.headers);
		const readerTiming = `reader;dur=${(performance.now() - startedAt).toFixed(1)}`;
		const existingTiming = headers.get('server-timing');
		headers.set(
			'server-timing',
			existingTiming ? `${existingTiming}, ${readerTiming}` : readerTiming
		);
		return payloadResponse(request, payload, { ...init, headers });
	};
	const cacheKey = readerCacheKey(url);
	const cached = readerResponseCache.get(cacheKey);
	if (cached) {
		return respond(cached, {
			headers: { 'server-timing': 'reader_cache;desc="hit"' }
		});
	}
	const cachedRespond = (payload: unknown, init: ResponseInit = {}) => {
		if ((init.status ?? 200) < 400 && canCacheReaderResponse(payload)) {
			readerResponseCache.set(cacheKey, payload);
		}
		return respond(payload, init);
	};

	try {
		if (mode === 'catalogs') return cachedRespond(await readerCatalogs(options));
		if (mode === 'summary') return cachedRespond(await readerSummary(catalogId, options));
		if (mode === 'collections') return cachedRespond(await readerCollections(catalogId, options));
		if (mode === 'aliases') return cachedRespond(await readerAliases(catalogId, options));
		if (mode === 'facets') return cachedRespond(await readerFacets(catalogId, language, options));
		if (mode === 'groups') return cachedRespond(await readerGroups(catalogId, language, options));
		if (mode === 'tags') return cachedRespond(await readerTags(catalogId, language, options));
		if (mode === 'author-facets') {
			return cachedRespond(await readerAuthorFacets(catalogId, language, options));
		}
		if (mode === 'shelves') {
			if (!language) {
				return respond({ error: 'Reader shelves require a language.' }, { status: 400 });
			}
			return cachedRespond(
				await readerShelves({
					catalogId,
					language,
					limit: readInteger(url.searchParams.get('limit'), 12, 1, 60),
					sampleLimit: readInteger(
						url.searchParams.get('sample_limit') ?? url.searchParams.get('sampleLimit'),
						2,
						0,
						8
					),
					options
				})
			);
		}
		if (mode === 'search') {
			const query = (url.searchParams.get('q') ?? url.searchParams.get('query') ?? '').trim();
			if (!query)
				return respond({ error: 'Reader text search requires a query.' }, { status: 400 });
			return cachedRespond(
				await readerSearch({
					catalogId,
					language,
					query,
					searchMode: readSearchMode(
						url.searchParams.get('search_mode') ?? url.searchParams.get('searchMode')
					),
					collection: url.searchParams.get('collection') ?? undefined,
					workId: url.searchParams.get('work_id') ?? url.searchParams.get('workId') ?? undefined,
					authorId:
						url.searchParams.get('author_id') ?? url.searchParams.get('authorId') ?? undefined,
					group: url.searchParams.get('group') ?? undefined,
					tag: url.searchParams.get('tag') ?? undefined,
					context: readInteger(url.searchParams.get('context'), 1, 0, 20),
					limit: readInteger(url.searchParams.get('limit'), 20, 1, 100),
					cursor: url.searchParams.get('cursor') ?? undefined,
					options
				})
			);
		}
		if (mode === 'author-sections') {
			if (!language) {
				return respond({ error: 'Reader author sections require a language.' }, { status: 400 });
			}
			return cachedRespond(await readerAuthorSections({ catalogId, language, options }));
		}
		if (mode === 'authors') {
			return cachedRespond(
				await readerAuthors({
					catalogId,
					language,
					query: url.searchParams.get('q') ?? url.searchParams.get('query') ?? undefined,
					section: url.searchParams.get('section') ?? undefined,
					agentKind:
						url.searchParams.get('agent_kind') ?? url.searchParams.get('agentKind') ?? undefined,
					historicity: url.searchParams.get('historicity') ?? undefined,
					sort: readAuthorSort(url.searchParams.get('sort')),
					limit: readInteger(url.searchParams.get('limit'), 50, 1, 200),
					cursor: url.searchParams.get('cursor') ?? undefined,
					options
				})
			);
		}
		if (mode === 'work') {
			const work = (url.searchParams.get('work') ?? url.searchParams.get('ref') ?? '').trim();
			if (!work)
				return respond({ error: 'Reader work lookup requires a work parameter.' }, { status: 400 });
			return cachedRespond(await readerWork({ catalogId, language, work, options }));
		}
		if (mode === 'works') {
			return cachedRespond(
				await readerWorks({
					catalogId,
					language,
					query: url.searchParams.get('q') ?? url.searchParams.get('query') ?? undefined,
					author: url.searchParams.get('author') ?? undefined,
					authorId:
						url.searchParams.get('author_id') ?? url.searchParams.get('authorId') ?? undefined,
					attributedTo: url.searchParams.get('attributed_to') ?? undefined,
					collection: url.searchParams.get('collection') ?? undefined,
					scope: url.searchParams.get('scope') ?? undefined,
					group: url.searchParams.get('group') ?? undefined,
					tag: url.searchParams.get('tag') ?? undefined,
					sort: readWorksSort(url.searchParams.get('sort')),
					limit: readInteger(url.searchParams.get('limit'), 40, 1, 200),
					cursor: url.searchParams.get('cursor') ?? undefined,
					options
				})
			);
		}
		if (mode === 'contents') {
			const work = (url.searchParams.get('work') ?? '').trim();
			if (!work)
				return respond({ error: 'Reader contents requires a work parameter.' }, { status: 400 });
			return cachedRespond(
				await readerContents({
					catalogId,
					language,
					work,
					limit: readInteger(url.searchParams.get('limit'), 80, 1, 500),
					cursor: url.searchParams.get('cursor') ?? undefined,
					from: url.searchParams.get('from') ?? undefined,
					around: url.searchParams.get('around') ?? undefined,
					radius: readOptionalInteger(url.searchParams.get('radius'), 1, 250),
					charBudget: readOptionalInteger(
						url.searchParams.get('char_budget') ?? url.searchParams.get('charBudget'),
						500,
						100_000
					),
					options
				})
			);
		}
		if (mode === 'show') {
			const address = (
				url.searchParams.get('address') ??
				url.searchParams.get('work') ??
				''
			).trim();
			if (!address)
				return respond(
					{ error: 'Reader show requires an address or work parameter.' },
					{ status: 400 }
				);
			return cachedRespond(
				await readerShow({
					catalogId,
					language,
					address,
					segment: url.searchParams.get('segment') ?? undefined,
					options
				})
			);
		}
		if (mode === 'resolve-address') {
			const address = (url.searchParams.get('address') ?? '').trim();
			if (!address) {
				return respond(
					{ error: 'Reader address resolution requires an address parameter.' },
					{ status: 400 }
				);
			}
			return cachedRespond(await readerResolveAddress({ catalogId, language, address, options }));
		}
	} catch (error) {
		return respond(
			{
				error: error instanceof Error ? error.message : 'Reader request failed.',
				mode
			},
			{ status: 502 }
		);
	}

	return respond({ error: 'Unsupported reader mode.', mode }, { status: 400 });
}

function readLanguage(value: string | null): LanguageMode | undefined {
	if (!value) return undefined;
	return validLanguages.has(value as LanguageMode) ? (value as LanguageMode) : undefined;
}

function readInteger(value: string | null, fallback: number, min: number, max: number) {
	if (!value) return fallback;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return fallback;
	return Math.min(max, Math.max(min, parsed));
}

function readOptionalInteger(value: string | null, min: number, max: number) {
	if (!value) return undefined;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return undefined;
	return Math.min(max, Math.max(min, parsed));
}

function readWorksSort(value: string | null) {
	if (
		value === 'catalog' ||
		value === 'popularity' ||
		value === 'global-popularity' ||
		value === 'group-popularity'
	) {
		return value;
	}
	return undefined;
}

function readSearchMode(value: string | null) {
	if (value === 'keyword' || value === 'phrase' || value === 'exact' || value === 'fuzzy') {
		return value;
	}
	return 'fuzzy';
}

function readAuthorSort(value: string | null) {
	if (value === 'catalog' || value === 'prominence') return value;
	return undefined;
}
