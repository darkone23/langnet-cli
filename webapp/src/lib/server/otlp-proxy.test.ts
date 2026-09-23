import assert from 'node:assert/strict';
import { handleOtlpProxyPost } from './otlp-proxy';
import {
	defaultOtlpUpstreamBase,
	isHttpUrl,
	isOversizedOtlpBody,
	isSameOriginOtlp,
	maxOtlpProxyBodyBytes,
	normalizeOtlpSubPath,
	resolveOtlpUpstream
} from './otlp-upstream';

const envVar = 'OTEL_EXPORTER_OTLP_ENDPOINT';
const originalEnv = process.env[envVar];

function setEnv(value: string | undefined) {
	if (value === undefined) {
		delete process.env[envVar];
	} else {
		process.env[envVar] = value;
	}
}

function withEnv(value: string | undefined, fn: () => void) {
	setEnv(value);
	try {
		fn();
	} finally {
		setEnv(originalEnv);
	}
}

function expectUpstreamResolution() {
	withEnv(undefined, () => {
		assert.deepEqual(resolveOtlpUpstream({}), { enabled: true, base: defaultOtlpUpstreamBase });
	});
	assert.deepEqual(
		resolveOtlpUpstream({ OTEL_EXPORTER_OTLP_ENDPOINT: 'http://collector.lan:4318///' }),
		{
			enabled: true,
			base: 'http://collector.lan:4318'
		}
	);
	assert.equal(resolveOtlpUpstream({ OTEL_EXPORTER_OTLP_ENDPOINT: '  ' }).enabled, false);
	assert.equal(resolveOtlpUpstream({ OTEL_EXPORTER_OTLP_ENDPOINT: 'not-a-url' }).enabled, false);
	assert.equal(resolveOtlpUpstream({ OTEL_EXPORTER_OTLP_ENDPOINT: 'ftp://host' }).enabled, false);
}

function expectHttpUrl() {
	assert.equal(isHttpUrl('http://host:4318'), true);
	assert.equal(isHttpUrl('https://host'), true);
	assert.equal(isHttpUrl('file:///tmp'), false);
	assert.equal(isHttpUrl('host'), false);
}

function expectSubPathAllowlist() {
	assert.equal(normalizeOtlpSubPath('v1/traces'), 'v1/traces');
	assert.equal(normalizeOtlpSubPath('/v1/traces/'), 'v1/traces');
	assert.equal(normalizeOtlpSubPath('v1/metrics'), 'v1/metrics');
	assert.equal(normalizeOtlpSubPath('v1/logs'), null);
	assert.equal(normalizeOtlpSubPath('../admin'), null);
	assert.equal(normalizeOtlpSubPath(''), null);
	assert.equal(normalizeOtlpSubPath(undefined), null);
}

function expectSameOrigin() {
	assert.equal(isSameOriginOtlp('http://app.example', 'http://app.example', 'app.example'), true);
	assert.equal(isSameOriginOtlp('https://app.example', 'http://app.example', 'app.example'), true);
	assert.equal(
		isSameOriginOtlp('http://app.example:44210', 'https://app.example:44210', 'app.example:44210'),
		true
	);
	assert.equal(isSameOriginOtlp('http://evil.example', 'http://app.example', 'app.example'), false);
	assert.equal(
		isSameOriginOtlp('http://evil.example:8', 'http://app.example', 'app.example'),
		false
	);
	assert.equal(isSameOriginOtlp(null, 'http://app.example', 'app.example'), false);
	assert.equal(isSameOriginOtlp('', 'http://app.example', 'app.example'), false);
	assert.equal(isSameOriginOtlp('not a url', 'http://app.example', 'app.example'), false);
}

function expectBodyCap() {
	assert.equal(isOversizedOtlpBody(null, 10), false);
	assert.equal(isOversizedOtlpBody(String(maxOtlpProxyBodyBytes + 1), 0), true);
	assert.equal(isOversizedOtlpBody(null, maxOtlpProxyBodyBytes + 1), true);
	assert.equal(isOversizedOtlpBody(null, maxOtlpProxyBodyBytes), false);
	assert.equal(isOversizedOtlpBody('garbage', 10), false);
}

