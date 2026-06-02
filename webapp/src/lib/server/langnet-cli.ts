import { spawn } from 'node:child_process';
import path from 'node:path';
import { componentGlossFromCli } from '$lib/component-gloss';
import type { EncounterBriefingFlow, EncounterBriefingRequest } from '$lib/encounter-briefing';
import { normalizeParadigmPayload, type ParadigmPayload } from '$lib/paradigm';
import { normalizeParadigmResolution } from '$lib/paradigm-resolution';
import {
	toolsForLanguage,
	type EncounterAnalysis,
	type EncounterBucket,
	type EncounterComponent,
	type EncounterComponentMeaning,
	type EncounterResult,
	type LanguageMode,
	type ToolId,
	type ToolRequest,
	type TranslationCache,
	type TranslationMode,
	type WordRecommendationItem,
	type WordRecommendationResult
} from '$lib/search-data';
import { extractSourceOutlineSegments, type SourceOutlineSegment } from '$lib/source-outline';
import type {
	WordIndexItem,
	WordIndexMode,
	WordIndexOrder,
	WordIndexRequest,
	WordIndexResponse,
	WordIndexSectionsResponse
} from '$lib/word-index';

export type CliRequest = {
	language: LanguageMode;
	query: string;
	dictionaries: ToolRequest[];
	translationMode: TranslationMode;
	maxBuckets: number;
	maxGlossChars: number;
	timeoutMs: number;
};

export type TranslationRetryRequest = {
	translationId?: string;
	sourceLexicon?: ToolId;
	entryId?: string;
	occurrence?: number;
	headword?: string;
	sourceTextHash?: string;
	retryReason?: string;
	maxRetries?: number;
	timeoutMs: number;
};

type ParadigmCliRequest = {
	language: LanguageMode;
	lemma: string;
	kind: string;
	gender?: string;
	presentClass?: string;
	timeoutMs: number;
};

export type JsonValue =
	| null
	| boolean
	| number
	| string
	| JsonValue[]
	| { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

const cliDirectory = resolveCliDirectory();
let cliQueue: Promise<void> = Promise.resolve();

type CliCommandOptions = {
	signal?: AbortSignal;
	queued?: boolean;
	stdin?: string;
};

export function buildCliEnvironment(baseEnv: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
	const pathEntries = (baseEnv.PATH ?? '').split(path.delimiter).filter(Boolean);
	const userLocalBin = baseEnv.HOME ? path.join(baseEnv.HOME, '.local', 'bin') : undefined;
	const PATH = dedupe(userLocalBin ? [...pathEntries, userLocalBin] : pathEntries).join(
		path.delimiter
	);

	return {
		...baseEnv,
		NO_COLOR: '1',
		...(PATH ? { PATH } : {})
	};
}

export function resolveCliDirectory(
	cwd: string = process.cwd(),
	env: NodeJS.ProcessEnv = process.env
): string {
	return path.resolve(cwd, env.LANGNET_CLI_DIR ?? '..');
}

export async function wordRecommendationsFromCli({
	language,
	dictionary,
	count,
	level,
	translationMode,
	timeoutMs,
	candidateSource,
	includeAmbiguous,
	requireCleanPrimary,
	finalizeCards,
	fresh,
	avoid,
	nonce,
	signal
}: {
	language: LanguageMode | 'all';
	dictionary?: string;
	count: number;
	level: string;
	translationMode: TranslationMode;
	timeoutMs: number;
	candidateSource: 'auto' | 'llm' | 'curated';
	includeAmbiguous?: boolean;
	requireCleanPrimary?: boolean;
	finalizeCards?: boolean;
	fresh: boolean;
	avoid: string[];
	nonce?: string;
	signal?: AbortSignal;
}): Promise<WordRecommendationResult> {
	const args = [
		'cli',
		'word-of-day',
		language,
		'--count',
		String(count),
		'--level',
		level,
		'--dictionary',
		dictionary ?? 'all',
		'--translation-mode',
		translationMode,
		'--candidate-source',
		candidateSource,
		'--timeout-ms',
		String(timeoutMs),
		'--output',
		'json'
	];

	if (fresh) args.push('--fresh');
	if (includeAmbiguous) args.push('--include-ambiguous');
	if (requireCleanPrimary) args.push('--require-clean-primary');
	if (finalizeCards === false) args.push('--no-finalize-cards');
	if (avoid.length) args.push('--avoid', avoid.join(','));
	if (nonce) args.push('--nonce', nonce);

	const payload = await runJsonCommand(args, timeoutMs + 8_000, { signal, queued: false });

	return mapWordRecommendationPayload(payload);
}

export async function wordRecommendationsFromMotdPool({
	language,
	count,
	level,
	timeoutMs,
	seed,
	avoid,
	signal
}: {
	language: LanguageMode | 'all';
	count: number;
	level: string;
	timeoutMs: number;
	seed?: string;
	avoid: string[];
	signal?: AbortSignal;
}): Promise<WordRecommendationResult> {
	const args = [
		'cli',
		'motd-pool',
		'sample',
		'--language',
		language,
		'--count',
		String(count),
		'--level',
		level,
		'--output',
		'json'
	];

	if (seed) args.push('--seed', seed);
	if (avoid.length) args.push('--avoid', avoid.join(','));

	const payload = await runJsonCommand(args, timeoutMs, { signal, queued: false });

	return mapWordRecommendationPayload(payload);
}

export async function encounterWordFromCli(request: CliRequest): Promise<EncounterResult> {
	const toolFilter = cliToolFilter(request.language, request.dictionaries);
	const args = [
		'cli',
		'encounter',
		request.language,
		request.query,
		toolFilter,
		'--translation-mode',
		request.translationMode,
		'--cache-policy',
		'read-only',
		'--output',
		'json',
		'--max-buckets',
		String(request.maxBuckets),
		'--max-gloss-chars',
		String(request.maxGlossChars),
		'--include-paradigm-resolution',
		'--include-learning'
	];
	const payload = await runJsonCommand(args, request.timeoutMs, { queued: false });

	return mapCliPayload(payload, request, toolFilter);
}

export async function encounterBriefingFromCli(
	request: EncounterBriefingRequest
): Promise<EncounterBriefingFlow> {
	const toolFilter = cliToolFilter(request.language, request.dictionaries);
	const encounterArgs = [
		'cli',
		'encounter',
		request.language,
		request.query,
		toolFilter,
		'--translation-mode',
		request.translationMode,
		'--cache-policy',
		'read-only',
		'--output',
		'json',
		'--max-buckets',
		String(request.maxBuckets),
		'--max-gloss-chars',
		String(request.maxGlossChars),
		'--include-paradigm-resolution',
		'--include-learning'
	];
	const encounterPayload = await runJsonCommand(encounterArgs, request.timeoutMs, {
		queued: false
	});
	const briefingArgs = [
		'cli',
		'encounter-briefing',
		'--input-json',
		'-',
		'--model',
		request.model,
		'--cache-policy',
		request.cachePolicy,
		'--max-meanings',
		String(request.maxMeanings),
		'--max-reader-usages',
		String(request.maxReaderUsages),
		'--max-source-refs',
		String(request.maxSourceRefs)
	];

	if (request.generate) briefingArgs.push('--generate');
	else briefingArgs.push('--cache-only');

	const payload = await runJsonCommand(briefingArgs, request.timeoutMs, {
		queued: true,
		stdin: JSON.stringify(encounterPayload)
	});

	return mapEncounterBriefingPayload(payload);
}

export async function clearTranslationCacheFromCli(
	request: TranslationRetryRequest
): Promise<JsonObject> {
	const args = ['cli', 'translation-cache', 'clear', '--yes', '--output', 'json'];
	if (request.translationId) args.push('--translation-id', request.translationId);
	if (request.sourceLexicon) args.push('--source-lexicon', request.sourceLexicon);
	if (request.entryId) args.push('--entry-id', request.entryId);
	if (request.occurrence !== undefined) args.push('--occurrence', String(request.occurrence));
	if (request.headword) args.push('--headword', request.headword);
	if (request.sourceTextHash) args.push('--source-text-hash', request.sourceTextHash);
	if (request.retryReason) args.push('--retry-reason', request.retryReason);
	if (request.maxRetries !== undefined) args.push('--max-retries', String(request.maxRetries));

	return await runJsonCommand(args, request.timeoutMs, { queued: true });
}

export async function wordIndexFromCli(
	request: WordIndexRequest
): Promise<WordIndexResponse | WordIndexSectionsResponse> {
	const args = wordIndexArgs(request);
	const payload = await runJsonCommand(args, request.timeoutMs ?? 30_000, { queued: false });

	if (request.mode === 'sections') return mapWordIndexSectionsPayload(payload, request);
	return mapWordIndexPayload(payload, request);
}

export async function paradigmFromCli(request: ParadigmCliRequest): Promise<ParadigmPayload> {
	const args = ['cli', 'paradigm', request.language, request.lemma, '--kind', request.kind];

	if (request.gender) args.push('--gender', request.gender);
	if (request.presentClass) args.push('--class', request.presentClass);
	args.push('--output', 'json');

	const payload = await runJsonCommand(args, request.timeoutMs, { queued: false });
	const normalized = normalizeParadigmPayload(payload);
	if (!normalized) throw new Error('langnet-cli did not return a paradigm payload.');
	return normalized;
}

function wordIndexArgs(request: WordIndexRequest) {
	const mode = request.mode === 'neighborhood' ? 'nearby' : request.mode;
	const args = ['cli', 'word-index', mode, request.language];

	if (mode === 'sections') {
		args.push('--source', request.source || 'all');
	} else if (mode === 'nearby') {
		args.push(request.query ?? '');
		args.push('--source', request.source || 'all');
		args.push('--radius', String(request.radius ?? 5));
	} else if (mode === 'list') {
		args.push('--source', request.source || 'all');
		args.push('--prefix', request.prefix ?? request.query ?? '');
		args.push('--limit', String(request.count ?? 12));
	} else if (mode === 'browse') {
		args.push('--source', request.source || 'all');
		args.push('--prefix', request.prefix ?? request.query ?? '');
		args.push('--limit', String(request.count ?? 12));
	} else if (mode === 'wheel') {
		args.push('--source', request.source || 'all');
		args.push('--count', String(request.count ?? 12));
		args.push('--seed', request.seed || 'daily');
	} else if (mode === 'sources') {
		// No extra flags before output.
	}

	args.push('--output', 'json');
	return args;
}

function cliToolFilter(language: LanguageMode, dictionaries: ToolRequest[]) {
	const requested = dictionaries.includes('all') ? ['all'] : dictionaries;
	const validTools = new Set(toolsForLanguage(language).map(({ id }) => id));
	const concreteTools = requested.filter(
		(tool): tool is ToolId => tool !== 'all' && validTools.has(tool as ToolId)
	);

	if (concreteTools.length === 1) return concreteTools[0];
	return 'all';
}

async function runJsonCommand(
	args: string[],
	timeoutMs: number,
	options: CliCommandOptions = {}
): Promise<JsonObject> {
	if (options.queued === false) {
		if (options.signal?.aborted) throw abortError();
		return await runJsonCommandUnlocked(args, timeoutMs, options);
	}

	const previous = cliQueue;
	let release!: () => void;
	cliQueue = previous
		.catch(() => undefined)
		.then(
			() =>
				new Promise<void>((resolve) => {
					release = resolve;
				})
		);

	await previous.catch(() => undefined);

	try {
		if (options.signal?.aborted) throw abortError();
		return await runJsonCommandUnlocked(args, timeoutMs, options);
	} finally {
		release();
	}
}

function runJsonCommandUnlocked(
	args: string[],
	timeoutMs: number,
	options: CliCommandOptions = {}
): Promise<JsonObject> {
	return new Promise((resolve, reject) => {
		if (options.signal?.aborted) {
			reject(abortError());
			return;
		}

		const child = spawn('just', args, {
			cwd: cliDirectory,
			stdio: [options.stdin === undefined ? 'ignore' : 'pipe', 'pipe', 'pipe'],
			env: buildCliEnvironment()
		});
		if (!child.stdout || !child.stderr) {
			reject(new Error('langnet-cli process streams were unavailable.'));
			return;
		}
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
		const onAbort = () => {
			rejectAndKill(abortError());
		};

		options.signal?.addEventListener('abort', onAbort, { once: true });
		timer = setTimeout(() => {
			rejectAndKill(new Error(`langnet-cli timed out after ${Math.round(timeoutMs / 1000)}s`));
		}, timeoutMs);

		if (options.stdin !== undefined) {
			child.stdin?.end(options.stdin);
		}

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
					new Error(
						errorMessageFromPayload(parsed) || stderr.trim() || `langnet-cli exited ${code}`
					)
				);
				return;
			}

			if (!parsed) {
				reject(new Error(stderr.trim() || stdout.trim() || 'langnet-cli did not return JSON'));
				return;
			}

			resolve(parsed);
		});
	});
}

