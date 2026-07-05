import assert from 'node:assert/strict';

import { createDeskTranslationArrivalController } from './desk-translation-arrival-controller';

type TimeoutHandle = ReturnType<typeof globalThis.setTimeout>;

const state = {
	translationArrived: false,
	translationArrivalTimer: null as TimeoutHandle | null
};
const cleared: TimeoutHandle[] = [];
const callbacks: Array<() => void> = [];
let nextHandle = 1;

const controller = createDeskTranslationArrivalController(state, {
	browser: true,
	setTimeout: (callback) => {
		callbacks.push(callback);
		return nextHandle++ as unknown as TimeoutHandle;
	},
	clearTimeout: (handle) => {
		cleared.push(handle);
	}
});

controller.trigger();
assert.equal(state.translationArrived, true);
assert.equal(state.translationArrivalTimer, 1 as unknown as TimeoutHandle);

controller.trigger();
assert.deepEqual(cleared, [1 as unknown as TimeoutHandle]);
assert.equal(state.translationArrived, true);
assert.equal(state.translationArrivalTimer, 2 as unknown as TimeoutHandle);

callbacks.at(-1)?.();
assert.equal(state.translationArrived, false);
assert.equal(state.translationArrivalTimer, null);

controller.trigger();
controller.clear();
assert.equal(state.translationArrived, false);
assert.equal(state.translationArrivalTimer, null);
assert.deepEqual(cleared, [1, 3] as unknown as TimeoutHandle[]);

console.log('desk translation arrival controller checks complete');
