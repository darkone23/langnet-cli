import { strict as assert } from 'node:assert';
import {
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

console.log('msgpack transport helpers ok');
