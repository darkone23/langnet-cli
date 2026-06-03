import type { LanguageMode, ToolRequest } from './search-data';

export type WordIndexLanguage = LanguageMode | 'all';
export type WordIndexMode = 'sources' | 'sections' | 'wheel' | 'list' | 'nearby' | 'browse';

export type WordIndexRequest = {
	mode: WordIndexMode | 'neighborhood';
	language: WordIndexLanguage;
	source: string;
	query?: string;
	prefix?: string;
	radius?: number;
	count?: number;
	seed?: string;
	timeoutMs?: number;
};

export type WordIndexSource = {
	source: string;
	language: LanguageMode;
	dictionary: string;
	available: boolean;
	entry_count: number;
};

export type WordIndexOrder = {
	policy: string;
	label: string;
	collation: string;
	key: string;
	display_key: string;
	explanation: string;
};

export type WordIndexItem = {
	lexeme_id: string;
	wheel_id: string;
	wheel_order_key: string;
	index_entry_id: string;
	source_order_id: string;
	language: LanguageMode;
	source: string;
	dictionary: string;
	kind: string;
	canonical_name: string;
	canonical_key: string;
	source_name: string;
	lookup: string;
	display: {
		primary: string;
		transliteration: string;
		source_key: string;
	};
	sort_key: string;
	source_order_key: string;
	source_ref: string;
	order?: WordIndexOrder;
	homograph_count?: number;
	homograph_policy?: string;
	ids: {
		lexeme: string;
		wheel: string;
		index_entry: string;
		source_order: string;
		source_ref: string;
	};
	encounter: {
		language: LanguageMode;
		q: string;
		dictionary: ToolRequest;
	};
	metadata: Record<string, unknown>;
	position?: 'before' | 'anchor' | 'after' | 'nearby';
	match?: boolean;
	source_count?: number;
	source_entry_count?: number;
	source_counts?: {
		source: string;
		dictionary: string;
		count: number;
	}[];
	sources?: {
		source: string;
		dictionary: string;
	}[];
	source_entries: {
		index_entry_id?: string;
		source_order_id?: string;
		wheel_id?: string;
		wheel_order_key?: string;
		source: string;
		dictionary: string;
		source_name?: string;
		source_display?: string;
		source_ref: string;
		source_order_key: string;
		order?: WordIndexOrder;
		display?: {
			primary: string;
			transliteration: string;
			source_key: string;
		};
	}[];
};

export type WordIndexSectionAnchor = {
	language: LanguageMode;
	source: string;
	dictionary: string;
	query: string;
	canonical_key: string;
	source_order_key: string;
	lexeme_id: string;
	index_entry_id: string;
	source_order_id: string;
	display?: {
		primary: string;
		transliteration: string;
		source_key: string;
	};
	order?: WordIndexOrder;
};

export type WordIndexSection = {
	id: string;
	label: string;
	transliteration: string;
	group_label: string;
	order_key: string;
	anchor: WordIndexSectionAnchor | null;
	available: boolean;
	entry_count: number;
};

export type WordIndexNeighborhoodGroup = {
	language: LanguageMode;
	source: string;
	dictionary: string;
	anchor?: WordIndexItem;
	before: WordIndexItem[];
	after: WordIndexItem[];
	radius: number;
	neighborhood_kind: string;
	anchor_status: string;
	window: {
		policy: string;
		contiguous: boolean;
		collapsed: boolean;
		before_count: number;
		after_count: number;
		source_entry_count: number;
	};
};

export type WordIndexBrowseGroup = {
	source: string;
	dictionary: string;
	order?: WordIndexOrder;
	item_count: number;
	items: WordIndexItem[];
};

export type WordIndexResponse = {
	schema_version: string;
	request: WordIndexRequest;
	sources: WordIndexSource[];
	order?: WordIndexOrder;
	items: WordIndexItem[];
	neighborhood: {
		policy?: string;
		anchor?: WordIndexItem;
		items?: WordIndexItem[];
		groups: WordIndexNeighborhoodGroup[];
		window?: {
			policy: string;
			contiguous: boolean;
			collapsed: boolean;
			before_count: number;
			after_count: number;
			source_group_count?: number;
			lexeme_count?: number;
		};
	} | null;
	browse?: {
		group_limit_policy?: string;
		groups: WordIndexBrowseGroup[];
	};
	pagination: {
		next_cursor: string | null;
		prev_cursor: string | null;
	};
	warnings: {
		source?: string;
		language?: LanguageMode;
		query?: string;
		message: string;
	}[];
	error?: string;
};

export type WordIndexSectionsResponse = {
	schema_version: string;
	request: {
		language: LanguageMode;
		source: string;
	};
	order?: WordIndexOrder;
	sections: WordIndexSection[];
	warnings: {
		source?: string;
		language?: LanguageMode;
		query?: string;
		message: string;
	}[];
	error?: string;
};

export type WordIndexSectionLookupTarget = {
	language: LanguageMode;
	query: string;
	dictionary: string;
};

export type WordIndexItemLookupTarget = {
	language: LanguageMode;
	query: string;
	dictionary: ToolRequest;
};

export function wordIndexDisplayOrderLabel(
	response: WordIndexResponse | WordIndexSectionsResponse | null,
	fallback = 'Nearby lexeme order'
) {
	if (!response) return fallback;
	if ('sections' in response) return response.order?.label || fallback;
	if (response.request.mode === 'wheel' && response.order?.label) return response.order.label;

	const sourceOrder = firstSourceNativeOrder(response);
	if (sourceOrder?.label) return sourceOrder.label;
	if (response.order?.label) return response.order.label;
	return fallback;
}

