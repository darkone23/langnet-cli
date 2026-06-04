import { strict as assert } from 'node:assert';
import {
	clearClientAttestationCacheForTests,
	clientAttestationHeader,
	fetchPayload,
	msgpackContentType,
	payloadAcceptHeaders,
	readResponsePayload,
	requestAcceptsMsgpack
} from './msgpack';

const payload = {
	schema_version: 'langnet.reader.web.v1',
	items: [
		{ title: 'Ἀθηναίων πολιτεία', count: 1 },
		{ title: 'Aeneid', count: 3 }
	]
};

assert.equal(requestAcceptsMsgpack(new Headers({ accept: 'application/msgpack' })), true);
assert.equal(
	requestAcceptsMsgpack(new Headers({ accept: 'application/json, application/msgpack;q=0.9' })),
	true
);
assert.equal(requestAcceptsMsgpack(new Headers({ accept: 'application/json' })), false);

const headers = payloadAcceptHeaders();
assert.equal(headers.get('accept'), 'application/msgpack, application/json');

const jsonResponse = new Response(JSON.stringify(payload), {
	headers: { 'content-type': 'application/json' }
});
assert.deepEqual(await readResponsePayload(jsonResponse), payload);

const msgpackResponse = new Response(new Uint8Array([1, 2, 3]), {
	headers: { 'content-type': msgpackContentType }
});
await assert.rejects(readResponsePayload(msgpackResponse), /MessagePack/);

const originalFetch = globalThis.fetch;
const originalLocation = (globalThis as unknown as { location?: { origin: string } }).location;
type FetchCall = { input: string; init?: RequestInit };
const fetchCalls: FetchCall[] = [];

type TokenReply = { status?: number; payload: Record<string, unknown> };
const tokenReplies: TokenReply[] = [];

function enqueueTokenReply(reply: TokenReply) {
	tokenReplies.push(reply);
}

function nextTokenReply() {
	const reply = tokenReplies.shift();
	if (!reply) {
		return new Response(JSON.stringify({ token: 'missing-token', expires_at: 120 }), {
			headers: { 'content-type': 'application/json' }
		});
	}
	if ('status' in reply && reply.status !== undefined) {
		return new Response(JSON.stringify(reply.payload), { status: reply.status, headers: { 'content-type': 'application/json' } });
	}
	return new Response(JSON.stringify(reply.payload), { headers: { 'content-type': 'application/json' } });
}

globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
	const url = String(input);
	fetchCalls.push({ input: url, init });
	if (url === '/api/auth/request-token') {
		return nextTokenReply();
	}
	return new Response(JSON.stringify({ ok: true }), {
		headers: { 'content-type': 'application/json' }
	});
}) as typeof fetch;

function tokenCallCount() {
	return fetchCalls.filter((call) => call.input === '/api/auth/request-token').length;
}

function apiCallInputs() {
	return fetchCalls.filter((call) => call.input !== '/api/auth/request-token');
}

function lastApiCall() {
	return apiCallInputs().at(-1);
}

function apiRequestHeader(init: RequestInit | undefined, header: string) {
	return new Headers(init?.headers).get(header);
}

function tokenRequestScopes() {
	return fetchCalls
		.filter((call) => call.input === '/api/auth/request-token')
		.map((call) => {
			const body = call.init?.body;
			if (typeof body === 'string') {
				return JSON.parse(body).scope;
			}
			return undefined;
		})
		.filter(Boolean);
}

function defineLocation(origin: string) {
	Object.defineProperty(globalThis, 'location', {
		value: { origin },
		configurable: true,
		writable: true
	});
}

function clearMocksAndReset() {
	fetchCalls.length = 0;
	tokenReplies.length = 0;
	clearClientAttestationCacheForTests();
}

