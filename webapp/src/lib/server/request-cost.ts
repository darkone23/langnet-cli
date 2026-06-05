export type RequestCost = {
	score: number;
	route: string;
	dictionary: string;
	translation: string;
	reason: string;
};

const expensiveDictionaries = new Set(['diogenes', 'bailly', 'gaffiot', 'cdsl']);

export function requestCostFromUrl(url: URL): RequestCost {
	let score = 1;
	let reason = 'default';
	const route = url.pathname;
	let dictionary = url.searchParams.get('dictionary')?.trim() ?? 'none';
	let translation = url.searchParams.get('translation')?.trim() ?? '';

	if (route === '/api/word-index') {
		const mode = url.searchParams.get('mode')?.trim() ?? 'nearby';
		score = mode === 'sections' ? 1 : 5;
		reason = `route:${route}:mode=${mode}`;
		dictionary = url.searchParams.get('source')?.trim() ?? dictionary;
	} else if (route === '/api/search') {
		const mode = translation || 'cache';
		if (mode === 'cache') score = 10;
		else if (mode === 'auto') score = 25;
		else if (mode === 'populate' || mode === 'do-it-all') score = 40;
		else score = 1;
		reason = `route:${route}:translation=${mode}`;
	} else if (route === '/api/word-of-day') {
		score = 1;
		reason = `route:${route}:curated-public-copy`;
	}

	if (dictionary !== 'none' && expensiveDictionaries.has(dictionary)) {
		score += 10;
		reason += ':expensive-dictionary';
	}

	return {
		score,
		route,
		dictionary,
		translation: translation || 'off',
		reason
	};
}

export function appendRequestCostHeaders(headers: Headers, cost: RequestCost) {
	headers.set('LangNet-Request-Cost', String(cost.score));
}
