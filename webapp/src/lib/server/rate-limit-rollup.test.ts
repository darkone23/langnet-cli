import { strict as assert } from 'node:assert';
import { rmSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { resolve } from 'node:path';
import {
	buildRateLimitObservation,
	clearRateLimitRollupsForTests,
	flushRateLimitRollups,
	hashPrincipal,
	getRateLimitRollupsForTests,
	observeRateLimitRequest
} from './rate-limit-rollup';
import type { RateLimitObservationInput } from './rate-limit-rollup';
import type { RateLimitDecision } from './rate-limit';
import type { RequestScope } from '$lib/attestation-scope';
import type { AttestationStatus } from './client-attestation';
import type { ClientClass } from './client-classification';

const scope: RequestScope = 'search';
const dbPath = resolve(process.cwd(), `data/cache/rate-limit-rollup-test-${randomBytes(8).toString('hex')}.duckdb`);

process.env.LANGNET_RATE_LIMIT_ROLLUP_DB_PATH = dbPath;

type RollupInputOverrides = Omit<Partial<RateLimitObservationInput>, 'clientClass' | 'attestationStatus' | 'attestationScope' | 'keyType' | 'principal'>;

type ObservationFactoryInput = {
	clientClass: ClientClass;
	attestationStatus: AttestationStatus;
	attestationScope: RequestScope;
	keyType: 'client_ip' | 'anonymous_session';
	principal: string;
	rateLimitDecision?: RateLimitDecision;
	overrides?: RollupInputOverrides;
};

function makeDecision(clientClass: ClientClass, attestationScope: RequestScope, wouldLimit = false): RateLimitDecision {
	return {
		mode: 'observe',
		wouldLimit,
		keyType: 'client_ip',
		bucket: `${clientClass}:${attestationScope}`,
		limit: 80,
		remaining: 70,
		used: 10,
		windowSeconds: 60
	};
}

function buildInput(input: ObservationFactoryInput): RateLimitObservationInput {
	return {
		status: 200,
		requestCost: 1,
		clientClass: input.clientClass,
		attestationStatus: input.attestationStatus,
		attestationScope: input.attestationScope,
		rateLimitDecision: input.rateLimitDecision ?? makeDecision(input.clientClass, input.attestationScope),
		keyType: input.keyType,
		principal: input.principal,
		...(input.overrides ?? {})
	};
}

clearRateLimitRollupsForTests();

// Hashing tests
{
	const priorHashSecret = process.env.LANGNET_RATE_LIMIT_HASH_SECRET;
	process.env.LANGNET_RATE_LIMIT_HASH_SECRET = 'rate-limit-hash-phase3b';

	const first = buildRateLimitObservation(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: scope,
			keyType: 'anonymous_session',
			principal: 'sso-user-abc'
		})
	);
	const second = buildRateLimitObservation(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: scope,
			keyType: 'anonymous_session',
			principal: 'sso-user-abc'
		})
	);
	const different = buildRateLimitObservation(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: scope,
			keyType: 'anonymous_session',
			principal: 'sso-user-def'
		})
	);

	assert.equal(first.keyHash, second.keyHash);
	assert.equal(first.keyHash, hashPrincipal('sso-user-abc', 'rate-limit-hash-phase3b'));
	assert.equal(first.keyHash === different.keyHash, false);
	assert.equal(first.keyHash.includes('sso-user-abc'), false);

	if (priorHashSecret === undefined) {
		delete process.env.LANGNET_RATE_LIMIT_HASH_SECRET;
	} else {
		process.env.LANGNET_RATE_LIMIT_HASH_SECRET = priorHashSecret;
	}
}

// Bitset tests
{
	clearRateLimitRollupsForTests();
	const second0 = buildRateLimitObservation(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'ip-0',
			overrides: { observedAtEpochSeconds: 3600 }
		})
	);
	assert.equal(BigInt(second0.secondBits) & (1n << 0n), 1n);

	const second59 = buildRateLimitObservation(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'ip-59',
			overrides: { observedAtEpochSeconds: 3659 }
		})
	);
	assert.equal(BigInt(second59.secondBits) & (1n << 59n), 1n << 59n);

	observeRateLimitRequest(
		buildInput({
			clientClass: 'trusted_web_session',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'bitset-combine',
			overrides: {
				status: 200,
				requestCost: 3,
				observedAtEpochSeconds: 7200
			}
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'trusted_web_session',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'bitset-combine',
			overrides: {
				status: 200,
				requestCost: 4,
				observedAtEpochSeconds: 7259,
				minuteWindowSeconds: 60
			}
		})
	);
	const bitsetRows = getRateLimitRollupsForTests();
	const bitsetRow = bitsetRows.find((row) => row.keyHash === hashPrincipal('bitset-combine'));
	assert.equal(Boolean(bitsetRow), true);
	assert.equal(bitsetRow?.requestCount, 2);
	assert.equal(bitsetRow?.costSum, 7);
	const bitset = BigInt(bitsetRow?.secondBits ?? '0');
	assert.equal((bitset & (1n << 0n)) > 0n, true);
	assert.equal((bitset & (1n << 59n)) > 0n, true);
}