export function wordIndexAvailableSections(response: WordIndexSectionsResponse | null) {
	return response?.sections ?? [];
}

export function wordIndexBrowseGroups(response: WordIndexResponse | null) {
	return response?.browse?.groups ?? [];
}

export function wordIndexBrowseItems(response: WordIndexResponse | null) {
	if (!response) return [];
	if (response.request.mode === 'browse' && response.items.length) return response.items;
	return wordIndexBrowseGroups(response).flatMap((group) => group.items);
}

export function wordIndexItemEntryCount(item: WordIndexItem) {
	return item.homograph_count || item.source_entry_count || item.source_entries.length || 0;
}

export function wordIndexSectionLookupTarget(
	section: WordIndexSection
): WordIndexSectionLookupTarget | null {
	const anchor = section.anchor;
	if (!section.available || !anchor) return null;

	const query =
		anchor.language === 'san'
			? anchor.display?.transliteration ||
				section.transliteration ||
				anchor.canonical_key ||
				anchor.query
			: anchor.query ||
				anchor.display?.source_key ||
				anchor.canonical_key ||
				section.transliteration;

	if (!query.trim()) return null;

	return {
		language: anchor.language,
		query: query.trim(),
		dictionary: anchor.source || 'all'
	};
}

export function wordIndexItemLookupTarget(item: WordIndexItem): WordIndexItemLookupTarget {
	const query =
		item.encounter.q ||
		item.lookup ||
		item.display.source_key ||
		item.canonical_name ||
		item.canonical_key;
	const dictionary =
		item.encounter.dictionary && item.encounter.dictionary !== 'all'
			? item.encounter.dictionary
			: item.dictionary || item.source || 'all';

	return {
		language: item.encounter.language || item.language,
		query: query.trim(),
		dictionary: dictionary as ToolRequest
	};
}

export function wordIndexSectionForItem(
	item: WordIndexItem,
	response: WordIndexSectionsResponse | null
) {
	if (!response || response.request.language !== item.language) return undefined;

	const candidates = response.sections
		.filter((section) => section.available)
		.flatMap((section) =>
			sectionCandidateKeys(section).map((key) => ({
				section,
				key
			}))
		)
		.filter(({ key }) => key)
		.sort(
			(left, right) =>
				right.key.length - left.key.length ||
				left.section.order_key.localeCompare(right.section.order_key)
		);

	const itemKeys = itemCandidateKeys(item);

	for (const itemKey of itemKeys) {
		const match = candidates.find(({ key }) => itemKey.startsWith(key));
		if (match) return match.section;
	}

	return undefined;
}

function sectionCandidateKeys(section: WordIndexSection) {
	return uniqueSectionKeys([
		section.transliteration,
		sectionKeyIfSafe(section.anchor?.query),
		section.anchor?.canonical_key,
		sectionKeyIfSafe(section.anchor?.display?.source_key),
		section.anchor?.display?.transliteration
	]);
}

function sectionKeyIfSafe(value: string | undefined) {
	if (!value) return undefined;
	if (/[A-Z]/.test(value) && value.length > 1) return undefined;
	return value;
}

function itemCandidateKeys(item: WordIndexItem) {
	return uniqueSectionKeys([
		item.display.transliteration,
		item.canonical_key,
		item.lookup,
		item.encounter.q,
		item.display.source_key,
		item.source_name,
		...item.source_entries.flatMap((entry) => [
			entry.display?.transliteration,
			entry.display?.source_key,
			entry.source_display,
			entry.source_name
		])
	]);
}

function uniqueSectionKeys(values: (string | undefined)[]) {
	const keys: string[] = [];
	for (const value of values) {
		const key = normalizeSectionKey(value);
		if (key && !keys.includes(key)) keys.push(key);
	}
	return keys;
}

export function wordIndexActiveSection(
	response: WordIndexResponse | null,
	sections: WordIndexSectionsResponse | null
) {
	if (!response || !sections) return undefined;
	const activeItem = activeWordIndexItem(response);
	if (!activeItem) return undefined;
	return wordIndexSectionForItem(activeItem, sections);
}

function firstSourceNativeOrder(response: WordIndexResponse) {
	const groupedItems = (response.neighborhood?.groups ?? []).flatMap((group) => [
		...(group.anchor ? [group.anchor] : []),
		...group.before,
		...group.after
	]);
	const browseItems = (response.browse?.groups ?? []).flatMap((group) => group.items);
	const candidates = [
		...groupedItems,
		...(response.neighborhood?.items ?? []),
		...browseItems,
		...response.items
	];

	for (const item of candidates) {
		for (const entry of item.source_entries) {
			if (entry.order?.policy === 'source-native') return entry.order;
		}
	}

	return undefined;
}

function activeWordIndexItem(response: WordIndexResponse) {
	if (response.neighborhood?.anchor) return response.neighborhood.anchor;

	for (const group of response.neighborhood?.groups ?? []) {
		if (group.anchor) return group.anchor;
	}

	const positionedAnchor = (response.neighborhood?.items ?? response.items).find(
		(item) => item.position === 'anchor' || item.match
	);
	if (positionedAnchor) return positionedAnchor;

	for (const group of response.browse?.groups ?? []) {
		if (group.items[0]) return group.items[0];
	}

	return response.items[0];
}

function normalizeSectionKey(value: string | undefined) {
	return (value ?? '')
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '');
}
