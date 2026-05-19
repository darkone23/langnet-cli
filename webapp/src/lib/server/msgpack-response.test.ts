import { strict as assert } from 'node:assert';
import { msgpackContentType, readResponsePayload } from '../msgpack';
import { payloadResponse } from './msgpack-response';

const payload = { mode: 'works', items: [{ title: 'Aeneid' }] };

const jsonRequest = new Request('http://example.test/api/reader', {
	headers: { accept: 'application/json' }
});
const jsonResponse = payloadResponse(jsonRequest, payload);
assert.equal(jsonResponse.headers.get('content-type')?.startsWith('application/json'), true);
assert.deepEqual(await readResponsePayload(jsonResponse), payload);

const msgpackRequest = new Request('http://example.test/api/reader', {
	headers: { accept: msgpackContentType }
});
const msgpackResponse = payloadResponse(msgpackRequest, payload, { status: 202 });
assert.equal(msgpackResponse.status, 202);
assert.equal(msgpackResponse.headers.get('content-type'), msgpackContentType);
assert.equal(msgpackResponse.headers.get('vary'), 'Accept');
assert.deepEqual(await readResponsePayload(msgpackResponse), payload);

const timedResponse = payloadResponse(msgpackRequest, payload, {
	headers: { 'server-timing': 'reader;dur=12.3' }
});
assert.equal(timedResponse.headers.get('server-timing'), 'reader;dur=12.3');

console.log('msgpack response helpers ok');
