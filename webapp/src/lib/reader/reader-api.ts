import { fetchPayload } from '../msgpack';
import type { EncounterBriefingFlow } from '../encounter-briefing';
import type { LanguageMode } from '../search-data';
import type { ReaderCatalogLanguage, ReaderSearchMode } from './index';

type ReaderCatalogLanguageParams = {
	catalogId: string;
	language: LanguageMode;
};

function readerApiUrl(params: URLSearchParams) {
	return `/api/reader?${params.toString()}`;
}

function setIfPresent(params: URLSearchParams, key: string, value?: string | null) {
	const normalized = value?.trim();
	if (normalized) params.set(key, normalized);
}

export function readerCatalogsUrl() {
	return '/api/reader?mode=catalogs';
}

export function readerCollectionsUrl({ catalogId }: { catalogId?: string | null } = {}) {
	const params = new URLSearchParams({ mode: 'collections' });
	setIfPresent(params, 'catalog', catalogId);
	return readerApiUrl(params);
}

export async function fetchReaderApi<T>(url: string) {
	return fetchPayload<T & { error?: string }>(url);
}

export function readerEncounterBriefingUrl({
	language,
	token,
	generate
}: {
	language: LanguageMode;
	token: string;
	generate: boolean;
}) {
	const params = new URLSearchParams({
		language,
		q: token.trim(),
		translation: 'cache',
		timeout_ms: generate ? '300000' : '180000'
	});
	if (generate) params.set('generate', '1');
	return `/api/encounter-briefing?${params.toString()}`;
}

export async function fetchReaderEncounterBriefing({
	language,
	token,
	generate,
	signal
}: {
	language: LanguageMode;
	token: string;
	generate: boolean;
	signal?: AbortSignal;
}) {
	return fetchPayload<EncounterBriefingFlow & { error?: string }>(
		readerEncounterBriefingUrl({ language, token, generate }),
		{ signal }
	);
}

export function readerFacetsUrl({ catalogId, language }: ReaderCatalogLanguageParams) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'facets',
			catalog: catalogId,
			language
		})
	);
}

export function readerShelvesUrl({
	catalogId,
	language,
	limit = 12,
	sampleLimit = 2,
	timeoutMs = 300000
}: ReaderCatalogLanguageParams & {
	limit?: number;
	sampleLimit?: number;
	timeoutMs?: number;
}) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'shelves',
			catalog: catalogId,
			language,
			limit: String(limit),
			sample_limit: String(sampleLimit),
			timeout_ms: String(timeoutMs)
		})
	);
}

export function readerAuthorSectionsUrl({ catalogId, language }: ReaderCatalogLanguageParams) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'author-sections',
			catalog: catalogId,
			language
		})
	);
}

export function readerAuthorsUrl({
	catalogId,
	language,
	limit = 50,
	section,
	query,
	agentKind,
	historicity,
	sort,
	cursor
}: ReaderCatalogLanguageParams & {
	limit?: number;
	section?: string | null;
	query?: string | null;
	agentKind?: string | null;
	historicity?: string | null;
	sort?: string | null;
	cursor?: string | null;
}) {
	const params = new URLSearchParams({
		mode: 'authors',
		catalog: catalogId,
		language,
		limit: String(limit)
	});
	setIfPresent(params, 'section', section);
	setIfPresent(params, 'q', query);
	setIfPresent(params, 'agent_kind', agentKind);
	setIfPresent(params, 'historicity', historicity);
	setIfPresent(params, 'sort', sort);
	setIfPresent(params, 'cursor', cursor);
	return readerApiUrl(params);
}

export function readerWorksUrl({
	catalogId,
	language,
	limit = 120,
	authorId,
	authorName,
	query,
	group,
	tag,
	sort,
	collection,
	cursor
}: ReaderCatalogLanguageParams & {
	limit?: number;
	authorId?: string | null;
	authorName?: string | null;
	query?: string | null;
	group?: string | null;
	tag?: string | null;
	sort?: string | null;
	collection?: string | null;
	cursor?: string | null;
}) {
	const params = new URLSearchParams({
		mode: 'works',
		catalog: catalogId,
		language,
		limit: String(limit)
	});
	setIfPresent(params, 'author_id', authorId);
	if (!authorId?.trim()) setIfPresent(params, 'author', authorName);
	if (!authorId?.trim() && !authorName?.trim()) setIfPresent(params, 'q', query);
	setIfPresent(params, 'group', group);
	setIfPresent(params, 'tag', tag);
	setIfPresent(params, 'sort', sort);
	if (collection && collection !== 'all') params.set('collection', collection);
	setIfPresent(params, 'cursor', cursor);
	return readerApiUrl(params);
}

