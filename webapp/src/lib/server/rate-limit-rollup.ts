import type { RequestScope } from '$lib/attestation-scope';
import { upsertRateLimitRollups } from './rate-limit-rollup-duckdb';
import type { AttestationStatus } from './client-attestation';
import type { ClientClass } from './client-classification';
import type { RateLimitDecision, RateLimitKeyType } from './rate-limit';
import { createHmac } from 'node:crypto';

export type RateLimitRollup = {
	minuteWindowStartEpochSeconds: number;
	clientClass: ClientClass;
	attestationStatus: AttestationStatus;
	attestationScope: RequestScope;
	rateLimitBucket: string;
	keyType: RateLimitKeyType;
	keyHash: string;
	requestCount: number;
	costSum: number;
	wouldLimitCount: number;
	validAttestationCount: number;
	missingAttestationCount: number;
	expiredAttestationCount: number;
	status2xxCount: number;
	status4xxCount: number;
	status5xxCount: number;
	secondBits: string;
};

export type RateLimitObservation = RateLimitRollup;

export type RateLimitObservationInput = {
	observedAtEpochSeconds?: number;
	status: number;
	requestCost: number;
	clientClass: ClientClass;
	attestationStatus: AttestationStatus;
	attestationScope: RequestScope;
	rateLimitDecision: RateLimitDecision;
	keyType: RateLimitKeyType;
	principal: string;
	minuteWindowSeconds?: number;
};

type RollupMap = Map<string, RateLimitRollup>;

type FlushingPromise = Promise<void>;

const rollupStateByKey: RollupMap = new Map();
const minutesInWindow = 60;
const defaultFlushIntervalMs = 2500;
const autoFlushMs = Number(process.env.LANGNET_RATE_LIMIT_ROLLUP_FLUSH_MS ?? defaultFlushIntervalMs);
const autoFlushEnabled = process.env.NODE_ENV !== 'test' && process.env.LANGNET_RATE_LIMIT_ROLLUP_AUTOSYNC !== '0';

let flushPromise: FlushingPromise | null = null;
let flushTimer: ReturnType<typeof setTimeout> | null = null;

export function buildRateLimitObservation(input: RateLimitObservationInput): RateLimitObservation {
	const observedAtEpochSeconds = input.observedAtEpochSeconds ?? Math.floor(Date.now() / 1000);
	const configuredWindowSeconds = input.minuteWindowSeconds ?? minutesInWindow;
	const normalizedWindowSeconds = configuredWindowSeconds > 0 ? configuredWindowSeconds : minutesInWindow;
	const secondInWindow = observedAtEpochSeconds % normalizedWindowSeconds;
	const minuteWindowStartEpochSeconds =
		Math.floor(observedAtEpochSeconds / normalizedWindowSeconds) * normalizedWindowSeconds;
	const statusBuckets = statusBucketCounts(input.status);

	return {
		minuteWindowStartEpochSeconds,
		clientClass: input.clientClass,
		attestationStatus: input.attestationStatus,
		attestationScope: input.attestationScope,
		rateLimitBucket: input.rateLimitDecision.bucket,
		keyType: input.keyType,
		keyHash: hashPrincipal(input.principal),
		requestCount: 1,
		costSum: input.requestCost,
		wouldLimitCount: input.rateLimitDecision.wouldLimit ? 1 : 0,
		validAttestationCount: input.attestationStatus === 'valid' ? 1 : 0,
		missingAttestationCount: input.attestationStatus === 'missing' ? 1 : 0,
		expiredAttestationCount: input.attestationStatus === 'expired' ? 1 : 0,
		status2xxCount: statusBuckets.status2xx,
		status4xxCount: statusBuckets.status4xx,
		status5xxCount: statusBuckets.status5xx,
		secondBits: setBitInWindow(0n, secondInWindow).toString()
	};
}

export function observeRateLimitRequest(input: RateLimitObservationInput) {
	const observation = buildRateLimitObservation(input);
	const key = buildRollupKey(observation);
	const existing = rollupStateByKey.get(key);

	if (!existing) {
		rllSetRollup({ ...observation });
		scheduleAutoFlush();
		return;
	}

	existing.requestCount += observation.requestCount;
	existing.costSum += observation.costSum;
	existing.wouldLimitCount += observation.wouldLimitCount;
	existing.validAttestationCount += observation.validAttestationCount;
	existing.missingAttestationCount += observation.missingAttestationCount;
	existing.expiredAttestationCount += observation.expiredAttestationCount;
	existing.status2xxCount += observation.status2xxCount;
	existing.status4xxCount += observation.status4xxCount;
	existing.status5xxCount += observation.status5xxCount;
	existing.secondBits = (BigInt(existing.secondBits) | BigInt(observation.secondBits)).toString();
	scheduleAutoFlush();
}

