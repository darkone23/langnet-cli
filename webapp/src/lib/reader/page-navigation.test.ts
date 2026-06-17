import { strict as assert } from 'node:assert';

import type { ReaderDiscoveryShelf, ReaderSearchResult, ReaderSegment, ReaderWork } from './index';
import {
	readerCurrentReadingWorkRef,
	readerSearchResultWorkRef,
	readerSegmentIsActive,
	readerShelfIsActive
} from './page-navigation';

const shelf: ReaderDiscoveryShelf = {
	id: 'dialogue',
	label: 'Dialogue',
	description: '',
	query: { tag: 'dialogue' },
	work_count: 3,
	classified_work_count: 3,
	author_count: 1,
	sample_works: []
};

assert.equal(readerShelfIsActive(shelf, { discoveryGroup: '', discoveryTag: 'dialogue' }), true);
assert.equal(
	readerShelfIsActive(shelf, { discoveryGroup: 'philosophy', discoveryTag: 'dialogue' }),
	false
);

const selectedSegment: ReaderSegment = {
	segment_id: 's1',
	work_id: 'rep',
	edition_id: 'e1',
	segment_kind: 'section',
	citation_path: '1.1',
	text: 'text'
};
const otherSegment = { ...selectedSegment, segment_id: 's2', citation_path: '1.2' };

assert.equal(readerSegmentIsActive(selectedSegment, { ...selectedSegment }), true);
assert.equal(readerSegmentIsActive(selectedSegment, otherSegment), false);
assert.equal(readerSegmentIsActive(null, selectedSegment), false);

const work: ReaderWork = {
	work_id: 'rep',
	collection_id: 'fixture',
	language: 'grc',
	title: 'Republic',
	author: 'Plato',
	author_id: 'plato',
	source_id: 'plato.rep',
	cts_work_urn: 'urn:cts:greekLit:tlg0059.tlg030',
	canonical_text_id: 'urn:ctsv2:greekLit:tlg0059.tlg030'
};

assert.equal(
	readerCurrentReadingWorkRef(work, selectedSegment),
	'urn:ctsv2:greekLit:tlg0059.tlg030'
);
assert.equal(readerCurrentReadingWorkRef(null, selectedSegment), 'rep');
assert.equal(readerCurrentReadingWorkRef(null, null), '');

const result: ReaderSearchResult = {
	score: 1,
	work_id: 'fallback-work',
	collection_id: 'fixture',
	language: 'grc',
	title: 'Republic',
	author: 'Plato',
	citation_path: '1.1',
	segment_id: 's1',
	text: 'text',
	snippet: 'text',
	target: { work_ref: 'target-work' }
};

assert.equal(readerSearchResultWorkRef(result), 'target-work');
assert.equal(
	readerSearchResultWorkRef({ ...result, target: undefined, cts_work_urn: 'cts-work' }),
	'fallback-work'
);
assert.equal(
	readerSearchResultWorkRef({ ...result, target: undefined, cts_work_urn: null }),
	'fallback-work'
);
