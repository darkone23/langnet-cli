import { spawn } from 'node:child_process';
import type { LanguageMode } from '$lib/search-data';
import type {
	ReaderAuthorSectionsResponse,
	ReaderAuthorsResponse,
	ReaderCatalog,
	ReaderCatalogsResponse,
	ReaderFacetsResponse,
	ReaderSearchMode,
	ReaderSearchResponse,
	ReaderShelvesResponse,
	ReaderWorksResponse
} from '$lib/reader';
import {
	readerCatalogDefaults,
	readerDiscoverySortValue,
	readerProductCatalogs,
	resolveReaderCatalogChoice
} from '$lib/reader';
import { buildCliEnvironment, resolveCliDirectory } from './langnet-cli';
import { readerCatalogCache } from './reader-cache';

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
type JsonObject = { [key: string]: JsonValue };

type ReaderCliOptions = {
	timeoutMs?: number;
	signal?: AbortSignal;
};

const cliDirectory = resolveCliDirectory();
const defaultTimeoutMs = 120_000;

export async function readerCatalogs(
	options: ReaderCliOptions = {}
): Promise<ReaderCatalogsResponse> {
	const catalogs = await loadReaderCatalogs(options);
	const productCatalogs = readerProductCatalogs(catalogs);
	const hiddenAuditCount = catalogs.length - productCatalogs.length;

	return {
		schema_version: 'langnet.reader.web.v1',
		mode: 'catalogs',
		items: productCatalogs,
		defaults: readerCatalogDefaults(catalogs),
		warnings: [
			...(hiddenAuditCount
				? [
						`${hiddenAuditCount} reader audit ${hiddenAuditCount === 1 ? 'catalog is' : 'catalogs are'} hidden from the learner-facing catalog list.`
					]
				: []),
			...(catalogs.some((catalog) => catalog.id === 'development' && catalog.available)
				? ['Using the verified unified development catalog for reader defaults.']
				: [])
		]
	};
}

export async function readerSummary(catalogId: string | null, options: ReaderCliOptions = {}) {
	const catalog = await resolveReaderCatalog(catalogId, undefined, options);
	return withCatalog(
		await runReaderJsonCommand(catalog, ['summary', '--output', 'json'], options),
		catalog
	);
}

export async function readerCollections(catalogId: string | null, options: ReaderCliOptions = {}) {
	const catalog = await resolveReaderCatalog(catalogId, undefined, options);
	return withCatalog(
		await runReaderJsonCommand(catalog, ['collections', '--output', 'json'], options),
		catalog
	);
}

export async function readerAliases(catalogId: string | null, options: ReaderCliOptions = {}) {
	const catalog = await resolveReaderCatalog(catalogId, undefined, options);
	return withCatalog(
		await runReaderJsonCommand(catalog, ['aliases', '--output', 'json'], options),
		catalog
	);
}

export async function readerFacets(
	catalogId: string | null,
	language?: LanguageMode,
	options: ReaderCliOptions = {}
): Promise<ReaderFacetsResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['facets'];
	if (language) args.push('--language', language);
	args.push('--output', 'json');
	const rawPayload = await runReaderJsonCommand(catalog, args, options);
	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderFacetsResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderFacet)
	};
}

export async function readerGroups(
	catalogId: string | null,
	language?: LanguageMode,
	options: ReaderCliOptions = {}
): Promise<ReaderFacetsResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['groups'];
	if (language) args.push('--language', language);
	args.push('--output', 'json');
	const rawPayload = await runReaderJsonCommand(catalog, args, options);
	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderFacetsResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderFacet)
	};
}

export async function readerTags(
	catalogId: string | null,
	language?: LanguageMode,
	options: ReaderCliOptions = {}
): Promise<ReaderFacetsResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['tags'];
	if (language) args.push('--language', language);
	args.push('--output', 'json');
	const rawPayload = await runReaderJsonCommand(catalog, args, options);
	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderFacetsResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderFacet)
	};
}

export async function readerAuthorFacets(
	catalogId: string | null,
	language?: LanguageMode,
	options: ReaderCliOptions = {}
): Promise<ReaderFacetsResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const rawPayload = await runReaderJsonCommand(
		catalog,
		['author-facets', '--output', 'json'],
		options
	);
	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderFacetsResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderFacet)
	};
}

