type TimeoutHandle = ReturnType<typeof globalThis.setTimeout>;

export type DeskTranslationArrivalState = {
	translationArrived: boolean;
	translationArrivalTimer: TimeoutHandle | null;
};

type DeskTranslationArrivalDeps = {
	browser: boolean;
	setTimeout?: (callback: () => void, delayMs: number) => TimeoutHandle;
	clearTimeout?: (handle: TimeoutHandle) => void;
};
type ScheduleTimeout = NonNullable<DeskTranslationArrivalDeps['setTimeout']>;
type ClearScheduledTimeout = NonNullable<DeskTranslationArrivalDeps['clearTimeout']>;

export function createDeskTranslationArrivalController(
	state: DeskTranslationArrivalState,
	deps: DeskTranslationArrivalDeps
) {
	const scheduleTimeout: ScheduleTimeout =
		deps.setTimeout ??
		((callback, delayMs) => globalThis.setTimeout(callback, delayMs) as TimeoutHandle);
	const clearScheduledTimeout: ClearScheduledTimeout =
		deps.clearTimeout ?? ((handle) => globalThis.clearTimeout(handle));

	function clear() {
		state.translationArrived = false;
		if (state.translationArrivalTimer) {
			clearScheduledTimeout(state.translationArrivalTimer);
			state.translationArrivalTimer = null;
		}
	}

	function trigger() {
		if (!deps.browser) return;
		clear();
		state.translationArrived = true;
		state.translationArrivalTimer = scheduleTimeout(() => {
			state.translationArrived = false;
			state.translationArrivalTimer = null;
		}, 1800);
	}

	return {
		clear,
		trigger
	};
}