function abortError() {
	const error = new Error('langnet-cli request was cancelled.');
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

export function mapCliPayload(
	payload: JsonObject,
	request: CliRequest,
	toolFilter: string
): EncounterResult {
	const display = objectValue(payload.display);
	const rawBuckets = arrayOfObjects(payload.buckets);
	const rankings = arrayOfObjects(payload.ranking);
	const meanings = arrayOfObjects(display?.meanings);
	const mappedBuckets = meanings.map((meaning, index) => {
		const bucketId =
			stringValue(meaning.bucket_id) || `bucket:${request.language}:${request.query}:${index}`;
		const rawBucket = rawBuckets.find((bucket) => stringValue(bucket.bucket_id) === bucketId);
		const ranking = rankings.find((rank) => stringValue(rank.bucket_id) === bucketId);

		const bucket = mapCliBucket({
			meaning,
			rawBucket,
			ranking,
			language: request.language,
			index
		});

		return { bucket, meaning, rawBucket };
	});
	const readerTranslationKeys = new Set(
		mappedBuckets
			.map(({ bucket }) => bucket)
			.filter((bucket) => bucket.translation?.available)
			.map(translatableEntryKey)
			.filter(Boolean)
	);
	const segmentedReaderTranslationKeys = new Set(
		mappedBuckets
			.filter(({ bucket, meaning, rawBucket }) => {
				if (!bucket.translation?.available) return false;
				return extractSourceOutlineSegments({
					tool:
						bucket.source_tools.find((tool) => tool === 'bailly') ??
						sourceToolFromSourceRef(bucket.source_refs[0]),
					rawWitnesses: arrayOfObjects(rawBucket?.witnesses),
					entries: arrayOfObjects(meaning.entries)
				}).some((segment) => segment.translatedText);
			})
			.map(({ bucket }) => translatableEntryKey(bucket))
			.filter(Boolean)
	);
	const buckets = mappedBuckets.flatMap(({ bucket, meaning, rawBucket }) => {
		const key = translatableEntryKey(bucket);
		if (!bucket.translation?.available && key && segmentedReaderTranslationKeys.has(key)) return [];
		if (!bucket.translation?.available && key && readerTranslationKeys.has(key)) return [bucket];
		return expandOutlinedSourceBucket(bucket, meaning, rawBucket);
	});
	const mergedBuckets = mergeTranslatedSourceBuckets(buckets);
	const filteredBuckets = filterBucketsByRequestedTools(mergedBuckets, request.dictionaries);
	const payloadSourceTools = normalizeToolIds(
		arrayOfStrings(payload.source_tools).filter((tool) => tool !== 'translation')
	);
	const responseSourceTools = filterToolIdsByRequest(payloadSourceTools, request.dictionaries);

	const translationCache = normalizeTranslationCache(
		objectValue(payload.translation_cache),
		request.translationMode
	);
	const payloadRequest = objectValue(payload.request);
	const analysis = arrayOfObjects(display?.analysis).map(mapCliAnalysis);
	const components = componentPayloads(payload, display).map(mapCliComponent);
	const paradigmResolution = normalizeParadigmResolution(payload.paradigm_resolution);
	const componentTools = dedupe(
		components.flatMap((component) => [
			component.source_tool,
			...component.evidence.meanings.flatMap((meaning) => meaning.source_tools)
		])
	);

	return {
		query: stringValue(payload.query) || request.query,
		language: request.language,
		dictionaries: request.dictionaries,
		source_tools: responseSourceTools.length
			? dedupe([
					...responseSourceTools,
					...componentTools,
					...filteredBuckets.flatMap((bucket) => bucket.source_tools)
				])
			: dedupe([...filteredBuckets.flatMap((bucket) => bucket.source_tools), ...componentTools]),
		lexeme_anchors: arrayOfStrings(payload.lexeme_anchors),
		buckets: filteredBuckets,
		analysis,
		components,
		...(paradigmResolution ? { paradigm_resolution: paradigmResolution } : {}),
		word_index: mapEncounterWordIndexContext(objectValue(payload.word_index)),
		translation_cache: translationCache,
		warnings: arrayOfStrings(payload.warnings),
		request: {
			translation_mode: normalizeTranslationMode(
				payloadRequest?.translation_mode,
				request.translationMode
			),
			tool_filter: toolFilter === 'all' ? ['all'] : [normalizeToolId(toolFilter)],
			reader_lang: 'en',
			cache_policy: stringValue(payloadRequest?.cache_policy) || undefined,
			normalization_cache_writes: booleanValue(payloadRequest?.normalization_cache_writes),
			translation_cache_writes: booleanValue(payloadRequest?.translation_cache_writes)
		},
		backend: 'cli'
	};
}

export function mapEncounterBriefingPayload(payload: JsonObject): EncounterBriefingFlow {
	const generation = objectValue(payload.generation);
	const digest = objectValue(payload.digest);
	const draftOutput = mapEncounterBriefingSummary(objectValue(payload.draft_output));
	const finalOutput = mapEncounterBriefingSummary(objectValue(payload.final_output));
	const modelOutput = mapEncounterBriefingSummary(objectValue(payload.model_output));

	return {
		schema_version: stringValue(payload.schema_version),
		...(digest
			? {
					digest: {
						query: stringValue(digest.query),
						language: normalizeLanguage(stringValue(digest.language)),
						forms: arrayOfStrings(digest.forms)
					}
				}
			: {}),
		generation: {
			status: stringValue(generation?.status),
			cached_status: stringValue(generation?.cached_status) || undefined,
			model: stringValue(generation?.model) || undefined,
			prompt_version: stringValue(generation?.prompt_version) || undefined,
			validation_issue_count: numberValue(generation?.validation_issue_count) || undefined,
			validation_issues: arrayOfObjects(generation?.validation_issues).map((issue) => ({
				code: stringValue(issue.code),
				path: stringValue(issue.path),
				message: stringValue(issue.message)
			}))
		},
		...(draftOutput ? { draft_output: draftOutput } : {}),
		...(finalOutput ? { final_output: finalOutput } : {}),
		...(modelOutput ? { model_output: modelOutput } : {}),
		error: stringValue(payload.error) || undefined
	};
}

function mapEncounterBriefingSummary(summary: JsonObject | undefined) {
	if (!summary) return undefined;

	return {
		schema_version: stringValue(summary.schema_version),
		short: stringValue(summary.short),
		forms: arrayOfStrings(summary.forms),
		meanings: arrayOfObjects(summary.meanings).map((meaning) => ({
			summary: stringValue(meaning.summary),
			source_glosses: arrayOfStrings(meaning.source_glosses),
			source_gloss_language: stringValue(meaning.source_gloss_language),
			translation_status: stringValue(meaning.translation_status),
			sources: arrayOfStrings(meaning.sources),
			translation_sources: arrayOfStrings(meaning.translation_sources),
			confidence: stringValue(meaning.confidence) || undefined,
			source_refs: arrayOfStrings(meaning.source_refs)
		})),
		grammar_functions: arrayOfObjects(summary.grammar_functions).map((item) => ({
			summary: stringValue(item.summary),
			form: stringValue(item.form),
			lemma: stringValue(item.lemma),
			analysis: stringValue(item.analysis),
			foster_display: stringValue(item.foster_display),
			source: stringValue(item.source)
		})),
		word_decomposition: arrayOfObjects(summary.word_decomposition).map((item) => ({
			form: stringValue(item.form),
			lemma: stringValue(item.lemma),
			analysis: stringValue(item.analysis),
			source: stringValue(item.source),
			note: stringValue(item.note)
		})),
		reader_usages: arrayOfObjects(summary.reader_usages).map((item) => ({
			label: stringValue(item.label),
			snippet: stringValue(item.snippet),
			note: stringValue(item.note)
		})),
		phrase_pairs: arrayOfObjects(summary.phrase_pairs).map((item) => ({
			phrase: stringValue(item.phrase),
			gloss: stringValue(item.gloss),
			source: stringValue(item.source),
			source_ref: stringValue(item.source_ref),
			note: stringValue(item.note)
		})),
		dictionary_sources: arrayOfStrings(summary.dictionary_sources),
		caveats: arrayOfStrings(summary.caveats)
	};
}

function mapEncounterWordIndexContext(context: JsonObject | undefined) {
	if (!context) return undefined;

	const request = objectValue(context.request);

	return {
		request: {
			language: normalizeLanguage(stringValue(request?.language)),
			query: stringValue(request?.query),
			query_candidates: arrayOfStrings(request?.query_candidates),
			source: stringValue(request?.source) || 'all',
			radius: numberValue(request?.radius)
		},
		anchors: arrayOfObjects(context.anchors).map((anchor) => ({
			language: normalizeLanguage(stringValue(anchor.language)),
			query: stringValue(anchor.query),
			source: stringValue(anchor.source),
			dictionary: stringValue(anchor.dictionary),
			anchor_status: stringValue(anchor.anchor_status),
			lexeme_id: stringValue(anchor.lexeme_id),
			wheel_id: stringValue(anchor.wheel_id),
			wheel_order_key: stringValue(anchor.wheel_order_key),
			canonical_name: stringValue(anchor.canonical_name),
			canonical_key: stringValue(anchor.canonical_key),
			source_name: stringValue(anchor.source_name),
			source_ref: stringValue(anchor.source_ref),
			index_entry_id: stringValue(anchor.index_entry_id),
			source_order_id: stringValue(anchor.source_order_id),
			source_order_key: stringValue(anchor.source_order_key)
		})),
		warnings: arrayOfObjects(context.warnings).map((warning) => ({
			source: stringValue(warning.source) || undefined,
			message: stringValue(warning.message)
		}))
	};
}

function mapWordRecommendationPayload(payload: JsonObject): WordRecommendationResult {
	const exhaustion = objectValue(payload.exhaustion);
	return {
		schema_version: stringValue(payload.schema_version) || 'langnet.word_of_day.v1',
		generated_at: stringValue(payload.generated_at) || new Date().toISOString(),
		suggested_ttl_seconds: numberValue(payload.suggested_ttl_seconds) || 3600,
		items: arrayOfObjects(payload.items).map(mapWordRecommendationItem),
		exhaustion: exhaustion
			? {
					fresh_requested: booleanValue(exhaustion.fresh_requested),
					fresh_satisfied: booleanValue(exhaustion.fresh_satisfied),
					reason: stringValue(exhaustion.reason) || null
				}
			: undefined,
		warnings: arrayOfObjects(payload.warnings).map((warning) => ({
			language: normalizeOptionalLanguage(stringValue(warning.language)),
			query: stringValue(warning.query) || undefined,
			message: stringValue(warning.message) || 'Word recommendation warning.'
		}))
	};
}

function mapWordIndexPayload(payload: JsonObject, fallback: WordIndexRequest): WordIndexResponse {
	const request = objectValue(payload.request);
	const neighborhood = objectValue(payload.neighborhood);
	const pagination = objectValue(payload.pagination);
	const order = mapWordIndexOrder(objectValue(payload.order));
	const browseGroups = arrayOfObjects(payload.groups).map(mapWordIndexBrowseGroup);

	return {
		schema_version: stringValue(payload.schema_version) || 'langnet.word_index.v1',
		request: {
			mode:
				(stringValue(request?.mode) as WordIndexMode | 'neighborhood') ||
				(fallback.mode === 'nearby' ? 'neighborhood' : fallback.mode),
			language: normalizeWordIndexLanguage(stringValue(request?.language) || fallback.language),
			source: stringValue(request?.source) || fallback.source || 'all',
			query: stringValue(request?.query) || fallback.query,
			prefix: stringValue(request?.prefix) || fallback.prefix,
			radius: numberValue(request?.radius) || fallback.radius,
			count: numberValue(request?.count) || numberValue(request?.limit) || fallback.count,
			seed: stringValue(request?.seed) || fallback.seed
		},
		sources: arrayOfObjects(payload.sources).map((source) => ({
			source: stringValue(source.source),
			language: normalizeLanguage(stringValue(source.language)),
			dictionary: stringValue(source.dictionary),
			available: booleanValue(source.available),
			entry_count: numberValue(source.entry_count)
		})),
		...(order ? { order } : {}),
		items: arrayOfObjects(payload.items).map(mapWordIndexItem).filter(wordIndexItemHasLookup),
		neighborhood: neighborhood
			? {
					policy: stringValue(neighborhood.policy) || undefined,
					anchor: objectValue(neighborhood.anchor)
						? mapWordIndexItem(objectValue(neighborhood.anchor) as JsonObject)
						: undefined,
					items: arrayOfObjects(neighborhood.items)
						.map(mapWordIndexItem)
						.filter(wordIndexItemHasLookup),
					groups: arrayOfObjects(neighborhood.groups).map(mapWordIndexNeighborhoodGroup),
					window: objectValue(neighborhood.window)
						? mapWordIndexWindow(objectValue(neighborhood.window) as JsonObject)
						: undefined
				}
			: null,
		...(browseGroups.length
			? {
					browse: {
						group_limit_policy: stringValue(request?.group_limit_policy) || undefined,
						groups: browseGroups
					}
				}
			: {}),
		pagination: {
			next_cursor: stringValue(pagination?.next_cursor) || null,
			prev_cursor: stringValue(pagination?.prev_cursor) || null
		},
		warnings: arrayOfObjects(payload.warnings).map((warning) => ({
			source: stringValue(warning.source) || undefined,
			language: normalizeOptionalLanguage(stringValue(warning.language)),
			query: stringValue(warning.query) || undefined,
			message: stringValue(warning.message) || 'Dictionary index warning.'
		}))
	};
}

function mapWordIndexSectionsPayload(
	payload: JsonObject,
	fallback: WordIndexRequest
): WordIndexSectionsResponse {
	const request = objectValue(payload.request);
	const order = mapWordIndexOrder(objectValue(payload.order));

	return {
		schema_version: stringValue(payload.schema_version) || 'langnet.word_index_sections.v1',
		request: {
			language: normalizeLanguage(stringValue(request?.language) || stringValue(fallback.language)),
			source: stringValue(request?.source) || fallback.source || 'all'
		},
		...(order ? { order } : {}),
		sections: arrayOfObjects(payload.sections).map(mapWordIndexSection),
		warnings: arrayOfObjects(payload.warnings).map((warning) => ({
			source: stringValue(warning.source) || undefined,
			language: normalizeOptionalLanguage(stringValue(warning.language)),
			query: stringValue(warning.query) || undefined,
			message: stringValue(warning.message) || 'Dictionary index section warning.'
		}))
	};
}

function mapWordIndexSection(section: JsonObject) {
	const anchor = objectValue(section.anchor);

	return {
		id: stringValue(section.id),
		label: stringValue(section.label),
		transliteration: stringValue(section.transliteration),
		group_label: stringValue(section.group_label),
		order_key: stringValue(section.order_key),
		anchor: anchor ? mapWordIndexSectionAnchor(anchor) : null,
		available: booleanValue(section.available),
		entry_count: numberValue(section.entry_count)
	};
}

function mapWordIndexSectionAnchor(anchor: JsonObject) {
	const display = objectValue(anchor.display);
	const order = mapWordIndexOrder(objectValue(anchor.order));

	return {
		language: normalizeLanguage(stringValue(anchor.language)),
		source: stringValue(anchor.source),
		dictionary: stringValue(anchor.dictionary),
		query: stringValue(anchor.query),
		canonical_key: stringValue(anchor.canonical_key),
		source_order_key: stringValue(anchor.source_order_key),
		lexeme_id: stringValue(anchor.lexeme_id),
		index_entry_id: stringValue(anchor.index_entry_id),
		source_order_id: stringValue(anchor.source_order_id),
		display: display
			? {
					primary: stringValue(display.primary),
					transliteration: stringValue(display.transliteration),
					source_key: stringValue(display.source_key)
				}
			: undefined,
		...(order ? { order } : {})
	};
}

function mapWordIndexOrder(order: JsonObject | undefined): WordIndexOrder | undefined {
	if (!order) return undefined;

	const policy = stringValue(order.policy);
	const label = stringValue(order.label);
	const collation = stringValue(order.collation);
	const key = stringValue(order.key);
	const displayKey = stringValue(order.display_key);
	const explanation = stringValue(order.explanation);

	if (!policy && !label && !collation && !key && !displayKey && !explanation) return undefined;

	return {
		policy,
		label,
		collation,
		key,
		display_key: displayKey,
		explanation
	};
}

function mapWordIndexWindow(window: JsonObject) {
	return {
		policy: stringValue(window.policy),
		contiguous: booleanValue(window.contiguous),
		collapsed: booleanValue(window.collapsed),
		before_count: numberValue(window.before_count),
		after_count: numberValue(window.after_count),
		source_group_count: numberValue(window.source_group_count),
		lexeme_count: numberValue(window.lexeme_count)
	};
}

function mapWordIndexNeighborhoodGroup(group: JsonObject) {
	const anchor = objectValue(group.anchor);
	const window = objectValue(group.window);

	return {
		language: normalizeLanguage(stringValue(group.language)),
		source: stringValue(group.source),
		dictionary: stringValue(group.dictionary),
		anchor: anchor ? mapWordIndexItem(anchor) : undefined,
		before: arrayOfObjects(group.before).map(mapWordIndexItem).filter(wordIndexItemHasLookup),
		after: arrayOfObjects(group.after).map(mapWordIndexItem).filter(wordIndexItemHasLookup),
		radius: numberValue(group.radius),
		neighborhood_kind: stringValue(group.neighborhood_kind),
		anchor_status: stringValue(group.anchor_status),
		window: {
			policy: stringValue(window?.policy),
			contiguous: booleanValue(window?.contiguous),
			collapsed: booleanValue(window?.collapsed),
			before_count: numberValue(window?.before_count),
			after_count: numberValue(window?.after_count),
			source_entry_count: numberValue(window?.source_entry_count)
		}
	};
}

function mapWordIndexBrowseGroup(group: JsonObject) {
	const items = arrayOfObjects(group.items).map(mapWordIndexItem).filter(wordIndexItemHasLookup);

	return {
		source: stringValue(group.source),
		dictionary: stringValue(group.dictionary),
		order: mapWordIndexOrder(objectValue(group.order)),
		item_count: numberValue(group.item_count) || items.length,
		items
	};
}

function mapWordIndexItem(item: JsonObject): WordIndexItem {
	const display = objectValue(item.display);
	const ids = objectValue(item.ids);
	const encounter = objectValue(item.encounter);
	const order = mapWordIndexOrder(objectValue(item.order));

	return {
		lexeme_id: stringValue(item.lexeme_id),
		wheel_id: stringValue(item.wheel_id),
		wheel_order_key: stringValue(item.wheel_order_key),
		index_entry_id: stringValue(item.index_entry_id),
		source_order_id: stringValue(item.source_order_id),
		language: normalizeLanguage(stringValue(item.language)),
		source: stringValue(item.source),
		dictionary: stringValue(item.dictionary),
		kind: stringValue(item.kind),
		canonical_name: stringValue(item.canonical_name),
		canonical_key: stringValue(item.canonical_key),
		source_name: stringValue(item.source_name),
		lookup: stringValue(item.lookup),
		display: {
			primary: stringValue(display?.primary),
			transliteration: stringValue(display?.transliteration),
			source_key: stringValue(display?.source_key)
		},
		sort_key: stringValue(item.sort_key),
		source_order_key: stringValue(item.source_order_key),
		source_ref: stringValue(item.source_ref),
		...(order ? { order } : {}),
		homograph_count: numberValue(item.homograph_count),
		homograph_policy: stringValue(item.homograph_policy),
		ids: {
			lexeme: stringValue(ids?.lexeme),
			wheel: stringValue(ids?.wheel),
			index_entry: stringValue(ids?.index_entry),
			source_order: stringValue(ids?.source_order),
			source_ref: stringValue(ids?.source_ref)
		},
		encounter: {
			language: normalizeLanguage(stringValue(encounter?.language) || stringValue(item.language)),
			q: stringValue(encounter?.q) || stringValue(item.lookup) || stringValue(item.canonical_key),
			dictionary:
				stringValue(encounter?.dictionary) === 'all'
					? 'all'
					: normalizeToolId(stringValue(encounter?.dictionary) || stringValue(item.source))
		},
		metadata: objectValue(item.metadata) ?? {},
		position: normalizeWordIndexPosition(stringValue(item.position)),
		match: booleanValue(item.match),
		source_count: numberValue(item.source_count),
		source_entry_count: numberValue(item.source_entry_count),
		source_counts: arrayOfObjects(item.source_counts).map((source) => ({
			source: stringValue(source.source),
			dictionary: stringValue(source.dictionary),
			count: numberValue(source.count)
		})),
		sources: arrayOfObjects(item.sources).map((source) => ({
			source: stringValue(source.source),
			dictionary: stringValue(source.dictionary)
		})),
		source_entries: arrayOfObjects(item.source_entries).map(mapWordIndexSourceEntry)
	};
}

function mapWordIndexSourceEntry(entry: JsonObject) {
	const order = mapWordIndexOrder(objectValue(entry.order));
	const display = objectValue(entry.display);

	return {
		index_entry_id: stringValue(entry.index_entry_id),
		source_order_id: stringValue(entry.source_order_id),
		wheel_id: stringValue(entry.wheel_id),
		wheel_order_key: stringValue(entry.wheel_order_key),
		source: stringValue(entry.source),
		dictionary: stringValue(entry.dictionary),
		source_name: stringValue(entry.source_name),
		source_display: stringValue(entry.source_display),
		source_ref: stringValue(entry.source_ref),
		source_order_key: stringValue(entry.source_order_key),
		...(order ? { order } : {}),
		display: display
			? {
					primary: stringValue(display.primary),
					transliteration: stringValue(display.transliteration),
					source_key: stringValue(display.source_key)
				}
			: undefined
	};
}

function wordIndexItemHasLookup(item: WordIndexItem) {
	return Boolean(item.encounter.q || item.lookup || item.canonical_key || item.canonical_name);
}

function normalizeWordIndexPosition(value: string) {
	if (value === 'before' || value === 'anchor' || value === 'after' || value === 'nearby') {
		return value;
	}
	return undefined;
}

function componentPayloads(payload: JsonObject, display: JsonObject | undefined) {
	const displayComponents = arrayOfObjects(display?.components);
	if (displayComponents.length) return displayComponents;
	return arrayOfObjects(payload.components);
}

function mapCliAnalysis(analysis: JsonObject): EncounterAnalysis {
	return {
		form: postProcessDictionaryText('dico', stringValue(analysis.form)),
		lemma: postProcessDictionaryText('dico', stringValue(analysis.lemma)),
		analysis: stringValue(analysis.analysis),
		source: stringValue(analysis.source),
		foster_display: stringValue(analysis.foster_display),
		display_text: postProcessDictionaryText('dico', stringValue(analysis.display_text))
	};
}

function mapCliComponent(component: JsonObject): EncounterComponent {
	const evidence = objectValue(component.evidence);
	const lookupToolFilter = normalizeToolRequest(stringValue(evidence?.lookup_tool_filter));
	const sourceTool = normalizeToolId(stringValue(component.source_tool));

	return {
		surface: postProcessDictionaryText('dico', stringValue(component.surface)),
		lemma: postProcessDictionaryText('dico', stringValue(component.lemma)),
		display: postProcessDictionaryText('dico', stringValue(component.display)),
		role: stringValue(component.role),
		analysis: stringValue(component.analysis),
		source_tool: sourceTool,
		lookup_terms: arrayOfStrings(component.lookup_terms).map((term) =>
			postProcessDictionaryText('dico', term)
		),
		evidence: {
			status: stringValue(evidence?.status),
			source: stringValue(evidence?.source),
			lookup_tool_filter: lookupToolFilter,
			meanings: mergeComponentTranslationMeanings(
				arrayOfObjects(evidence?.meanings).map((meaning, index) =>
					mapCliComponentMeaning(meaning, lookupToolFilter, index)
				)
			),
			error: stringValue(evidence?.error)
		}
	};
}

function mapCliComponentMeaning(
	meaning: JsonObject,
	lookupToolFilter: ToolRequest,
	index: number
): EncounterComponentMeaning {
	const rawSources = arrayOfStrings(meaning.sources);
	const sourceRefs = arrayOfStrings(meaning.source_refs);
	const sourceLangs = arrayOfStrings(meaning.source_langs);
	const isTranslation =
		rawSources.includes('translation') || stringValue(meaning.source_text) === 'translation';
	const sourceTools = normalizeToolIds(rawSources.filter((source) => source !== 'translation'));
	const refTool = sourceToolFromSourceRef(sourceRefs[0] ?? '');
	const firstTool =
		sourceTools[0] ?? refTool ?? (lookupToolFilter === 'all' ? undefined : lookupToolFilter);
	const displayGloss = postProcessDictionaryText(
		firstTool,
		componentGlossFromCli(stringValue(meaning.display_gloss), stringValue(meaning.evidence_gloss))
	);
	const nonEnglishSourceLang = sourceLangs.find((lang) => lang && lang !== 'en');

	return {
		bucket_id: stringValue(meaning.bucket_id) || `component:${index}`,
		display_gloss: displayGloss || 'No component gloss returned.',
		source_tools: sourceTools.length ? sourceTools : firstTool ? [firstTool] : [],
		source_refs: sourceRefs,
		source_langs: sourceLangs,
		translation: isTranslation
			? {
					available: true,
					source_tool: firstTool,
					source_lang: nonEnglishSourceLang || 'fr',
					source_label: sourceLayerLabel(firstTool, nonEnglishSourceLang || 'fr'),
					source_text: '',
					target_lang: 'en',
					target_text: displayGloss,
					model: stringValue(translationPayload(meaning)?.model)
				}
			: nonEnglishSourceLang && firstTool && displayGloss
				? {
						available: false,
						source_tool: firstTool,
						source_lang: nonEnglishSourceLang,
						source_label: sourceLayerLabel(firstTool, nonEnglishSourceLang),
						source_text: displayGloss,
						target_lang: 'en',
						target_text: displayGloss
					}
				: undefined
	};
}

function translationPayload(meaning: JsonObject) {
	return objectValue(meaning.translation);
}

function mergeComponentTranslationMeanings(
	meanings: EncounterComponentMeaning[]
): EncounterComponentMeaning[] {
	const groups = new Map<
		string,
		{
			source?: EncounterComponentMeaning;
			reader?: EncounterComponentMeaning;
			other: EncounterComponentMeaning[];
		}
	>();

	for (const meaning of meanings) {
		const key = componentTranslationKey(meaning);
		if (!key) {
			const uniqueKey = `other:${meaning.bucket_id}:${meaning.source_refs[0] ?? ''}`;
			const group = groups.get(uniqueKey) ?? { other: [] };
			group.other.push(meaning);
			groups.set(uniqueKey, group);
			continue;
		}

		const group = groups.get(key) ?? { other: [] };
		if (meaning.translation?.available) group.reader = meaning;
		else if (meaning.translation) group.source = meaning;
		else group.other.push(meaning);
		groups.set(key, group);
	}

	return [...groups.values()].flatMap((group) => {
		if (group.reader && group.source) {
			return [mergeComponentTranslationMeaning(group.reader, group.source), ...group.other];
		}

		if (group.reader) return [group.reader, ...group.other];
		if (group.source) return [group.source, ...group.other];
		return group.other;
	});
}

function mergeComponentTranslationMeaning(
	reader: EncounterComponentMeaning,
	source: EncounterComponentMeaning
): EncounterComponentMeaning {
	const sourceText = source.translation?.source_text || source.display_gloss;
	return {
		...reader,
		bucket_id: source.bucket_id || reader.bucket_id,
		display_gloss: reader.translation?.target_text || reader.display_gloss,
		source_tools: dedupe([...source.source_tools, ...reader.source_tools]),
		source_refs: dedupe([...source.source_refs, ...reader.source_refs]),
		source_langs: dedupe([...source.source_langs, ...reader.source_langs]),
		translation: reader.translation
			? {
					...reader.translation,
					source_tool: source.translation?.source_tool ?? reader.translation.source_tool,
					source_lang: source.translation?.source_lang ?? reader.translation.source_lang,
					source_label: source.translation?.source_label ?? reader.translation.source_label,
					source_text: sourceText,
					target_text: reader.translation.target_text || reader.display_gloss
				}
			: undefined
	};
}

function componentTranslationKey(meaning: EncounterComponentMeaning) {
	const tool = meaning.translation?.source_tool ?? meaning.source_tools[0];
	if (tool !== 'dico' && tool !== 'gaffiot' && tool !== 'bailly') return '';
	const sourceRef = meaning.source_refs[0] ?? '';
	if (!sourceRef) return '';
	return `${tool}:${sourceRef}`;
}

function mapWordRecommendationItem(item: JsonObject): WordRecommendationItem {
	const recommendedRequest = objectValue(item.recommended_request);
	const ambiguity = objectValue(item.ambiguity);
	const ui = objectValue(item.ui);
	const displayForms = wordRecommendationDisplayForms(item, ui);
	const novelty = objectValue(item.novelty);
	const language = normalizeLanguage(stringValue(item.language));
	const query = stringValue(item.query);

	return {
		language,
		query,
		key: stringValue(item.key) || `${language}:${query}`,
		display: stringValue(item.display) || query,
		primary_lexeme: stringValue(item.primary_lexeme),
		lexeme_anchors: arrayOfStrings(item.lexeme_anchors),
		summary: stringValue(item.summary),
		learner_note: stringValue(item.learner_note),
		mnemonic: stringValue(item.mnemonic),
		difficulty: stringValue(item.difficulty) || 'beginner',
		confidence: stringValue(item.confidence) || 'unknown',
		ambiguity: {
			has_multiple_lexemes: booleanValue(ambiguity?.has_multiple_lexemes),
			lexeme_count: numberValue(ambiguity?.lexeme_count),
			note: stringValue(ambiguity?.note)
		},
		recommended_request: {
			language: normalizeLanguage(stringValue(recommendedRequest?.language) || language),
			q: stringValue(recommendedRequest?.q) || query,
			dictionary:
				stringValue(recommendedRequest?.dictionary) === 'all'
					? 'all'
					: normalizeToolId(stringValue(recommendedRequest?.dictionary)),
			translation: normalizeTranslationMode(recommendedRequest?.translation, 'auto'),
			backend: stringValue(recommendedRequest?.backend) === 'sample' ? 'sample' : 'cli'
		},
		source_basis: arrayOfObjects(item.source_basis).map((basis) => ({
			tool: stringValue(basis.tool),
			source_ref: stringValue(basis.source_ref),
			lexeme_anchor: stringValue(basis.lexeme_anchor),
			evidence: stringValue(basis.evidence)
		})),
		display_forms: displayForms,
		ui: {
			href_query: stringValue(ui?.href_query),
			badge: stringValue(ui?.badge),
			short_gloss: stringValue(ui?.short_gloss)
		},
		novelty: novelty
			? {
					is_repeat: booleanValue(novelty.is_repeat),
					avoided_recent_count: numberValue(novelty.avoided_recent_count),
					fresh_requested: booleanValue(novelty.fresh_requested),
					reason: stringValue(novelty.reason)
				}
			: undefined
	};
}

function wordRecommendationDisplayForms(item: JsonObject, ui: JsonObject | undefined) {
	const forms = objectValue(item.display_forms) ?? objectValue(item.forms);
	const canonical = objectValue(item.canonical);
	return {
		native:
			stringValue(forms?.native) ||
			stringValue(forms?.devanagari) ||
			stringValue(forms?.greek) ||
			stringValue(canonical?.native) ||
			stringValue(canonical?.devanagari) ||
			stringValue(canonical?.greek) ||
			stringValue(canonical?.name) ||
			stringValue(item.canonical_name) ||
			stringValue(item.display_native) ||
			stringValue(item.display_devanagari) ||
			stringValue(item.display_greek) ||
			stringValue(ui?.display_native) ||
			stringValue(ui?.display_devanagari) ||
			stringValue(ui?.display_greek),
		roman:
			stringValue(forms?.roman) ||
			stringValue(forms?.iast) ||
			stringValue(forms?.transliteration) ||
			stringValue(canonical?.roman) ||
			stringValue(canonical?.iast) ||
			stringValue(canonical?.transliteration) ||
			stringValue(item.display_roman) ||
			stringValue(item.display_iast) ||
			stringValue(item.transliteration) ||
			stringValue(ui?.display_roman) ||
			stringValue(ui?.display_iast) ||
			stringValue(ui?.transliteration),
		canonical:
			stringValue(forms?.canonical) ||
			stringValue(canonical?.display) ||
			stringValue(canonical?.name) ||
			stringValue(item.canonical_display) ||
			stringValue(item.canonical_name),
		script:
			stringValue(forms?.script) ||
			stringValue(canonical?.script) ||
			stringValue(item.display_script) ||
			stringValue(ui?.display_script)
	};
}

function filterToolIdsByRequest(toolIds: ToolId[], dictionaries: ToolRequest[]) {
	if (dictionaries.includes('all')) return toolIds;
	const requestedTools = new Set(dictionaries);
	return toolIds.filter((toolId) => requestedTools.has(toolId));
}

function filterBucketsByRequestedTools(buckets: EncounterBucket[], dictionaries: ToolRequest[]) {
	if (dictionaries.includes('all')) return buckets;

	const requestedTools = new Set(dictionaries);
	return buckets.filter((bucket) => {
		if (bucket.source_tools.some((tool) => requestedTools.has(tool))) return true;
		if (bucket.translation?.source_tool && requestedTools.has(bucket.translation.source_tool))
			return true;
		return bucket.witnesses.some((witness) => requestedTools.has(witness.tool));
	});
}

function mapCliBucket({
	meaning,
	rawBucket,
	ranking,
	language,
	index
}: {
	meaning: JsonObject;
	rawBucket?: JsonObject;
	ranking?: JsonObject;
	language: LanguageMode;
	index: number;
}): EncounterBucket {
	const entries = arrayOfObjects(meaning.entries);
	const rawWitnesses = arrayOfObjects(rawBucket?.witnesses);
	const entrySourceTools = normalizeToolIds(
		entries.map((entry) => sourceToolValueFromEntry(entry)).filter(Boolean)
	);
	const rawSourceTools = arrayOfStrings(ranking?.source_tools).length
		? arrayOfStrings(ranking?.source_tools)
		: arrayOfStrings(meaning.sources);
	const sourceTools = dedupe([
		...normalizeToolIds(rawSourceTools.filter((tool) => tool !== 'translation')),
		...entrySourceTools
	]);
	const sourceRefs = dedupe([
		...arrayOfStrings(meaning.source_refs),
		...entries.map((entry) => stringValue(entry.source_ref)).filter(Boolean)
	]);
	const sourceLangs = dedupe([
		...arrayOfStrings(meaning.source_langs),
		...entries.map((entry) => stringValue(entry.source_lang)).filter(Boolean)
	]);
	const firstSourceTool = sourceTools[0] ?? sourceToolFromSourceRef(sourceRefs[0]) ?? 'diogenes';
	const translationEntry = entries.find((entry) => {
		const translation = objectValue(entry.translation);
		return booleanValue(translation?.available);
	});
	const sourceText = postProcessDictionaryText(
		firstSourceTool,
		sourceTextFromCli(meaning, rawBucket, rawWitnesses)
	);
	const readerText = postProcessDictionaryText(
		firstSourceTool,
		stringValue(meaning.display_gloss) || stringValue(rawBucket?.display_gloss)
	);
	const displayText = displayTextFromCli(
		readerText,
		sourceText,
		firstSourceTool,
		Boolean(translationEntry)
	);
	const firstSourceLang = sourceLangs.find((lang) => lang !== 'en') ?? sourceLangs[0] ?? language;
	const translation = translationEntry
		? translationFromEntry(
				translationEntry,
				translatedSourceTextFromEntries(translationEntry, entries, rawWitnesses) || sourceText,
				displayText
			)
		: sourceLangs.some((lang) => lang && lang !== 'en') && sourceText
			? {
					available: false,
					...translationRetryMetadataFromEntry(entries[0]),
					source_tool: firstSourceTool,
					source_lang: firstSourceLang,
					source_label: sourceLayerLabel(firstSourceTool, firstSourceLang),
					source_text: sourceText,
					target_lang: 'en' as const,
					target_text: readerText || sourceText
				}
			: undefined;

	return {
		bucket_id:
			stringValue(meaning.bucket_id) || stringValue(rawBucket?.bucket_id) || `bucket:${index}`,
		display_gloss: displayText || 'No display gloss returned.',
		normalized_gloss: stringValue(rawBucket?.normalized_gloss) || displayText.toLowerCase(),
		bucket_lemmas: arrayOfStrings(ranking?.bucket_lemmas).length
			? arrayOfStrings(ranking?.bucket_lemmas)
			: dedupe(entries.map((entry) => stringValue(entry.headword)).filter(Boolean)),
		source_tools: sourceTools,
		source_refs: sourceRefs,
		reasons: arrayOfStrings(ranking?.reasons).map(sanitizeReason),
		witnesses: entries.length
			? entries.map((entry) => witnessFromEntry(entry))
			: rawWitnesses.map((witness) => witnessFromRaw(witness)),
		witness_count: numberValue(meaning.witness_count) || entries.length || rawWitnesses.length,
		preferred_lemma_rank: numberValue(ranking?.preferred_lemma_rank),
		effective_preferred_lemma_rank: numberValue(ranking?.effective_preferred_lemma_rank),
		learner_quality_order: numberValue(ranking?.learner_quality_order),
		has_english_translation: booleanValue(ranking?.has_english_translation) || Boolean(readerText),
		has_source_translation: booleanValue(ranking?.has_bilingual_source) || Boolean(translation),
		source_langs: sourceLangs.length ? sourceLangs : ['en'],
		reader_lang: 'en',
		evidence_note: postProcessDictionaryText(firstSourceTool, evidenceNote(meaning)),
		translation_note: translationNote(meaning, translation),
		translation
	};
}

function expandOutlinedSourceBucket(
	bucket: EncounterBucket,
	meaning: JsonObject,
	rawBucket: JsonObject | undefined
): EncounterBucket[] {
	if (!bucket.source_tools.includes('bailly')) return [bucket];

	const firstSourceTool =
		bucket.source_tools.find((tool) => tool === 'bailly') ??
		sourceToolFromSourceRef(bucket.source_refs[0]);
	const segments = extractSourceOutlineSegments({
		tool: firstSourceTool,
		rawWitnesses: arrayOfObjects(rawBucket?.witnesses),
		entries: arrayOfObjects(meaning.entries)
	});
	if (segments.length < 2) return [bucket];

	return segments.map((segment, index) => outlinedSourceSegmentBucket(bucket, segment, index));
}

function outlinedSourceSegmentBucket(
	bucket: EncounterBucket,
	segment: SourceOutlineSegment,
	index: number
): EncounterBucket {
	const displayText = postProcessDictionaryText('bailly', segment.text);
	const sourceRefs = dedupe([segment.sourceRef, ...bucket.source_refs.filter(Boolean)]);
	const translation = bucket.translation
		? {
				...bucket.translation,
				source_text: displayText,
				target_text: bucket.translation.available
					? (segment.translatedText ?? bucket.translation.target_text)
					: displayText
			}
		: undefined;

	return {
		...bucket,
		bucket_id: `${bucket.bucket_id}:outline:${index}`,
		display_gloss: displayText,
		normalized_gloss: normalizeComparableText(displayText),
		source_refs: sourceRefs,
		reasons: dedupe([...bucket.reasons, 'source outline segment']),
		witnesses: outlineSegmentWitnesses(bucket, segment, displayText),
		witness_count: Math.max(1, bucket.witness_count),
		learner_quality_order: bucket.learner_quality_order + index / 1000,
		has_source_translation: Boolean(translation) || bucket.has_source_translation,
		evidence_note: displayText,
		translation_note: translation
			? bucket.translation_note
			: 'Bailly source outline segment returned.',
		translation
	};
}

function outlineSegmentWitnesses(
	bucket: EncounterBucket,
	segment: SourceOutlineSegment,
	displayText: string
) {
	const marker = segment.marker ? `${segment.marker} ` : '';
	const witnesses = bucket.witnesses.length
		? bucket.witnesses
		: [
				{
					tool: 'bailly' as const,
					label: `bailly ${segment.sourceRef}`,
					detail: displayText,
					dictionary: 'bailly',
					source_ref: segment.sourceRef
				}
			];

	return witnesses.map((witness) => ({
		...witness,
		label: `${witness.dictionary ?? witness.tool} ${segment.sourceRef}`,
		detail: `${marker}${displayText}`.trim(),
		source_ref: segment.sourceRef
	}));
}

function translationFromEntry(entry: JsonObject, sourceText: string, readerText: string) {
	const translation = objectValue(entry.translation);
	const sourceLang =
		stringValue(translation?.source_text_lang) || stringValue(entry.source_lang) || 'fr';
	const targetLang = stringValue(translation?.target_lang) || 'en';
	const sourceTool = sourceToolFromEntry(entry);
	const cleanSourceText = postProcessDictionaryText(sourceTool, sourceText);
	const cleanReaderText = postProcessDictionaryText(sourceTool, readerText);

	return {
		available: true,
		...translationRetryMetadataFromEntry(entry),
		source_tool: sourceTool,
		source_lang: sourceLang,
		source_label: sourceLayerLabel(sourceTool, sourceLang),
		source_text: cleanSourceText || cleanReaderText,
		target_lang: targetLang === 'en' ? ('en' as const) : ('en' as const),
		target_text: cleanReaderText || cleanSourceText,
		model: stringValue(translation?.model)
	};
}

function translatedSourceTextFromEntries(
	translationEntry: JsonObject,
	entries: JsonObject[],
	rawWitnesses: JsonObject[]
) {
	const translation = objectValue(translationEntry.translation);
	const sourceTool = sourceToolFromEntry(translationEntry);
	const sourceRef = stringValue(translationEntry.source_ref);
	const derivedSense = stringValue(translation?.derived_from_sense);
	const sourceWitness =
		findSourceWitness(rawWitnesses, sourceTool, sourceRef, derivedSense) ??
		findSourceWitness(rawWitnesses, sourceTool, sourceRef, '');
	const witnessText = rawWitnessSourceText(sourceWitness);
	if (witnessText) return witnessText;

	const sourceEntry =
		entries.find((entry) => {
			if (entry === translationEntry) return false;
			if (sourceToolFromEntry(entry) !== sourceTool) return false;
			if (derivedSense && stringValue(entry.sense_anchor) === derivedSense) return true;
			return sourceRef && stringValue(entry.source_ref) === sourceRef;
		}) ??
		entries.find(
			(entry) => entry !== translationEntry && sourceToolFromEntry(entry) === sourceTool
		);

	return sourceEntryText(sourceEntry, { includeSummary: true });
}

function findSourceWitness(
	rawWitnesses: JsonObject[],
	sourceTool: ToolId,
	sourceRef: string,
	derivedSense: string
) {
	return rawWitnesses.find((witness) => {
		const evidence = objectValue(witness.evidence);
		const witnessTool = normalizeToolId(
			stringValue(evidence?.source_tool) || stringValue(witness.source_tool)
		);
		if (witnessTool !== sourceTool) return false;
		if (derivedSense && stringValue(witness.sense_anchor) === derivedSense) return true;
		const witnessSourceRef = stringValue(evidence?.source_ref) || stringValue(witness.source_ref);
		return Boolean(sourceRef && witnessSourceRef === sourceRef);
	});
}

function rawWitnessSourceText(witness: JsonObject | undefined) {
	const evidence = objectValue(witness?.evidence);
	const sourceEntry = objectValue(evidence?.source_entry);
	return (
		stringValue(evidence?.display_gloss) ||
		stringValue(witness?.gloss) ||
		stringValue(sourceEntry?.source_text)
	);
}

function sourceEntryText(
	entry: JsonObject | undefined,
	{ includeSummary }: { includeSummary: boolean }
) {
	const sourceLayerText = stringValue(entry?.source_layer_text);
	if (sourceLayerText) return sourceLayerText;

	const sourceEntry = objectValue(entry?.source_entry);
	const sourceText =
		stringValue(sourceEntry?.display_gloss) || stringValue(sourceEntry?.source_text);
	if (sourceText) return sourceText;

	if (!includeSummary) return '';
	const sourceSummary = objectValue(entry?.source_detail_summary);
	return stringValue(sourceSummary?.text);
}

function translationRetryMetadataFromEntry(entry: JsonObject | undefined) {
	const translation = objectValue(entry?.translation);
	const sourceEntry = objectValue(entry?.source_entry);
	const sourceRef = stringValue(entry?.source_ref);
	const parsedRef = parseTranslatableSourceRef(sourceRef);
	const sourceLexicon = normalizeToolId(
		stringValue(translation?.source_lexicon) ||
			stringValue(sourceEntry?.dict) ||
			stringValue(entry?.dictionary) ||
			stringValue(translation?.derived_from_tool)
	);
	const entryId =
		stringValue(sourceEntry?.entry_id) || parsedRef.entryId || stringValue(entry?.headword);
	const occurrence =
		numberValue(sourceEntry?.occurrence) ||
		numberValue(sourceEntry?.variant_num) ||
		(parsedRef.occurrence === undefined ? undefined : parsedRef.occurrence);
	const headwordNorm =
		stringValue(sourceEntry?.headword_norm) ||
		stringValue(entry?.headword) ||
		stringValue(entry?.display_form);

	return {
		translation_id: stringValue(translation?.translation_id) || undefined,
		source_lexicon: isTranslatedSourceTool(sourceLexicon) ? sourceLexicon : undefined,
		entry_id: entryId || undefined,
		occurrence,
		headword_norm: normalizeComparableText(headwordNorm) || undefined,
		source_text_hash: stringValue(translation?.source_text_hash) || undefined,
		model: stringValue(translation?.model) || undefined
	};
}

function parseTranslatableSourceRef(sourceRef: string) {
	const parsed = /^(?:dico|gaffiot|bailly):(?:.*#)?([^:#]+)(?::(\d+))?$/.exec(sourceRef);
	if (!parsed) return {};
	const occurrence = parsed[2] === undefined ? undefined : Number.parseInt(parsed[2], 10);
	return {
		entryId: parsed[1],
		occurrence: Number.isFinite(occurrence) ? occurrence : undefined
	};
}

function isTranslatedSourceTool(tool: ToolId | undefined) {
	return tool === 'dico' || tool === 'gaffiot' || tool === 'bailly';
}

function witnessFromEntry(entry: JsonObject) {
	const tool = sourceToolFromEntry(entry);
	const dictionary = stringValue(entry.dictionary) || tool;
	const sourceRef = stringValue(entry.source_ref);
	const sourceEntry = objectValue(entry.source_entry);
	const charCount = numberValue(sourceEntry?.source_text_chars);

	return {
		tool,
		label: `${dictionary}${sourceRef ? ` ${sourceRef}` : ''}`,
		detail: charCount
			? `Source entry has ${charCount} characters.`
			: postProcessDictionaryText(tool, stringValue(entry.sense_anchor)),
		dictionary,
		headword: postProcessDictionaryText(
			tool,
			stringValue(entry.headword) || stringValue(entry.display_form)
		),
		lexeme_anchor: stringValue(entry.lexeme_anchor),
		source_ref: sourceRef
	};
}

function mergeTranslatedSourceBuckets(buckets: EncounterBucket[]): EncounterBucket[] {
	const groups = new Map<string, { source?: EncounterBucket; reader?: EncounterBucket }>();

	for (const bucket of buckets) {
		const key = translatableEntryKey(bucket);
		if (!key) continue;

		const group = groups.get(key) ?? {};
		if (bucket.translation?.available) {
			group.reader = bucket;
		} else if (bucket.translation) {
			group.source = bucket;
		}
		groups.set(key, group);
	}

	const emitted = new Set<string>();
	return buckets.flatMap((bucket) => {
		const key = translatableEntryKey(bucket);
		if (!key) return [bucket];

		const group = groups.get(key);
		if (!group?.reader || !group.source) return [bucket];
		if (emitted.has(key)) return [];

		emitted.add(key);
		return [mergeTranslatedSourceBucket(group.reader, group.source)];
	});
}

function mergeTranslatedSourceBucket(
	reader: EncounterBucket,
	source: EncounterBucket
): EncounterBucket {
	const sourceText =
		source.translation?.source_text ||
		source.display_gloss ||
		reader.translation?.source_text ||
		reader.display_gloss;
	const translation = reader.translation
		? {
				...reader.translation,
				translation_id: reader.translation.translation_id ?? source.translation?.translation_id,
				source_lexicon: reader.translation.source_lexicon ?? source.translation?.source_lexicon,
				entry_id: reader.translation.entry_id ?? source.translation?.entry_id,
				occurrence: reader.translation.occurrence ?? source.translation?.occurrence,
				headword_norm: reader.translation.headword_norm ?? source.translation?.headword_norm,
				source_text_hash:
					reader.translation.source_text_hash ?? source.translation?.source_text_hash,
				source_text: sourceText,
				source_label: source.translation?.source_label ?? reader.translation.source_label,
				source_lang: source.translation?.source_lang ?? reader.translation.source_lang
			}
		: undefined;

	return {
		...reader,
		source_tools: dedupe([...source.source_tools, ...reader.source_tools]),
		source_refs: dedupe([...source.source_refs, ...reader.source_refs]),
		reasons: dedupe([...source.reasons, ...reader.reasons]),
		witnesses: dedupeWitnesses([...source.witnesses, ...reader.witnesses]),
		witness_count: Math.max(
			source.witness_count,
			reader.witness_count,
			source.witnesses.length + reader.witnesses.length
		),
		has_source_translation: true,
		has_english_translation: true,
		source_langs: dedupe(
			[
				...source.source_langs,
				...reader.source_langs,
				source.translation?.source_lang ?? ''
			].filter(Boolean)
		),
		evidence_note:
			reader.evidence_note ||
			reader.translation?.target_text ||
			reader.display_gloss ||
			source.evidence_note,
		translation_note: translation
			? `${translation.source_label} is available beside the Reader EN layer.`
			: reader.translation_note,
		translation
	};
}

function translatableEntryKey(bucket: EncounterBucket) {
	const tool = bucket.translation?.source_tool;
	if (tool !== 'dico' && tool !== 'gaffiot' && tool !== 'bailly') return '';

	const sourceRef = bucket.source_refs[0] ?? bucket.witnesses[0]?.source_ref ?? '';
	if (!sourceRef) return '';

	const headword = bucket.witnesses[0]?.headword ?? bucket.bucket_lemmas[0] ?? '';
	return `${tool}:${sourceRef}:${headword}`;
}

function dedupeWitnesses(witnesses: EncounterBucket['witnesses']) {
	const seen = new Set<string>();
	return witnesses.filter((witness) => {
		const key = `${witness.tool}:${witness.source_ref ?? ''}:${witness.headword ?? ''}:${witness.label}`;
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

function sourceToolFromEntry(entry: JsonObject): ToolId {
	return normalizeToolId(sourceToolValueFromEntry(entry));
}

function sourceToolValueFromEntry(entry: JsonObject) {
	const translation = objectValue(entry.translation);
	return (
		stringValue(translation?.derived_from_tool) ||
		stringValue(translation?.source_lexicon) ||
		sourceToolFromSourceRef(stringValue(entry.source_ref)) ||
		stringValue(entry.source_tool) ||
		stringValue(entry.dictionary)
	);
}

function sourceToolFromSourceRef(sourceRef: string): ToolId | undefined {
	if (sourceRef.startsWith('dico:')) return 'dico';
	if (sourceRef.startsWith('gaffiot:')) return 'gaffiot';
	if (sourceRef.startsWith('bailly:')) return 'bailly';
	if (sourceRef.startsWith('lewis_1890:')) return 'lewis_1890';
	if (sourceRef.startsWith('mw:') || sourceRef.startsWith('ap90:')) return 'cdsl';
	if (sourceRef.startsWith('diogenes:')) return 'diogenes';
	return undefined;
}

function witnessFromRaw(witness: JsonObject) {
	const tool = normalizeToolId(stringValue(witness.source_tool));
	return {
		tool,
		label: stringValue(witness.sense_anchor) || tool,
		detail: postProcessDictionaryText(
			tool,
			stringValue(witness.gloss) || stringValue(witness.normalized_gloss)
		),
		headword: postProcessDictionaryText(
			tool,
			stringValue(witness.lexeme_anchor).replace(/^lex:/, '')
		),
		lexeme_anchor: stringValue(witness.lexeme_anchor)
	};
}

function firstSourceText(rawWitnesses: JsonObject[]) {
	for (const witness of rawWitnesses) {
		const evidence = objectValue(witness.evidence);
		const sourceEntry = objectValue(evidence?.source_entry);
		const sourceText = stringValue(sourceEntry?.source_text);
		if (sourceText) return sourceText;
	}

	return '';
}

function sourceTextFromCli(
	meaning: JsonObject,
	rawBucket: JsonObject | undefined,
	rawWitnesses: JsonObject[]
) {
	const evidenceGloss = stringValue(meaning.evidence_gloss);
	if (evidenceGloss) return evidenceGloss;

	const sourceSummary = objectValue(meaning.source_detail_summary);
	const summaryText = stringValue(sourceSummary?.text);
	if (summaryText) return summaryText;

	const rawDisplay = stringValue(rawBucket?.display_gloss);
	if (rawDisplay && rawDisplay.length <= 1600) return rawDisplay;

	const rawSource = firstSourceText(rawWitnesses);
	if (rawSource && rawSource.length <= 1600) return rawSource;
	return rawSource ? `${rawSource.slice(0, 1599).trim()}...` : '';
}

function postProcessDictionaryText(tool: ToolId | undefined, value: string) {
	if (tool !== 'dico') return value;
	return stripDicoNumericSuffixes(value);
}

function stripDicoNumericSuffixes(value: string) {
	return value.replace(/_\d+\b/g, '');
}

function evidenceNote(meaning: JsonObject) {
	const lengthNote = stringValue(meaning.evidence_length_note) || stringValue(meaning.length_note);
	const evidenceGloss = stringValue(meaning.evidence_gloss);
	const sourceSummary = objectValue(meaning.source_detail_summary);
	const summaryText = stringValue(sourceSummary?.text);
	return appendUniqueText([lengthNote, evidenceGloss, summaryText]).join(' ');
}

function displayTextFromCli(
	readerText: string,
	sourceText: string,
	sourceTool: ToolId,
	hasTranslation: boolean
) {
	const cleanSourceText = stripEvidenceLabel(sourceText).trim();
	if (!readerText) return cleanSourceText;

	if (
		sourceTool === 'diogenes' &&
		isClippedText(readerText) &&
		cleanSourceText.length > readerText.length + 8
	) {
		return cleanSourceText;
	}

	if (hasTranslation && shouldPromoteTranslatedEvidence(readerText, cleanSourceText)) {
		return cleanSourceText;
	}

	return readerText;
}

function shouldPromoteTranslatedEvidence(readerText: string, sourceText: string) {
	if (sourceText.length <= readerText.length + 24) return false;

	const normalizedReader = normalizeComparableText(readerText);
	const normalizedSource = normalizeComparableText(sourceText);
	if (
		normalizedSource.startsWith(normalizedReader) ||
		normalizedSource.includes(normalizedReader)
	) {
		return true;
	}

	const readerTokens = normalizedReader.split(' ').filter(Boolean);
	const sourceTokens = normalizedSource.split(' ').filter(Boolean);
	const comparableTokenCount = Math.min(readerTokens.length, 14);
	if (comparableTokenCount < 5) return false;

	return readerTokens
		.slice(0, comparableTokenCount)
		.every((token, index) => sourceTokens[index] === token);
}

function isClippedText(value: string) {
	return /(?:…|\.\.\.)\s*$/u.test(value.trim());
}

function appendUniqueText(values: string[]) {
	const result: string[] = [];

	for (const value of values.map((candidate) => candidate.trim()).filter(Boolean)) {
		const normalizedValue = normalizeComparableText(value);
		const normalizedUnlabeledValue = normalizeComparableText(stripEvidenceLabel(value));
		if (
			result.some((existing) => {
				const normalizedExisting = normalizeComparableText(existing);
				const normalizedUnlabeledExisting = normalizeComparableText(stripEvidenceLabel(existing));
				return (
					normalizedExisting.includes(normalizedValue) ||
					normalizedExisting.includes(normalizedUnlabeledValue) ||
					normalizedUnlabeledExisting.includes(normalizedValue) ||
					normalizedUnlabeledExisting.includes(normalizedUnlabeledValue)
				);
			})
		) {
			continue;
		}
		result.push(value);
	}

	return result;
}

function stripEvidenceLabel(value: string) {
	return value.replace(/^(examples|cross refs):\s*/i, '');
}

function normalizeComparableText(value: string) {
	return value
		.replace(/[|[\](),;:.—–-]+/g, ' ')
		.replace(/\s+/g, ' ')
		.trim()
		.toLowerCase();
}

function translationNote(meaning: JsonObject, translation: EncounterBucket['translation']) {
	if (translation?.available)
		return `${translation.source_label} is available beside the Reader EN layer.`;
	if (translation)
		return `${translation.source_label} is available; Reader EN is waiting on translation cache.`;
	const sourceLangs = arrayOfStrings(meaning.source_langs);
	if (sourceLangs.some((lang) => lang && lang !== 'en')) {
		return 'Source text is not English; no cached English translation was returned.';
	}
	return 'Reader-ready source evidence returned.';
}

function normalizeTranslationCache(
	cache: JsonObject | undefined,
	fallbackMode: TranslationMode
): TranslationCache {
	return {
		mode: normalizeTranslationMode(cache?.mode, fallbackMode),
		cache_db: stringValue(cache?.cache_db),
		model: stringValue(cache?.model),
		cache_available: booleanValue(cache?.cache_available),
		populate: booleanValue(cache?.populate),
		written: numberValue(cache?.written),
		before: cacheCounts(objectValue(cache?.before)),
		after: cacheCounts(objectValue(cache?.after))
	};
}

function sanitizeReason(reason: string) {
	return reason
		.replace(
			'has DICO/Gaffiot bilingual source evidence',
			'has DICO/Gaffiot translated-source evidence'
		)
		.replace('has bilingual source evidence', 'has translated-source evidence');
}

function cacheCounts(value: JsonObject | undefined) {
	return {
		total: numberValue(value?.total),
		hits: numberValue(value?.hits),
		missing: numberValue(value?.missing),
		errors: numberValue(value?.errors),
		empty: numberValue(value?.empty)
	};
}

function normalizeTranslationMode(
	value: JsonValue | undefined,
	fallback: TranslationMode
): TranslationMode {
	const mode = stringValue(value);
	if (
		mode === 'off' ||
		mode === 'cache' ||
		mode === 'populate' ||
		mode === 'auto' ||
		mode === 'do-it-all'
	) {
		return mode;
	}
	return fallback;
}

function normalizeLanguage(value: string): LanguageMode {
	if (value === 'san' || value === 'grc' || value === 'lat') return value;
	return 'san';
}

function normalizeOptionalLanguage(value: string): LanguageMode | undefined {
	if (value === 'san' || value === 'grc' || value === 'lat') return value;
	return undefined;
}

function normalizeWordIndexLanguage(value: string) {
	if (value === 'all') return 'all';
	return normalizeLanguage(value);
}

function normalizeToolIds(values: string[]) {
	return dedupe(values.map((value) => normalizeToolId(value)));
}

function normalizeToolRequest(value: string): ToolRequest {
	return value === 'all' ? 'all' : normalizeToolId(value);
}

function normalizeToolId(value: string): ToolId {
	if (value === 'whitaker') return 'whitakers';
	if (value === 'sanskrit-heritage') return 'heritage';
	if (
		value === 'cdsl' ||
		value === 'heritage' ||
		value === 'dico' ||
		value === 'diogenes' ||
		value === 'bailly' ||
		value === 'cts_index' ||
		value === 'spacy' ||
		value === 'cltk' ||
		value === 'whitakers' ||
		value === 'gaffiot' ||
		value === 'lewis_1890'
	) {
		return value;
	}
	return 'diogenes';
}

function languageLabel(tag: string) {
	const labels: Record<string, string> = {
		en: 'English',
		fr: 'French',
		grc: 'Greek',
		lat: 'Latin',
		san: 'Sanskrit',
		sa: 'Sanskrit'
	};

	return labels[tag] ?? tag.toUpperCase();
}

function sourceLayerLabel(toolId: ToolId | undefined, sourceLang: string) {
	const toolLabels: Partial<Record<ToolId, string>> = {
		cdsl: 'CDSL',
		heritage: 'Heritage',
		dico: 'DICO',
		diogenes: 'Diogenes',
		bailly: 'Bailly',
		cts_index: 'CTS',
		spacy: 'spaCy',
		cltk: 'CLTK',
		whitakers: 'Words',
		gaffiot: 'Gaffiot',
		lewis_1890: 'Lewis 1890'
	};
	const tool = toolId ? toolLabels[toolId] : '';
	const lang = languageCodeLabel(sourceLang);

	return tool ? `${tool} ${lang}` : `${lang} source`;
}

function languageCodeLabel(tag: string) {
	const labels: Record<string, string> = {
		en: 'EN',
		fr: 'FR',
		grc: 'GRC',
		lat: 'LAT',
		san: 'SAN',
		sa: 'SAN'
	};

	return labels[tag] ?? tag.toUpperCase();
}

function errorMessageFromPayload(payload: JsonObject) {
	const error = objectValue(payload.error);
	return stringValue(error?.message) || stringValue(payload.message);
}

function isObject(value: unknown): value is JsonObject {
	return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function objectValue(value: JsonValue | undefined): JsonObject | undefined {
	return isObject(value) ? value : undefined;
}

function arrayOfObjects(value: JsonValue | undefined): JsonObject[] {
	return Array.isArray(value) ? value.filter(isObject) : [];
}

function arrayOfStrings(value: JsonValue | undefined): string[] {
	return Array.isArray(value) ? value.map((item) => stringValue(item)).filter(Boolean) : [];
}

function stringValue(value: JsonValue | undefined): string {
	return typeof value === 'string' ? value : '';
}

function numberValue(value: JsonValue | undefined): number {
	return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function booleanValue(value: JsonValue | undefined): boolean {
	return value === true;
}

function dedupe<T>(values: T[]) {
	return [...new Set(values)];
}
