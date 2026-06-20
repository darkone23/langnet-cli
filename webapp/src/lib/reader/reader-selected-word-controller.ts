import { cleanReaderToken } from '$lib/reader';
import type { LanguageMode } from '$lib/search-data';

type ReaderSelectedWordState = Record<string, any>;

type ReaderUrlOverrides = {
	selectedWord?: string | null;
};

type ReaderSelectedWordControllerDeps = {
	updateReaderUrl: (overrides: ReaderUrlOverrides, historyMode?: 'replace' | 'push') => void;
	currentWorkRef: () => string;
	fetchEncounterBriefing: (input: {
		language: LanguageMode;
		token: string;
		generate: boolean;
		signal: AbortSignal;
	}) => Promise<{ response: { ok: boolean }; data: Record<string, unknown> & { error?: string } }>;
	fetchWordContext: (input: {
		catalogId: string;
		language: LanguageMode;
		query: string;
		work: string;
		segment: string | null;
	}) => Promise<{ response: { ok: boolean }; data: Record<string, unknown> & { error?: string } }>;
};

export function createReaderSelectedWordController(
	state: ReaderSelectedWordState,
	deps: ReaderSelectedWordControllerDeps
) {
	let selectedWordBriefingController: AbortController | null = null;
	let selectedWordContextController: AbortController | null = null;

	function abortBriefing() {
		selectedWordBriefingController?.abort();
		selectedWordBriefingController = null;
	}

	function abortContext() {
		selectedWordContextController?.abort();
		selectedWordContextController = null;
	}

	function reset({ clearWord = false }: { clearWord?: boolean } = {}) {
		abortBriefing();
		abortContext();
		if (clearWord) state.selectedWord = '';
		state.selectedWordBriefing = null;
		state.selectedWordBriefingError = '';
		state.selectedWordBriefingLoading = false;
		state.selectedWordBriefingGenerating = false;
		state.selectedWordContext = null;
		state.selectedWordContextError = '';
		state.selectedWordContextLoading = false;
	}

	async function fetchEncounterBriefing(word: string, generate = false) {
		const token = cleanReaderToken(word);
		if (!token) return;
		abortBriefing();
		const controller = new AbortController();
		selectedWordBriefingController = controller;
		state.selectedWordBriefingLoading = true;
		state.selectedWordBriefingGenerating = generate;
		state.selectedWordBriefingError = '';
		if (!generate) state.selectedWordBriefing = null;
		try {
			const { response, data } = await deps.fetchEncounterBriefing({
				language: state.language,
				token,
				generate,
				signal: controller.signal
			});
			if (!response.ok) throw new Error(data.error || 'Encounter briefing failed.');
			if (state.selectedWord === token) state.selectedWordBriefing = data;
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			if (state.selectedWord === token) {
				state.selectedWordBriefingError =
					error instanceof Error ? error.message : 'Encounter briefing failed.';
			}
		} finally {
			if (selectedWordBriefingController === controller) {
				selectedWordBriefingController = null;
				state.selectedWordBriefingLoading = false;
				state.selectedWordBriefingGenerating = false;
			}
		}
	}

	async function fetchWordContext(word: string) {
		const token = cleanReaderToken(word);
		if (!token || !state.catalogId) return;
		abortContext();
		const controller = new AbortController();
		selectedWordContextController = controller;
		state.selectedWordContextLoading = true;
		state.selectedWordContextError = '';
		const work = deps.currentWorkRef();
		const segment = state.selectedSegment?.citation_path ?? null;
		try {
			const { response, data } = await deps.fetchWordContext({
				catalogId: state.catalogId,
				language: state.language,
				query: token,
				work,
				segment
			});
			if (!response.ok) throw new Error(data.error || 'Reader word context failed.');
			if (state.selectedWord === token) state.selectedWordContext = data;
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			if (state.selectedWord === token) {
				state.selectedWordContextError =
					error instanceof Error ? error.message : 'Reader word context failed.';
			}
		} finally {
			if (selectedWordContextController === controller) {
				selectedWordContextController = null;
				state.selectedWordContextLoading = false;
			}
		}
	}

	async function selectToken(text: string) {
		const token = cleanReaderToken(text);
		if (!token) return;
		reset();
		state.selectedWord = token;
		deps.updateReaderUrl({ selectedWord: token }, 'replace');
		await Promise.all([fetchWordContext(token), fetchEncounterBriefing(token)]);
	}

	return {
		fetchEncounterBriefing,
		fetchWordContext,
		selectToken,
		reset
	};
}
