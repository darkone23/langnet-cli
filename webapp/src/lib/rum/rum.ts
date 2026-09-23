import type { Tracer } from '@opentelemetry/api';
import { ScrubbingSpanExporter } from './query-scrub';

export type RumVitalMetric = {
	name: string;
	value: number;
	rating?: string;
	delta?: number;
	id?: string;
	navigationType?: string;
};

export type RumPageView = { routeId: string | null; url: URL };

export type RumSpanTiming = { start: number; end: number };

const vitalSpanNamePrefix = 'web.vital.';

const vitalsWithElapsedTime = new Set(['LCP', 'FCP', 'TTFB', 'INP']);

const sessionKey = 'langnet-rum-session';

type RumState = {
	started: boolean;
	tracer: Tracer | null;
	pendingPageViews: RumPageView[];
};

const state: RumState = { started: false, tracer: null, pendingPageViews: [] };

export function vitalSpanName(metricName: string): string {
	return `${vitalSpanNamePrefix}${metricName}`;
}

export function vitalSpanTiming(
	metricName: string,
	value: number,
	now: number = performance.now()
): RumSpanTiming {
	if (vitalsWithElapsedTime.has(metricName)) {
		return { start: now - value, end: now };
	}
	return { start: now, end: now };
}

export function vitalSpanAttributes(metric: RumVitalMetric): Record<string, string | number> {
	const attributes: Record<string, string | number> = {
		'web.vital.name': metric.name,
		'web.vital.value': metric.value
	};
	if (metric.rating !== undefined) attributes['web.vital.rating'] = metric.rating;
	if (metric.delta !== undefined) attributes['web.vital.delta'] = metric.delta;
	if (metric.id !== undefined) attributes['web.vital.id'] = metric.id;
	if (metric.navigationType !== undefined) {
		attributes['web.vital.navigation_type'] = metric.navigationType;
	}
	return attributes;
}

export function pageViewSpanAttributes(routeId: string | null, url: URL): Record<string, string> {
	const attributes: Record<string, string> = {
		'page.path': `${url.origin}${url.pathname}`
	};
	if (routeId !== null) attributes['page.route'] = routeId;
	return attributes;
}

export function rumSessionId(): string {
	try {
		const existing = sessionStorage.getItem(sessionKey);
		if (existing !== null) return existing;
		const id = crypto.randomUUID();
		sessionStorage.setItem(sessionKey, id);
		return id;
	} catch {
		return 'anonymous';
	}
}

export function trackPageView(routeId: string | null, url: URL | null): void {
	if (typeof window === 'undefined' || url === null) return;
	const tracer = state.tracer;
	if (state.started && tracer !== null) {
		emitPageView(tracer, routeId, url);
		return;
	}
	state.pendingPageViews.push({ routeId, url });
}

export async function startRum(): Promise<void> {
	if (typeof window === 'undefined' || state.started) return;
	state.started = true;
	try {
		const [
			{ WebTracerProvider, BatchSpanProcessor },
			{ OTLPTraceExporter },
			{ registerInstrumentations },
			{ DocumentLoadInstrumentation },
			{ FetchInstrumentation },
			{ UserInteractionInstrumentation },
			{ resourceFromAttributes },
			webVitals
		] = await Promise.all([
			import('@opentelemetry/sdk-trace-web'),
			import('@opentelemetry/exporter-trace-otlp-http'),
			import('@opentelemetry/instrumentation'),
			import('@opentelemetry/instrumentation-document-load'),
			import('@opentelemetry/instrumentation-fetch'),
			import('@opentelemetry/instrumentation-user-interaction'),
			import('@opentelemetry/resources'),
			import('web-vitals')
		]);

		const exporter = new OTLPTraceExporter({
			url: `${window.location.origin}/api/otel/v1/traces`
		});
		const provider = new WebTracerProvider({
			resource: resourceFromAttributes({
				'service.name': 'langnet_web',
				'session.id': rumSessionId()
			}),
			spanProcessors: [
				new BatchSpanProcessor(new ScrubbingSpanExporter(exporter), {
					scheduledDelayMillis: 5000,
					maxExportBatchSize: 16,
					exportTimeoutMillis: 10_000
				})
			]
		});
		provider.register();

		registerInstrumentations({
			tracerProvider: provider,
			instrumentations: [
				new DocumentLoadInstrumentation(),
				new FetchInstrumentation({ ignoreUrls: [/\/api\/otel\//] }),
				new UserInteractionInstrumentation()
			]
		});

		const tracer = provider.getTracer('langnet-rum');
		state.tracer = tracer;

		registerWebVitals(tracer, webVitals);
		flushPendingPageViews();
		armForceFlushOnHide(provider);
	} catch (error) {
		console.warn('[rum] telemetry disabled', error);
		state.started = false;
	}
}

function flushPendingPageViews(): void {
	const tracer = state.tracer;
	if (tracer === null) return;
	const pending = state.pendingPageViews;
	state.pendingPageViews = [];
	for (const view of pending) {
		emitPageView(tracer, view.routeId, view.url);
	}
}

function emitPageView(tracer: Tracer, routeId: string | null, url: URL): void {
	const span = tracer.startSpan('page.view', {
		attributes: pageViewSpanAttributes(routeId, url)
	});
	span.end();
}

type RumVitalsModule = {
	onCLS: VitalListener;
	onINP: VitalListener;
	onLCP: VitalListener;
	onFCP: VitalListener;
	onTTFB: VitalListener;
};

type VitalListener = (onReport: (metric: RumVitalMetric) => void) => void;

function registerWebVitals(tracer: Tracer, webVitals: RumVitalsModule): void {
	const listeners = [
		webVitals.onCLS,
		webVitals.onINP,
		webVitals.onLCP,
		webVitals.onFCP,
		webVitals.onTTFB
	];
	for (const on of listeners) {
		try {
			on((metric) => emitVital(tracer, metric));
		} catch {
			// A failing vital observer must never break the others.
		}
	}
}

function emitVital(tracer: Tracer, metric: RumVitalMetric): void {
	const timing = vitalSpanTiming(metric.name, metric.value);
	const span = tracer.startSpan(vitalSpanName(metric.name), {
		startTime: timing.start,
		attributes: vitalSpanAttributes(metric)
	});
	span.end(timing.end);
}

function armForceFlushOnHide(provider: { forceFlush: () => Promise<void> }): void {
	const flush = () => {
		void provider.forceFlush().catch(() => undefined);
	};
	document.addEventListener('visibilitychange', () => {
		if (document.visibilityState === 'hidden') flush();
	});
	window.addEventListener('pagehide', flush, { once: true });
}
