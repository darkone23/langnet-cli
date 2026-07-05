import { normalizeParadigmPayload, type ParadigmPayload } from '$lib/paradigm';
import type { ParadigmResolutionCandidate } from '$lib/paradigm-resolution';
import { paradigmPayloadHasForms, paradigmUnavailableMessage } from '$lib/paradigm-ui';
import { paradigmCandidateKey, paradigmRequestUrl } from './desk-paradigm';

export type DeskParadigmState = {
	paradigmPayloads: Record<string, ParadigmPayload>;
	paradigmLoading: Record<string, boolean>;
	paradigmErrors: Record<string, string>;
};

type DeskParadigmControllerDeps = {
	fetchPayload: <T>(url: string) => Promise<{ response: { ok: boolean }; data: T }>;
	indexFailedMessage: string;
};

export function createDeskParadigmController(
	state: DeskParadigmState,
	deps: DeskParadigmControllerDeps
) {
	async function load(candidate: ParadigmResolutionCandidate) {
		const key = paradigmCandidateKey(candidate);
		if (!candidate.paradigm_request || state.paradigmPayloads[key] || state.paradigmLoading[key]) {
			return;
		}

		state.paradigmLoading = { ...state.paradigmLoading, [key]: true };
		state.paradigmErrors = { ...state.paradigmErrors, [key]: '' };

		try {
			const { response, data } = await deps.fetchPayload<ParadigmPayload>(paradigmRequestUrl(candidate));
			const payload = normalizeParadigmPayload(data);
			if (!response.ok || payload?.error) {
				throw new Error(payload?.error ?? deps.indexFailedMessage);
			}
			if (!payload) throw new Error('Paradigm lookup did not return a table.');
			if (!paradigmPayloadHasForms(payload)) throw new Error(paradigmUnavailableMessage(payload));
			state.paradigmPayloads = { ...state.paradigmPayloads, [key]: payload };
		} catch (error) {
			state.paradigmErrors = {
				...state.paradigmErrors,
				[key]: error instanceof Error ? error.message : 'Paradigm lookup failed.'
			};
		} finally {
			state.paradigmLoading = { ...state.paradigmLoading, [key]: false };
		}
	}

	function clear() {
		state.paradigmPayloads = {};
		state.paradigmLoading = {};
		state.paradigmErrors = {};
	}

	return {
		load,
		clear
	};
}
