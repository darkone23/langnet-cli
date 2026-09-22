import assert from 'node:assert/strict';
import type { ReadableSpan, SpanExporter } from '@opentelemetry/sdk-trace-base';
import type { ExportResult } from '@opentelemetry/core';
import { ScrubbingSpanExporter, scrubUrlAttribute } from './query-scrub';
import {
	pageViewSpanAttributes,
	rumSessionId,
	vitalSpanAttributes,
	vitalSpanName,
	vitalSpanTiming
} from './rum';

const success: ExportResult = { code: 0 };

function fakeSpan(attributes: Record<string, unknown>): ReadableSpan {
	return { attributes } as unknown as ReadableSpan;
}

function fakeExporterSpy() {
	const exported: ReadableSpan[] = [];
	let shutdowns = 0;
	let flushes = 0;
	const exporter = {
		export: (spans: ReadableSpan[], resultCallback: (result: ExportResult) => void) => {
			exported.push(...spans);
			resultCallback(success);
		},
		shutdown: async () => {
			shutdowns += 1;
			return undefined;
		},
		forceFlush: async () => {
			flushes += 1;
			return undefined;
		}
	} satisfies SpanExporter;
	return { exported, exporter, shutdownCount: () => shutdowns, flushCount: () => flushes };
}

function expectVitalSpanName() {
	assert.equal(vitalSpanName('LCP'), 'web.vital.LCP');
	assert.equal(vitalSpanName('CLS'), 'web.vital.CLS');
}

function expectVitalSpanTiming() {
	const timing = vitalSpanTiming('LCP', 1834, 5000);
	assert.equal(timing.start, 5000 - 1834);
	assert.equal(timing.end, 5000);

	const score = vitalSpanTiming('CLS', 0.07, 5000);
	assert.equal(score.start, 5000);
	assert.equal(score.end, 5000);
}

function expectVitalSpanAttributes() {
	assert.deepEqual(vitalSpanAttributes({ name: 'LCP', value: 1834 }), {
		'web.vital.name': 'LCP',
		'web.vital.value': 1834
	});

	const attributes = vitalSpanAttributes({
		name: 'INP',
		value: 120,
		rating: 'needs-improvement',
		delta: 40,
		id: 'v1:1',
		navigationType: 'navigate'
	});
	assert.equal(attributes['web.vital.rating'], 'needs-improvement');
	assert.equal(attributes['web.vital.delta'], 40);
	assert.equal(attributes['web.vital.id'], 'v1:1');
	assert.equal(attributes['web.vital.navigation_type'], 'navigate');
}

function expectPageViewSpanAttributes() {
	const url = new URL('http://app.example/reader/liar?q=lupus&lang=lat#frame');
	assert.deepEqual(pageViewSpanAttributes('/reader/[slug]', url), {
		'page.route': '/reader/[slug]',
		'page.path': 'http://app.example/reader/liar'
	});

	const unknown = pageViewSpanAttributes(null, new URL('http://app.example/nope'));
	assert.equal('page.route' in unknown, false);
	assert.equal(unknown['page.path'], 'http://app.example/nope');

	const values = Object.values(
		pageViewSpanAttributes('/q', new URL('http://app.example/q?q=personnel-file'))
	);
	assert.equal(
		values.some((value) => String(value).includes('personnel-file')),
		false
	);
}

function expectScrubUrlAttribute() {
	assert.equal(
		scrubUrlAttribute('http://app.example/api/search?q=statira&lang=grc'),
		'http://app.example/api/search'
	);
	assert.equal(scrubUrlAttribute('not a url'), 'not a url');
}

async function expectScrubbingSpanExporter() {
	const spy = fakeExporterSpy();
	const exporter = new ScrubbingSpanExporter(spy.exporter);

	const span = fakeSpan({
		'http.url': 'http://app.example/api/search?q=secret-term',
		'session.id': 'abc'
	});
	exporter.export([span], () => undefined);
	assert.equal(spy.exported.length, 1);
	assert.equal(spy.exported[0].attributes['http.url'], 'http://app.example/api/search');
	assert.equal(spy.exported[0].attributes['session.id'], 'abc');
	assert.equal(span.attributes['http.url'], 'http://app.example/api/search?q=secret-term');

	const untouched = fakeSpan({ 'session.id': 'abc' });
	exporter.export([untouched], () => undefined);
	assert.equal(spy.exported[1], untouched);

	await exporter.shutdown();
	await exporter.forceFlush();
	assert.equal(spy.shutdownCount(), 1);
	assert.equal(spy.flushCount(), 1);
}

function expectRumSessionId() {
	assert.ok(rumSessionId().length > 0);
}

expectVitalSpanName();
expectVitalSpanTiming();
expectVitalSpanAttributes();
expectPageViewSpanAttributes();
expectScrubUrlAttribute();
await expectScrubbingSpanExporter();
expectRumSessionId();
console.log('rum: all assertions passed');
