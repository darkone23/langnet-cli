import { deriveReaderPagePagination } from '$lib/reader/page-formatting';
import { readerIsCanonicalRef, readerWorkHasContributorMetadata } from '$lib/reader/page-routing';
import type { ReaderLoadingKey } from '$lib/reader/loading-timers';
import {
	fetchReaderApi,
	readerContentsUrl,
	readerResolveAddressUrl,
	readerShowUrl,
	readerStructureUrl,
	readerWorkDossierUrl,
	readerWorkMetadataUrl
} from '$lib/reader/reader-api';
import { readerWorkRef } from '$lib/reader';
import type { LanguageMode } from '$lib/search-data';
import type {
	ReaderContentsResponse,
	ReaderSegment,
	ReaderShowResponse,
	ReaderStructureNode,
	ReaderWork,
	ReaderWorkDossierResponse,
	ReaderStructureResponse,
	ReaderWorkResponse
} from '$lib/reader';
import type { ReaderHistoryMode } from './reader-route-workspace';
import type { ReaderRouteOverrides } from './page-routing';

type ReaderRouteContentLoaderState = Record<string, unknown>;

type ReaderRouteContentLoaderDeps = {
	readerLoadingTimers: {
		start: (kind: ReaderLoadingKey) => void;
		stop: (kind: ReaderLoadingKey) => void;
	};
	updateReaderUrl: (
		overrides?: ReaderRouteOverrides,
		historyMode?: ReaderHistoryMode
	) => void;
	syncAddressUrl: (work: string, segment: string, historyMode?: ReaderHistoryMode) => void;
	getPageLimit: () => number;
	getPageTextBudget: () => number;
	getPageRadius: () => number;
};

export type ReaderRouteContentLoaders = {
	openWork: (work: ReaderWork) => Promise<void>;
	loadStructure: (work: string) => Promise<void>;
	loadWorkDossier: (work: string) => Promise<void>;
	loadContentsPage: (
		work: string,
		cursor?: string | null,
		historyMode?: ReaderHistoryMode
	) => Promise<void>;
	showSegment: (
		work: string,
		segment: string,
		historyMode?: ReaderHistoryMode
	) => Promise<void>;
	openAddress: (historyMode?: ReaderHistoryMode) => Promise<void>;
	showAddress: (address: string, historyMode?: ReaderHistoryMode) => Promise<void>;
	resolveAddress: (address: string, historyMode?: ReaderHistoryMode) => Promise<void>;
	ensureSelectedWork: (work: string) => Promise<void>;
	loadPageWindow: (work: string, citation: string) => Promise<void>;
};

