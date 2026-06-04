import { strict as assert } from 'node:assert';
import {
	attestationScopeFromPath,
	isAttestablePath,
	isAuthPath,
	isHealthPath,
	requestScopeFromPath
} from './attestation-scope';

assert.equal(attestationScopeFromPath('/api/search'), 'search');
assert.equal(attestationScopeFromPath('/api/word-index'), 'word_index');
assert.equal(attestationScopeFromPath('/api/reader'), 'reader');
assert.equal(attestationScopeFromPath('/api/unknown'), 'unknown_api');
assert.equal(attestationScopeFromPath('/api/auth/request-token'), 'unknown_api');
assert.equal(attestationScopeFromPath('/api/health'), 'unknown_api');

assert.equal(isAuthPath('/api/auth/login'), true);
assert.equal(isAuthPath('/api/search'), false);

assert.equal(isHealthPath('/api/health'), true);
assert.equal(isHealthPath('/api/search'), false);

assert.equal(isAttestablePath('/api/search'), true);
assert.equal(isAttestablePath('/api/auth/login'), false);
assert.equal(isAttestablePath('/api/health'), false);
assert.equal(isAttestablePath('/reader'), false);

assert.equal(requestScopeFromPath({ pathname: '/', clientIp: '66.249.66.70' }), 'page_view');
assert.equal(
	requestScopeFromPath({
		pathname: '/',
		clientIp: '127.0.0.1',
		userAgent: 'Go-http-client/1.1'
	}),
	'page_view'
);
assert.equal(requestScopeFromPath({ pathname: '/api/health' }), 'healthcheck');
assert.equal(requestScopeFromPath({ pathname: '/_app/immutable/chunks/app.js' }), 'static_asset');
assert.equal(requestScopeFromPath({ pathname: '/api/search' }), 'search');
assert.equal(requestScopeFromPath({ pathname: '/api/auth/request-token' }), 'unknown_api');

console.log('attestation scope helper checks complete');