export function readerSourceIndexUrl({
	catalogId,
	language,
	collection,
	query,
	limit = 100,
	timeoutMs = 300000
}: {
	catalogId?: string | null;
	language?: ReaderCatalogLanguage | null;
	collection?: string | null;
	query?: string | null;
	limit?: number;
	timeoutMs?: number;
}) {
	const params = new URLSearchParams({
		mode: 'source-index',
		limit: String(limit),
		timeout_ms: String(timeoutMs)
	});
	setIfPresent(params, 'catalog', catalogId);
	setIfPresent(params, 'language', language);
	if (collection && collection !== 'all') params.set('collection', collection);
	setIfPresent(params, 'q', query);
	return readerApiUrl(params);
}

export function readerLibraryWatchlistUrl({
	query,
	language,
	status,
	limit = 100,
	timeoutMs = 120000
}: {
	query?: string | null;
	language?: ReaderCatalogLanguage | null;
	status?: string | null;
	limit?: number;
	timeoutMs?: number;
} = {}) {
	const params = new URLSearchParams({
		mode: 'library-watchlist',
		limit: String(limit),
		timeout_ms: String(timeoutMs)
	});
	setIfPresent(params, 'q', query);
	setIfPresent(params, 'language', language);
	setIfPresent(params, 'status', status);
	return readerApiUrl(params);
}

export function readerTextSearchUrl({
	catalogId,
	language,
	query,
	searchMode,
	collection,
	cursor
}: ReaderCatalogLanguageParams & {
	query: string;
	searchMode: ReaderSearchMode;
	collection?: string | null;
	cursor?: string | null;
}) {
	const params = new URLSearchParams({
		mode: 'search',
		catalog: catalogId,
		language,
		q: query.trim(),
		search_mode: searchMode,
		context: '1',
		limit: '5',
		timeout_ms: '90000'
	});
	if (collection && collection !== 'all') params.set('collection', collection);
	setIfPresent(params, 'cursor', cursor);
	return readerApiUrl(params);
}

export function readerStructureUrl({
	catalogId,
	language,
	work
}: ReaderCatalogLanguageParams & { work: string }) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'structure',
			catalog: catalogId,
			language,
			work,
			timeout_ms: '120000'
		})
	);
}

export function readerWorkDossierUrl({
	catalogId,
	language,
	work
}: ReaderCatalogLanguageParams & { work: string }) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'about',
			catalog: catalogId,
			language,
			work,
			timeout_ms: '120000'
		})
	);
}

export function readerContentsUrl({
	catalogId,
	language,
	work,
	limit,
	charBudget,
	cursor,
	around,
	radius
}: ReaderCatalogLanguageParams & {
	work: string;
	limit: number;
	charBudget: number;
	cursor?: string | null;
	around?: string | null;
	radius?: number | null;
}) {
	const params = new URLSearchParams({
		mode: 'contents',
		catalog: catalogId,
		language,
		work
	});
	setIfPresent(params, 'around', around);
	if (radius !== undefined && radius !== null) params.set('radius', String(radius));
	params.set('limit', String(limit));
	params.set('char_budget', String(charBudget));
	setIfPresent(params, 'cursor', cursor);
	return readerApiUrl(params);
}

export function readerShowUrl({
	catalogId,
	language,
	work,
	segment,
	address
}: ReaderCatalogLanguageParams & {
	work?: string | null;
	segment?: string | null;
	address?: string | null;
}) {
	const params = new URLSearchParams({
		mode: 'show',
		catalog: catalogId,
		language
	});
	setIfPresent(params, 'work', work);
	setIfPresent(params, 'segment', segment);
	setIfPresent(params, 'address', address);
	return readerApiUrl(params);
}

export function readerResolveAddressUrl({
	catalogId,
	language,
	address
}: ReaderCatalogLanguageParams & { address: string }) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'resolve-address',
			catalog: catalogId,
			language,
			address
		})
	);
}

export function readerWorkMetadataUrl({
	catalogId,
	language,
	work
}: ReaderCatalogLanguageParams & { work: string }) {
	return readerApiUrl(
		new URLSearchParams({
			mode: 'work',
			catalog: catalogId,
			language,
			work
		})
	);
}
