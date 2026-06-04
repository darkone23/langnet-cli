import { strict as assert } from 'node:assert';
import { requestIdentityFromHeaders } from './request-identity';

const cfHeaders = new Headers({
	'cf-connecting-ip': '198.51.100.7',
	'x-forwarded-for': '203.0.113.1, 198.51.100.8',
	'cf-ray': 'ray-id-123',
	'cf-ipcountry': 'US',
	'user-agent': 'Mozilla/5.0 (Testing)',
	referer: 'https://example.test/'
});

assert.deepEqual(requestIdentityFromHeaders(cfHeaders, '127.0.0.1'), {
	clientIp: '198.51.100.7',
	clientIpSource: 'cf-connecting-ip',
	cfConnectingIp: '198.51.100.7',
	cfRay: 'ray-id-123',
	cfCountry: 'US',
	userAgent: 'Mozilla/5.0 (Testing)',
	referer: 'https://example.test/'
});

const proxyHeaders = new Headers({
	'x-forwarded-for': '203.0.113.1, 198.51.100.8',
	'user-agent': '',
	referer: ''
});

assert.deepEqual(requestIdentityFromHeaders(proxyHeaders, '127.0.0.1'), {
	clientIp: '203.0.113.1',
	clientIpSource: 'x-forwarded-for',
	cfConnectingIp: undefined,
	cfRay: undefined,
	cfCountry: undefined,
	userAgent: '',
	referer: ''
});

const noHeaders = new Headers({});
assert.deepEqual(requestIdentityFromHeaders(noHeaders), {
	clientIp: 'unknown',
	clientIpSource: 'unknown',
	cfConnectingIp: undefined,
	cfRay: undefined,
	cfCountry: undefined,
	userAgent: '',
	referer: ''
});

console.log('request identity helper checks complete');
