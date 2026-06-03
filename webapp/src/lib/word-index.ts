import { tools, type LanguageMode, type ToolId, type ToolRequest } from './search-data';

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

export type WordIndexRow = {
	item: WordIndexItem;
	position: 'before' | 'anchor' | 'after';
};

export type WordIndexMergedPosition = WordIndexRow['position'] | 'nearby' | 'browse';

export type WordIndexMergedRow = {
	key: string;
	items: WordIndexItem[];
	positions: WordIndexMergedPosition[];
	sortKey: string;
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

export function wordIndexRows(group: WordIndexNeighborhoodGroup): WordIndexRow[] {
	return [
		...group.before.map((item) => ({ item, position: 'before' as const })),
		...(group.anchor ? [{ item: group.anchor, position: 'anchor' as const }] : []),
		...group.after.map((item) => ({ item, position: 'after' as const }))
	];
}

export function mergeWordIndexRows(groups: WordIndexNeighborhoodGroup[]): WordIndexMergedRow[] {
	const merged = new Map<string, WordIndexMergedRow>();

	for (const row of groups.flatMap(wordIndexRows)) {
		const key = wordIndexMergeKey(row.item);
		const existing = merged.get(key);

		if (existing) {
			if (!existing.items.some((item) => wordIndexItemKey(item) === wordIndexItemKey(row.item))) {
				existing.items.push(row.item);
			}
			if (!existing.positions.includes(row.position)) existing.positions.push(row.position);
			if (wordIndexSortKey(row.item) < existing.sortKey)
				existing.sortKey = wordIndexSortKey(row.item);
		} else {
			merged.set(key, {
				key,
				items: [row.item],
				positions: [row.position],
				sortKey: wordIndexSortKey(row.item)
			});
		}
	}

	return [...merged.values()];
}

export function wordIndexMergedRowsFromResponse(
	result: WordIndexResponse | null
): WordIndexMergedRow[] {
	const browseRows = wordIndexMergedRowsFromBrowseItems(wordIndexBrowseItems(result));
	if (browseRows.length) return browseRows;

	const mergedItemRows = wordIndexMergedRowsFromItems(result?.neighborhood?.items ?? []);
	const groupedRows = mergeWordIndexRows(result?.neighborhood?.groups ?? []);

	if (preferMergedWordIndexItems(mergedItemRows, groupedRows)) return mergedItemRows;
	if (groupedRows.length) return groupedRows;
	if (mergedItemRows.length) return mergedItemRows;

	const anchor = result?.neighborhood?.anchor;
	if (!anchor) return [];

	return [
		{
			key: wordIndexMergeKey(anchor),
			items: [anchor],
			positions: ['anchor'],
			sortKey: wordIndexSortKey(anchor)
		}
	];
}

export function wordIndexMergedRowsFromItems(items: WordIndexItem[]): WordIndexMergedRow[] {
	return items.map((item) => ({
		key: wordIndexMergeKey(item),
		items: [item],
		positions: [item.position ?? 'anchor'],
		sortKey: wordIndexSortKey(item)
	}));
}

export function wordIndexMergedRowsFromBrowseItems(items: WordIndexItem[]): WordIndexMergedRow[] {
	return items.map((item) => ({
		key: `browse:${wordIndexItemKey(item)}`,
		items: [item],
		positions: ['browse' as const],
		sortKey: wordIndexSortKey(item)
	}));
}

export function wordIndexMergedRowsFromBrowseGroups(
	groups: ReturnType<typeof wordIndexBrowseGroups>
): WordIndexMergedRow[] {
	return groups.flatMap((group) =>
		group.items.map((item) => ({
			key: `${group.source}:${group.dictionary}:${wordIndexItemKey(item)}`,
			items: [item],
			positions: ['browse' as const],
			sortKey: wordIndexSortKey(item)
		}))
	);
}

export function wordIndexMergeKey(item: WordIndexItem) {
	return (
		item.wheel_id ||
		item.lexeme_id ||
		`${item.language}:${item.canonical_key || item.lookup || item.encounter.q}`
	);
}

export function wordIndexSortKey(item: WordIndexItem) {
	return item.wheel_order_key || item.canonical_key || item.lookup || item.encounter.q;
}

export function wordIndexPrimaryItem(row: WordIndexMergedRow) {
	return (
		row.items.find((item) => item.encounter.dictionary === 'all') ??
		row.items.find((item) => isTranslatedSourceTool(sourceToolFromWordIndex(item.source))) ??
		row.items[0]
	);
}

export function wordIndexDisplay(item: WordIndexItem) {
	const display = item.display.primary || item.canonical_name || item.source_name;
	const cleanDisplay = stripSourceVariantNumber(display);
	const normalizedLookup = item.lookup || item.canonical_key || item.encounter.q;

	if (display !== cleanDisplay && normalizedLookup) return normalizedLookup.normalize('NFC');
	return (cleanDisplay || normalizedLookup).normalize('NFC');
}

export function wordIndexLookup(item: WordIndexItem) {
	const display = wordIndexDisplay(item).toLowerCase();
	const lookup = item.display.transliteration || item.lookup || item.canonical_key;
	if (!lookup || lookup.toLowerCase() === display) return '';
	return lookup.normalize('NFC');
}

export function wordIndexEntryCountLabel(item: WordIndexItem) {
	const count = wordIndexItemEntryCount(item);
	if (count <= 1) return '';
	return `${count} entries`;
}

export function wordIndexRowSources(row: WordIndexMergedRow, fallbackLanguage?: LanguageMode) {
	return [
		...new Set(
			row.items.flatMap((item) => {
				if (item.source_counts?.length) {
					return item.source_counts.map((source) =>
						source.count > 1
							? `${wordIndexSourceLabelFromParts(source, fallbackLanguage)} ${source.count}`
							: wordIndexSourceLabelFromParts(source, fallbackLanguage)
					);
				}
				if (item.sources?.length) {
					return item.sources.map((source) =>
						wordIndexSourceLabelFromParts(source, fallbackLanguage)
					);
				}
				if (item.source_entries.length) {
					return item.source_entries.map((entry) =>
						wordIndexSourceLabelFromParts(entry, fallbackLanguage)
					);
				}
				return [wordIndexSourceLabel(item, fallbackLanguage)];
			})
		)
	];
}

export function wordIndexSourceLabel(item: WordIndexItem, fallbackLanguage?: LanguageMode) {
	return wordIndexSourceLabelFromParts(
		{
			source: item.source,
			dictionary: item.dictionary,
			language: item.language
		},
		fallbackLanguage
	);
}

export function wordIndexSourceLabelFromParts(
	{
		source,
		dictionary,
		language
	}: {
		source: string;
		dictionary: string;
		language?: LanguageMode;
	},
	fallbackLanguage?: LanguageMode
) {
	const sourceLanguage = language ?? fallbackLanguage;
	const tool = toolMeta(sourceToolFromWordIndex(source), sourceLanguage);
	return dictionary && dictionary !== source ? `${tool.shortLabel}/${dictionary}` : tool.shortLabel;
}

export function wordIndexRowPosition(row: WordIndexMergedRow): WordIndexMergedPosition {
	const directPosition = row.items.find((item) => item.position)?.position;
	if (directPosition) return directPosition;
	if (row.positions.includes('anchor')) return 'anchor';
	if (row.positions.includes('before') && row.positions.includes('after')) return 'nearby';
	return row.positions[0] ?? 'anchor';
}

export function wordIndexRowMatched(
	row: WordIndexMergedRow,
	{
		query,
		encounterMatchKeys = new Set<string>()
	}: {
		query: string;
		encounterMatchKeys?: Set<string>;
	}
) {
	if (row.items.some((item) => item.match)) return true;

	const queryKeys = queryEquivalentKeys(query);
	for (const key of encounterMatchKeys) queryKeys.add(key);
	if (!queryKeys.size) return false;

	return row.items.some((item) => wordIndexItemLexemeKeys(item).some((key) => queryKeys.has(key)));
}

export function encounterWordIndexMatchKeys(
	result: {
		lexeme_anchors: string[];
		buckets: {
			bucket_lemmas: string[];
			witnesses: {
				headword?: string;
				lexeme_anchor?: string;
			}[];
		}[];
	} | null
) {
	const keys = new Set<string>();
	if (!result) return keys;

	for (const anchor of result.lexeme_anchors) addWordIndexMatchKey(keys, anchor);
	for (const bucket of result.buckets) {
		for (const lemma of bucket.bucket_lemmas) addWordIndexMatchKey(keys, lemma);
		for (const witness of bucket.witnesses) {
			addWordIndexMatchKey(keys, witness.headword);
			addWordIndexMatchKey(keys, witness.lexeme_anchor);
		}
	}

	return keys;
}

export function queryEquivalentKeys(value: string) {
	const keys = new Set<string>();
	addWordIndexMatchKey(keys, value);
	return keys;
}

export function wordIndexItemLexemeKeys(item: WordIndexItem) {
	const keys = new Set<string>();
	addWordIndexMatchKey(keys, item.lookup);
	addWordIndexMatchKey(keys, item.canonical_key);
	addWordIndexMatchKey(keys, item.canonical_name);
	addWordIndexMatchKey(keys, item.source_name);
	addWordIndexMatchKey(keys, item.display.primary);
	addWordIndexMatchKey(keys, item.display.transliteration);
	addWordIndexMatchKey(keys, item.encounter.q);
	for (const entry of item.source_entries) {
		addWordIndexMatchKey(keys, entry.source_name);
		addWordIndexMatchKey(keys, entry.source_display);
	}
	return [...keys];
}

export function addWordIndexMatchKey(keys: Set<string>, value: string | undefined) {
	const key = strictStudyKey(value);
	if (key) keys.add(key);
	const sanskritKey = sanskritSourceStudyKey(value);
	if (sanskritKey) keys.add(sanskritKey);
}

export function strictStudyKey(value: string | undefined) {
	return (value ?? '')
		.replace(/^lex:/, '')
		.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '')
		.normalize('NFC')
		.toLowerCase()
		.replace(/[^a-z0-9.\-āīūṛṝḷḹṃḥṅñṭḍṇśṣ\u0370-\u03ff\u0900-\u097f]+/gu, '')
		.trim();
}

