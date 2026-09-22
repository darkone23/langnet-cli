import type { Attributes } from '@opentelemetry/api';
import type { ExportResult } from '@opentelemetry/core';
import type { ReadableSpan, SpanExporter } from '@opentelemetry/sdk-trace-base';

const urlAttributeKeys = new Set([
	'http.url',
	'http.target',
	'url.full',
	'url.original',
	'url.query',
	'url.fragment'
]);

export function scrubUrlAttribute(value: string): string {
	try {
		const url = new URL(value);
		return `${url.origin}${url.pathname}`;
	} catch {
		return value;
	}
}

function scrubSpanAttributes(attributes: ReadableSpan['attributes']): Attributes {
	const scrubbed: Attributes = {};
	let changed = false;
	for (const [key, value] of Object.entries(attributes)) {
		if (urlAttributeKeys.has(key) && typeof value === 'string') {
			const scrubbedValue = scrubUrlAttribute(value);
			if (scrubbedValue !== value) changed = true;
			scrubbed[key] = scrubbedValue;
		} else {
			scrubbed[key] = value;
		}
	}
	return changed ? scrubbed : attributes;
}

export class ScrubbingSpanExporter implements SpanExporter {
	private readonly delegate: SpanExporter;

	constructor(delegate: SpanExporter) {
		this.delegate = delegate;
	}

	export(spans: ReadableSpan[], resultCallback: (result: ExportResult) => void): void {
		const scrubbed = spans.map((span) => {
			const attributes = scrubSpanAttributes(span.attributes);
			if (attributes === span.attributes) return span;
			return { ...span, attributes };
		});
		this.delegate.export(scrubbed, resultCallback);
	}

	shutdown(): Promise<void> {
		return this.delegate.shutdown();
	}

	forceFlush(): Promise<void> {
		return this.delegate.forceFlush?.() ?? Promise.resolve();
	}
}
