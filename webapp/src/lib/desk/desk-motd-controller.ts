import { motdItemKeys } from '$lib/motd-cache';
import type { WordRecommendationResult } from '$lib/search-data';
import { normalizeMotdResult } from './desk-motd';

export type DeskMotdState = {
	motd: WordRecommendationResult | null;
	motdStale: boolean;
	motdLoading: boolean;
	motdRefreshing: boolean;
	motdError: string;
};

type DeskMotdControllerDeps = {
	fetchPayload: <T>(
		url: string,
		init?: { signal?: AbortSignal }
	) => Promise<{ response: { ok: boolean }; data: T }>;
	saveMotd: (result: WordRecommendationResult) => void;
	recommendationsFailedMessage: string;
};

export function createDeskMotdController(state: DeskMotdState, deps: DeskMotdControllerDeps) {
	let abortController: AbortController | null = null;
	let requestId = 0;

	async function load(refresh = false) {
		const currentRequestId = ++requestId;
		const showRefreshState = Boolean(state.motd);
		abortController?.abort();
		const controller = new AbortController();
		abortController = controller;
		state.motdLoading = !showRefreshState;
		state.motdRefreshing = showRefreshState;
		state.motdError = '';

		try {
			const params = new URLSearchParams({
				language: 'all',
				count: '1',
				translation: 'cache',
				candidate_source: 'pool',
				timeout_ms: '3000'
			});
			if (refresh || state.motdStale) {
				params.set('refresh', '1');
				const avoid = motdItemKeys(state.motd);
				if (avoid.length) params.set('avoid', avoid.join(','));
			}
			const { response, data: motdPayload } = await deps.fetchPayload<WordRecommendationResult>(
				`/api/motd?${params.toString()}`,
				{ signal: controller.signal }
			);
			const data = normalizeMotdResult(motdPayload);

			if (!response.ok) throw new Error(data.error ?? deps.recommendationsFailedMessage);
			if (!data.items.length) throw new Error(data.error ?? deps.recommendationsFailedMessage);

			if (currentRequestId !== requestId) return;
			state.motd = data;
			state.motdStale = false;
			deps.saveMotd(data);
		} catch (error) {
			if (currentRequestId !== requestId) return;
			if (isAbortError(error)) return;
			state.motdError =
				error instanceof Error ? error.message : deps.recommendationsFailedMessage;
		} finally {
			if (currentRequestId === requestId) {
				state.motdLoading = false;
				state.motdRefreshing = false;
				if (abortController === controller) abortController = null;
			}
		}
	}

	function abort() {
		requestId += 1;
		abortController?.abort();
		abortController = null;
		state.motdLoading = false;
		state.motdRefreshing = false;
	}

	function reset() {
		abort();
		state.motd = null;
		state.motdStale = false;
		state.motdError = '';
	}

	return {
		load,
		abort,
		reset
	};
}

function isAbortError(error: unknown) {
	return error instanceof DOMException
		? error.name === 'AbortError'
		: error instanceof Error && error.name === 'AbortError';
}
