import { strict as assert } from 'node:assert';
import {
	findReaderWatchlistMatches,
	readerAcquisitionStatusLabel,
	readerSourceFileStatusLabel,
	readerWorkAvailabilityLabel,
	type ReaderWatchlistTarget
} from './library-watchlist';

const targets: ReaderWatchlistTarget[] = [
	{
		id: 'agrippa-occult-philosophy',
		displayName: 'Heinrich Cornelius Agrippa, De occulta philosophia',
		aliases: ['Agrippa', 'Three Books of Occult Philosophy'],
		languages: ['lat'],
		period: 'early modern',
		tradition: 'humanist',
		status: 'needs_source_review',
		sourcePlan: 'Compare clean electronic text against control witness.',
		note: 'Candidate source exists but needs review.'
	}
];

assert.equal(readerAcquisitionStatusLabel('imported'), 'Imported');
assert.equal(readerAcquisitionStatusLabel('needs_source_review'), 'Needs source review');
assert.equal(readerSourceFileStatusLabel('imported_from_staging'), 'Imported from staging');
assert.equal(readerSourceFileStatusLabel(''), 'Source status unknown');
assert.equal(readerWorkAvailabilityLabel({ word_count: 1200, segment_count: 15 }), 'Readable text');
assert.equal(readerWorkAvailabilityLabel({ word_count: 0, segment_count: 0 }), 'Catalog shell');
assert.deepEqual(findReaderWatchlistMatches(targets, 'occult')[0]?.id, 'agrippa-occult-philosophy');
