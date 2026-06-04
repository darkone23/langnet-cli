import { strict as assert } from 'node:assert';
import { clearRateLimitForTests, getRateLimitDecision } from './rate-limit';

function makeCost(score: number) {
	return { score, route: '/api/search', dictionary: 'bailly', translation: 'cache', reason: 'test' };
}

clearRateLimitForTests();

const trusted = getRateLimitDecision({
	clientClass: 'trusted_web_session',
	requestCost: makeCost(299),
	attestationScope: 'search',
	anonymousSessionId: 'trusted-sid'
});
assert.equal(trusted.wouldLimit, false);
assert.equal(trusted.limit, 300);

const trustedOver = getRateLimitDecision({
	clientClass: 'trusted_web_session',
	requestCost: makeCost(2),
	attestationScope: 'search',
	anonymousSessionId: 'trusted-sid'
});
assert.equal(trustedOver.wouldLimit, true);
assert.equal(trustedOver.limit, 300);

const anonymous = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(81),
	attestationScope: 'search',
	clientIp: '198.51.100.11'
});
assert.equal(anonymous.limit, 80);
assert.equal(anonymous.wouldLimit, true);

const suspicious = getRateLimitDecision({
	clientClass: 'suspicious',
	requestCost: makeCost(11),
	attestationScope: 'search',
	clientIp: '198.51.100.11'
});
assert.equal(suspicious.limit, 10);
assert.equal(suspicious.wouldLimit, true);
assert.equal(trustedOver.limit > anonymous.limit, true);
assert.equal(anonymous.limit > suspicious.limit, true);

const minimumOne = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(0),
	attestationScope: 'search',
	clientIp: '198.51.100.12'
});
assert.equal(minimumOne.used, 1);

clearRateLimitForTests();

const first = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(30),
	attestationScope: 'search',
	clientIp: '198.51.100.13'
});
const second = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(40),
	attestationScope: 'search',
	clientIp: '198.51.100.13'
});
const third = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(20),
	attestationScope: 'search',
	clientIp: '198.51.100.13'
});
assert.equal(first.wouldLimit, false);
assert.equal(second.wouldLimit, false);
assert.equal(third.wouldLimit, true);
assert.equal(third.used, 90);

const firstWindow = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(40),
	attestationScope: 'search',
	anonymousSessionId: 'anonymous-sid-window',
	clientIp: '198.51.100.14',
	windowSeconds: 60,
	nowSeconds: 0
});
const secondWindow = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(40),
	attestationScope: 'search',
	anonymousSessionId: 'anonymous-sid-window',
	clientIp: '198.51.100.14',
	windowSeconds: 60,
	nowSeconds: 30
});
const resetWindow = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(1),
	attestationScope: 'search',
	anonymousSessionId: 'anonymous-sid-window',
	clientIp: '198.51.100.14',
	windowSeconds: 60,
	nowSeconds: 61
});
assert.equal(firstWindow.used, 40);
assert.equal(secondWindow.used, 80);
assert.equal(resetWindow.used, 1);

clearRateLimitForTests();

const trustedSessionFirst = getRateLimitDecision({
	clientClass: 'trusted_web_session',
	requestCost: makeCost(200),
	attestationScope: 'search',
	anonymousSessionId: 'prefer-session-id',
	clientIp: '198.51.100.101'
});
const trustedSessionSecond = getRateLimitDecision({
	clientClass: 'trusted_web_session',
	requestCost: makeCost(150),
	attestationScope: 'search',
	anonymousSessionId: 'prefer-session-id',
	clientIp: '198.51.100.102'
});
assert.equal(trustedSessionFirst.used, 200);
assert.equal(trustedSessionSecond.used, 350);
assert.equal(trustedSessionSecond.wouldLimit, true);

const ipFallbackFirst = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(50),
	attestationScope: 'search',
	clientIp: '198.51.100.201'
});
const ipFallbackSecond = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(10),
	attestationScope: 'search',
	clientIp: '198.51.100.201'
});
const ipFallbackDifferent = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(10),
	attestationScope: 'search',
	clientIp: '198.51.100.202'
});
assert.equal(ipFallbackSecond.used, 60);
assert.equal(ipFallbackDifferent.used, 10);

const bucketed = getRateLimitDecision({
	clientClass: 'trusted_web_session',
	requestCost: makeCost(1),
	attestationScope: 'search',
	anonymousSessionId: 'secret-session-id-abc123',
	clientIp: '198.51.100.255'
});
assert.equal(bucketed.bucket.includes('secret-session-id-abc123'), false);
assert.equal(bucketed.bucket.includes('198.51.100.255'), false);

const pageView = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(11),
	requestScope: 'page_view',
	anonymousSessionId: 'page-view-session'
});
assert.equal(pageView.bucket, 'anonymous_unattested:page_view');

const healthcheck = getRateLimitDecision({
	clientClass: 'anonymous_unattested',
	requestCost: makeCost(1),
	requestScope: 'healthcheck',
	anonymousSessionId: 'healthcheck-session'
});
assert.equal(healthcheck.bucket, 'anonymous_unattested:healthcheck');

console.log('rate limit checks complete');