type FakeEventInput = {
	url: string;
	origin: string | null;
	paramsPath: string;
	body?: BodyInit;
	contentType?: string;
};

function fakeEvent(input: FakeEventInput) {
	const headers = new Headers();
	if (input.origin !== null) headers.set('origin', input.origin);
	if (input.contentType) headers.set('content-type', input.contentType);
	return {
		request: new Request(input.url, { method: 'POST', body: input.body ?? 'x', headers }),
		url: new URL(input.url),
		params: { path: input.paramsPath }
	} as unknown as Parameters<typeof handleOtlpProxyPost>[0];
}

type CapturedFetch = { url: string; init: RequestInit | undefined };
async function withFetchMock(
	impl: (url: string | URL, init?: RequestInit) => Promise<Response>,
	fn: () => Promise<void>
) {
	const originalFetch = globalThis.fetch;
	globalThis.fetch = impl as typeof fetch;
	try {
		await fn();
	} finally {
		globalThis.fetch = originalFetch;
	}
}

async function expectProxyForwarding() {
	const seen: CapturedFetch[] = [];
	await withFetchMock(
		(url: string | URL, init?: RequestInit) => {
			seen.push({ url: String(url), init });
			return Promise.resolve(new Response('{"partialSuccess":{}}', { status: 200 }));
		},
		async () => {
			setEnv('http://collector.lan:4318');
			const response = await handleOtlpProxyPost(
				fakeEvent({
					url: 'http://app.example/api/otel/v1/traces',
					origin: 'http://app.example',
					paramsPath: 'v1/traces',
					body: '{"resourceSpans":[]}',
					contentType: 'application/json'
				})
			);
			assert.equal(response.status, 200);
			assert.equal(await response.text(), '{"partialSuccess":{}}');
			assert.equal(seen.length, 1);
			assert.equal(seen[0].url, 'http://collector.lan:4318/v1/traces');
			const headers = new Headers(seen[0].init?.headers);
			assert.equal(headers.get('content-type'), 'application/json');
			assert.equal(headers.has('cookie'), false);
			assert.equal(headers.has('authorization'), false);
		}
	);
}

async function expectProxyGuards() {
	setEnv(' ');
	const disabled = await handleOtlpProxyPost(
		fakeEvent({
			url: 'http://app.example/api/otel/v1/traces',
			origin: 'http://app.example',
			paramsPath: 'v1/traces'
		})
	);
	assert.equal(disabled.status, 503);

	setEnv('http://collector.lan:4318');
	const badPath = await handleOtlpProxyPost(
		fakeEvent({
			url: 'http://app.example/api/otel/v1/logs',
			origin: 'http://app.example',
			paramsPath: 'v1/logs'
		})
	);
	assert.equal(badPath.status, 404);

	const crossOrigin = await handleOtlpProxyPost(
		fakeEvent({
			url: 'http://app.example/api/otel/v1/traces',
			origin: 'http://evil.example',
			paramsPath: 'v1/traces'
		})
	);
	assert.equal(crossOrigin.status, 403);

	const noOrigin = await handleOtlpProxyPost(
		fakeEvent({
			url: 'http://app.example/api/otel/v1/traces',
			origin: null,
			paramsPath: 'v1/traces'
		})
	);
	assert.equal(noOrigin.status, 403);

	setEnv(originalEnv);
}

async function expectProxyUnreachable() {
	await withFetchMock(
		() => {
			throw new Error('connection refused');
		},
		async () => {
			setEnv('http://collector.lan:4318');
			const response = await handleOtlpProxyPost(
				fakeEvent({
					url: 'http://app.example/api/otel/v1/traces',
					origin: 'http://app.example',
					paramsPath: 'v1/traces'
				})
			);
			assert.equal(response.status, 502);
		}
	);
	setEnv(originalEnv);
}

expectUpstreamResolution();
expectHttpUrl();
expectSubPathAllowlist();
expectSameOrigin();
expectBodyCap();
await expectProxyForwarding();
await expectProxyGuards();
await expectProxyUnreachable();
console.log('otlp-proxy: all assertions passed');