export function createReaderRouteContentLoaders(
	state: ReaderRouteContentLoaderState,
	deps: ReaderRouteContentLoaderDeps
): ReaderRouteContentLoaders {
	const stateBag = state as Record<string, any>;

	function inferReaderLanguageFromWorkRef(work: string): LanguageMode | undefined {
		if (work.startsWith('urn:ctsv2:lat:')) return 'lat';
		if (work.startsWith('urn:ctsv2:grc:')) return 'grc';
		if (work.startsWith('urn:ctsv2:san:')) return 'san';
		return undefined;
	}

	function applyInferredWorkLanguage(work: string) {
		const inferredLanguage = inferReaderLanguageFromWorkRef(work);
		if (inferredLanguage && inferredLanguage !== stateBag.language) {
			stateBag.language = inferredLanguage;
		}
	}

	function applyResolvedWorkLanguage(work: ReaderWork) {
		stateBag.selectedWork = work;
		if (work.language && work.language !== stateBag.language) {
			stateBag.language = work.language;
		}
	}

	async function openWork(work: ReaderWork) {
		applyResolvedWorkLanguage(work);
		stateBag.selectedSegment = null;
		stateBag.selectedWord = '';
		stateBag.contents = [];
		stateBag.structure = [];
		stateBag.workDossier = null;
		stateBag.contentsError = '';
		stateBag.structureError = '';
		stateBag.dossierError = '';
		stateBag.contentsCursorParam = null;
		stateBag.pageCursorParam = null;
		void Promise.allSettled([loadStructure(readerWorkRef(work)), loadWorkDossier(readerWorkRef(work))]);
		await loadContentsPage(readerWorkRef(work), null, 'push');
	}

	async function loadStructure(work: string) {
		if (!work || !stateBag.catalogId) return;
		stateBag.structureLoading = true;
		stateBag.structureError = '';
		deps.readerLoadingTimers.start('structure');
		try {
			const { response, data } = await fetchReaderApi<ReaderStructureResponse>(
				readerStructureUrl({ catalogId: stateBag.catalogId, language: stateBag.language, work })
			);
			if (!response.ok) throw new Error(data.error || 'Reader structure failed.');
			stateBag.structure = data.items ?? [];
		} catch (error) {
			stateBag.structureError =
				error instanceof Error ? error.message : 'Reader structure failed.';
		} finally {
			stateBag.structureLoading = false;
			deps.readerLoadingTimers.stop('structure');
		}
	}

	async function loadWorkDossier(work: string) {
		if (!work || !stateBag.catalogId) return;
		stateBag.dossierLoading = true;
		stateBag.dossierError = '';
		deps.readerLoadingTimers.start('dossier');
		try {
			const { response, data } = await fetchReaderApi<ReaderWorkDossierResponse>(
				readerWorkDossierUrl({ catalogId: stateBag.catalogId, language: stateBag.language, work })
			);
			if (!response.ok) throw new Error(data.error || 'Reader work dossier failed.');
			stateBag.workDossier = data;
		} catch (error) {
			stateBag.dossierError =
				error instanceof Error ? error.message : 'Reader work dossier failed.';
		} finally {
			stateBag.dossierLoading = false;
			deps.readerLoadingTimers.stop('dossier');
		}
	}

	async function loadContentsPage(
		work: string,
		cursor?: string | null,
		historyMode: ReaderHistoryMode = 'replace'
	) {
		stateBag.contentsLoading = true;
		stateBag.contentsError = '';
		deps.readerLoadingTimers.start('contents');
		try {
			const { response, data } = await fetchReaderApi<ReaderContentsResponse>(
				readerContentsUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					work,
					limit: deps.getPageLimit(),
					charBudget: deps.getPageTextBudget(),
					cursor
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader contents failed.');
			stateBag.contents = data.items;
			stateBag.pageSegments = data.items;
			stateBag.selectedSegment =
				data.items.find((item: ReaderSegment) => item.text && !/^\{.*\}$/u.test(item.text.trim())) ??
				data.items[0] ??
				null;
			stateBag.pageNextCursor = data.pagination?.next_cursor ?? null;
			stateBag.pagePrevCursor = data.pagination?.prev_cursor ?? null;
			stateBag.navigation = { previous: null, next: null };
			stateBag.selectedWord = '';
			stateBag.contentsCursorParam = cursor ?? null;
			stateBag.pageCursorParam = cursor ?? null;
			if (stateBag.selectedSegment) {
				deps.syncAddressUrl(stateBag.selectedSegment.work_id, stateBag.selectedSegment.citation_path, historyMode);
			}
		} catch (error) {
			stateBag.contentsError = error instanceof Error ? error.message : 'Reader contents failed.';
		} finally {
			stateBag.contentsLoading = false;
			deps.readerLoadingTimers.stop('contents');
		}
	}

	async function loadPageWindow(work: string, citation: string) {
		try {
			const { response, data } = await fetchReaderApi<ReaderContentsResponse>(
				readerContentsUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					work,
					around: citation,
					radius: deps.getPageRadius(),
					limit: deps.getPageRadius() * 2 + 1,
					charBudget: deps.getPageTextBudget()
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reader page window failed.');
			stateBag.pageSegments = data.items.length ? data.items : stateBag.selectedSegment ? [stateBag.selectedSegment] : [];
			stateBag.contents = data.items.length ? data.items : stateBag.contents;
			const derivedPagination = deriveReaderPagePagination(
				stateBag.pageSegments,
				deps.getPageLimit()
			);
			stateBag.pageNextCursor = data.pagination?.next_cursor ?? derivedPagination.next;
			stateBag.pagePrevCursor = data.pagination?.prev_cursor ?? derivedPagination.previous;
		} catch {
			stateBag.pageSegments = stateBag.selectedSegment ? [stateBag.selectedSegment] : [];
			stateBag.pageNextCursor = null;
			stateBag.pagePrevCursor = null;
		}
	}

	async function showSegment(
		work: string,
		segment: string,
		historyMode: ReaderHistoryMode = 'replace'
	) {
		applyInferredWorkLanguage(work);
		stateBag.segmentLoading = true;
		deps.readerLoadingTimers.start('segment');
		stateBag.segmentError = '';
		stateBag.selectedWord = '';
		try {
			await ensureSelectedWork(work);
			const selectedWorkRef = stateBag.selectedWork ? readerWorkRef(stateBag.selectedWork) : work;
			const chromeLoads: Promise<void>[] = [];
			if (
				stateBag.selectedWork &&
				!stateBag.structure.some((node: ReaderStructureNode) => node.work_id === stateBag.selectedWork?.work_id)
			) {
				chromeLoads.push(loadStructure(selectedWorkRef));
			}
			if (
				stateBag.selectedWork &&
				stateBag.workDossier?.work?.work_id !== stateBag.selectedWork.work_id
			) {
				chromeLoads.push(loadWorkDossier(selectedWorkRef));
			}
			const showRequest = fetchReaderApi<ReaderShowResponse>(
				readerShowUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					work,
					segment
				})
			);
			const pageWindowRequest = loadPageWindow(selectedWorkRef, segment);
			const { response, data } = await showRequest;
			if (!response.ok) throw new Error(data.error || 'Reader segment failed.');
			stateBag.selectedSegment = data.segment;
			stateBag.navigation = data.navigation ?? { previous: null, next: null };
			await pageWindowRequest;
			stateBag.contentsCursorParam = null;
			stateBag.pageCursorParam = null;
			deps.syncAddressUrl(work, segment, historyMode);
			void Promise.allSettled(chromeLoads);
		} catch (error) {
			stateBag.segmentError = error instanceof Error ? error.message : 'Reader segment failed.';
		} finally {
			stateBag.segmentLoading = false;
			deps.readerLoadingTimers.stop('segment');
		}
	}

	async function openAddress(historyMode: ReaderHistoryMode = 'replace') {
		const address = String(stateBag.addressInput || '').trim();
		if (!address) return;
		deps.updateReaderUrl(
			{
				address,
				work: null,
				segment: null,
				contentsCursor: null,
				pageCursor: null,
				selectedWord: null
			},
			historyMode
		);
		const workSegment = address.match(/^(.+)\s+([^\s]+)$/u);
		if (workSegment && readerIsCanonicalRef(workSegment[1])) {
			await showSegment(workSegment[1], workSegment[2], 'replace');
			return;
		}
		if (readerIsCanonicalRef(address)) {
			await showAddress(address, 'replace');
			return;
		}
		await resolveAddress(address, 'replace');
	}

	async function showAddress(address: string, historyMode: ReaderHistoryMode = 'replace') {
		stateBag.segmentLoading = true;
		deps.readerLoadingTimers.start('segment');
		stateBag.segmentError = '';
		stateBag.selectedWord = '';
		try {
			const { response, data } = await fetchReaderApi<ReaderShowResponse>(
				readerShowUrl({ catalogId: stateBag.catalogId, language: stateBag.language, address })
			);
			if (!response.ok) throw new Error(data.error || 'Reader segment failed.');
			stateBag.selectedSegment = data.segment;
			stateBag.navigation = data.navigation ?? { previous: null, next: null };
			if (data.segment) {
				await ensureSelectedWork(data.segment.work_id);
				await loadPageWindow(data.segment.work_id, data.segment.citation_path);
				stateBag.contentsCursorParam = null;
				stateBag.pageCursorParam = null;
				deps.syncAddressUrl(data.segment.work_id, data.segment.citation_path, historyMode);
			}
		} catch (error) {
			stateBag.segmentError = error instanceof Error ? error.message : 'Reader segment failed.';
		} finally {
			stateBag.segmentLoading = false;
			deps.readerLoadingTimers.stop('segment');
		}
	}

	async function resolveAddress(address: string, historyMode: ReaderHistoryMode = 'replace') {
		stateBag.segmentLoading = true;
		deps.readerLoadingTimers.start('segment');
		stateBag.segmentError = '';
		stateBag.selectedWord = '';
		try {
			const { response, data } = await fetchReaderApi<ReaderShowResponse>(
				readerResolveAddressUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					address
				})
			);
			if (!response.ok) throw new Error(data.error || 'Reference lookup failed.');
			stateBag.selectedSegment = data.segment
				? {
						...data.segment,
						current_divisions: data.current_divisions ?? data.segment.current_divisions
					}
				: null;
			stateBag.navigation = data.navigation ?? { previous: null, next: null };
			if (data.segment) {
				const resolvedWork = data.structure_node?.work_id || data.segment.work_id;
				await ensureSelectedWork(resolvedWork);
				if (data.structure_node && !stateBag.structure.some((node: ReaderStructureNode) => node.work_id === resolvedWork)) {
					await loadStructure(resolvedWork);
				}
				if (
					stateBag.selectedWork &&
					stateBag.workDossier?.work?.work_id !== stateBag.selectedWork.work_id
				) {
					await loadWorkDossier(readerWorkRef(stateBag.selectedWork));
				}
				await loadPageWindow(resolvedWork, data.segment.citation_path);
				stateBag.contentsCursorParam = null;
				stateBag.pageCursorParam = null;
				deps.syncAddressUrl(resolvedWork, data.segment.citation_path, historyMode);
			}
		} catch (error) {
			stateBag.segmentError = error instanceof Error ? error.message : 'Reference lookup failed.';
		} finally {
			stateBag.segmentLoading = false;
			deps.readerLoadingTimers.stop('segment');
		}
	}

	async function ensureSelectedWork(work: string) {
		applyInferredWorkLanguage(work);
		if (
			stateBag.selectedWork &&
			(stateBag.selectedWork.work_id === work ||
				stateBag.selectedWork.cts_work_urn === work ||
				stateBag.selectedWork.canonical_text_id === work ||
				stateBag.selectedWork.canonical_address === work) &&
			readerWorkHasContributorMetadata(stateBag.selectedWork)
		) {
			return;
		}
		try {
			const { response, data } = await fetchReaderApi<ReaderWorkResponse>(
				readerWorkMetadataUrl({
					catalogId: stateBag.catalogId,
					language: stateBag.language,
					work
				})
			);
			if (response.ok && data.item) applyResolvedWorkLanguage(data.item);
		} catch {
			// Work metadata is useful chrome; failure should not block reading.
		}
	}

	return {
		openWork,
		loadStructure,
		loadWorkDossier,
		loadContentsPage,
		showSegment,
		openAddress,
		showAddress,
		resolveAddress,
		ensureSelectedWork,
		loadPageWindow
	};
}
