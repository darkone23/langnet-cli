import { decode, encode } from 'msgpackr';
import { attestationScopeFromPath, isAttestablePath } from './attestation-scope';

export const msgpackContentType = 'application/msgpack';
export const clientAttestationHeader = 'X-LangNet-Client-Attestation';
const attestationSafetyWindowSeconds = 15;

type AttestationCacheEntry = {
	expiresAt: number;
	token: string;
};

const attestationCache = new Map<string, AttestationCacheEntry>();
const attestationInFlight = new Map<string, Promise<string | null>>();

export function serializePayload(payload: unknown) {
	return new Uint8Array(encode(payload));
}

export function deserializePayload<T = unknown>(bytes: Uint8Array | ArrayBuffer): T {
	try {
		const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
		return decode(view) as T;
	} catch (error) {
		const message = error instanceof Error ? error.message : 'unknown decode error';
		throw new Error(`MessagePack decode failed: ${message}`);
	}
}

export function requestAcceptsMsgpack(headers: Headers) {
	const accept = headers.get('accept');
	if (!accept) return false;
	return accept.split(',').some((part) => {
		const [mime, ...parameters] = part.split(';').map((value) => value.trim().toLowerCase());
		if (mime !== msgpackContentType) return false;
		return !parameters.some((parameter) => parameter === 'q=0' || parameter === 'q=0.0');
	});
}

export function payloadAcceptHeaders(headers?: HeadersInit) {
	const next = new Headers(headers);
	next.set('accept', `${msgpackContentType}, application/json`);
	return next;
}

export async function readResponsePayload<T = unknown>(response: Response): Promise<T> {
	const contentType = response.headers.get('content-type')?.split(';')[0]?.trim().toLowerCase();
	if (contentType === msgpackContentType) {
		return deserializePayload<T>(await response.arrayBuffer());
	}
	return (await response.json()) as T;
}

export async function fetchPayload<T = unknown>(input: RequestInfo | URL, init: RequestInit = {}) {
	const headers = new Headers(init.headers);
	if (shouldRequestAttestation(input)) {
		const token = await requestClientAttestation(input);
		if (token) {
			headers.set(clientAttestationHeader, token);
		}
	}

	const response = await fetch(input, {
		...init,
		headers: payloadAcceptHeaders(headers)
	});
	const data = await readResponsePayload<T>(response);
	return { response, data };
}

export function attestationScopeForRequest(input: RequestInfo | URL) {
	const { url, isAbsolute } = coerceUrl(input);
	if (!shouldRequestAttestationWithUrl({ url, isAbsolute })) return null;
	return attestationScopeFromPath(url.pathname);
}

export function attestationCacheKey(scope: string) {
	return `scope:${scope}`;
}

export function clearClientAttestationCacheForTests() {
	attestationCache.clear();
	attestationInFlight.clear();
}

function shouldRequestAttestation(input: RequestInfo | URL) {
	const { url, isAbsolute } = coerceUrl(input);
	return shouldRequestAttestationWithUrl({ url, isAbsolute });
}

function shouldRequestAttestationWithUrl({
	url,
	isAbsolute
}: {
	url: URL;
	isAbsolute: boolean;
}) {
	if (!isAttestablePath(url.pathname)) return false;
	if (url.pathname.startsWith('/api/auth/request-token')) return false;
	return isAbsolute ? isSameOrigin(url) : true;
}

async function requestClientAttestation(input: RequestInfo | URL) {
	const scope = attestationScopeForRequest(input);
	if (!scope) return null;
	const key = attestationCacheKey(scope);
	const nowSeconds = Math.floor(Date.now() / 1000);
	const cached = attestationCache.get(key);
	if (cached && cached.expiresAt > nowSeconds + attestationSafetyWindowSeconds) {
		return cached.token;
	}
	if (cached) {
		attestationCache.delete(key);
	}

	const ongoing = attestationInFlight.get(key);
	if (ongoing) {
		return ongoing;
	}

	const requestPromise = (async () => {
		try {
			const response = await fetch('/api/auth/request-token', {
				method: 'POST',
				headers: {
					accept: `${msgpackContentType}, application/json`,
					'content-type': 'application/json'
				},
				body: JSON.stringify({ scope })
			});
			if (!response.ok) return null;

			const tokenPayload = await response.json();
			const token = tokenPayload?.token;
			const expiresAt = tokenPayload?.expires_at;
			if (typeof token !== 'string' || typeof expiresAt !== 'number' || Number.isNaN(expiresAt)) {
				return null;
			}

			attestationCache.set(key, { token, expiresAt });
			return token;
		} catch {
			return null;
		}
	})()
		.finally(() => {
			attestationInFlight.delete(key);
		});

	attestationInFlight.set(key, requestPromise);
	return requestPromise;
}

function coerceUrl(input: RequestInfo | URL) {
	if (input instanceof URL) {
		return { url: input, isAbsolute: true };
	}
	if (typeof Request !== 'undefined' && input instanceof Request) {
		return { url: new URL(input.url), isAbsolute: true };
	}

	const inputString = String(input);
	const isAbsolute = /^([a-z][a-z0-9+.-]*:)?\/\//i.test(inputString) || /^[a-z][a-z0-9+.-]*:/i.test(inputString);
	return {
		url: new URL(inputString, getCurrentOrigin()),
		isAbsolute
	};
}

function isSameOrigin(url: URL) {
	const currentOrigin = getCurrentOrigin();
	return url.origin === currentOrigin;
}

function getCurrentOrigin() {
	const location = globalThis.location;
	if (location && typeof location === 'object' && typeof location.origin === 'string' && location.origin) {
		return location.origin;
	}
	return 'https://localhost';
}
