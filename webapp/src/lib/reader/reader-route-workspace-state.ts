import type { ReaderRouteWorkspaceState } from './reader-route-workspace';

type ReaderRouteStateBinding<T> = {
	get: () => T;
	set: (next: T) => void;
};

const defineWorkspaceBinding = <T>(
	state: ReaderRouteWorkspaceState,
	key: string,
	binding: ReaderRouteStateBinding<T>
) => {
	Object.defineProperty(state, key, {
		get: binding.get,
		set: (next: unknown) => binding.set(next as T),
		configurable: true,
		enumerable: true
	});
};

export function createReaderRouteWorkspaceState(
	bindings: Record<string, unknown>
): ReaderRouteWorkspaceState {
	const workspaceState: ReaderRouteWorkspaceState = {};

	for (const key of Object.keys(bindings)) {
		const binding = bindings[key];
		defineWorkspaceBinding(workspaceState, key, binding as ReaderRouteStateBinding<unknown>);
	}

	return workspaceState;
}

export function readerRouteWorkspaceBinding<T>(
	get: () => T,
	set: (next: T) => void
): ReaderRouteStateBinding<T> {
	return { get, set };
}
