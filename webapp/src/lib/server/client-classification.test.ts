import { strict as assert } from 'node:assert';
import { classifyClient } from './client-classification';

assert.deepEqual(
	classifyClient({
		path: '/api/search',
		attestationStatus: 'valid',
		anonymousSessionId: 'abc1234567890123',
		userAgent: 'Mozilla/5.0'
	}),
	{
		clientClass: 'trusted_web_session',
		reason: 'valid-attestation'
	}
);

assert.deepEqual(
	classifyClient({
		path: '/api/search',
		attestationStatus: 'missing',
		anonymousSessionId: 'abc1234567890123',
		userAgent: 'curl'
	}),
	{
		clientClass: 'anonymous_unattested',
		reason: 'attestation-missing'
	}
);

assert.deepEqual(
	classifyClient({
		path: '/wp-admin',
		attestationStatus: 'valid',
		anonymousSessionId: 'abc1234567890123',
		userAgent: 'Mozilla/5.0'
	}),
	{
		clientClass: 'suspicious',
		reason: 'scanner-path'
	}
);

assert.deepEqual(
	classifyClient({
		path: '/xmlrpc.php',
		attestationStatus: 'valid',
		anonymousSessionId: 'abc1234567890123',
		userAgent: 'Mozilla/5.0'
	}),
	{
		clientClass: 'suspicious',
		reason: 'scanner-path'
	}
);

console.log('client classification checks complete');