clearClientAttestationCacheForTests();

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'signed-token', expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(tokenCallCount(), 1);
assert.equal(apiCallInputs().at(-1)?.input, '/api/search?q=logos');
assert.equal(apiRequestHeader(lastApiCall()?.init, clientAttestationHeader), 'signed-token');
assert.equal(tokenRequestScopes().at(-1), 'search');

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'ordered-token', expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
await fetchPayload<{ ok: boolean }>('/api/search?dictionary=bailly&q=logos');
assert.equal(tokenCallCount(), 1);
assert.equal(apiRequestHeader(lastApiCall()?.init, clientAttestationHeader), 'ordered-token');
assert.equal(tokenRequestScopes().at(-1), 'search');

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'ordered-token', expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos&dictionary=bailly');
await fetchPayload<{ ok: boolean }>('/api/search?dictionary=bailly&q=logos');
assert.equal(tokenCallCount(), 1);
assert.equal(tokenRequestScopes().at(-1), 'search');

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'logos-token', expires_at: Math.floor(Date.now() / 1000) + 300 } });
enqueueTokenReply({ payload: { token: 'word-index-token', expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
await fetchPayload<{ ok: boolean }>('/api/word-index?q=logos');
assert.equal(tokenCallCount(), 2);
assert.equal(tokenRequestScopes().at(0), 'search');
assert.equal(tokenRequestScopes().at(1), 'word_index');

clearMocksAndReset();
const closeExpiry = Math.floor(Date.now() / 1000) + 10;
enqueueTokenReply({ payload: { token: 'near-expiry-token', expires_at: closeExpiry } });
enqueueTokenReply({ payload: { token: 'refreshed-token', expires_at: closeExpiry + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(tokenCallCount(), 2);
assert.equal(apiRequestHeader(apiCallInputs().at(0)?.init, clientAttestationHeader), 'near-expiry-token');
assert.equal(apiRequestHeader(apiCallInputs().at(1)?.init, clientAttestationHeader), 'refreshed-token');

clearMocksAndReset();
await fetchPayload<{ ok: boolean }>('/api/auth/request-token', { method: 'POST' });
assert.equal(fetchCalls.length, 1);
assert.equal(fetchCalls[0].input, '/api/auth/request-token');

defineLocation('https://app.example.test');
clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'signed-same-origin', expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('https://app.example.test/api/search?q=logos');
assert.equal(tokenCallCount(), 1);
assert.equal(apiRequestHeader(apiCallInputs().at(-1)?.init, clientAttestationHeader), 'signed-same-origin');

clearMocksAndReset();
await fetchPayload<{ ok: boolean }>('https://example.com/api/search?q=logos');
assert.equal(tokenCallCount(), 0);
assert.equal(apiCallInputs().length, 1);
assert.equal(apiRequestHeader(apiCallInputs().at(-1)?.init, clientAttestationHeader), null);

clearMocksAndReset();
enqueueTokenReply({ payload: { expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(apiRequestHeader(apiCallInputs().at(-1)?.init, clientAttestationHeader), null);
assert.equal(tokenCallCount(), 1);
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(tokenCallCount(), 2);

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 1234, expires_at: Math.floor(Date.now() / 1000) + 300 } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(apiRequestHeader(apiCallInputs().at(-1)?.init, clientAttestationHeader), null);
assert.equal(tokenCallCount(), 1);
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(tokenCallCount(), 2);

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'no-exp' } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(apiRequestHeader(apiCallInputs().at(-1)?.init, clientAttestationHeader), null);
assert.equal(tokenCallCount(), 1);
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(tokenCallCount(), 2);

clearMocksAndReset();
enqueueTokenReply({ payload: { token: 'bad-exp', expires_at: '1234' } });
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(apiRequestHeader(apiCallInputs().at(-1)?.init, clientAttestationHeader), null);
assert.equal(tokenCallCount(), 1);
await fetchPayload<{ ok: boolean }>('/api/search?q=logos');
assert.equal(tokenCallCount(), 2);

clearMocksAndReset();
const concurrent = async () => {
	enqueueTokenReply({
		payload: { token: 'concurrent-token', expires_at: Math.floor(Date.now() / 1000) + 300 },
		status: undefined
	});
	return Promise.all([
		fetchPayload<{ ok: boolean }>('/api/search?q=logos'),
		fetchPayload<{ ok: boolean }>('/api/search?q=logos')
	]);
};
const concurrentResults = await concurrent();
assert.deepEqual(concurrentResults[0].data, { ok: true });
assert.deepEqual(concurrentResults[1].data, { ok: true });
assert.equal(tokenCallCount(), 1);
assert.equal(apiCallInputs().length, 2);
for (const call of apiCallInputs()) {
	assert.equal(apiRequestHeader(call.init, clientAttestationHeader), 'concurrent-token');
}

if (originalLocation === undefined) {
	delete (globalThis as { location?: unknown }).location;
} else {
	Object.defineProperty(globalThis, 'location', { value: originalLocation });
}

globalThis.fetch = originalFetch;

console.log('msgpack transport helpers ok');
