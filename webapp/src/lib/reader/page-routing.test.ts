import { strict as assert } from 'node:assert';

import type { ReaderSegment, ReaderWork } from './index';
import {
	buildCurrentReaderRouteState,
	buildReaderRouteUrlUpdate,
	defaultReaderAddressForLanguage,
	formatReaderAddress,
	readerIsCanonicalRef,
	readerWorkHasContributorMetadata
} from './page-routing';

const republic: ReaderWork = {
	work_id: 'rep',
	collection_id: 'fixture',
	language: 'grc',
	title: 'Republic',
	author: 'Plato',
	author_id: 'plato',
	source_id: 'plato.rep',
	cts_work_urn: 'urn:cts:greekLit:tlg0059.tlg030',
	canonical_text_id: 'urn:ctsv2:greekLit:tlg0059.tlg030',
	canonical_address: 'Republic',
	translator_names: ['Paul Shorey']
};

const segment: ReaderSegment = {
	segment_id: 's1',
	work_id: 'rep',
	edition_id: 'e1',
	segment_kind: 'section',
	citation_path: '10.614b',
	text: 'text',
	sort_key: 614
};

assert.equal(defaultReaderAddressForLanguage('grc'), 'Od. 3.74');
assert.equal(defaultReaderAddressForLanguage('lat'), '');
assert.equal(
	formatReaderAddress('urn:ctsv2:greekLit:tlg0059.tlg030', '10.614b'),
	'urn:ctsv2:greekLit:tlg0059.tlg030?ref=10.614b'
);
assert.equal(formatReaderAddress('Republic', 'Book 10'), 'Republic Book 10');
assert.equal(readerIsCanonicalRef('ctsv2://greekLit/tlg0059.tlg030'), true);
assert.equal(readerIsCanonicalRef('Republic Book 10'), false);
assert.equal(readerWorkHasContributorMetadata(republic), true);
assert.equal(readerWorkHasContributorMetadata({ ...republic, translator_names: [] }), false);

assert.deepEqual(
	buildCurrentReaderRouteState({
		language: 'grc',
		catalogId: 'perseus',
		readerView: 'shelves',
		selectedWork: republic,
		selectedSegment: segment,
		addressInput: 'Od. 3.74',
		showAddressLookup: true,
		workQuery: 'plato',
		textQuery: 'apollo',
		textSearchMode: 'fuzzy',
		textSearchCursorParam: 'text-2',
		discoveryGroup: 'philosophy',
		discoveryTag: 'dialogue',
		discoveryAuthorId: 'plato',
		discoveryAuthorLabel: 'Plato',
		discoverySort: 'global-popularity',
		authorAgentKind: 'person',
		authorHistoricity: 'historical',
		activeAuthorSection: 'Π',
		selectedAuthorId: 'plato',
		routeAuthorId: '',
		routeAuthorName: '',
		authorsCursorParam: 'authors-2',
		worksCursorParam: 'works-2',
		contentsCursorParam: 'contents-2',
		pageCursorParam: 'page-2',
		activeCollection: 'all',
		selectedWord: 'λόγος',
		theme: 'vespers',
		showTransliteration: true
	}),
	{
		language: 'grc',
		catalogId: 'perseus',
		readerView: 'shelves',
		address: undefined,
		query: 'plato',
		textQuery: undefined,
		textSearchMode: undefined,
		textSearchCursor: undefined,
		discoveryGroup: 'philosophy',
		discoveryTag: 'dialogue',
		discoveryAuthorId: 'plato',
		discoveryAuthorLabel: 'Plato',
		discoverySort: 'global-popularity',
		authorAgentKind: undefined,
		authorHistoricity: undefined,
		authorSection: undefined,
		authorId: undefined,
		authorName: undefined,
		authorsCursor: undefined,
		worksCursor: 'works-2',
		contentsCursor: 'contents-2',
		pageCursor: 'page-2',
		collection: 'all',
		work: 'urn:ctsv2:greekLit:tlg0059.tlg030',
		segment: '10.614b',
		selectedWord: 'λόγος',
		theme: 'vespers',
		transliteration: true
	}
);

assert.equal(
	buildCurrentReaderRouteState({
		language: 'grc',
		catalogId: 'perseus',
		readerView: 'search',
		selectedWork: null,
		selectedSegment: null,
		addressInput: 'Od. 3.74',
		showAddressLookup: true,
		workQuery: '',
		textQuery: 'apollo',
		textSearchMode: 'exact',
		textSearchCursorParam: 'next',
		discoveryGroup: '',
		discoveryTag: '',
		discoveryAuthorId: '',
		discoveryAuthorLabel: '',
		discoverySort: 'catalog',
		authorAgentKind: '',
		authorHistoricity: '',
		activeAuthorSection: '',
		selectedAuthorId: null,
		routeAuthorId: '',
		routeAuthorName: '',
		authorsCursorParam: null,
		worksCursorParam: null,
		contentsCursorParam: null,
		pageCursorParam: null,
		activeCollection: 'all',
		selectedWord: '',
		theme: 'manuscript',
		showTransliteration: false
	}).textQuery,
	'apollo'
);

assert.deepEqual(
	buildReaderRouteUrlUpdate({
		currentUrl: '/reader?lang=grc&q=plato&word=logos',
		state: {
			language: 'grc',
			catalogId: 'perseus',
			readerView: 'shelves',
			query: 'plato',
			selectedWord: 'logos',
			theme: 'manuscript'
		},
		overrides: { selectedWord: null, pageCursor: 'next' }
	}),
	'/reader?lang=grc&catalog=perseus&view=shelves&q=plato&page_cursor=next&theme=manuscript'
);

assert.equal(
	buildReaderRouteUrlUpdate({
		currentUrl: '/reader?lang=grc',
		state: { language: 'grc' },
		overrides: {}
	}),
	null
);
