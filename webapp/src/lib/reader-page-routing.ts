import {
	readerAddressRouteValue,
	readerWorkRef,
	type ReaderRouteState,
	type ReaderSearchMode,
	type ReaderSegment,
	type ReaderWork
} from './reader';
import type { ReaderIndexView } from './reader-index-storage';
import type { LanguageMode } from './search-data';

export type ReaderRouteOverrides = Partial<{
	[K in keyof ReaderRouteState]: ReaderRouteState[K] | null;
}>;

export type CurrentReaderRouteStateInput = {
	language: LanguageMode;
	catalogId: string;
	readerView: ReaderIndexView;
	selectedWork: ReaderWork | null;
	selectedSegment: ReaderSegment | null;
	addressInput: string;
	showAddressLookup: boolean;
	workQuery: string;
	textQuery: string;
	textSearchMode: ReaderSearchMode;
	textSearchCursorParam: string | null;
	discoveryGroup: string;
	discoveryTag: string;
	discoveryAuthorId: string;
	discoveryAuthorLabel: string;
	discoverySort: ReaderRouteState['discoverySort'];
	authorAgentKind: string;
	authorHistoricity: string;
	activeAuthorSection: string;
	selectedAuthorId?: string | null;
	routeAuthorId: string;
	routeAuthorName: string;
	authorsCursorParam: string | null;
	worksCursorParam: string | null;
	contentsCursorParam: string | null;
	pageCursorParam: string | null;
	activeCollection: string;
	selectedWord: string;
	theme: ReaderRouteState['theme'];
	showTransliteration: boolean;
};

export function defaultReaderAddressForLanguage(nextLanguage: LanguageMode) {
	return nextLanguage === 'grc' ? 'Od. 3.74' : '';
}

export function formatReaderAddress(work: string, segment: string) {
	if (work.startsWith('urn:ctsv2:') || work.startsWith('ctsv2://')) {
		return `${work}?ref=${encodeURIComponent(segment)}`;
	}
	return [work, segment].filter(Boolean).join(' ');
}

export function readerIsCanonicalRef(value: string) {
	return (
		value.startsWith('urn:ctsv2:') ||
		value.startsWith('ctsv2://') ||
		value.startsWith('urn:cts:') ||
		value.startsWith('langnet:reader:')
	);
}

export function readerWorkHasContributorMetadata(work: ReaderWork) {
	return Boolean(
		work.translator_names?.length ||
		work.traditional_author_names?.length ||
		work.attributed_author_names?.length ||
		work.metadata_attributions?.length
	);
}

export function buildCurrentReaderRouteState({
	language,
	catalogId,
	readerView,
	selectedWork,
	selectedSegment,
	addressInput,
	showAddressLookup,
	workQuery,
	textQuery,
	textSearchMode,
	textSearchCursorParam,
	discoveryGroup,
	discoveryTag,
	discoveryAuthorId,
	discoveryAuthorLabel,
	discoverySort,
	authorAgentKind,
	authorHistoricity,
	activeAuthorSection,
	selectedAuthorId,
	routeAuthorId,
	routeAuthorName,
	authorsCursorParam,
	worksCursorParam,
	contentsCursorParam,
	pageCursorParam,
	activeCollection,
	selectedWord,
	theme,
	showTransliteration
}: CurrentReaderRouteStateInput): Partial<ReaderRouteState> {
	const work = selectedWork ? readerWorkRef(selectedWork) : selectedSegment?.work_id || undefined;
	const segment = selectedSegment?.citation_path || undefined;
	const address = readerAddressRouteValue({
		addressInput,
		defaultAddress: defaultReaderAddressForLanguage(language),
		hasWork: Boolean(work),
		showAddressLookup
	});

	return {
		language,
		catalogId,
		readerView: readerView === 'choose' ? undefined : readerView,
		address,
		query: readerView === 'shelves' || readerView === 'authors' ? workQuery : undefined,
		textQuery: readerView === 'search' ? textQuery : undefined,
		textSearchMode: readerView === 'search' ? textSearchMode : undefined,
		textSearchCursor: readerView === 'search' ? (textSearchCursorParam ?? undefined) : undefined,
		discoveryGroup: readerView === 'shelves' ? discoveryGroup || undefined : undefined,
		discoveryTag: readerView === 'shelves' ? discoveryTag || undefined : undefined,
		discoveryAuthorId: readerView === 'shelves' ? discoveryAuthorId || undefined : undefined,
		discoveryAuthorLabel: readerView === 'shelves' ? discoveryAuthorLabel || undefined : undefined,
		discoverySort: readerView === 'shelves' ? discoverySort : undefined,
		authorAgentKind: readerView === 'authors' ? authorAgentKind || undefined : undefined,
		authorHistoricity: readerView === 'authors' ? authorHistoricity || undefined : undefined,
		authorSection: readerView === 'authors' ? activeAuthorSection : undefined,
		authorId: readerView === 'authors' ? (selectedAuthorId ?? routeAuthorId) : undefined,
		authorName: readerView === 'authors' ? routeAuthorName || undefined : undefined,
		authorsCursor: readerView === 'authors' ? (authorsCursorParam ?? undefined) : undefined,
		worksCursor: worksCursorParam ?? undefined,
		contentsCursor: contentsCursorParam ?? undefined,
		pageCursor: pageCursorParam ?? undefined,
		collection: activeCollection,
		work,
		segment,
		selectedWord,
		theme,
		transliteration: showTransliteration || undefined
	};
}
