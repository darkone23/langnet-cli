import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { motdItemKeys, motdTtlMs } from '$lib/motd-cache';
import { resolveCliDirectory, wordRecommendationsFromCli } from '$lib/server/langnet-cli';
import { payloadResponse } from '$lib/server/msgpack-response';
import type { LanguageMode, TranslationMode, WordRecommendationResult } from '$lib/search-data';

const translationModes = new Set(['off', 'cache', 'populate', 'auto', 'do-it-all']);
const candidateSources = new Set(['auto', 'llm', 'curated']);
const languages = new Set(['san', 'grc', 'lat', 'all']);
const levels = new Set(['beginner', 'intermediate', 'deep']);
const cache = new Map<string, { expiresAt: number; result: WordRecommendationResult }>();
const refreshingCacheKeys = new Set<string>();
const recentKeys: string[] = [];
const maxRecentKeys = 24;
const motdDiskCachePath = path.join(resolveCliDirectory(), 'data', 'cache', 'web-motd-cache.json');
const maxPersistedStaleMs = 7 * 24 * 60 * 60 * 1000;
let hydrateDiskCachePromise: Promise<void> | null = null;
let persistDiskCachePromise: Promise<void> = Promise.resolve();
type CandidateSource = 'auto' | 'llm' | 'curated';
type MotdLanguage = LanguageMode | 'all';
type PersistedMotdCache = {
	version: 1;
	savedAt: string;
	entries: Record<string, { expiresAt: number; result: WordRecommendationResult }>;
};

