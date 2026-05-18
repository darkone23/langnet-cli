export const bootStateStorageKey = 'orion-boot-state:last-ready';
export const bootStateTtlMs = 12 * 60 * 60 * 1000;

export function shouldFastBoot(lastReadyAt: string | null, now = Date.now()) {
	const timestamp = Number(lastReadyAt);
	return Number.isFinite(timestamp) && timestamp > 0 && now - timestamp < bootStateTtlMs;
}
