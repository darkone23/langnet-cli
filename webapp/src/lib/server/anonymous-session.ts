import { randomBytes } from 'node:crypto';
import type { Cookies } from '@sveltejs/kit';

export const defaultAnonymousSessionCookieName = 'ln_anon';

export type AnonymousSession = {
	id: string;
	isNew: boolean;
	cookieName: string;
};

const defaultMaxAgeSeconds = 24 * 60 * 60;
const defaultSessionIdLength = 16;

const validSessionPattern = /^[A-Za-z0-9_-]{16,}$/;
const runtimeSecureDefault = process.env.NODE_ENV === 'production';

export function validAnonymousSessionId(value: string | undefined): value is string {
	return Boolean(value && validSessionPattern.test(value));
}

export function createAnonymousSessionId() {
	return randomBytes(defaultSessionIdLength).toString('hex');
}

export function getOrCreateAnonymousSession(
	sessionCookies: Cookies,
	options: { secure?: boolean; maxAgeSeconds?: number; cookieName?: string } = {}
): AnonymousSession {
	const cookieName =
		options.cookieName ??
		process.env.LANGNET_ANON_SESSION_COOKIE ??
		defaultAnonymousSessionCookieName;
	const candidate = sessionCookies.get(cookieName);

	if (validAnonymousSessionId(candidate)) {
		return {
			id: candidate,
			isNew: false,
			cookieName
		};
	}

	const sessionId = createAnonymousSessionId();
	sessionCookies.set(cookieName, sessionId, {
		httpOnly: true,
		sameSite: 'lax',
		path: '/',
		maxAge: options.maxAgeSeconds ?? defaultMaxAgeSeconds,
		secure: Boolean(options.secure ?? runtimeSecureDefault)
	});

	return {
		id: sessionId,
		isNew: true,
		cookieName
	};
}
