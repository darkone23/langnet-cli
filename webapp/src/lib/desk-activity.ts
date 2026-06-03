export type DeskActivityKey =
	| 'lookup'
	| 'translation'
	| 'wordIndex'
	| 'wordIndexSections'
	| 'motd'
	| 'paradigm';

export type DeskActivityItem = {
	key: DeskActivityKey;
	label: string;
	detail: string;
	elapsedSeconds: number;
};

type DeskActivityState = {
	active: Record<DeskActivityKey, boolean>;
	elapsed: Partial<Record<DeskActivityKey, number>>;
};

type IntervalHandle = ReturnType<typeof globalThis.setInterval>;

type DeskLoadingTimerScheduler = {
	now: () => number;
	setInterval: (callback: () => void, intervalMs: number) => IntervalHandle;
	clearInterval: (handle: IntervalHandle) => void;
};

const activityOrder: DeskActivityKey[] = [
	'lookup',
	'translation',
	'wordIndex',
	'wordIndexSections',
	'motd',
	'paradigm'
];

const activityCopy: Record<DeskActivityKey, { label: string; detail: string }> = {
	lookup: {
		label: 'Lookup',
		detail: 'Dictionary and morphology sources'
	},
	translation: {
		label: 'Reader text',
		detail: 'Translation cache and source rendering'
	},
	wordIndex: {
		label: 'Word wheel',
		detail: 'Lexical neighborhood and anchors'
	},
	wordIndexSections: {
		label: 'Alphabet rail',
		detail: 'Native section headings'
	},
	motd: {
		label: 'Margin note',
		detail: 'Recommended word folio'
	},
	paradigm: {
		label: 'Forms',
		detail: 'Paradigm table retrieval'
	}
};

const defaultScheduler: DeskLoadingTimerScheduler = {
	now: () => Date.now(),
	setInterval: globalThis.setInterval.bind(globalThis),
	clearInterval: globalThis.clearInterval.bind(globalThis)
};

export function deskActivityItems(state: DeskActivityState): DeskActivityItem[] {
	return activityOrder
		.filter((key) => state.active[key])
		.map((key) => ({
			key,
			label: activityCopy[key].label,
			detail: activityCopy[key].detail,
			elapsedSeconds: state.elapsed[key] ?? 0
		}));
}

export function createDeskLoadingTimers(
	onElapsed: (kind: DeskActivityKey, seconds: number) => void,
	scheduler: DeskLoadingTimerScheduler = defaultScheduler
) {
	const timers = new Map<DeskActivityKey, IntervalHandle>();

	function stop(kind: DeskActivityKey) {
		const timer = timers.get(kind);
		if (!timer) return;
		scheduler.clearInterval(timer);
		timers.delete(kind);
	}

	return {
		start(kind: DeskActivityKey) {
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
		isRunning(kind: DeskActivityKey) {
			return timers.has(kind);
		}
	};
}
