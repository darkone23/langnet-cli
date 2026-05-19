import { TimedResponseCache } from './search-cache';
import type { ReaderCatalog } from '$lib/reader';

const readerCacheTtlMs = 2 * 60 * 1000;
const catalogCacheTtlMs = 60 * 1000;

export const readerResponseCache = new TimedResponseCache<unknown>({
	ttlMs: readerCacheTtlMs,
	maxEntries: 160
});

export const readerCatalogCache = new TimedResponseCache<ReaderCatalog[]>({
	ttlMs: catalogCacheTtlMs,
	maxEntries: 1
});

export function readerCacheKey(url: URL) {
	const params = [...url.searchParams.entries()].sort(
		([leftKey, leftValue], [rightKey, rightValue]) =>
			leftKey === rightKey ? leftValue.localeCompare(rightValue) : leftKey.localeCompare(rightKey)
	);
	return params
		.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
		.join('&');
}

export function canCacheReaderResponse(payload: unknown) {
	if (!payload || typeof payload !== 'object') return false;
	return !('error' in payload);
}
