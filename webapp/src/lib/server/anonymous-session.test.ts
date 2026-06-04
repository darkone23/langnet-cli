import { strict as assert } from 'node:assert';
import type { Cookies } from '@sveltejs/kit';
import {
	createAnonymousSessionId,
	getOrCreateAnonymousSession,
	validAnonymousSessionId
} from './anonymous-session';

type TestCookies = Pick<Cookies, 'get' | 'set'> & {
	values: Record<string, string>;
	get: (name: string) => string | undefined;
	set: (name: string, value: string, _options: object) => void;
};

function makeCookies(initial: Record<string, string> = {}): TestCookies {
	return {
		values: { ...initial },
		get: function (name: string) {
			return this.values[name];
		},
		set: function (name: string, value: string, options: object) {
			assert.equal(typeof name, 'string');
			assert.equal(typeof value, 'string');
			assert.equal((options as { path?: string }).path, '/');
			assert.equal((options as { sameSite?: string }).sameSite, 'lax');
			assert.equal((options as { httpOnly?: boolean }).httpOnly, true);
			const secure = (options as { secure?: boolean }).secure;
			assert.equal(typeof secure, 'boolean');
			this.values[name] = value;
		}
	};
}

const sample = createAnonymousSessionId();
assert.equal(sample.length, 32);
assert.equal(validAnonymousSessionId(sample), true);
assert.equal(validAnonymousSessionId('bad'), false);

const cookiesWithExisting = makeCookies({
	ln_anon: sample
});
const existingSession = getOrCreateAnonymousSession(cookiesWithExisting as unknown as Cookies);
assert.equal(existingSession.id, sample);
assert.equal(existingSession.isNew, false);
assert.equal(existingSession.cookieName, 'ln_anon');

const invalidCookies = makeCookies({
	ln_anon: '***not-valid***'
});
const replacedSession = getOrCreateAnonymousSession(invalidCookies as unknown as Cookies);
assert.equal(replacedSession.isNew, true);
assert.equal(replacedSession.id.length, 32);
assert.equal(invalidCookies.values.ln_anon, replacedSession.id);

const missingCookies = makeCookies();
const newSession = getOrCreateAnonymousSession(missingCookies as unknown as Cookies, {
	cookieName: 'alt_anon',
	secure: false,
	maxAgeSeconds: 30
});
assert.equal(newSession.cookieName, 'alt_anon');
assert.equal(newSession.isNew, true);
assert.equal(missingCookies.values.alt_anon.length, 32);

console.log('anonymous session helper checks complete');
