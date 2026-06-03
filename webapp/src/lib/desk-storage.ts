import { motdTtlMs, storedMotdStatus, type StoredMotd } from './motd-cache';
import type {
	EncounterResult,
	LanguageMode,
	SearchBackend,
	ToolId,
	TranslationMode,
	WordRecommendationResult
} from './search-data';
import type { WordIndexItem, WordIndexResponse, WordIndexSectionsResponse } from './word-index';

export type StoredDeskState = {
	version: 5;
	expiresAt: number;
	routeKey: string;
	language: LanguageMode;
	query: string;
	backendMode: SearchBackend;
	translationMode: TranslationMode;
	theme: 'manuscript' | 'vespers';
	lookupTools: ToolId[];
	visibleTools: ToolId[];
	encounter: EncounterResult | null;
	textLayers: Record<string, 'reader' | 'source'>;
	expandedSections: Record<string, boolean>;
	collapsedBranches: Record<string, boolean>;
	wordIndex?: WordIndexResponse | null;
	wordIndexSections?: WordIndexSectionsResponse | null;
};

export type StoredWordIndexEarmarks = {
	version: 1;
	items: WordIndexItem[];
};

type MotdNormalizer = (result: WordRecommendationResult) => WordRecommendationResult;

export function readStoredMotd(
	storage: Storage,
	key: string,
	normalize: MotdNormalizer,
	now = Date.now()
): { result: WordRecommendationResult | null; stale: boolean } {
	try {
		const raw = storage.getItem(key);
		if (!raw) return { result: null, stale: false };

		const stored = JSON.parse(raw) as Partial<StoredMotd>;
		const status = storedMotdStatus(stored, now);
		if (status === 'invalid') {
			storage.removeItem(key);
			return { result: null, stale: false };
		}

		if (!stored.result) return { result: null, stale: false };
		const result = normalize(stored.result);
		if (!result.items.length) {
			storage.removeItem(key);
			return { result: null, stale: false };
		}
		return { result, stale: status === 'stale' };
	} catch {
		storage.removeItem(key);
		return { result: null, stale: false };
	}
}

export function saveStoredMotd(
	storage: Storage,
	key: string,
	result: WordRecommendationResult,
	now = Date.now()
) {
	if (!result.items.length) return;

	const ttlMs = motdTtlMs(result.suggested_ttl_seconds);
	const stored: StoredMotd = {
		version: 3,
		savedAt: now,
		expiresAt: now + ttlMs,
		kind: 'current',
		result
	};

	try {
		storage.setItem(key, JSON.stringify(stored));
	} catch {
		// Browser storage may be unavailable or full; the app can still use live API data.
	}
}

export function readStoredWordIndexEarmarks(storage: Storage, key: string) {
	try {
		const raw = storage.getItem(key);
		if (!raw) return [];

		const stored = JSON.parse(raw) as Partial<StoredWordIndexEarmarks>;
		if (stored.version !== 1 || !Array.isArray(stored.items)) {
			storage.removeItem(key);
			return [];
		}

		return stored.items.filter((item) => Boolean(item?.encounter?.q)).slice(0, 18);
	} catch {
		storage.removeItem(key);
		return [];
	}
}

export function saveStoredWordIndexEarmarks(storage: Storage, key: string, items: WordIndexItem[]) {
	try {
		storage.setItem(key, JSON.stringify({ version: 1, items } satisfies StoredWordIndexEarmarks));
	} catch {
		// Earmarks are a reader convenience; failure must not affect lookup.
	}
}

export function readStoredDeskState(storage: Storage, key: string, now = Date.now()) {
	try {
		const raw = storage.getItem(key);
		if (!raw) return null;

		const stored = JSON.parse(raw) as Partial<StoredDeskState>;
		if (stored.version !== 5 || !stored.expiresAt || stored.expiresAt <= now) {
			storage.removeItem(key);
			return null;
		}

		return stored as StoredDeskState;
	} catch {
		storage.removeItem(key);
		return null;
	}
}

export function saveStoredDeskState(storage: Storage, key: string, state: StoredDeskState) {
	try {
		storage.setItem(key, JSON.stringify(state));
	} catch {
		// Long dictionary entries can exceed browser storage limits; hard links still work.
	}
}

export function clearStorageKeys(storage: Storage, keys: string[]) {
	try {
		for (const key of keys) storage.removeItem(key);
	} catch {
		// Ignore storage failures.
	}
}
