import { strict as assert } from 'node:assert';
import { createHmac } from 'node:crypto';
import { createAttestationToken, verifyAttestationToken } from './client-attestation';

const secret = 'test-secret-for-client-attestation';
const sessionId = 'session-abc1234567890';
const nowSeconds = 1_780_590_000;

function base64UrlEncode(input: string | Uint8Array) {
	const base64 = input instanceof Uint8Array ? Buffer.from(input).toString('base64') : Buffer.from(input).toString('base64');
	return base64.replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

function legacySignature(encodedPayload: string, secret: string) {
	const raw = createHmac('sha256', secret).update(encodedPayload).digest();
	const bytes = raw instanceof Uint8Array ? raw : new Uint8Array(raw as ArrayBuffer);
	return base64UrlEncode(bytes);
}

const legacyPayload = {
	sid: sessionId,
	method: 'GET',
	path: '/api/search',
	query_hash: 'dictionary=bailly&dictionary=diogenes&q=logos',
	iat: nowSeconds,
	exp: nowSeconds + 300
};
const encodedLegacyPayload = base64UrlEncode(JSON.stringify(legacyPayload));
const legacyToken = `${encodedLegacyPayload}.${legacySignature(encodedLegacyPayload, secret)}`;

const token = createAttestationToken({
	sessionId,
	scope: 'search',
	secret,
	nowSeconds,
	ttlSeconds: 300
});
const futureToken = createAttestationToken({
	sessionId,
	scope: 'search',
	secret,
	nowSeconds: nowSeconds + 60,
	ttlSeconds: 300
});

assert.equal(
	verifyAttestationToken({
		token,
		sessionId,
		scope: 'search',
		secret,
		nowSeconds: nowSeconds + 60
	}).status,
	'valid'
);

assert.equal(
	verifyAttestationToken({
		token: futureToken,
		sessionId,
		scope: 'search',
		secret,
		nowSeconds: nowSeconds
	}).status,
	'future_iat'
);

assert.equal(
	verifyAttestationToken({
		token,
		sessionId,
		scope: 'reader',
		secret,
		nowSeconds: nowSeconds + 60
	}).status,
	'scope_mismatch'
);

assert.equal(
	verifyAttestationToken({
		token,
		sessionId,
		scope: 'search',
		secret,
		nowSeconds: nowSeconds + 301
	}).status,
	'expired'
);

assert.equal(
	verifyAttestationToken({
		token,
		sessionId: 'different-session',
		scope: 'search',
		secret,
		nowSeconds: nowSeconds + 60
	}).status,
	'session_mismatch'
);

assert.equal(
	verifyAttestationToken({
		token: `${token.slice(0, -1)}x`,
		sessionId,
		scope: 'search',
		secret,
		nowSeconds: nowSeconds + 60
	}).status,
	'bad_signature'
);

assert.equal(
	verifyAttestationToken({
		token: 'not-a-token',
		sessionId,
		scope: 'search',
		secret,
		nowSeconds: nowSeconds + 60
	}).status,
	'malformed'
);

assert.equal(
	verifyAttestationToken({
		token: legacyToken,
		sessionId,
		scope: 'search',
		secret,
		nowSeconds: nowSeconds + 60
	}).status,
	'valid'
);

console.log('client attestation checks complete');
