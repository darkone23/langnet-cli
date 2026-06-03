import type { LanguageMode, SearchBackend, ToolId, TranslationMode } from '../search-data';

type SearchEndpointInput = {
	language: LanguageMode;
	query: string;
	backendMode: SearchBackend;
	translationMode: TranslationMode;
	lookupTools: ToolId[];
	allLookupSelected: boolean;
};

type WordIndexNearbyEndpointInput = {
	language: LanguageMode;
	query: string;
	radius: number;
};

type WordIndexBrowseEndpointInput = {
	language: LanguageMode;
	prefix: string;
	count?: number;
};

export function searchEndpointUrl({
	language,
	query,
	backendMode,
	translationMode,
	lookupTools,
	allLookupSelected
}: SearchEndpointInput) {
	const params = new URLSearchParams();
	params.set('language', language);

	const trimmedQuery = query.trim();
	if (trimmedQuery) {
		params.set('q', trimmedQuery);
	}

	params.set('backend', backendMode);
	if (backendMode === 'cli') {
		params.set('translation', translationMode);
		params.set('max_buckets', '54321');
		params.set('max_gloss_chars', '54321');
		params.set('source_layer_version', '3');
	}

	if (allLookupSelected) {
		params.set('dictionary', 'all');
	} else {
		for (const tool of lookupTools) {
			params.append('dictionary', tool);
		}
	}

	return `/api/search?${params.toString()}`;
}

export function wordIndexNearbyEndpointUrl({
	language,
	query,
	radius
}: WordIndexNearbyEndpointInput) {
	const params = new URLSearchParams({
		mode: 'nearby',
		language,
		q: query,
		source: 'all',
		radius: String(radius)
	});

	return `/api/word-index?${params.toString()}`;
}

export function wordIndexSectionsEndpointUrl(language: LanguageMode) {
	const params = new URLSearchParams({
		mode: 'sections',
		language,
		source: 'all'
	});

	return `/api/word-index?${params.toString()}`;
}

export function wordIndexBrowseEndpointUrl({
	language,
	prefix,
	count = 12
}: WordIndexBrowseEndpointInput) {
	const params = new URLSearchParams({
		mode: 'browse',
		language,
		prefix,
		source: 'all',
		count: String(count)
	});

	return `/api/word-index?${params.toString()}`;
}