export async function GET({ url, request }) {
	const respond = (payload: unknown, init?: ResponseInit) =>
		payloadResponse(request, payload, init);
	const requestedLanguage = url.searchParams.get('language') ?? 'san';
	const language = languages.has(requestedLanguage)
		? (requestedLanguage as LanguageMode | 'all')
		: ('san' as const);
	const count = readInteger(url.searchParams.get('count'), 1, 1, 5);
	const requestedLevel = url.searchParams.get('level') ?? 'beginner';
	const level = levels.has(requestedLevel) ? requestedLevel : 'beginner';
	const requestedTranslationMode = url.searchParams.get('translation') ?? 'cache';
	const translationMode = translationModes.has(requestedTranslationMode)
		? (requestedTranslationMode as TranslationMode)
		: ('cache' as const);
	const timeoutMs = readInteger(url.searchParams.get('timeout_ms'), 12_000, 5_000, 30_000);
	const shouldRefresh =
		url.searchParams.get('refresh') === '1' || url.searchParams.get('refresh') === 'yes';
	const requestedCandidateSource = url.searchParams.get('candidate_source') ?? 'llm';
	const candidateSource = candidateSources.has(requestedCandidateSource)
		? (requestedCandidateSource as CandidateSource)
		: 'llm';
	const generationCandidateSource = candidateSource;
	const dictionary = motdDictionary(language);
	const explicitAvoid = readList(url.searchParams.get('avoid'));
	const avoid = dedupe([...recentKeys, ...explicitAvoid]);
	const nonce = shouldRefresh
		? url.searchParams.get('nonce') ||
			`web-motd-${Date.now()}-${Math.random().toString(36).slice(2)}`
		: (url.searchParams.get('nonce') ?? undefined);
	const currentCacheKey = motdCacheKey({
		count,
		language,
		level,
		translationMode,
		candidateSource: 'auto',
		avoid: []
	});
	const cacheKey =
		candidateSource === 'auto' && !explicitAvoid.length
			? currentCacheKey
			: motdCacheKey({
					count,
					language,
					level,
					translationMode,
					candidateSource: generationCandidateSource,
					avoid: shouldRefresh ? [] : explicitAvoid
				});
	await hydrateMotdDiskCache();
	const cached = cache.get(cacheKey);

	if (!shouldRefresh && cached && cached.expiresAt > Date.now()) {
		return respond(cached.result);
	}

	if (!shouldRefresh && cached) {
		void refreshMotdCacheInBackground({
			cacheKey,
			currentCacheKey,
			count,
			language,
			dictionary,
			level,
			translationMode,
			timeoutMs,
			candidateSource: generationCandidateSource,
			avoid,
			nonce: nonce || `web-motd-stale-refresh-${Date.now()}-${Math.random().toString(36).slice(2)}`
		});
		return respond(serveStaleWhileRefreshing(cached.result));
	}

	if (!shouldRefresh && generationCandidateSource === 'llm') {
		void refreshMotdCacheInBackground({
			cacheKey,
			currentCacheKey,
			count,
			language,
			dictionary,
			level,
			translationMode,
			timeoutMs,
			candidateSource: 'llm',
			avoid,
			nonce: nonce || `web-motd-llm-warm-${Date.now()}-${Math.random().toString(36).slice(2)}`
		});
		try {
			const fallback = await wordRecommendationsFromCli({
				language,
				dictionary,
				count,
				level,
				translationMode,
				timeoutMs: Math.min(timeoutMs, 8_000),
				candidateSource: 'curated',
				includeAmbiguous: true,
				finalizeCards: false,
				fresh: false,
				avoid: explicitAvoid,
				signal: request.signal
			});
			fallback.suggested_ttl_seconds = Math.min(fallback.suggested_ttl_seconds, 60);
			fallback.warnings = [
				{
					message:
						'Showing fast source-backed learner cards while live LLM recommendations warm in the background.'
				},
				...fallback.warnings
			];
			rememberRecentKeys(motdItemKeys(fallback));
			const ttlMs = fallback.items.length ? motdTtlMs(fallback.suggested_ttl_seconds) : 60_000;
			cacheMotdResult(cacheKey, currentCacheKey, candidateSource, Date.now() + ttlMs, fallback);
			return respond(fallback);
		} catch {
			// Fall through to the live LLM attempt below if the fast source-backed path fails.
		}
	}

	try {
		const result = await wordRecommendationsFromCli({
			language,
			dictionary,
			count,
			level,
			translationMode,
			timeoutMs,
			candidateSource: generationCandidateSource,
			includeAmbiguous: true,
			finalizeCards: false,
			fresh: shouldRefresh || Boolean(cached),
			avoid: shouldRefresh || cached ? avoid : explicitAvoid,
			nonce:
				nonce ||
				(cached
					? `web-motd-refresh-${Date.now()}-${Math.random().toString(36).slice(2)}`
					: undefined),
			signal: request.signal
		});
		rememberRecentKeys(motdItemKeys(result));
		const ttlMs = result.items.length ? motdTtlMs(result.suggested_ttl_seconds) : 60_000;
		cacheMotdResult(cacheKey, currentCacheKey, candidateSource, Date.now() + ttlMs, result);
		return respond(result);
	} catch (error) {
		if (cached?.result) {
			return respond({
				...cached.result,
				warnings: [
					{
						message: `Using the previous word of the day; replacement could not be prepared: ${error instanceof Error ? error.message : 'Word recommendations failed.'}`
					},
					...cached.result.warnings
				]
			});
		}
		if (generationCandidateSource !== 'curated') {
			try {
				const fallback = await wordRecommendationsFromCli({
					language,
					dictionary,
					count,
					level,
					translationMode,
					timeoutMs: Math.min(timeoutMs, 10_000),
					candidateSource: 'curated',
					includeAmbiguous: true,
					finalizeCards: false,
					fresh: false,
					avoid: explicitAvoid,
					signal: request.signal
				});
				fallback.warnings = [
					{
						message: `Live learner word generation fell back to curated words: ${error instanceof Error ? error.message : 'Word recommendations failed.'}`
					},
					...fallback.warnings
				];
				rememberRecentKeys(motdItemKeys(fallback));
				const ttlMs = fallback.items.length ? motdTtlMs(fallback.suggested_ttl_seconds) : 60_000;
				cacheMotdResult(currentCacheKey, currentCacheKey, 'auto', Date.now() + ttlMs, fallback);
				return respond(fallback);
			} catch {
				// Fall through to the structured 502 below.
			}
		}
		return respond(
			{
				schema_version: 'langnet.word_of_day.v1',
				generated_at: new Date().toISOString(),
				suggested_ttl_seconds: 300,
				items: [],
				warnings: [],
				error: error instanceof Error ? error.message : 'Word recommendations failed.'
			} satisfies WordRecommendationResult,
			{ status: 502 }
		);
	}
}

async function refreshMotdCacheInBackground({
	cacheKey,
	currentCacheKey,
	count,
	language,
	dictionary,
	level,
	translationMode,
	timeoutMs,
	candidateSource,
	avoid,
	nonce
}: {
	cacheKey: string;
	currentCacheKey: string;
	count: number;
	language: MotdLanguage;
	dictionary: string;
	level: string;
	translationMode: TranslationMode;
	timeoutMs: number;
	candidateSource: CandidateSource;
	avoid: string[];
	nonce: string;
}) {
	if (refreshingCacheKeys.has(cacheKey)) return;
	refreshingCacheKeys.add(cacheKey);
	try {
		const result = await wordRecommendationsFromCli({
			language,
			dictionary,
			count,
			level,
			translationMode,
			timeoutMs,
			candidateSource,
			includeAmbiguous: true,
			finalizeCards: false,
			fresh: true,
			avoid,
			nonce
		});
		rememberRecentKeys(motdItemKeys(result));
		const ttlMs = result.items.length ? motdTtlMs(result.suggested_ttl_seconds) : 60_000;
		cacheMotdResult(cacheKey, currentCacheKey, candidateSource, Date.now() + ttlMs, result);
	} catch (error) {
		console.warn(
			`MOTD background refresh failed: ${
				error instanceof Error ? error.message : 'Word recommendations failed.'
			}`
		);
	} finally {
		refreshingCacheKeys.delete(cacheKey);
	}
}

