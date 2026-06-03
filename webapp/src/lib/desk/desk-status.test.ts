import assert from 'node:assert/strict';

import type { EncounterResult } from '../search-data';
import { uiCopy } from '../ui-copy';
import {
	deskCacheSummary,
	deskCurrentStatusDetail,
	deskCurrentStatusLabel,
	deskReaderLayerStatus
} from './desk-status';

function encounter(overrides: Partial<EncounterResult['translation_cache']> = {}): EncounterResult {
	return {
		query: 'logos',
		language: 'grc',
		dictionaries: ['all'],
		source_tools: ['diogenes'],
		lexeme_anchors: [],
		analysis: [],
		components: [],
		buckets: [{ bucket_id: 'a' }, { bucket_id: 'b' }] as EncounterResult['buckets'],
		translation_cache: {
			mode: 'cache',
			cache_db: '',
			model: '',
			cache_available: true,
			populate: false,
			written: 0,
			before: { total: 0, hits: 0, missing: 0, errors: 0, empty: 0 },
			after: { total: 0, hits: 0, missing: 0, errors: 0, empty: 0 },
			...overrides
		},
		warnings: [],
		request: {
			translation_mode: 'cache',
			tool_filter: ['all'],
			reader_lang: 'en'
		},
		backend: 'cli'
	};
}

assert.equal(
	deskCacheSummary(encounter({ cache_available: false })),
	uiCopy.status.cacheUnavailable
);
assert.equal(deskCacheSummary(encounter()), uiCopy.status.cacheWarm);
assert.equal(
	deskCacheSummary(
		encounter({
			written: 3,
			after: { total: 0, hits: 0, missing: 2, errors: 0, empty: 0 }
		})
	),
	uiCopy.status.newTranslations(3)
);
assert.equal(
	deskCacheSummary(
		encounter({
			after: { total: 0, hits: 0, missing: 4, errors: 0, empty: 0 }
		})
	),
	uiCopy.status.missingTranslations(4)
);

assert.equal(
	deskCurrentStatusLabel({
		loading: true,
		enrichingTranslations: false,
		hasAttention: false,
		hasEncounter: false
	}),
	uiCopy.status.searching
);
assert.equal(
	deskCurrentStatusLabel({
		loading: false,
		enrichingTranslations: true,
		hasAttention: false,
		hasEncounter: false
	}),
	uiCopy.status.awaitingReader
);
assert.equal(
	deskCurrentStatusLabel({
		loading: false,
		enrichingTranslations: false,
		hasAttention: true,
		hasEncounter: true
	}),
	uiCopy.status.attention
);
assert.equal(
	deskCurrentStatusLabel({
		loading: false,
		enrichingTranslations: false,
		hasAttention: false,
		hasEncounter: true
	}),
	uiCopy.status.reading
);

assert.equal(
	deskCurrentStatusDetail({
		loading: true,
		enrichingTranslations: false,
		lookupToolCount: 3,
		encounter: null,
		visibleBucketCount: 0,
		query: ''
	}),
	uiCopy.status.askingSources(3)
);
assert.equal(
	deskCurrentStatusDetail({
		loading: false,
		enrichingTranslations: true,
		lookupToolCount: 3,
		encounter: null,
		visibleBucketCount: 0,
		query: ''
	}),
	uiCopy.status.awaitingReaderDetail
);
assert.equal(
	deskCurrentStatusDetail({
		loading: false,
		enrichingTranslations: false,
		lookupToolCount: 3,
		encounter: encounter(),
		visibleBucketCount: 1,
		query: ''
	}),
	uiCopy.status.showingSections(1, 2, 'logos')
);
assert.equal(
	deskCurrentStatusDetail({
		loading: false,
		enrichingTranslations: false,
		lookupToolCount: 3,
		encounter: null,
		visibleBucketCount: 0,
		query: 'agni'
	}),
	uiCopy.status.readyForWord
);

assert.equal(
	deskReaderLayerStatus({
		enrichingTranslations: false,
		translationMode: 'auto',
		backendMode: 'cli',
		encounter: null
	}),
	uiCopy.readerLayer.unsearched
);
assert.equal(
	deskReaderLayerStatus({
		enrichingTranslations: true,
		translationMode: 'populate',
		backendMode: 'cli',
		encounter: encounter()
	}),
	uiCopy.readerLayer.awaiting('populate')
);
assert.equal(
	deskReaderLayerStatus({
		enrichingTranslations: false,
		translationMode: 'auto',
		backendMode: 'cli',
		encounter: encounter()
	}),
	uiCopy.readerLayer.cacheSupplied('auto')
);
assert.equal(
	deskReaderLayerStatus({
		enrichingTranslations: false,
		translationMode: 'cache',
		backendMode: 'cli',
		encounter: encounter()
	}),
	uiCopy.readerLayer.served('cache')
);
