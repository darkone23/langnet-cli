const defaultTtlMs = 15 * 60 * 1000;
const defaultMaxEntries = 48;

type CacheEntry<T> = {
	value: T;
	expiresAt: number;
};

export class TimedResponseCache<T> {
	readonly ttlMs: number;
	readonly maxEntries: number;
	#entries = new Map<string, CacheEntry<T>>();

	constructor({ ttlMs = defaultTtlMs, maxEntries = defaultMaxEntries } = {}) {
		this.ttlMs = ttlMs;
		this.maxEntries = maxEntries;
	}

	get(key: string, now = Date.now()): T | undefined {
		const entry = this.#entries.get(key);
		if (!entry) return undefined;
		if (entry.expiresAt <= now) {
			this.#entries.delete(key);
			return undefined;
		}
		this.#entries.delete(key);
		this.#entries.set(key, entry);
		return entry.value;
	}

	set(key: string, value: T, now = Date.now()) {
		this.#entries.delete(key);
		this.#entries.set(key, { value, expiresAt: now + this.ttlMs });
		while (this.#entries.size > this.maxEntries) {
			const oldest = this.#entries.keys().next().value;
			if (!oldest) break;
			this.#entries.delete(oldest);
		}
	}

	clear() {
		this.#entries.clear();
	}

	get size() {
		return this.#entries.size;
	}
}

export const searchResponseCache = new TimedResponseCache<unknown>();

export function searchCacheKey(url: URL) {
	const params = [...url.searchParams.entries()].sort(
		([leftKey, leftValue], [rightKey, rightValue]) =>
			leftKey === rightKey ? leftValue.localeCompare(rightValue) : leftKey.localeCompare(rightKey)
	);
	return params
		.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
		.join('&');
}

export function canCacheSearchResponse({
	backend,
	word,
	translationMode,
	payload
}: {
	backend: string;
	word: string;
	translationMode: string;
	payload: unknown;
}) {
	if (backend !== 'cli' || !word) return false;
	if (!['off', 'cache'].includes(translationMode)) return false;
	if (!payload || typeof payload !== 'object') return false;
	if ('error' in payload) return false;
	if (translationMode === 'cache' && hasIncompleteTranslationCache(payload)) return false;
	return true;
}

function hasIncompleteTranslationCache(payload: object) {
	const cache = objectValue((payload as { translation_cache?: unknown }).translation_cache);
	if (!cache) return false;
	const after = objectValue(cache.after);
	if (!after) return false;
	return (
		numberValue(after.missing) > 0 || numberValue(after.errors) > 0 || numberValue(after.empty) > 0
	);
}

function objectValue(value: unknown): Record<string, unknown> | undefined {
	if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
	return value as Record<string, unknown>;
}

function numberValue(value: unknown) {
	return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}
