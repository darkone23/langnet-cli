import { canCacheReaderResponse, readerCacheKey } from './reader-cache';

function assert(condition: unknown, message: string): asserts condition {
	if (!condition) throw new Error(message);
}

const first = new URL('https://langnet.local/api/reader?mode=shelves&language=san&limit=12');
const second = new URL('https://langnet.local/api/reader?limit=12&language=san&mode=shelves');

assert(readerCacheKey(first) === readerCacheKey(second), 'reader cache keys should be stable');
assert(canCacheReaderResponse({ items: [] }), 'successful reader payloads should be cacheable');
assert(
	!canCacheReaderResponse({ error: 'failed' }),
	'reader error payloads should not be cacheable'
);

console.log('reader response cache helpers ok');
