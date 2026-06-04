import { strict as assert } from 'node:assert';
import type { Cookies } from '@sveltejs/kit';
import { POST } from '../../routes/api/auth/request-token/+server';

type TestCookies = Pick<Cookies, 'get' | 'set'> & {
	values: Record<string, string>;
	get: (name: string) => string | undefined;
	set: (name: string, value: string, options: object) => void;
};

function makeCookies(initial: Record<string, string> = {}) {
	return {
		values: { ...initial },
		get: function (name: string) {
			return this.values[name];
		},
		set: function (name: string, value: string, _options: object) {
			assert.equal(name, 'ln_anon');
			assert.equal(typeof value, 'string');
			this.values[name] = value;
			return undefined;
		}
	} satisfies TestCookies;
}

function makeRequest(body: string | Record<string, unknown>) {
	const payload = typeof body === 'string' ? body : JSON.stringify(body);
	return new Request('https://example.test/api/auth/request-token', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: payload
	});
}

const malformed = await POST({
	request: makeRequest('not-json'),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
assert.equal(malformed.status, 400);
const malformedBody = (await malformed.json()) as { error?: string };
assert.equal(malformedBody.error, 'Malformed token request body.');

const invalidScope = await POST({
	request: makeRequest({ scope: 'invalid-scope' }),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
assert.equal(invalidScope.status, 400);

const valid = await POST({
	request: makeRequest({ scope: 'search' }),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
assert.equal(valid.status, 200);
const validBody = (await valid.json()) as { token?: string; expires_at?: number; scope?: string };
assert.equal(typeof validBody.token, 'string');
assert.equal(typeof validBody.expires_at, 'number');
assert.equal(validBody.scope, 'search');

const localsWithScope: { tokenScope?: string } = {};
const validWithLocals = await POST({
	request: makeRequest({ scope: 'search' }),
	locals: localsWithScope as Parameters<typeof POST>[0]['locals'],
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
assert.equal(validWithLocals.status, 200);
assert.equal(localsWithScope.tokenScope, 'search');

const legacyValid = await POST({
	request: makeRequest({
		method: 'GET',
		path: '/api/search',
		query: 'q=logos&dictionary=bailly'
	}),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
assert.equal(legacyValid.status, 200);
const legacyBody = (await legacyValid.json()) as { token?: string; expires_at?: number; scope?: string };
assert.equal(legacyBody.scope, 'search');

const missingApi = await POST({
	request: makeRequest({ method: 'GET', path: '/health' }),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
const missingApiBody = (await missingApi.json()) as { error?: string };
assert.equal(missingApi.status, 400);
assert.equal(missingApiBody.error, 'Token requests require /api paths.');

const unknownApi = await POST({
	request: makeRequest({ method: 'GET', path: '/api/foo' }),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
const unknownApiBody = (await unknownApi.json()) as { scope?: string };
assert.equal(unknownApi.status, 200);
assert.equal(unknownApiBody.scope, 'unknown_api');

const authPath = await POST({
	request: makeRequest({ method: 'POST', path: '/api/auth/login' }),
	locals: {},
	cookies: makeCookies()
} as unknown as Parameters<typeof POST>[0]);
const authPathBody = (await authPath.json()) as { error?: string };
assert.equal(authPath.status, 400);
assert.equal(authPathBody.error, 'Token requests cannot be generated for auth endpoints.');

console.log('request-token endpoint checks complete');
