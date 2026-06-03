import { strict as assert } from 'node:assert';

import { createDeskLoadingTimers, deskActivityItems, type DeskActivityKey } from './desk-activity';

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

{
	const items = deskActivityItems({
		active: {
			wordIndex: true,
			lookup: true,
			motd: true,
			paradigm: false,
			translation: false,
			wordIndexSections: false
		},
		elapsed: {
			lookup: 3,
			wordIndex: 1,
			motd: 8
		}
	});

	assert.deepEqual(
		items.map((item) => [item.key, item.label, item.elapsedSeconds]),
		[
			['lookup', 'Lookup', 3],
			['wordIndex', 'Word wheel', 1],
			['motd', 'Margin note', 8]
		]
	);
	assert.equal(items[0]?.detail, 'Dictionary and morphology sources');
}

{
	const emissions: Array<[DeskActivityKey, number]> = [];
	const fake = createFakeScheduler();
	const timers = createDeskLoadingTimers((kind, seconds) => {
		emissions.push([kind, seconds]);
	}, fake.scheduler);

	timers.start('lookup');
	assert.deepEqual(emissions, [['lookup', 0]]);
	assert.deepEqual(fake.intervals, [1_000]);
	assert.equal(timers.isRunning('lookup'), true);

	fake.setNow(4_250);
	fake.callbacks.get(1)?.();
	assert.deepEqual(emissions, [
		['lookup', 0],
		['lookup', 3]
	]);

	timers.start('lookup');
	assert.deepEqual(fake.cleared, [1]);
	assert.deepEqual(emissions.at(-1), ['lookup', 0]);

	timers.start('translation');
	timers.stopAll();
	assert.deepEqual(fake.cleared, [1, 2, 3]);
	assert.equal(timers.isRunning('lookup'), false);
	assert.equal(timers.isRunning('translation'), false);
}
