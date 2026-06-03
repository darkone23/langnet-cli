import { strict as assert } from 'node:assert';
import {
	buildStoredReaderIndexState,
	readStoredReaderIndexState,
	readerIndexStorageKey,
	readerIndexStorageTtlMs,
	writeStoredReaderIndexState,
	type StoredReaderIndexState
} from './reader-index-storage';

class MemoryStorage implements Storage {
	private items = new Map<string, string>();
	length = 0;

	clear() {
		this.items.clear();
		this.length = 0;
	}

	getItem(key: string) {
		return this.items.get(key) ?? null;
	}

	key(index: number) {
		return [...this.items.keys()][index] ?? null;
	}

	removeItem(key: string) {
		this.items.delete(key);
		this.length = this.items.size;
	}

	setItem(key: string, value: string) {
		this.items.set(key, value);
		this.length = this.items.size;
	}
}

const now = 1_700_000_000_000;
const storage = new MemoryStorage();

const stored: StoredReaderIndexState = {
	version: 6,
	expiresAt: now + 1000,
	language: 'grc',
	catalogId: 'development',
	readerView: 'authors',
	activeAuthorSection: 'Α',
	workQuery: 'plato',
	textQuery: 'logos',
	textSearchMode: 'fuzzy',
	discoveryGroup: 'philosophy',
	discoveryTag: '',
	discoveryAuthorId: '',
	discoveryAuthorLabel: '',
	discoverySort: 'global-popularity',
	authorAgentKind: '',
	authorHistoricity: '',
	worksNextCursor: '10',
	worksPrevCursor: null,
	authorsNextCursor: '20',
	authorsPrevCursor: null,
	textSearchNextCursor: '30',
	textSearchPrevCursor: null
};

storage.setItem(readerIndexStorageKey, JSON.stringify(stored));
assert.deepEqual(
	readStoredReaderIndexState(storage, {
		language: 'grc',
		catalogId: 'development',
		now
	}),
	stored
);

storage.setItem(readerIndexStorageKey, JSON.stringify({ ...stored, expiresAt: now - 1 }));
assert.equal(
	readStoredReaderIndexState(storage, { language: 'grc', catalogId: 'development', now }),
	null
);
assert.equal(storage.getItem(readerIndexStorageKey), null);

storage.setItem(readerIndexStorageKey, JSON.stringify({ ...stored, catalogId: 'other' }));
assert.equal(
	readStoredReaderIndexState(storage, { language: 'grc', catalogId: 'development', now }),
	null
);
assert.equal(storage.getItem(readerIndexStorageKey), null);

const built = buildStoredReaderIndexState(
	{
		language: 'san',
		catalogId: 'development',
		readerView: 'shelves',
		activeAuthorSection: '',
		workQuery: '',
		textQuery: '',
		textSearchMode: 'exact',
		discoveryGroup: '',
		discoveryTag: 'gita',
		discoveryAuthorId: '',
		discoveryAuthorLabel: '',
		discoverySort: 'group-popularity',
		authorAgentKind: '',
		authorHistoricity: '',
		worksNextCursor: null,
		worksPrevCursor: null,
		authorsNextCursor: null,
		authorsPrevCursor: null,
		textSearchNextCursor: null,
		textSearchPrevCursor: null
	},
	now
);

assert.equal(built.version, 6);
assert.equal(built.expiresAt, now + readerIndexStorageTtlMs);
assert.equal(writeStoredReaderIndexState(storage, built), true);
assert.equal(JSON.parse(storage.getItem(readerIndexStorageKey) ?? '{}').language, 'san');
