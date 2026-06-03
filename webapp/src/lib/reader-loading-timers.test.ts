import { strict as assert } from 'node:assert';

import { createReaderLoadingTimers, type ReaderLoadingKey } from './reader-loading-timers';

type IntervalHandle = ReturnType<typeof globalThis.setInterval>;

function createFakeScheduler() {
	let now = 1_000;
	let nextHandle = 1;
	const callbacks = new Map<number, () => void>();
	const cleared: number[] = [];
	const intervals: number[] = [];

	return {
		callbacks,
		cleared,
		intervals,
		scheduler: {
			now: () => now,
			setInterval(callback: () => void, intervalMs: number) {
				const handle = nextHandle++;
				callbacks.set(handle, callback);
				intervals.push(intervalMs);
				return handle as unknown as IntervalHandle;
			},
			clearInterval(handle: IntervalHandle) {
				const id = handle as unknown as number;
				cleared.push(id);
				callbacks.delete(id);
			}
		},
		setNow(value: number) {
			now = value;
		}
	};
}

const emissions: Array<[ReaderLoadingKey, number]> = [];
const fake = createFakeScheduler();
const timers = createReaderLoadingTimers((kind, seconds) => {
	emissions.push([kind, seconds]);
}, fake.scheduler);

timers.start('segment');
assert.deepEqual(emissions, [['segment', 0]]);
assert.deepEqual(fake.intervals, [1_000]);
assert.equal(timers.isRunning('segment'), true);

fake.setNow(3_550);
fake.callbacks.get(1)?.();
assert.deepEqual(emissions, [
	['segment', 0],
	['segment', 2]
]);

timers.start('segment');
assert.deepEqual(fake.cleared, [1]);
assert.deepEqual(emissions.at(-1), ['segment', 0]);
assert.equal(timers.isRunning('segment'), true);

timers.start('structure');
assert.equal(timers.isRunning('structure'), true);
timers.stopAll();
assert.deepEqual(fake.cleared, [1, 2, 3]);
assert.equal(timers.isRunning('segment'), false);
assert.equal(timers.isRunning('structure'), false);
