import assert from 'node:assert/strict';

import {
	readerAuthorSectionsUrl,
	readerAuthorsUrl,
	readerCatalogsUrl,
	readerContentsUrl,
	readerEncounterBriefingUrl,
	fetchReaderApi,
	fetchReaderEncounterBriefing,
	readerFacetsUrl,
	readerResolveAddressUrl,
	readerShelvesUrl,
	readerShowUrl,
	readerStructureUrl,
	readerTextSearchUrl,
	readerWorkDossierUrl,
	readerWorkMetadataUrl,
	readerWorksUrl
} from './reader-api';

assert.equal(readerCatalogsUrl(), '/api/reader?mode=catalogs');

assert.equal(
	readerEncounterBriefingUrl({
		language: 'grc',
		token: ' τελευταίαις ',
		generate: true
	}),
	'/api/encounter-briefing?language=grc&q=%CF%84%CE%B5%CE%BB%CE%B5%CF%85%CF%84%CE%B1%CE%AF%CE%B1%CE%B9%CF%82&translation=cache&timeout_ms=300000&generate=1'
);

assert.equal(
	readerFacetsUrl({ catalogId: 'perseus', language: 'grc' }),
	'/api/reader?mode=facets&catalog=perseus&language=grc'
);

assert.equal(
	readerShelvesUrl({ catalogId: 'perseus', language: 'grc' }),
	'/api/reader?mode=shelves&catalog=perseus&language=grc&limit=12&sample_limit=2&timeout_ms=300000'
);

assert.equal(
	readerAuthorSectionsUrl({ catalogId: 'perseus', language: 'grc' }),
	'/api/reader?mode=author-sections&catalog=perseus&language=grc'
);

assert.equal(
	readerAuthorsUrl({
		catalogId: 'perseus',
		language: 'grc',
		section: 'Π',
		query: 'plato',
		agentKind: 'person',
		historicity: 'historical',
		cursor: 'authors:2'
	}),
	'/api/reader?mode=authors&catalog=perseus&language=grc&limit=50&section=%CE%A0&q=plato&agent_kind=person&historicity=historical&cursor=authors%3A2'
);

assert.equal(
	readerWorksUrl({
		catalogId: 'perseus',
		language: 'grc',
		authorId: 'plato',
		collection: 'canonical',
		cursor: 'works:2'
	}),
	'/api/reader?mode=works&catalog=perseus&language=grc&limit=120&author_id=plato&collection=canonical&cursor=works%3A2'
);

assert.equal(
	readerWorksUrl({
		catalogId: 'perseus',
		language: 'grc',
		query: 'republic',
		group: 'philosophy',
		tag: 'dialogue',
		sort: 'global-popularity'
	}),
	'/api/reader?mode=works&catalog=perseus&language=grc&limit=120&q=republic&group=philosophy&tag=dialogue&sort=global-popularity'
);

assert.equal(
	readerTextSearchUrl({
		catalogId: 'perseus',
		language: 'grc',
		query: 'apollo',
		searchMode: 'fuzzy',
		collection: 'homer',
		cursor: 'text:2'
	}),
	'/api/reader?mode=search&catalog=perseus&language=grc&q=apollo&search_mode=fuzzy&context=1&limit=5&timeout_ms=90000&collection=homer&cursor=text%3A2'
);

assert.equal(
	readerStructureUrl({ catalogId: 'perseus', language: 'grc', work: 'Republic' }),
	'/api/reader?mode=structure&catalog=perseus&language=grc&work=Republic&timeout_ms=120000'
);

assert.equal(
	readerWorkDossierUrl({ catalogId: 'perseus', language: 'grc', work: 'Republic' }),
	'/api/reader?mode=about&catalog=perseus&language=grc&work=Republic&timeout_ms=120000'
);

assert.equal(
	readerContentsUrl({
		catalogId: 'perseus',
		language: 'grc',
		work: 'Republic',
		limit: 8,
		charBudget: 2200,
		cursor: 'contents:2'
	}),
	'/api/reader?mode=contents&catalog=perseus&language=grc&work=Republic&limit=8&char_budget=2200&cursor=contents%3A2'
);

assert.equal(
	readerContentsUrl({
		catalogId: 'perseus',
		language: 'grc',
		work: 'Republic',
		limit: 5,
		charBudget: 2200,
		around: '10.614b',
		radius: 2
	}),
	'/api/reader?mode=contents&catalog=perseus&language=grc&work=Republic&around=10.614b&radius=2&limit=5&char_budget=2200'
);

assert.equal(
	readerShowUrl({
		catalogId: 'perseus',
		language: 'grc',
		work: 'Republic',
		segment: '10.614b'
	}),
	'/api/reader?mode=show&catalog=perseus&language=grc&work=Republic&segment=10.614b'
);

assert.equal(
	readerShowUrl({
		catalogId: 'perseus',
		language: 'grc',
		address: 'Republic Book 10'
	}),
	'/api/reader?mode=show&catalog=perseus&language=grc&address=Republic+Book+10'
);

assert.equal(
	readerResolveAddressUrl({
		catalogId: 'perseus',
		language: 'grc',
		address: 'Republic Book 10'
	}),
	'/api/reader?mode=resolve-address&catalog=perseus&language=grc&address=Republic+Book+10'
);

assert.equal(
	readerWorkMetadataUrl({ catalogId: 'perseus', language: 'grc', work: 'Republic' }),
	'/api/reader?mode=work&catalog=perseus&language=grc&work=Republic'
);

const originalFetch = globalThis.fetch;
const fetchedUrls: string[] = [];
const acceptHeaders: string[] = [];

globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
	fetchedUrls.push(String(input));
	acceptHeaders.push(new Headers(init?.headers).get('accept') ?? '');
	const data = String(input).includes('/api/encounter-briefing') ? { flow: [] } : { ok: true };
	return new Response(JSON.stringify(data), {
		headers: { 'content-type': 'application/json' }
	});
};

try {
	const apiResult = await fetchReaderApi<{ ok: boolean }>('/api/reader?mode=catalogs');
	const briefingResult = await fetchReaderEncounterBriefing({
		language: 'grc',
		token: 'λόγος',
		generate: false
	});

	assert.equal(apiResult.data.ok, true);
	assert.deepEqual(briefingResult.data, { flow: [] });
	assert.deepEqual(fetchedUrls, [
		'/api/auth/request-token',
		'/api/reader?mode=catalogs',
		'/api/auth/request-token',
		'/api/encounter-briefing?language=grc&q=%CE%BB%CF%8C%CE%B3%CE%BF%CF%82&translation=cache&timeout_ms=180000'
	]);
	assert.ok(
		acceptHeaders.every((header) => header === 'application/msgpack, application/json'),
		'reader fetch helpers should preserve the fetchPayload accept headers'
	);
} finally {
	globalThis.fetch = originalFetch;
}
