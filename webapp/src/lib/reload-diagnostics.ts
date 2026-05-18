export type ReloadDiagnostic = {
	event: 'mount' | 'pageshow' | 'pagehide' | 'visibilitychange';
	href: string;
	at: string;
	visibility: DocumentVisibilityState;
	navigationType: string;
	wasDiscarded: boolean;
	cause: ReloadCause;
	persisted?: boolean;
	msSinceLastMount?: number;
};

export type ReloadCause =
	| 'browser-discard'
	| 'bfcache-restore'
	| 'document-reload'
	| 'document-navigation'
	| 'app-resume';

const storageKey = 'orion-reload-diagnostic:last-mount';

export function installReloadDiagnostics() {
	if (!shouldLogReloadDiagnostics()) return () => undefined;

	logReloadDiagnostic('mount');

	const handlePageShow = (event: PageTransitionEvent) =>
		logReloadDiagnostic('pageshow', { persisted: event.persisted });
	const handlePageHide = (event: PageTransitionEvent) =>
		logReloadDiagnostic('pagehide', { persisted: event.persisted });
	const handleVisibility = () => logReloadDiagnostic('visibilitychange');

	window.addEventListener('pageshow', handlePageShow);
	window.addEventListener('pagehide', handlePageHide);
	document.addEventListener('visibilitychange', handleVisibility);

	return () => {
		window.removeEventListener('pageshow', handlePageShow);
		window.removeEventListener('pagehide', handlePageHide);
		document.removeEventListener('visibilitychange', handleVisibility);
	};
}

export function reloadDiagnosticSnapshot(
	event: ReloadDiagnostic['event'],
	options: { persisted?: boolean; now?: number; lastMountAt?: number | null } = {}
): ReloadDiagnostic {
	const now = options.now ?? Date.now();
	const lastMountAt = options.lastMountAt ?? readLastMountAt();
	const diagnostic: ReloadDiagnostic = {
		event,
		href: window.location.href,
		at: new Date(now).toISOString(),
		visibility: document.visibilityState,
		navigationType: navigationType(),
		wasDiscarded: documentWasDiscarded(),
		cause: diagnoseReloadCause({
			wasDiscarded: documentWasDiscarded(),
			navigationType: navigationType(),
			persisted: options.persisted
		}),
		...(options.persisted !== undefined ? { persisted: options.persisted } : {}),
		...(event === 'mount' && lastMountAt ? { msSinceLastMount: now - lastMountAt } : {})
	};

	if (event === 'mount') writeLastMountAt(now);
	return diagnostic;
}

function logReloadDiagnostic(
	event: ReloadDiagnostic['event'],
	options: { persisted?: boolean } = {}
) {
	const diagnostic = reloadDiagnosticSnapshot(event, options);
	console.info('[orion reload diagnostic]', diagnostic);
}

export function diagnoseReloadCause({
	wasDiscarded,
	navigationType,
	persisted
}: {
	wasDiscarded: boolean;
	navigationType: string;
	persisted?: boolean;
}): ReloadCause {
	if (wasDiscarded) return 'browser-discard';
	if (persisted) return 'bfcache-restore';
	if (navigationType === 'reload') return 'document-reload';
	if (navigationType === 'navigate') return 'document-navigation';
	return 'app-resume';
}

function shouldLogReloadDiagnostics() {
	return (
		import.meta.env.DEV ||
		localStorage.getItem('orion-debug-reloads') === '1' ||
		new URLSearchParams(window.location.search).has('debug_reload')
	);
}

function navigationType() {
	const [entry] = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
	return entry?.type ?? 'unknown';
}

function documentWasDiscarded() {
	return Boolean((document as Document & { wasDiscarded?: boolean }).wasDiscarded);
}

function readLastMountAt() {
	const value = Number(sessionStorage.getItem(storageKey));
	return Number.isFinite(value) && value > 0 ? value : null;
}

function writeLastMountAt(now: number) {
	try {
		sessionStorage.setItem(storageKey, String(now));
	} catch {
		// Diagnostics must not affect the app.
	}
}
