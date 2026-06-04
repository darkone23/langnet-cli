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
		path: '/api/search?language=grc&q=zhta',
		status: 200,
		durationMs: 3532.78,
		clientIp: '198.51.100.7',
		clientIpSource: 'x-forwarded-for',
		cfRay: 'ray',
		cfCountry: 'US',
		clientClass: 'trusted_web_session',
		attestationStatus: 'missing',
		requestCostScore: 42,
		language: 'grc',
		dictionary: 'diogenes',
		translation: 'auto',
		queryPresent: true,
		crawlerDisallowedRoute: true,
		crawlerBot: 'googlebot',
		crawlerPolicyReason: 'crawler-disallowed-route',
		attestationScope: 'search',
		requestScope: 'search',
		tokenScope: 'search',
		userAgent: 'Mozilla/5.0 (Linux x86_64)',
		referer: 'https://project-orion.net/?page=1&lang=grc',
		rateLimitDecision: {
			mode: 'observe',
			wouldLimit: true,
			keyType: 'anonymous_session',
			bucket: 'anonymous_unattested:search',
			limit: 80,
			remaining: 42,
			used: 38,
			windowSeconds: 60
		}
	}),
	'event=http_request method=GET path="/api/search?language=grc&q=zhta" status=200 duration_ms=3532.8 client_ip=198.51.100.7 client_ip_source=x-forwarded-for cf_ray=ray cf_country=US client_class=trusted_web_session attestation_status=missing attestation_scope=search request_scope=search token_scope=search request_cost=42 lang=grc dictionary=diogenes translation=auto query=true crawler_disallowed_route=true crawler_bot=googlebot crawler_policy_reason=crawler-disallowed-route ua="Mozilla/5.0 (Linux x86_64)" referer="https://project-orion.net/?page=1&lang=grc" rate_limit_mode=observe rate_limit_would_limit=true rate_limit_key_type=anonymous_session rate_limit_bucket=anonymous_unattested:search rate_limit_limit=80 rate_limit_remaining=42 rate_limit_used=38 rate_limit_window_seconds=60'
);

assert.equal(
	formatHttpRequestLog({
		method: 'POST',
		path: '/api/search?q=nexus',
		status: 504,
		durationMs: 1000,
		clientIp: '198.51.100.7'
	}),
	'event=http_request method=POST path="/api/search?q=nexus" status=504 duration_ms=1000 client_ip=198.51.100.7'
);

const uaNeedsQuoting = formatHttpRequestLog({
	method: 'GET',
	path: '/api/search',
	status: 200,
	durationMs: 12.2,
	userAgent: 'Mozilla/5.0 "Mozilla" Browser',
	referer: 'https://x.example/?a=1&b=2&name="quote"'
});
assert.equal(
	uaNeedsQuoting.includes('ua="Mozilla/5.0 \\"Mozilla\\" Browser"'),
	true
);
assert.equal(
	uaNeedsQuoting.includes('referer="https://x.example/?a=1&b=2&name=\\"quote\\""'),
	true
);

const escaped = formatHttpRequestLog({
	method: 'GET',
	path: '/api/reader',
	status: 200,
	durationMs: 10,
	userAgent: 'Agent \\ path',
	referer: 'https://x.example/path with space'
});
assert.equal(escaped.includes('useragent'), false);
assert.equal(escaped.includes('ua="Agent \\\\ path"'), true);

const omitted = formatHttpRequestLog({
	method: 'GET',
	path: '/reader',
	status: 200,
	durationMs: 1
});
assert.equal(omitted.includes('client_ip='), false);
assert.equal(omitted.includes('referer='), false);
assert.equal(/duration_ms=1\b/.test(omitted), true);
assert.equal(omitted.includes('query='), false);

const booleans = formatHttpRequestLog({
	method: 'GET',
	path: '/reader',
	status: 200,
	durationMs: 1,
	queryPresent: false,
	attestationScope: 'reader',
	requestScope: 'page_view',
	tokenScope: 'search'
});
assert.equal(/\bquery=false\b/.test(booleans), true);
assert.equal(booleans.includes('query="false"'), false);
assert.equal(booleans.includes('attestation_scope=reader'), true);
assert.equal(booleans.includes('request_scope=page_view'), true);
assert.equal(booleans.includes('token_scope=search'), true);

assert.equal(booleans.startsWith('event='), true);
assert.equal(booleans.includes('clientClass='), false);
assert.equal(booleans.includes('requestCost='), false);
assert.equal(booleans.includes('rate_limit_mode='), false);
assert.equal(booleans.includes('rate_limit_limit='), false);

const withRateLimitHeaders = formatHttpRequestLog({
	method: 'GET',
	path: '/api/search',
	status: 200,
	durationMs: 10,
	requestCostScore: 5,
	clientIp: '1.2.3.4',
	clientClass: 'anonymous_unattested',
	rateLimitDecision: {
		mode: 'observe',
		wouldLimit: false,
		keyType: 'client_ip',
		bucket: 'anonymous_unattested:search',
		limit: 80,
		remaining: 75,
		used: 5,
		windowSeconds: 60
	}
});
assert.equal(
	withRateLimitHeaders.includes('rate_limit_would_limit=false'),
	true
);
assert.equal(withRateLimitHeaders.includes('rate_limit_limit=80'), true);
assert.equal(withRateLimitHeaders.includes('rate_limit_key_type=client_ip'), true);
assert.equal(withRateLimitHeaders.includes('rate_limit_window_seconds=60'), true);

console.log('http log helpers ok');