export function sanskritSourceStudyKey(value: string | undefined) {
	return strictStudyKey(value)
		.replace(/\.n/g, 'ṇ')
		.replace(/\.s/g, 'ṣ')
		.replace(/aa/g, 'ā')
		.replace(/ii/g, 'ī')
		.replace(/uu/g, 'ū')
		.replace(/[^a-z0-9āīūṛṝḷḹṃḥṅñṭḍṇśṣ\u0900-\u097f]+/gu, '')
		.trim();
}

export function stripSourceVariantNumber(value: string) {
	return value.replace(/^\s*\d+\s+/u, '').trim();
}

export function wordIndexItemKey(item: WordIndexItem) {
	return (
		item.ids.index_entry ||
		item.index_entry_id ||
		item.source_ref ||
		`${item.language}:${item.source}:${item.dictionary}:${item.lookup || item.encounter.q}`
	);
}

export function sourceToolFromWordIndex(source: string): ToolId {
	if (source === 'gaffiot') return 'gaffiot';
	if (source === 'lewis_1890') return 'lewis_1890';
	if (source === 'bailly') return 'bailly';
	if (source === 'dico') return 'dico';
	if (source === 'cdsl') return 'cdsl';
	if (source === 'heritage') return 'heritage';
	if (source === 'whitakers') return 'whitakers';
	if (source === 'cltk') return 'cltk';
	if (source === 'spacy') return 'spacy';
	if (source === 'cts_index') return 'cts_index';
	return 'diogenes';
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

function preferMergedWordIndexItems(
	mergedItemRows: WordIndexMergedRow[],
	groupedRows: WordIndexMergedRow[]
) {
	if (!mergedItemRows.length) return false;
	if (!groupedRows.length) return true;

	const mergedBefore = mergedItemRows.filter((row) => row.positions.includes('before')).length;
	const groupedBefore = groupedRows.filter((row) => row.positions.includes('before')).length;
	const mergedHasAnchor = mergedItemRows.some((row) => row.positions.includes('anchor'));
	const groupedHasAnchor = groupedRows.some((row) => row.positions.includes('anchor'));
	const mergedHasAfter = mergedItemRows.some((row) => row.positions.includes('after'));

	return mergedHasAnchor && mergedHasAfter && (!groupedHasAnchor || mergedBefore > groupedBefore);
}

function toolMeta(toolId: ToolId, mode?: LanguageMode) {
	return (
		(mode && tools.find((tool) => tool.id === toolId && tool.language === mode)) ??
		tools.find((tool) => tool.id === toolId) ?? {
			id: toolId,
			language: mode ?? 'grc',
			label: toolId,
			shortLabel: toolId,
			kind: 'tool',
			description: 'Source entry evidence.'
		}
	);
}

function isTranslatedSourceTool(tool: ToolId | undefined) {
	return tool === 'dico' || tool === 'gaffiot' || tool === 'bailly';
}

function normalizeSectionKey(value: string | undefined) {
	return (value ?? '')
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '');
}