export async function flushRateLimitRollups(): Promise<void> {
	if (flushPromise) return flushPromise;
	if (rollupStateByKey.size === 0) return Promise.resolve();

	const pending = new Map(rollupStateByKey);
	rllClearState();

	flushPromise = upsertRateLimitRollups([...pending.values()])
		.catch((error) => {
			for (const row of pending.values()) {
				rllMergeIntoState(row);
			}
			throw error;
		})
		.finally(() => {
			flushPromise = null;
		});

	return flushPromise;
}

export function clearRateLimitRollupsForTests() {
	rllClearState();
}

export function getRateLimitRollupsForTests(): RateLimitRollup[] {
	return [...rollupStateByKey.values()].map((rollup) => ({ ...rollup }));
}

export function hashPrincipal(principal: string, secretOverride?: string) {
	const secret = secretOverride ?? rateLimitHashSecret();
	return createHmac('sha256', secret).update(principal).digest('hex').slice(0, 24);
}

function rllSetRollup(rollup: RateLimitRollup) {
	rollupStateByKey.set(buildRollupKey(rollup), { ...rollup });
}

function rllClearState() {
	rollupStateByKey.clear();
}

function rllMergeIntoState(rollup: RateLimitRollup) {
	const existing = rollupStateByKey.get(buildRollupKey(rollup));
	if (!existing) {
		rllSetRollup(rollup);
		return;
	}

	existing.requestCount += rollup.requestCount;
	existing.costSum += rollup.costSum;
	existing.wouldLimitCount += rollup.wouldLimitCount;
	existing.validAttestationCount += rollup.validAttestationCount;
	existing.missingAttestationCount += rollup.missingAttestationCount;
	existing.expiredAttestationCount += rollup.expiredAttestationCount;
	existing.status2xxCount += rollup.status2xxCount;
	existing.status4xxCount += rollup.status4xxCount;
	existing.status5xxCount += rollup.status5xxCount;
	existing.secondBits = (BigInt(existing.secondBits) | BigInt(rollup.secondBits)).toString();
}

function buildRollupKey(observation: RateLimitObservation): string {
	return [
		observation.minuteWindowStartEpochSeconds,
		observation.clientClass,
		observation.attestationStatus,
		observation.attestationScope,
		observation.rateLimitBucket,
		observation.keyType,
		observation.keyHash
	].join('|');
}

function setBitInWindow(bits: bigint, secondInMinute: number): bigint {
	const safeSecond = Number.isFinite(secondInMinute) ? Math.floor(secondInMinute) : 0;
	if (safeSecond < 0 || safeSecond >= minutesInWindow) return bits;
	return bits | (1n << BigInt(safeSecond));
}

function statusBucketCounts(status: number) {
	if (status >= 200 && status < 300) {
		return { status2xx: 1, status4xx: 0, status5xx: 0 };
	}
	if (status >= 400 && status < 500) {
		return { status2xx: 0, status4xx: 1, status5xx: 0 };
	}
	if (status >= 500 && status < 600) {
		return { status2xx: 0, status4xx: 0, status5xx: 1 };
	}
	return { status2xx: 0, status4xx: 0, status5xx: 0 };
}

function scheduleAutoFlush() {
	if (!autoFlushEnabled) return;
	if (flushTimer) return;

	const delayMs = Number.isFinite(autoFlushMs) && autoFlushMs > 0 ? autoFlushMs : defaultFlushIntervalMs;
	flushTimer = setTimeout(() => {
		flushTimer = null;
		void flushRateLimitRollups().catch(() => {});
	}, delayMs);
}

function rateLimitHashSecret() {
	return (
		process.env.LANGNET_RATE_LIMIT_HASH_SECRET ||
		process.env.LANGNET_CLIENT_ATTESTATION_SECRET ||
		'langnet-rate-limit-hash-dev-fallback'
	);
}
