import { strict as assert } from 'node:assert';
import { appendRequestCostHeaders, requestCostFromUrl } from './request-cost';

const sections = requestCostFromUrl(new URL('https://langnet.local/api/word-index?mode=sections'));
assert.equal(sections.score, 1);
assert.equal(sections.route, '/api/word-index');
assert.equal(sections.translation, 'off');

const index = requestCostFromUrl(
	new URL('https://langnet.local/api/word-index?mode=nearby&source=lsj')
);
assert.equal(index.score, 5);
assert.equal(index.dictionary, 'lsj');

const cache = requestCostFromUrl(
	new URL('https://langnet.local/api/search?language=grc&q=logos&dictionary=lsj&translation=cache')
);
assert.equal(cache.score, 10);

const auto = requestCostFromUrl(
	new URL('https://langnet.local/api/search?language=grc&q=logos&dictionary=lsj&translation=auto')
);
assert.equal(auto.score, 25);

const populate = requestCostFromUrl(
	new URL(
		'https://langnet.local/api/search?language=grc&q=logos&dictionary=diogenes&translation=populate'
	)
);
assert.equal(populate.score, 50);

const defaultHeaders = new Headers();
appendRequestCostHeaders(defaultHeaders, populate);
assert.equal(defaultHeaders.get('LangNet-Request-Cost'), '50');

console.log('request cost helper checks complete');