export async function readerShelves({
	catalogId,
	language,
	limit,
	sampleLimit,
	options = {}
}: {
	catalogId: string | null;
	language: LanguageMode;
	limit: number;
	sampleLimit: number;
	options?: ReaderCliOptions;
}): Promise<ReaderShelvesResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const rawPayload = await runReaderJsonCommand(
		catalog,
		[
			'shelves',
			'--language',
			language,
			'--limit',
			String(limit),
			'--sample-limit',
			String(sampleLimit),
			'--output',
			'json'
		],
		options
	);

	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderShelvesResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderShelf)
	};
}

export async function readerWorks({
	catalogId,
	language,
	query,
	author,
	authorId,
	attributedTo,
	collection,
	scope,
	group,
	tag,
	sort,
	limit,
	cursor,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	query?: string;
	author?: string;
	authorId?: string;
	attributedTo?: string;
	collection?: string;
	scope?: string;
	group?: string;
	tag?: string;
	sort?: 'catalog' | 'popularity' | 'global-popularity' | 'group-popularity';
	limit: number;
	cursor?: string;
	options?: ReaderCliOptions;
}): Promise<ReaderWorksResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['works'];
	if (language) args.push('--language', language);
	if (collection) args.push('--collection', collection);
	if (author) args.push('--author', author);
	if (authorId) args.push('--author-id', authorId);
	if (attributedTo) args.push('--attributed-to', attributedTo);
	if (scope) args.push('--scope', scope);
	if (group) args.push('--group', group);
	if (tag) args.push('--tag', tag);
	if (query) args.push('--query', query);
	args.push('--limit', String(limit));
	if (cursor) args.push('--cursor', cursor);
	if (sort) args.push('--sort', sort);
	args.push('--output', 'json');

	const rawPayload = await runReaderJsonCommand(catalog, args, options);
	const pagination = objectValue(rawPayload.pagination);

	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderWorksResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderWork),
		pagination: {
			limit: numberValue(pagination?.limit) || limit,
			next_cursor: nullableString(pagination?.next_cursor),
			prev_cursor: nullableString(pagination?.prev_cursor)
		}
	};
}

export async function readerSearch({
	catalogId,
	language,
	query,
	searchMode,
	collection,
	workId,
	authorId,
	group,
	tag,
	context,
	limit,
	cursor,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	query: string;
	searchMode: ReaderSearchMode;
	collection?: string;
	workId?: string;
	authorId?: string;
	group?: string;
	tag?: string;
	context: number;
	limit: number;
	cursor?: string;
	options?: ReaderCliOptions;
}): Promise<ReaderSearchResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['search', query];
	if (language) args.push('--language', language);
	if (collection) args.push('--collection', collection);
	if (workId) args.push('--work-id', workId);
	if (authorId) args.push('--author-id', authorId);
	if (group) args.push('--group', group);
	if (tag) args.push('--tag', tag);
	args.push('--mode', searchMode);
	args.push('--field', 'auto');
	args.push('--context', String(context));
	args.push('--limit', String(limit));
	if (cursor) args.push('--cursor', cursor);
	args.push('--output', 'json');

	const rawPayload = await runReaderJsonCommand(catalog, args, options);
	const pagination = objectValue(rawPayload.pagination);
	const request = objectValue(rawPayload.request);

	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderSearchResponse, 'items' | 'request'> & {
			catalog: ReaderCatalog;
		}),
		request: {
			query: stringValue(request?.query),
			language: nullableLanguage(request?.language),
			collection_id: nullableString(request?.collection_id),
			search_mode: readReaderSearchMode(stringValue(request?.search_mode)) ?? searchMode,
			field: stringValue(request?.field),
			query_candidates: arrayOfObjects(request?.query_candidates).map(mapReaderSearchCandidate)
		},
		items: arrayOfObjects(rawPayload.items).map(mapReaderSearchResult),
		pagination: {
			limit: numberValue(pagination?.limit) || limit,
			next_cursor: nullableString(pagination?.next_cursor),
			prev_cursor: nullableString(pagination?.prev_cursor)
		}
	};
}

export async function readerAuthorSections({
	catalogId,
	language,
	options = {}
}: {
	catalogId: string | null;
	language: LanguageMode;
	options?: ReaderCliOptions;
}): Promise<ReaderAuthorSectionsResponse & { catalog: ReaderCatalog }> {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const rawPayload = await runReaderJsonCommand(
		catalog,
		['author-sections', '--language', language, '--output', 'json'],
		options
	);
	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderAuthorSectionsResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderAuthorSection)
	};
}