function serveStaleWhileRefreshing(result: WordRecommendationResult): WordRecommendationResult {
	return {
		...result,
		warnings: [
			{
				message: 'Showing the previous word of the day while a fresh entry is prepared.'
			},
			...result.warnings
		]
	};
}

function cacheMotdResult(
	cacheKey: string,
	currentCacheKey: string,
	candidateSource: CandidateSource,
	expiresAt: number,
	result: WordRecommendationResult
) {
	cache.set(cacheKey, { expiresAt, result });
	if (candidateSource === 'auto') {
		cache.set(currentCacheKey, { expiresAt, result });
	}
	void persistMotdDiskCache();
}

async function hydrateMotdDiskCache() {
	hydrateDiskCachePromise ??= hydrateMotdDiskCacheOnce();
	await hydrateDiskCachePromise;
}

async function hydrateMotdDiskCacheOnce() {
	try {
		const raw = await readFile(motdDiskCachePath, 'utf8');
		const parsed = JSON.parse(raw) as Partial<PersistedMotdCache>;
		if (parsed.version !== 1 || !parsed.entries || typeof parsed.entries !== 'object') return;
		const oldestUsableExpiry = Date.now() - maxPersistedStaleMs;
		for (const [key, entry] of Object.entries(parsed.entries)) {
			if (
				!entry ||
				typeof entry.expiresAt !== 'number' ||
				entry.expiresAt < oldestUsableExpiry ||
				!entry.result ||
				!Array.isArray(entry.result.items)
			) {
				continue;
			}
			cache.set(key, entry);
		}
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
			console.warn(
				`MOTD disk cache could not be read: ${
					error instanceof Error ? error.message : 'unknown error'
				}`
			);
		}
	}
}

function persistMotdDiskCache() {
	persistDiskCachePromise = persistDiskCachePromise
		.catch(() => undefined)
		.then(async () => {
			const entries = Object.fromEntries(
				[...cache.entries()].filter(
					([, entry]) =>
						entry.result.items.length && entry.expiresAt > Date.now() - maxPersistedStaleMs
				)
			);
			const payload: PersistedMotdCache = {
				version: 1,
				savedAt: new Date().toISOString(),
				entries
			};
			await mkdir(path.dirname(motdDiskCachePath), { recursive: true });
			await writeFile(motdDiskCachePath, `${JSON.stringify(payload)}\n`, 'utf8');
		})
		.catch((error) => {
			console.warn(
				`MOTD disk cache could not be written: ${
					error instanceof Error ? error.message : 'unknown error'
				}`
			);
		});
	return persistDiskCachePromise;
}

function motdCacheKey({
	count,
	language,
	level,
	translationMode,
	candidateSource,
	avoid
}: {
	count: number;
	language: MotdLanguage;
	level: string;
	translationMode: TranslationMode;
	candidateSource: CandidateSource;
	avoid: string[];
}) {
	return JSON.stringify({
		count,
		language,
		level,
		translationMode,
		candidateSource,
		avoid
	});
}

function motdDictionary(language: MotdLanguage) {
	if (language === 'san') return 'cdsl';
	if (language === 'grc') return 'diogenes';
	if (language === 'lat') return 'whitakers';
	return 'motd-fast';
}

function readInteger(value: string | null, fallback: number, min: number, max: number) {
	if (!value) return fallback;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return fallback;
	return Math.min(max, Math.max(min, parsed));
}

function readList(value: string | null) {
	if (!value) return [];
	return value
		.split(',')
		.map((item) => item.trim())
		.filter(Boolean);
}

function rememberRecentKeys(keys: string[]) {
	for (const key of keys.filter(Boolean)) {
		const existingIndex = recentKeys.indexOf(key);
		if (existingIndex !== -1) recentKeys.splice(existingIndex, 1);
		recentKeys.unshift(key);
	}

	recentKeys.length = Math.min(recentKeys.length, maxRecentKeys);
}

function dedupe(values: string[]) {
	return [...new Set(values)];
}
