import { createAttestationToken } from '$lib/server/client-attestation';
import {
	attestationScopeFromPath,
	isAuthPath,
	type AttestationScope
} from '$lib/attestation-scope';
import { getOrCreateAnonymousSession } from '$lib/server/anonymous-session';

type TokenRequestBody = {
	scope?: unknown;
	method?: unknown;
	path?: unknown;
	ttl_seconds?: unknown;
};

const ttlFromInputMaxSeconds = 3_600;
const requestTokenTtlDefaultSeconds = 300;

export async function POST({ request, cookies, locals }) {
	const body = await parseJson(request);
	if (!body) {
		return responseJson({ error: 'Malformed token request body.' }, 400);
	}

	const normalizedScope = normalizeScope(body.scope);
	const hasExplicitScope = Object.prototype.hasOwnProperty.call(body, 'scope');
	if (hasExplicitScope && !normalizedScope) {
		return responseJson({ error: 'Invalid attestation scope.' }, 400);
	}

	let legacyPath: string | null = null;

	if (!normalizedScope) {
		if (typeof body.path !== 'string' || typeof body.method !== 'string') {
			return responseJson({ error: 'Malformed token request body.' }, 400);
		}
		legacyPath = body.path.trim();
		if (!legacyPath.startsWith('/api/')) {
			return responseJson({ error: 'Token requests require /api paths.' }, 400);
		}
		if (isAuthPath(legacyPath)) {
			return responseJson({ error: 'Token requests cannot be generated for auth endpoints.' }, 400);
		}
	}

	let scope: AttestationScope = normalizedScope as AttestationScope;
	if (!scope) {
		if (!legacyPath) {
			return responseJson({ error: 'Malformed token request body.' }, 400);
		}
		const normalizedPath = legacyPath.split('?')[0] ?? '';
		scope = attestationScopeFromPath(normalizedPath);
		if (isAuthPath(normalizedPath)) {
			return responseJson({ error: 'Token requests cannot be generated for auth endpoints.' }, 400);
		}
	}

	if (typeof body.path === 'string' && isAuthPath(body.path.trim())) {
		return responseJson({ error: 'Token requests cannot be generated for auth endpoints.' }, 400);
	}

	const session = locals.anonymousSessionId
		? { id: locals.anonymousSessionId, cookieName: 'ln_anon', isNew: false }
		: getOrCreateAnonymousSession(cookies);
	if (session.isNew) {
		locals.anonymousSessionId = session.id;
	}

	const ttlSeconds = normalizeTtl(body.ttl_seconds);
	locals.tokenScope = scope;
	const token = createAttestationToken({
		sessionId: session.id,
		scope,
		ttlSeconds
	});
	const expiresAt = Math.floor(Date.now() / 1000) + ttlSeconds;
	return responseJson({ token, expires_at: expiresAt, scope });
}

function normalizeTtl(ttlValue: unknown) {
	if (typeof ttlValue === 'number' && Number.isInteger(ttlValue) && ttlValue > 0) {
		return Math.min(ttlFromInputMaxSeconds, ttlValue);
	}
	if (typeof ttlValue === 'string') {
		const parsed = Number.parseInt(ttlValue, 10);
		return Number.isFinite(parsed) && parsed > 0 ? Math.min(ttlFromInputMaxSeconds, parsed) : requestTokenTtlDefaultSeconds;
	}
	return requestTokenTtlDefaultSeconds;
}

function normalizeScope(value: unknown): AttestationScope | undefined {
	if (typeof value !== 'string') return undefined;
	switch (value.trim()) {
		case 'search':
		case 'word_index':
		case 'reader':
		case 'paradigm':
		case 'motd':
		case 'translation_cache':
		case 'encounter_briefing':
		case 'unknown_api':
			return value.trim() as AttestationScope;
		default:
			return undefined;
	}
}

async function parseJson(request: Request) {
	try {
		const body = await request.json();
		if (body && typeof body === 'object') return body as TokenRequestBody;
	} catch {
		return null;
	}
	return null;
}

function responseJson(payload: unknown, status = 200) {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'content-type': 'application/json' }
	});
}