export async function readerWork({
	catalogId,
	language,
	work,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	work: string;
	options?: ReaderCliOptions;
}) {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const payload = await runReaderJsonCommand(catalog, ['work', work, '--output', 'json'], options);
	return {
		...withCatalog(payload, catalog),
		item: objectValue(payload.item) ? mapReaderWork(objectValue(payload.item) as JsonObject) : null
	};
}

export async function readerAuthors({
	catalogId,
	language,
	query,
	section,
	agentKind,
	historicity,
	sort,
	limit,
	cursor,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	query?: string;
	section?: string;
	agentKind?: string;
	historicity?: string;
	sort?: 'catalog' | 'prominence';
	limit: number;
	cursor?: string;
	options?: ReaderCliOptions;
}) {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['authors'];
	if (language) args.push('--language', language);
	if (section) args.push('--section', section);
	if (query) args.push('--query', query);
	if (agentKind) args.push('--agent-kind', agentKind);
	if (historicity) args.push('--historicity', historicity);
	if (sort) args.push('--sort', sort);
	args.push('--limit', String(limit));
	if (cursor) args.push('--cursor', cursor);
	args.push('--output', 'json');
	const rawPayload = await runReaderJsonCommand(catalog, args, options);
	const pagination = objectValue(rawPayload.pagination);

	return {
		...(withCatalog(rawPayload, catalog) as Omit<ReaderAuthorsResponse, 'items'> & {
			catalog: ReaderCatalog;
		}),
		items: arrayOfObjects(rawPayload.items).map(mapReaderAuthor),
		pagination: {
			limit: numberValue(pagination?.limit) || limit,
			next_cursor: nullableString(pagination?.next_cursor),
			prev_cursor: nullableString(pagination?.prev_cursor)
		}
	};
}

export async function readerContents({
	catalogId,
	language,
	work,
	limit,
	cursor,
	from,
	around,
	radius,
	charBudget,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	work: string;
	limit: number;
	cursor?: string;
	from?: string;
	around?: string;
	radius?: number;
	charBudget?: number;
	options?: ReaderCliOptions;
}) {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['contents', work, '--limit', String(limit)];
	if (cursor) args.push('--cursor', cursor);
	if (from) args.push('--from', from);
	if (around) args.push('--around', around);
	if (radius) args.push('--radius', String(radius));
	if (charBudget) args.push('--char-budget', String(charBudget));
	args.push('--output', 'json');
	return withCatalog(await runReaderJsonCommand(catalog, args, options), catalog);
}

export async function readerShow({
	catalogId,
	language,
	address,
	segment,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	address: string;
	segment?: string;
	options?: ReaderCliOptions;
}) {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	const args = ['show', address];
	if (segment) args.push('--segment', segment);
	args.push('--output', 'json');
	return withCatalog(await runReaderJsonCommand(catalog, args, options), catalog);
}

export async function readerResolveAddress({
	catalogId,
	language,
	address,
	options = {}
}: {
	catalogId: string | null;
	language?: LanguageMode;
	address: string;
	options?: ReaderCliOptions;
}) {
	const catalog = await resolveReaderCatalog(catalogId, language, options);
	return withCatalog(
		await runReaderJsonCommand(catalog, ['resolve-address', address, '--output', 'json'], options),
		catalog
	);
}

async function resolveReaderCatalog(
	id: string | null,
	language?: LanguageMode,
	options: ReaderCliOptions = {}
): Promise<ReaderCatalog> {
	const catalogs = await loadReaderCatalogs(options);
	const catalog = resolveReaderCatalogChoice(catalogs, id, language);

	if (!catalog) throw new Error('No reader catalog is available.');
	if (!catalog.available) throw new Error(`Reader catalog is not available: ${catalog.label}`);
	return catalog;
}

async function loadReaderCatalogs(options: ReaderCliOptions = {}) {
	const cached = readerCatalogCache.get('catalogs');
	if (cached) return cached;

	const payload = await runReaderJsonCommandWithoutCatalog(
		['catalogs', '--output', 'json'],
		options
	);
	const catalogs = arrayOfObjects(payload.items).map(mapReaderCatalog);
	readerCatalogCache.set('catalogs', catalogs);
	return catalogs;
}

async function runReaderJsonCommand(
	catalog: ReaderCatalog,
	args: string[],
	options: ReaderCliOptions
): Promise<JsonObject> {
	return runJustJsonCommand(['cli', 'reader', '--catalog', catalog.path, ...args], options);
}

