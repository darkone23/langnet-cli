import { motdItemKeys, motdTtlMs } from '$lib/motd-cache';
import { wordRecommendationsFromCli } from '$lib/server/langnet-cli';
import { payloadResponse } from '$lib/server/msgpack-response';
import type { TranslationMode, WordRecommendationResult } from '$lib/search-data';

const translationModes = new Set(['off', 'cache', 'populate', 'auto', 'do-it-all']);
const candidateSources = new Set(['auto', 'llm', 'curated']);
const levels = new Set(['beginner', 'intermediate', 'deep']);
const cache = new Map<string, { expiresAt: number; result: WordRecommendationResult }>();
const recentKeys: string[] = [];
const maxRecentKeys = 24;

export async function GET({ url, request }) {
	const respond = (payload: unknown, init?: ResponseInit) =>
		payloadResponse(request, payload, init);
	const count = readInteger(url.searchParams.get('count'), 1, 1, 5);
	const requestedLevel = url.searchParams.get('level') ?? 'beginner';
	const level = levels.has(requestedLevel) ? requestedLevel : 'beginner';
	const requestedTranslationMode = url.searchParams.get('translation') ?? 'cache';
	const translationMode = translationModes.has(requestedTranslationMode)
		? (requestedTranslationMode as TranslationMode)
		: ('cache' as const);
	const timeoutMs = readInteger(url.searchParams.get('timeout_ms'), 120_000, 5_000, 300_000);
	const shouldRefresh =
		url.searchParams.get('refresh') === '1' || url.searchParams.get('refresh') === 'yes';
	const requestedCandidateSource =
		url.searchParams.get('candidate_source') ?? (shouldRefresh ? 'llm' : 'auto');
	const candidateSource = candidateSources.has(requestedCandidateSource)
		? (requestedCandidateSource as 'auto' | 'llm' | 'curated')
		: shouldRefresh
			? 'llm'
			: 'auto';
	const generationCandidateSource = candidateSource;
	const explicitAvoid = readList(url.searchParams.get('avoid'));
	const avoid = dedupe([...recentKeys, ...explicitAvoid]);
	const nonce = shouldRefresh
		? url.searchParams.get('nonce') ||
			`web-motd-${Date.now()}-${Math.random().toString(36).slice(2)}`
		: (url.searchParams.get('nonce') ?? undefined);
	const currentCacheKey = motdCacheKey({
		count,
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
					level,
					translationMode,
					candidateSource: generationCandidateSource,
					avoid: shouldRefresh ? [] : explicitAvoid
				});
	const cached = cache.get(cacheKey);

	if (!shouldRefresh && cached && cached.expiresAt > Date.now()) {
		return respond(cached.result);
	}

	try {
		const result = await wordRecommendationsFromCli({
			count,
			level,
			translationMode,
			timeoutMs,
			candidateSource: generationCandidateSource,
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
		cache.set(cacheKey, { expiresAt: Date.now() + ttlMs, result });
		if (candidateSource === 'auto') {
			cache.set(currentCacheKey, { expiresAt: Date.now() + ttlMs, result });
		}
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

function motdCacheKey({
	count,
	level,
	translationMode,
	candidateSource,
	avoid
}: {
	count: number;
	level: string;
	translationMode: TranslationMode;
	candidateSource: 'auto' | 'llm' | 'curated';
	avoid: string[];
}) {
	return JSON.stringify({
		count,
		level,
		translationMode,
		candidateSource,
		avoid
	});
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
