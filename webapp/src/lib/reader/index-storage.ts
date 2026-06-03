import type { ReaderRouteState, ReaderSearchMode } from './index';
import type { LanguageMode } from '../search-data';

export type ReaderIndexView = 'choose' | NonNullable<ReaderRouteState['readerView']>;

export const readerIndexStorageKey = 'orion-reader-index-state:v6';
export const readerIndexStorageTtlMs = 2 * 60 * 60 * 1000;

export type StoredReaderIndexState = {
	version: 6;
	expiresAt: number;
	language: LanguageMode;
	catalogId: string;
	readerView: ReaderIndexView;
	activeAuthorSection: string;
	workQuery: string;
	textQuery: string;
	textSearchMode: ReaderSearchMode;
	discoveryGroup: string;
	discoveryTag: string;
	discoveryAuthorId: string;
	discoveryAuthorLabel: string;
	discoverySort: ReaderRouteState['discoverySort'];
	authorAgentKind: string;
	authorHistoricity: string;
	worksNextCursor: string | null;
	worksPrevCursor: string | null;
	authorsNextCursor: string | null;
	authorsPrevCursor: string | null;
	textSearchNextCursor: string | null;
	textSearchPrevCursor: string | null;
};

type StorageReadContext = {
	language: LanguageMode;
	catalogId: string;
	now?: number;
};

export function readStoredReaderIndexState(
	storage: Storage,
	{ language, catalogId, now = Date.now() }: StorageReadContext
) {
	try {
		const raw = storage.getItem(readerIndexStorageKey);
		if (!raw) return null;

		const stored = JSON.parse(raw) as Partial<StoredReaderIndexState>;
		if (
			stored.version !== 6 ||
			!stored.expiresAt ||
			stored.expiresAt <= now ||
			stored.language !== language ||
			(catalogId && stored.catalogId !== catalogId) ||
			!stored.catalogId
		) {
			storage.removeItem(readerIndexStorageKey);
			return null;
		}

		return stored as StoredReaderIndexState;
	} catch {
		storage.removeItem(readerIndexStorageKey);
		return null;
	}
}

export function buildStoredReaderIndexState(
	state: Omit<StoredReaderIndexState, 'version' | 'expiresAt'>,
	now = Date.now()
): StoredReaderIndexState {
	return {
		version: 6,
		expiresAt: now + readerIndexStorageTtlMs,
		...state
	};
}

export function writeStoredReaderIndexState(storage: Storage, state: StoredReaderIndexState) {
	try {
		storage.setItem(readerIndexStorageKey, JSON.stringify(state));
		return true;
	} catch {
		return false;
	}
}