async function runReaderJsonCommandWithoutCatalog(
	args: string[],
	options: ReaderCliOptions
): Promise<JsonObject> {
	return runJustJsonCommand(['cli', 'reader', ...args], options);
}

async function runJustJsonCommand(args: string[], options: ReaderCliOptions): Promise<JsonObject> {
	return new Promise((resolve, reject) => {
		if (options.signal?.aborted) {
			reject(abortError());
			return;
		}

		const child = spawn('just', args, {
			cwd: cliDirectory,
			stdio: ['ignore', 'pipe', 'pipe'],
			env: buildCliEnvironment()
		});
		const chunks: Buffer[] = [];
		const errorChunks: Buffer[] = [];
		let settled = false;
		let timer: ReturnType<typeof setTimeout>;
		const cleanup = () => {
			clearTimeout(timer);
			options.signal?.removeEventListener('abort', onAbort);
		};
		const rejectAndKill = (error: Error) => {
			if (settled) return;
			settled = true;
			cleanup();
			child.kill('SIGTERM');
			reject(error);
		};
		const onAbort = () => rejectAndKill(abortError());

		options.signal?.addEventListener('abort', onAbort, { once: true });
		timer = setTimeout(() => {
			rejectAndKill(
				new Error(
					`langnet reader command timed out after ${Math.round((options.timeoutMs ?? defaultTimeoutMs) / 1000)}s`
				)
			);
		}, options.timeoutMs ?? defaultTimeoutMs);

		child.stdout.on('data', (chunk: Buffer) => chunks.push(chunk));
		child.stderr.on('data', (chunk: Buffer) => errorChunks.push(chunk));
		child.on('error', (error) => {
			if (!settled) {
				settled = true;
				cleanup();
				reject(error);
			}
		});
		child.on('close', (code) => {
			if (settled) return;
			settled = true;
			cleanup();

			const stdout = Buffer.concat(chunks).toString('utf8');
			const stderr = Buffer.concat(errorChunks).toString('utf8');
			const parsed = parseJsonFromOutput(stdout);

			if (code !== 0 && parsed) {
				reject(
					new Error(errorMessageFromPayload(parsed) || stderr.trim() || `reader CLI exited ${code}`)
				);
				return;
			}
			if (!parsed) {
				reject(new Error(stderr.trim() || stdout.trim() || 'reader CLI did not return JSON'));
				return;
			}
			resolve(parsed);
		});
	});
}

function withCatalog(payload: JsonObject, catalog: ReaderCatalog) {
	return {
		...payload,
		catalog
	};
}

function abortError() {
	const error = new Error('reader CLI request was cancelled.');
	error.name = 'AbortError';
	return error;
}

function parseJsonFromOutput(output: string): JsonObject | null {
	const start = output.indexOf('{');
	const end = output.lastIndexOf('}');
	if (start === -1 || end === -1 || end <= start) return null;
	try {
		const parsed = JSON.parse(output.slice(start, end + 1));
		return isObject(parsed) ? parsed : null;
	} catch {
		return null;
	}
}

function errorMessageFromPayload(payload: JsonObject) {
	return stringValue(payload.error) || stringValue(payload.message);
}

function mapReaderCatalog(item: JsonObject): ReaderCatalog {
	return {
		id: stringValue(item.id),
		label: stringValue(item.label),
		path: stringValue(item.path),
		languages: arrayOfStrings(item.languages).filter(
			(language) =>
				language === 'san' || language === 'grc' || language === 'lat' || language === 'eng'
		) as ReaderCatalog['languages'],
		readiness: stringValue(item.readiness),
		available: booleanValue(item.exists) || booleanValue(item.available),
		work_count: numberValue(item.work_count),
		segment_count: numberValue(item.segment_count),
		description: catalogDescription(item)
	};
}

function catalogDescription(item: JsonObject) {
	const label = stringValue(item.label) || stringValue(item.id);
	const workCount = numberValue(item.work_count);
	const segmentCount = numberValue(item.segment_count);
	const readiness = stringValue(item.readiness);
	if (workCount || segmentCount) {
		return `${label}: ${workCount.toLocaleString()} works, ${segmentCount.toLocaleString()} segments (${readiness}).`;
	}
	return `${label}: ${readiness || 'catalog candidate'}.`;
}

