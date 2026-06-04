import { createHmac, timingSafeEqual } from 'node:crypto';
import { attestationScopeFromPath, type AttestationScope } from '$lib/attestation-scope';

export type AttestationStatus =
	| 'valid'
	| 'missing'
	| 'expired'
	| 'future_iat'
	| 'bad_signature'
	| 'scope_mismatch'
	| 'session_mismatch'
	| 'malformed';

export type AttestationPayload = {
	sid: string;
	scope: AttestationScope;
	iat: number;
	exp: number;
};

type LegacyAttestationPayload = {
	sid: string;
	method: string;
	path: string;
	query_hash: string;
	iat: number;
	exp: number;
};

export type AttestationResult = {
	status: AttestationStatus;
	expiresAt?: number;
	payload?: AttestationPayload;
};

type CreateInput = {
	sessionId: string;
	scope: AttestationScope;
	secret?: string;
	ttlSeconds?: number;
	nowSeconds?: number;
};

type VerifyInput = {
	token: string | undefined;
	sessionId: string;
	scope: AttestationScope;
	secret?: string;
	nowSeconds?: number;
};

const defaultTtlSeconds = 300;
const maxFutureIatSkewSeconds = 30;

export function createAttestationToken(input: CreateInput) {
	const nowSeconds = input.nowSeconds ?? Math.floor(Date.now() / 1000);
	const ttlSeconds = input.ttlSeconds ?? defaultTtlSeconds;
	const payload: AttestationPayload = {
		sid: input.sessionId,
		scope: input.scope,
		iat: nowSeconds,
		exp: nowSeconds + ttlSeconds
	};
	const encodedPayload = base64UrlEncode(JSON.stringify(payload));
	const secret = input.secret ?? attestationSecret();
	const signature = hmacSignature(encodedPayload, secret);
	return `${encodedPayload}.${signature}`;
}

export function verifyAttestationToken(input: VerifyInput): AttestationResult {
	if (!input.token) return { status: 'missing' };

	const parts = input.token.split('.');
	if (parts.length !== 2) return { status: 'malformed' };
	const [encodedPayload, encodedSignature] = parts;

	const payload = decodePayload(encodedPayload);
	if (!payload) return { status: 'malformed' };

	const nowSeconds = input.nowSeconds ?? Math.floor(Date.now() / 1000);
	if (payload.iat > nowSeconds + maxFutureIatSkewSeconds) {
		return { status: 'future_iat', payload, expiresAt: payload.exp };
	}
	if (nowSeconds >= payload.exp) return { status: 'expired', payload, expiresAt: payload.exp };

	const secret = input.secret ?? attestationSecret();
	const expectedSignature = hmacSignature(encodedPayload, secret);
	if (!constantTimeEqual(expectedSignature, encodedSignature)) return { status: 'bad_signature' };

	if (payload.sid !== input.sessionId) return { status: 'session_mismatch', payload, expiresAt: payload.exp };
	if (payload.scope !== input.scope) return { status: 'scope_mismatch', payload, expiresAt: payload.exp };

	return {
		status: 'valid',
		payload,
		expiresAt: payload.exp
	};
}

function decodePayload(encodedPayload: string) {
	const decoded = base64UrlDecode(encodedPayload);
	if (!decoded) return undefined;

	try {
		const parsed = JSON.parse(decoded);
		if (isNewPayload(parsed)) return parsed;
		if (!isLegacyPayload(parsed)) return undefined;
		return {
			sid: parsed.sid,
			scope: attestationScopeFromPath(parsed.path),
			iat: parsed.iat,
			exp: parsed.exp
		};
	} catch {
		return undefined;
	}
}

function isNewPayload(value: unknown): value is AttestationPayload {
	return (
		Boolean(value) &&
		typeof value === 'object' &&
		typeof (value as AttestationPayload).sid === 'string' &&
		isAttestationScope((value as AttestationPayload).scope) &&
		typeof (value as AttestationPayload).iat === 'number' &&
		typeof (value as AttestationPayload).exp === 'number'
	);
}

function isLegacyPayload(value: unknown): value is LegacyAttestationPayload {
	return (
		Boolean(value) &&
		typeof value === 'object' &&
		typeof (value as LegacyAttestationPayload).sid === 'string' &&
		typeof (value as LegacyAttestationPayload).method === 'string' &&
		typeof (value as LegacyAttestationPayload).path === 'string' &&
		typeof (value as LegacyAttestationPayload).query_hash === 'string' &&
		typeof (value as LegacyAttestationPayload).iat === 'number' &&
		typeof (value as LegacyAttestationPayload).exp === 'number'
	);
}

function isAttestationScope(value: unknown): value is AttestationScope {
	return (
		value === 'search' ||
		value === 'word_index' ||
		value === 'reader' ||
		value === 'paradigm' ||
		value === 'motd' ||
		value === 'translation_cache' ||
		value === 'encounter_briefing' ||
		value === 'unknown_api'
	);
}

function hmacSignature(message: string, secret: string) {
	const raw = createHmac('sha256', secret).update(message).digest();
	const bytes = raw instanceof Uint8Array ? raw : new Uint8Array(raw as ArrayBuffer);
	return base64UrlEncode(bytes);
}

function attestationSecret() {
	return process.env.LANGNET_CLIENT_ATTESTATION_SECRET || 'langnet-client-attestation-secret';
}

function base64UrlEncode(input: string | ArrayBuffer | Uint8Array) {
	const bytes = typeof input === 'string' ? new TextEncoder().encode(input) : new Uint8Array(input);
	const base64 = Buffer.from(bytes).toString('base64');
	return base64
		.replaceAll('+', '-')
		.replaceAll('/', '_')
		.replace(/=+$/, '');
}

function base64UrlDecode(input: string): string | undefined {
	const sanitized = input.replace(/-/g, '+').replace(/_/g, '/');
	const padded = sanitized + '='.repeat((4 - (sanitized.length % 4)) % 4);
	try {
		return Buffer.from(padded, 'base64').toString();
	} catch {
		return undefined;
	}
}

function constantTimeEqual(expected: string, actual: string) {
	const expectedBytes = new TextEncoder().encode(expected);
	const actualBytes = new TextEncoder().encode(actual);
	if (expectedBytes.length !== actualBytes.length) return false;
	return timingSafeEqual(expectedBytes, actualBytes);
}
