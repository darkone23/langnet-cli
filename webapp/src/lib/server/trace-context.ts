// HOL-229: forward W3C trace context from inbound requests to the warm
// langnet_cli server. The webapp emits no spans yet (no OTel JS SDK — that
// is Phase 3 / HOL-226); forwarding `traceparent`/`tracestate`/`baggage`
// is what lets caddy's front span and the langnet_cli server span share
// one trace id, which is the acceptance bar for HOL-229.
//
// SvelteKit route handlers pass typed request objects down to the
// transport (no `Request` reference), so the context rides an
// AsyncLocalStorage instead of threading headers through every surface.
// Scoped in hooks.server.ts via runWithTraceContext, read in langnet-cli.ts
// `runJsonCommandViaServer`.

import { AsyncLocalStorage } from 'node:async_hooks';

const storage = new AsyncLocalStorage<Readonly<Record<string, string>>>();

const TRACE_CONTEXT_HEADERS = ['traceparent', 'tracestate', 'baggage'] as const;

export function runWithTraceContext<T>(headers: Headers, fn: () => T): T {
	const context: Record<string, string> = {};
	for (const name of TRACE_CONTEXT_HEADERS) {
		const value = headers.get(name);
		if (value) context[name] = value;
	}
	// Always run scoped: a request with no trace headers gets an empty
	// store, so nothing can leak in from a concurrent request's context.
	return storage.run(context, fn);
}

export function currentTraceContext(): Readonly<Record<string, string>> | undefined {
	return storage.getStore();
}