function mapReaderWork(item: JsonObject) {
	return {
		work_id: stringValue(item.work_id),
		collection_id: stringValue(item.collection_id),
		language: normalizeLanguage(stringValue(item.language)),
		title: stringValue(item.title),
		author: stringValue(item.author),
		author_id: nullableString(item.author_id),
		source_author: nullableString(item.source_author),
		source_author_id: nullableString(item.source_author_id),
		source_id: stringValue(item.source_id),
		cts_work_urn: nullableString(item.cts_work_urn),
		work_kind: stringValue(item.work_kind),
		parent_work_id: nullableString(item.parent_work_id),
		start_citation: nullableString(item.start_citation),
		end_citation: nullableString(item.end_citation),
		word_count: numberValue(item.word_count),
		word_count_method: stringValue(item.word_count_method),
		classification_category: nullableString(item.classification_category),
		classification_period: nullableString(item.classification_period),
		classification_date_range: nullableString(item.classification_date_range),
		classification_authorship_status: nullableString(item.classification_authorship_status),
		classification_popularity_tier: nullableString(item.classification_popularity_tier),
		classification_scope: nullableString(item.classification_scope),
		classification_discovery_group_id: nullableString(item.classification_discovery_group_id),
		classification_discovery_tags: nullableString(item.classification_discovery_tags),
		classification_global_popularity_score: nullableNumber(
			item.classification_global_popularity_score
		),
		classification_global_popularity_tier: nullableString(
			item.classification_global_popularity_tier
		),
		classification_group_popularity_score: nullableNumber(
			item.classification_group_popularity_score
		),
		classification_group_popularity_tier: nullableString(item.classification_group_popularity_tier),
		classification_confidence: nullableString(item.classification_confidence),
		classification_notes: nullableString(item.classification_notes),
		canonical_author_id: nullableString(item.canonical_author_id),
		canonical_author_name: nullableString(item.canonical_author_name),
		canonical_author_kind: nullableString(item.canonical_author_kind),
		translator_names: arrayOfStrings(item.translator_names),
		traditional_author_names: arrayOfStrings(item.traditional_author_names),
		attributed_author_names: arrayOfStrings(item.attributed_author_names),
		metadata_attributions: arrayOfObjects(item.metadata_attributions).map(
			mapReaderMetadataAttribution
		)
	};
}

function mapReaderMetadataAttribution(item: JsonObject) {
	return {
		relation_type: stringValue(item.relation_type),
		agent: stringValue(item.agent),
		status: stringValue(item.status),
		confidence: stringValue(item.confidence),
		note: stringValue(item.note) || undefined,
		evidence_citation: stringValue(item.evidence_citation) || undefined,
		evidence_label: stringValue(item.evidence_label) || undefined
	};
}

function mapReaderFacet(item: JsonObject) {
	return {
		id: stringValue(item.id),
		label: stringValue(item.label),
		description: stringValue(item.description),
		command: stringValue(item.command),
		filter: stringValue(item.filter),
		values: arrayOfObjects(item.values).map(mapReaderFacetValue),
		examples: arrayOfObjects(item.examples).map((example) => ({
			question: stringValue(example.question),
			command: stringValue(example.command)
		}))
	};
}

function mapReaderFacetValue(item: JsonObject) {
	return {
		id: stringValue(item.id),
		label: stringValue(item.label),
		description: stringValue(item.description),
		work_count: numberValue(item.work_count),
		classified_work_count: numberValue(item.classified_work_count),
		author_count: numberValue(item.author_count),
		max_group_popularity_score: numberValue(item.max_group_popularity_score)
	};
}

function mapReaderShelf(item: JsonObject) {
	const query = objectValue(item.query);
	return {
		id: stringValue(item.id),
		label: stringValue(item.label),
		description: stringValue(item.description),
		query: {
			group: stringValue(query?.group) || undefined,
			tag: stringValue(query?.tag) || undefined,
			sort: readerDiscoverySortValue(stringValue(query?.sort))
		},
		work_count: numberValue(item.work_count),
		classified_work_count: numberValue(item.classified_work_count),
		author_count: numberValue(item.author_count),
		max_group_popularity_score: numberValue(item.max_group_popularity_score),
		sample_works: arrayOfObjects(item.sample_works).map(mapReaderShelfSampleWork)
	};
}

function mapReaderShelfSampleWork(item: JsonObject) {
	return {
		work_id: stringValue(item.work_id),
		title: stringValue(item.title),
		author: stringValue(item.author),
		language: normalizeLanguage(stringValue(item.language)),
		source_id: stringValue(item.source_id),
		classification_group_popularity_score: nullableNumber(
			item.classification_group_popularity_score
		)
	};
}

