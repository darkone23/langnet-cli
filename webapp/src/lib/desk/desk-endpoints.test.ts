import { strict as assert } from 'node:assert';

import {
	searchEndpointUrl,
	wordIndexBrowseEndpointUrl,
	wordIndexNearbyEndpointUrl,
	wordIndexSectionsEndpointUrl
} from './desk-endpoints';

assert.equal(
	searchEndpointUrl({
		language: 'grc',
		query: ' logos ',
		backendMode: 'cli',
		translationMode: 'auto',
		lookupTools: ['diogenes', 'bailly'],
		allLookupSelected: false
	}),
	'/api/search?language=grc&q=logos&backend=cli&translation=auto&max_buckets=54321&max_gloss_chars=54321&source_layer_version=3&dictionary=diogenes&dictionary=bailly'
);

assert.equal(
	searchEndpointUrl({
		language: 'san',
		query: '',
		backendMode: 'sample',
		translationMode: 'off',
		lookupTools: ['cdsl'],
		allLookupSelected: true
	}),
	'/api/search?language=san&backend=sample&dictionary=all'
);

assert.equal(
	wordIndexNearbyEndpointUrl({
		language: 'san',
		query: 'jyotis',
		radius: 5
	}),
	'/api/word-index?mode=nearby&language=san&q=jyotis&source=all&radius=5'
);

assert.equal(
	wordIndexSectionsEndpointUrl('lat'),
	'/api/word-index?mode=sections&language=lat&source=all'
);

assert.equal(
	wordIndexBrowseEndpointUrl({
		language: 'grc',
		prefix: 'logos',
		count: 12
	}),
	'/api/word-index?mode=browse&language=grc&prefix=logos&source=all&count=12'
);
