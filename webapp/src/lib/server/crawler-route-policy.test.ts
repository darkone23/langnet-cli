import { strict as assert } from 'node:assert';
import { getCrawlerDisallowedRouteDecision } from './crawler-route-policy';

const googlebotUa =
	'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)';

assert.deepEqual(
	getCrawlerDisallowedRouteDecision({
		pathname: '/api/search',
		search: '',
		clientIp: '66.249.66.1',
		userAgent: googlebotUa
	}),
	{
		block: true,
		botName: 'googlebot',
		reason: 'crawler-disallowed-route'
	}
);

assert.deepEqual(
	getCrawlerDisallowedRouteDecision({
		pathname: '/',
		search: '',
		clientIp: '66.249.66.1',
		userAgent: googlebotUa
	}),
	{ block: false }
);

assert.deepEqual(
	getCrawlerDisallowedRouteDecision({
		pathname: '/api/search',
		search: '',
		clientIp: '203.0.113.5',
		userAgent: googlebotUa
	}),
	{ block: false }
);

assert.deepEqual(
	getCrawlerDisallowedRouteDecision({
		pathname: '/api/search',
		search: '',
		clientIp: '66.249.66.1',
		userAgent: 'curl/8.0'
	}),
	{ block: false }
);

assert.equal(
	getCrawlerDisallowedRouteDecision({
		pathname: '/q',
		search: '?lang=lat&q=vatis',
		clientIp: '66.249.66.1',
		userAgent: googlebotUa
	}).block,
	true
);

assert.equal(
	getCrawlerDisallowedRouteDecision({
		pathname: '/',
		search: '?lang=lat&q=vatis',
		clientIp: '66.249.66.1',
		userAgent: googlebotUa
	}).block,
	true
);

assert.equal(
	getCrawlerDisallowedRouteDecision({
		pathname: '/learn',
		search: '',
		clientIp: '66.249.66.1',
		userAgent: googlebotUa
	}).block,
	false
);

console.log('crawler route policy checks complete');