function mapReaderSearchCandidate(item: JsonObject) {
	return {
		query: stringValue(item.query),
		kind: stringValue(item.kind),
		field: stringValue(item.field),
		rank: numberValue(item.rank)
	};
}

function mapReaderSearchContextLine(item: JsonObject) {
	return {
		citation_path: stringValue(item.citation_path),
		text: stringValue(item.text),
		sort_key: numberValue(item.sort_key)
	};
}

function mapReaderSearchResult(item: JsonObject) {
	const target = objectValue(item.target);
	return {
		score: numberValue(item.score),
		work_id: stringValue(item.work_id),
		collection_id: stringValue(item.collection_id),
		language: normalizeLanguage(stringValue(item.language)),
		title: stringValue(item.title),
		author: stringValue(item.author),
		canonical_author_id: nullableString(item.canonical_author_id),
		canonical_author_name: nullableString(item.canonical_author_name),
		cts_work_urn: nullableString(item.cts_work_urn),
		citation_path: stringValue(item.citation_path),
		segment_id: stringValue(item.segment_id),
		sort_key: numberValue(item.sort_key),
		text: stringValue(item.text),
		snippet: stringValue(item.snippet),
		context_before: arrayOfObjects(item.context_before).map(mapReaderSearchContextLine),
		context_after: arrayOfObjects(item.context_after).map(mapReaderSearchContextLine),
		target: target
			? {
					reader_command: stringValue(target.reader_command),
					work_ref: stringValue(target.work_ref),
					segment: stringValue(target.segment)
				}
			: undefined,
		matched_query: stringValue(item.matched_query) || undefined,
		input_query: stringValue(item.input_query) || undefined,
		match_type: stringValue(item.match_type) || undefined,
		candidate_rank: numberValue(item.candidate_rank),
		matched_field: stringValue(item.matched_field) || undefined
	};
}

function mapReaderAuthorSection(item: JsonObject) {
	return {
		key: stringValue(item.key),
		label: stringValue(item.label),
		native_label: stringValue(item.native_label),
		sort_key: stringValue(item.sort_key),
		author_count: numberValue(item.author_count),
		work_count: numberValue(item.work_count)
	};
}

function mapReaderAuthor(item: JsonObject) {
	return {
		author_id: stringValue(item.author_id),
		source_author_id: stringValue(item.source_author_id),
		display_name: stringValue(item.display_name),
		author: stringValue(item.author),
		index_name: stringValue(item.index_name),
		native_name: stringValue(item.native_name),
		section_key: stringValue(item.section_key),
		language: normalizeLanguage(stringValue(item.language)),
		work_count: numberValue(item.work_count),
		alternate_names: arrayOfStrings(item.alternate_names),
		sort_key: stringValue(item.sort_key),
		canonical_author_id: nullableString(item.canonical_author_id),
		canonical_author_name: nullableString(item.canonical_author_name),
		canonical_author_kind: nullableString(item.canonical_author_kind)
	};
}

function normalizeLanguage(value: string): LanguageMode {
	if (value === 'grc' || value === 'lat' || value === 'san') return value;
	return 'san';
}

function nullableLanguage(value: JsonValue | undefined): LanguageMode | null {
	const parsed = stringValue(value);
	return parsed === 'grc' || parsed === 'lat' || parsed === 'san' ? parsed : null;
}

function readReaderSearchMode(value: string): ReaderSearchMode | undefined {
	if (value === 'keyword' || value === 'phrase' || value === 'exact' || value === 'fuzzy') {
		return value;
	}
	return undefined;
}

function isObject(value: JsonValue | unknown): value is JsonObject {
	return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function objectValue(value: JsonValue | undefined): JsonObject | undefined {
	return isObject(value) ? value : undefined;
}

function arrayOfObjects(value: JsonValue | undefined): JsonObject[] {
	return Array.isArray(value)
		? value.map(objectValue).filter((item): item is JsonObject => Boolean(item))
		: [];
}

function arrayOfStrings(value: JsonValue | undefined): string[] {
	return Array.isArray(value)
		? value.filter((item): item is string => typeof item === 'string')
		: [];
}

function stringValue(value: JsonValue | undefined) {
	return typeof value === 'string' ? value : '';
}

function numberValue(value: JsonValue | undefined) {
	return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function nullableNumber(value: JsonValue | undefined) {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function booleanValue(value: JsonValue | undefined) {
	return typeof value === 'boolean' ? value : false;
}

function nullableString(value: JsonValue | undefined) {
	const parsed = stringValue(value);
	return parsed || null;
}
