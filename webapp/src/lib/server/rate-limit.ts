import type { ClientClass } from './client-classification';
import type { RequestCost } from './request-cost';
import type { RequestScope } from '$lib/attestation-scope';

export type RateLimitMode = 'observe' | 'enforce';

export type RateLimitKeyType = 'anonymous_session' | 'client_ip';

export type RateLimitDecision = {
	mode: RateLimitMode;
	wouldLimit: boolean;
	keyType: RateLimitKeyType;
	bucket: string;
	limit: number;
	remaining: number;
	used: number;
	windowSeconds: number;
};

export type RateLimitInput = {
	clientClass: ClientClass;
	requestCost: RequestCost;
	attestationScope?: string;
	requestScope?: RequestScope;
	anonymousSessionId?: string;
	clientIp?: string;
	mode?: RateLimitMode;
	windowSeconds?: number;
	nowSeconds?: number;
};

type BucketState = {
	windowStart: number;
	used: number;
};

const defaultRateLimitWindowSeconds = 60;
const defaultMode: RateLimitMode = 'observe';
const mode = normalizeMode(process.env.LANGNET_RATE_LIMIT_MODE);

const decisionStateByWindow = new Map<string, BucketState>();

const limits = {
	trusted_web_session: 300,
	anonymous_unattested: 80,
	suspicious: 10
} satisfies Record<ClientClass, number>;

export function getRateLimitDecision(input: RateLimitInput): RateLimitDecision {
	const normalizedMode = input.mode ?? mode;
	const requestCostValue = Number(input.requestCost?.score);
	const requestCost = Math.max(1, Number.isFinite(requestCostValue) ? requestCostValue : 1);
	const bucketScope = input.requestScope ?? input.attestationScope ?? 'unknown_api';
	const bucket = `${input.clientClass}:${bucketScope}`;
	const nowSeconds = input.nowSeconds ?? Math.floor(Date.now() / 1000);
	const configuredWindowSeconds = input.windowSeconds ?? defaultRateLimitWindowSeconds;
	const windowSeconds = configuredWindowSeconds > 0 ? configuredWindowSeconds : defaultRateLimitWindowSeconds;
	const keyType = input.anonymousSessionId ? 'anonymous_session' : 'client_ip';
	const principalKey = input.anonymousSessionId ?? input.clientIp ?? 'unknown';
	const stateKey = `${bucket}|${keyType}|${principalKey}`;
	const limit = limits[input.clientClass] ?? limits.anonymous_unattested;
	const existing = decisionStateByWindow.get(stateKey);
	let state: BucketState;
	if (!existing || nowSeconds - existing.windowStart >= windowSeconds) {
		state = { windowStart: nowSeconds, used: 0 };
	} else {
		state = { ...existing };
	}

	const projectedUsed = state.used + requestCost;
	const wouldLimit = projectedUsed > limit;
	state.used = projectedUsed;
	const remaining = Math.max(0, limit - state.used);
	decisionStateByWindow.set(stateKey, state);

	return {
		mode: normalizedMode,
		wouldLimit,
		keyType,
		bucket,
		limit,
		remaining,
		used: state.used,
		windowSeconds
	};
}

export function clearRateLimitForTests() {
	decisionStateByWindow.clear();
}

function normalizeMode(value?: string): RateLimitMode {
	const normalized = value?.trim().toLowerCase();
	return normalized === 'observe' || normalized === 'enforce' ? normalized : defaultMode;
}
