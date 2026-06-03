import { strict as assert } from 'node:assert';
import type { ReaderDiscoveryShelf, ReaderSearchQueryCandidate, ReaderSegment } from './reader';
import {
	deriveReaderPagePagination,
	readerAuthorSectionRomanHint,
	readerCitationRangeLabel,
	readerDiscoverySummaryLabel,
	readerDiscoveryTitleLabel,
	readerShelfMetaLabel,
	readerTextSearchCandidateLabel,
	readerVisibleTextSearchCandidates,
	readerWorkMetaLine
} from './reader-page-formatting';

const candidates: ReaderSearchQueryCandidate[] = [
	{ kind: 'input', query: 'λόγος', field: 'text', rank: 0 },
	{ kind: 'concept_alias', query: 'logos', field: 'text', rank: 1, concept_label: 'Speech' },
	{ kind: 'expanded', query: '', field: 'text', rank: 2 },
	{ kind: 'expanded', query: 'legein', field: 'text', rank: 3 }
];

assert.deepEqual(
	readerVisibleTextSearchCandidates(candidates).map((candidate) => candidate.query),
	['logos', 'legein']
);
assert.equal(readerTextSearchCandidateLabel(candidates[1]), 'Speech: logos');
assert.equal(readerTextSearchCandidateLabel(candidates[3]), 'legein');

assert.equal(readerAuthorSectionRomanHint('grc', 'Θ'), 'Th');
assert.equal(readerAuthorSectionRomanHint('san', 'भ'), 'bha');
assert.equal(readerAuthorSectionRomanHint('lat', 'A'), '');

const shelf: ReaderDiscoveryShelf = {
	id: 'epic',
	label: 'Epic',
	description: '',
	query: { group: 'epic' },
	work_count: 1200,
	classified_work_count: 1200,
	author_count: 42,
	sample_works: []
};

assert.equal(readerShelfMetaLabel(shelf), '1,200 works · 42 authors');
assert.equal(readerShelfMetaLabel({ ...shelf, work_count: 1, author_count: 0 }), '1 work');

assert.equal(
	readerWorkMetaLine({
		work_id: 'w1',
		collection_id: 'fixture',
		language: 'grc',
		title: 'Republic',
		author: 'Plato',
		author_id: 'plato',
		source_id: 'plato.rep',
		cts_work_urn: 'urn:cts:greekLit:tlg0059.tlg030',
		classification_category: 'philosophy',
		classification_period: 'classical',
		word_count: 90000
	}),
	'philosophy · classical · 90,000 words'
);

const pageSegments: ReaderSegment[] = [
	{
		segment_id: 's1',
		work_id: 'w1',
		edition_id: 'e1',
		segment_kind: 'line',
		citation_path: '1.1',
		text: 'a',
		sort_key: 14
	},
	{
		segment_id: 's2',
		work_id: 'w1',
		edition_id: 'e1',
		segment_kind: 'line',
		citation_path: '1.2',
		text: 'b',
		sort_key: 15
	}
];

assert.equal(readerCitationRangeLabel(pageSegments, null), '1.1 - 1.2');
assert.deepEqual(deriveReaderPagePagination(pageSegments, 10), {
	previous: '3',
	next: '15'
});

assert.equal(
	readerDiscoverySummaryLabel({
		discoveryGroup: 'epic',
		discoveryTag: '',
		workQuery: '',
		discoveryAuthorLabel: '',
		discoveryGroups: [{ id: 'epic', label: 'Epic', description: '', work_count: 12 }],
		discoveryTags: [],
		languageLabel: 'Greek'
	}),
	'Epic'
);
assert.equal(
	readerDiscoveryTitleLabel({
		readerView: 'search',
		activeDiscoverySummary: 'Greek works',
		textQuery: 'apollo',
		activeAuthorSection: '',
		workQuery: '',
		languageLabel: 'Greek'
	}),
	'Text matches for "apollo"'
);