// Aggregation dimensions
{
	clearRateLimitRollupsForTests();
	observeRateLimitRequest(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'anon-scope-1',
			overrides: { status: 200, observedAtEpochSeconds: 9000, requestCost: 1 }
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: 'reader',
			keyType: 'client_ip',
			principal: 'anon-scope-1',
			overrides: { status: 200, observedAtEpochSeconds: 9000, requestCost: 1 }
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'trusted_web_session',
			attestationStatus: 'missing',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'anon-scope-1',
			overrides: { status: 200, observedAtEpochSeconds: 9000, requestCost: 1 }
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'anon-scope-2',
			overrides: { status: 200, observedAtEpochSeconds: 9000, requestCost: 1 }
		})
	);

	observeRateLimitRequest(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: 'search',
			keyType: 'client_ip',
			principal: 'anon-scope-1',
			overrides: { status: 200, observedAtEpochSeconds: 9000, requestCost: 2 }
		})
	);
	const rows = getRateLimitRollupsForTests();
	const rowKeyHash1 = hashPrincipal('anon-scope-1');
	const rowKeyHash2 = hashPrincipal('anon-scope-2');
	const searchMissingScope = rows.find(
		(row) => row.clientClass === 'anonymous_unattested' && row.attestationScope === 'search' && row.keyHash === rowKeyHash1 && row.attestationStatus === 'missing'
	);
	const readerMissingScope = rows.find(
		(row) => row.clientClass === 'anonymous_unattested' && row.attestationScope === 'reader' && row.keyHash === rowKeyHash1 && row.attestationStatus === 'missing'
	);
	const trustedSearchMissingScope = rows.find(
		(row) => row.clientClass === 'trusted_web_session' && row.attestationScope === 'search' && row.keyHash === rowKeyHash1
	);
	const anonSearchDifferentKey = rows.find(
		(row) => row.clientClass === 'anonymous_unattested' && row.attestationScope === 'search' && row.keyHash === rowKeyHash2
	);

	assert.equal(rows.length, 4);
	assert.equal(searchMissingScope?.requestCount, 2);
	assert.equal(searchMissingScope?.costSum, 3);
	assert.equal(readerMissingScope?.attestationScope, 'reader');
	assert.equal(Boolean(trustedSearchMissingScope), true);
	assert.equal(Boolean(anonSearchDifferentKey), true);

	observeRateLimitRequest(
		buildInput({
			clientClass: 'anonymous_unattested',
			attestationStatus: 'missing',
			attestationScope: 'page_view',
			keyType: 'client_ip',
			principal: 'page-view-principal',
			overrides: { status: 200, observedAtEpochSeconds: 9000, requestCost: 11 }
		})
	);
	const pageViewScope = getRateLimitRollupsForTests().find(
		(row) => row.attestationScope === 'page_view' && row.keyHash === hashPrincipal('page-view-principal')
	);
	assert.equal(pageViewScope?.costSum, 11);
}

// Status and attestation counters
{
	clearRateLimitRollupsForTests();
	observeRateLimitRequest(
		buildInput({
			clientClass: 'suspicious',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'anonymous_session',
			principal: 'bad-actor',
			overrides: {
				status: 200,
				requestCost: 4,
				rateLimitDecision: makeDecision('suspicious', 'search', false)
			}
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'suspicious',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'anonymous_session',
			principal: 'bad-actor',
			overrides: {
				status: 404,
				requestCost: 5,
				rateLimitDecision: makeDecision('suspicious', 'search', false)
			}
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'suspicious',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'anonymous_session',
			principal: 'bad-actor',
			overrides: {
				status: 503,
				requestCost: 9,
				rateLimitDecision: makeDecision('suspicious', 'search', false)
			}
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'suspicious',
			attestationStatus: 'valid',
			attestationScope: 'search',
			keyType: 'anonymous_session',
			principal: 'bad-actor',
			overrides: {
				status: 200,
				requestCost: 2,
				rateLimitDecision: makeDecision('suspicious', 'search', true)
			}
		})
	);

	const validRow = getRateLimitRollupsForTests().find((row) => row.attestationStatus === 'valid' && row.keyHash === hashPrincipal('bad-actor') && row.clientClass === 'suspicious');
	assert.equal(validRow?.status2xxCount, 2);
	assert.equal(validRow?.status4xxCount, 1);
	assert.equal(validRow?.status5xxCount, 1);
	assert.equal(validRow?.validAttestationCount, 4);
	assert.equal(validRow?.wouldLimitCount, 1);

	observeRateLimitRequest(
		buildInput({
			clientClass: 'suspicious',
			attestationStatus: 'missing',
			attestationScope: 'search',
			keyType: 'anonymous_session',
			principal: 'att-missing',
			overrides: { status: 200, requestCost: 1, rateLimitDecision: makeDecision('suspicious', 'search', false) }
		})
	);
	observeRateLimitRequest(
		buildInput({
			clientClass: 'suspicious',
			attestationStatus: 'expired',
			attestationScope: 'search',
			keyType: 'anonymous_session',
			principal: 'att-expired',
			overrides: { status: 200, requestCost: 1, rateLimitDecision: makeDecision('suspicious', 'search', false) }
		})
	);

	const rows = getRateLimitRollupsForTests();
	const missingRow = rows.find((row) => row.attestationStatus === 'missing' && row.clientClass === 'suspicious' && row.keyHash === hashPrincipal('att-missing'));
	const expiredRow = rows.find((row) => row.attestationStatus === 'expired' && row.clientClass === 'suspicious' && row.keyHash === hashPrincipal('att-expired'));
	assert.equal(missingRow?.missingAttestationCount, 1);
	assert.equal(missingRow?.validAttestationCount, 0);
	assert.equal(expiredRow?.expiredAttestationCount, 1);
	assert.equal(expiredRow?.validAttestationCount, 0);
}

rmSync(dbPath, { force: true });

console.log('rate-limit rollup checks complete');
