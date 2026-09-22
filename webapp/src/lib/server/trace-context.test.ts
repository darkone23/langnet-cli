import assert from 'node:assert/strict';
import { currentTraceContext, runWithTraceContext } from './trace-context';

const TRACEPARENT_A = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
const TRACEPARENT_B = '00-11111111111111111111111111111111-2222222222222222-01';

// Outside any scope: no store.
assert.equal(currentTraceContext(), undefined);

// Full capture: traceparent + tracestate + baggage.
const inner = runWithTraceContext(
	new Headers({
		traceparent: TRACEPARENT_A,
		tracestate: 'rojo=00f067aa0ba902b7',
		baggage: 'session=42'
	}),
	() => currentTraceContext()
);
assert.equal(inner?.traceparent, TRACEPARENT_A);
assert.equal(inner?.tracestate, 'rojo=00f067aa0ba902b7');
assert.equal(inner?.baggage, 'session=42');

// Scope ends: the store is gone again after runWithTraceContext returns.
assert.equal(currentTraceContext(), undefined);

// Absent headers yield an empty store, not undefined — nothing leaks in
// from any outer scope.
const empty = runWithTraceContext(new Headers({ 'content-type': 'text/plain' }), () =>
	currentTraceContext()
);
assert.deepEqual(empty, {});

// Partial capture: only present headers land in the store.
const partial = runWithTraceContext(new Headers({ traceparent: TRACEPARENT_B }), () =>
	currentTraceContext()
);
assert.equal(partial?.traceparent, TRACEPARENT_B);
assert.equal(partial?.tracestate, undefined);
assert.equal(partial?.baggage, undefined);

// Async continuation keeps the scope alive across awaits.
const awaited = await runWithTraceContext(new Headers({ traceparent: TRACEPARENT_A }), async () => {
	await new Promise((resolve) => setTimeout(resolve, 5));
	return currentTraceContext();
});
assert.equal(awaited?.traceparent, TRACEPARENT_A);

// Nested scopes: the innermost context wins.
const nested = runWithTraceContext(new Headers({ traceparent: TRACEPARENT_A }), () =>
	runWithTraceContext(new Headers({ traceparent: TRACEPARENT_B }), () => currentTraceContext())
);
assert.equal(nested?.traceparent, TRACEPARENT_B);

// After the nested scope returns, the outer context is restored.
const restored = runWithTraceContext(new Headers({ traceparent: TRACEPARENT_A }), () => {
	runWithTraceContext(new Headers({ traceparent: TRACEPARENT_B }), () => undefined);
	return currentTraceContext();
});
assert.equal(restored?.traceparent, TRACEPARENT_A);

console.log('trace-context: all assertions passed');
