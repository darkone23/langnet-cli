export type ReaderLoadingKey =
	| 'shelves'
	| 'library'
	| 'authors'
	| 'textSearch'
	| 'contents'
	| 'segment'
	| 'dossier'
	| 'structure';

type IntervalHandle = ReturnType<typeof globalThis.setInterval>;

type ReaderLoadingTimerScheduler = {
	now: () => number;
	setInterval: (callback: () => void, intervalMs: number) => IntervalHandle;
	clearInterval: (handle: IntervalHandle) => void;
};

const defaultScheduler: ReaderLoadingTimerScheduler = {
	now: () => Date.now(),
	setInterval: globalThis.setInterval.bind(globalThis),
	clearInterval: globalThis.clearInterval.bind(globalThis)
};

export function createReaderLoadingTimers(
	onElapsed: (kind: ReaderLoadingKey, seconds: number) => void,
	scheduler: ReaderLoadingTimerScheduler = defaultScheduler
) {
	const timers = new Map<ReaderLoadingKey, IntervalHandle>();

	function stop(kind: ReaderLoadingKey) {
		const timer = timers.get(kind);
		if (!timer) return;
		scheduler.clearInterval(timer);
		timers.delete(kind);
	}

	return {
		start(kind: ReaderLoadingKey) {
			stop(kind);
			const startedAt = scheduler.now();
			onElapsed(kind, 0);
			timers.set(
				kind,
				scheduler.setInterval(() => {
					onElapsed(kind, Math.floor((scheduler.now() - startedAt) / 1_000));
				}, 1_000)
			);
		},
		stop,
		stopAll() {
			for (const kind of [...timers.keys()]) stop(kind);
		},
		isRunning(kind: ReaderLoadingKey) {
			return timers.has(kind);
		}
	};
}
