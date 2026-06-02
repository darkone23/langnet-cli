import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { motdItemKeys, motdTtlMs } from '$lib/motd-cache';
import {
	resolveCliDirectory,
	wordRecommendationsFromCli,
	wordRecommendationsFromMotdPool
} from '$lib/server/langnet-cli';
import { payloadResponse } from '$lib/server/msgpack-response';
import type { LanguageMode, TranslationMode, WordRecommendationResult } from '$lib/search-data';

const translationModes = new Set(['off', 'cache', 'populate', 'auto', 'do-it-all']);
const candidateSources = new Set(['pool', 'auto', 'llm', 'curated']);
const languages = new Set(['san', 'grc', 'lat', 'all']);
const levels = new Set(['beginner', 'intermediate', 'deep']);
const cache = new Map<string, { expiresAt: number; result: WordRecommendationResult }>();
const refreshingCacheKeys = new Set<string>();
const recentKeys: string[] = [];
const maxRecentKeys = 24;
const motdDiskCachePath = path.join(resolveCliDirectory(), 'data', 'cache', 'web-motd-cache.json');
const maxPersistedStaleMs = 7 * 24 * 60 * 60 * 1000;
const motdCacheVersion = 2;
let hydrateDiskCachePromise: Promise<void> | null = null;
let persistDiskCachePromise: Promise<void> = Promise.resolve();
type CandidateSource = 'pool' | 'auto' | 'llm' | 'curated';
type MotdLanguage = LanguageMode | 'all';
type PersistedMotdCache = {
	version: typeof motdCacheVersion;
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
	const timeoutMs = readInteger(url.searchParams.get('timeout_ms'), 3_000, 1_000, 30_000);
	const shouldRefresh =
		url.searchParams.get('refresh') === '1' || url.searchParams.get('refresh') === 'yes';
	const requestedCandidateSource = url.searchParams.get('candidate_source') ?? 'pool';
	const candidateSource = candidateSources.has(requestedCandidateSource)
		? (requestedCandidateSource as CandidateSource)
		: 'pool';
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
		candidateSource: 'pool',
		avoid: []
	});
	const cacheKey =
		candidateSource === 'pool' && !explicitAvoid.length
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

	if (generationCandidateSource === 'pool') {
		try {
			const result = await samplePoolMotd({
				cacheKey,
				currentCacheKey,
				count,
				language,
				level,
				timeoutMs,
				avoid: shouldRefresh || cached ? avoid : explicitAvoid,
				seed: nonce || motdPoolSeed(language, level),
				signal: request.signal
			});
			return respond(result);
		} catch (error) {
			if (cached?.result && !isRecoverablePoolMiss(error)) {
				return respond({
					...cached.result,
					warnings: [
						{
							message: `Using the previous word of the day; pool sample could not be prepared: ${error instanceof Error ? error.message : 'Pool sampling failed.'}`
						},
						...cached.result.warnings
					]
				});
			}
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
						message: `Precomputed learner pool fell back to curated words: ${error instanceof Error ? error.message : 'Pool sampling failed.'}`
					},
					...fallback.warnings
				];
				rememberRecentKeys(motdItemKeys(fallback));
				const ttlMs = fallback.items.length ? motdTtlMs(fallback.suggested_ttl_seconds) : 60_000;
				cacheMotdResult(cacheKey, currentCacheKey, 'pool', Date.now() + ttlMs, fallback);
				return respond(fallback);
			} catch {
				// Fall through to the structured 502 below.
			}
			return respond(
				{
					schema_version: 'langnet.word_of_day.v1',
					generated_at: new Date().toISOString(),
					suggested_ttl_seconds: 300,
					items: [],
					warnings: [],
					error: error instanceof Error ? error.message : 'Pool sampling failed.'
				} satisfies WordRecommendationResult,
				{ status: 502 }
			);
		}
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

async function samplePoolMotd({
	cacheKey,
	currentCacheKey,
	count,
	language,
	level,
	timeoutMs,
	avoid,
	seed,
	signal
}: {
	cacheKey: string;
	currentCacheKey: string;
	count: number;
	language: MotdLanguage;
	level: string;
	timeoutMs: number;
	avoid: string[];
	seed: string;
	signal?: AbortSignal;
}) {
	const result = await wordRecommendationsFromMotdPool({
		language,
		count: poolRequestCount(language, count),
		level,
		timeoutMs,
		seed,
		avoid,
		signal
	});
	if (!result.items.length) {
		const warning =
			result.warnings[0]?.message || result.exhaustion?.reason || 'MOTD pool returned no cards.';
		throw new Error(`Precomputed learner pool returned no cards: ${warning}`);
	}
	rememberRecentKeys(motdItemKeys(result));
	const ttlMs = result.items.length ? motdTtlMs(result.suggested_ttl_seconds) : 60_000;
	cacheMotdResult(cacheKey, currentCacheKey, 'pool', Date.now() + ttlMs, result);
	return result;
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
		const result =
			candidateSource === 'pool'
				? await wordRecommendationsFromMotdPool({
						language,
						count: poolRequestCount(language, count),
						level,
						timeoutMs,
						seed: nonce,
						avoid
					})
				: await wordRecommendationsFromCli({
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
		if (
			parsed.version !== motdCacheVersion ||
			!parsed.entries ||
			typeof parsed.entries !== 'object'
		)
			return;
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
				version: motdCacheVersion,
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

function isRecoverablePoolMiss(error: unknown) {
	const message = error instanceof Error ? error.message : String(error ?? '');
	return /MOTD pool database does not exist|Precomputed learner pool returned no cards/i.test(
		message
	);
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
		version: motdCacheVersion,
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

function motdPoolSeed(language: MotdLanguage, level: string) {
	return `web-motd-pool:${new Date().toISOString().slice(0, 10)}:${language}:${level}`;
}

function poolRequestCount(language: MotdLanguage, count: number) {
	return language === 'all' ? count * 3 : count;
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
