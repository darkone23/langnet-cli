import { strict as assert } from 'node:assert';
import { formatHttpRequestLog, httpRequestLoggingEnabled } from './http-log';

assert.equal(httpRequestLoggingEnabled(undefined), false);
assert.equal(httpRequestLoggingEnabled(''), false);
assert.equal(httpRequestLoggingEnabled('0'), false);
assert.equal(httpRequestLoggingEnabled('1'), true);
assert.equal(httpRequestLoggingEnabled('true'), true);
assert.equal(httpRequestLoggingEnabled('yes'), true);

assert.equal(
	formatHttpRequestLog({
		method: 'GET',
		path: '/reader',
		status: 200,
		durationMs: 12.345
	}),
	'[http] GET /reader 200 12.3ms'
);

assert.equal(
	formatHttpRequestLog({
		method: 'POST',
		path: '/api/search?q=nexus',
		status: 504,
		durationMs: 1000
	}),
	'[http] POST /api/search?q=nexus 504 1000.0ms'
);

console.log('http log helpers ok');
