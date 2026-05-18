import type { WordRecommendationResult } from './search-data';
import type { WordRecommendationItem } from './search-data';

export type StoredMotd = {
	version: 3;
	savedAt: number;
	expiresAt: number;
	kind: 'current';
	result: WordRecommendationResult;
};

export function motdTtlMs(ttlSeconds: number | undefined) {
	const seconds = ttlSeconds || 3600;
	return Math.max(60_000, Math.min(seconds, 86_400) * 1000);
}

export function storedMotdIsFresh(stored: Partial<StoredMotd>, now = Date.now()) {
	return storedMotdStatus(stored, now) === 'fresh';
}

export function storedMotdStatus(
	stored: Partial<StoredMotd>,
	now = Date.now()
): 'fresh' | 'stale' | 'invalid' {
	if (
		stored.version !== 3 ||
		stored.kind !== 'current' ||
		!stored.result ||
		typeof stored.savedAt !== 'number' ||
		typeof stored.expiresAt !== 'number'
	) {
		return 'invalid';
	}

	if (stored.expiresAt > now) return 'fresh';
	return 'stale';
}

export function motdItemKeys(
	result: { items: Partial<WordRecommendationItem>[] } | null | undefined
) {
	if (!result) return [];
	return dedupe(
		result.items.map((item) => motdItemKey(item)).filter((key): key is string => Boolean(key))
	);
}

function motdItemKey(item: Partial<WordRecommendationItem>) {
	if (item.key) return item.key;
	if (item.language && item.query) return `${item.language}:${item.query}`;
	return '';
}

function dedupe(values: string[]) {
	return [...new Set(values)];
}
