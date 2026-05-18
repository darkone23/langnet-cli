import assert from 'node:assert/strict';
import {
	wordIndexActiveSection,
	wordIndexAvailableSections,
	wordIndexBrowseItems,
	wordIndexBrowseGroups,
	wordIndexDisplayOrderLabel,
	wordIndexItemEntryCount,
	wordIndexSectionLookupTarget,
	wordIndexSectionForItem,
	type WordIndexResponse,
	type WordIndexItem,
	type WordIndexSectionsResponse
} from './word-index';

const baseResponse = {
	schema_version: 'langnet.word_index.v1',
	request: {
		mode: 'nearby',
		language: 'san',
		source: 'all'
	},
	sources: [],
	items: [],
	neighborhood: { groups: [] },
	pagination: { next_cursor: null, prev_cursor: null },
	warnings: []
} satisfies WordIndexResponse;

assert.equal(
	wordIndexDisplayOrderLabel({
		...baseResponse,
		request: { ...baseResponse.request, mode: 'wheel' },
		order: {
			policy: 'seeded-discovery',
			label: 'Seeded discovery order',
			collation: 'seeded-discovery',
			key: 'daily-2026-05-11',
			display_key: 'daily-2026-05-11',
			explanation: 'A stable seeded discovery list.'
		}
	}),
	'Seeded discovery order'
);

assert.equal(
	wordIndexDisplayOrderLabel({
		...baseResponse,
		neighborhood: {
			groups: [
				{
					language: 'san',
					source: 'cdsl',
					dictionary: 'mw',
					before: [],
					after: [],
					radius: 1,
					neighborhood_kind: 'source',
					anchor_status: 'exact',
					window: {
						policy: 'source',
						contiguous: true,
						collapsed: false,
						before_count: 0,
						after_count: 1,
						source_entry_count: 2
					},
					anchor: {
						lexeme_id: 'lexeme:san:dharma',
						wheel_id: 'wheel:san:dharma',
						wheel_order_key: '000:san:dharma',
						index_entry_id: 'word-index:san:cdsl:mw:dharma',
						source_order_id: 'word-order:san:cdsl:mw:dharma',
						language: 'san',
						source: 'cdsl',
						dictionary: 'mw',
						kind: 'headword',
						canonical_name: 'धर्म',
						canonical_key: 'dharma',
						source_name: 'Darma',
						lookup: 'dharma',
						display: {
							primary: 'धर्म',
							transliteration: 'dharma',
							source_key: 'Darma'
						},
						sort_key: 'dharma',
						source_order_key: 'darma:00000000000099903000',
						source_ref: 'cdsl:mw:99903.0',
						ids: {
							lexeme: 'lexeme:san:dharma',
							wheel: 'wheel:san:dharma',
							index_entry: 'word-index:san:cdsl:mw:dharma',
							source_order: 'word-order:san:cdsl:mw:dharma',
							source_ref: 'cdsl:mw:99903.0'
						},
						encounter: {
							language: 'san',
							q: 'dharma',
							dictionary: 'cdsl'
						},
						metadata: {},
						source_entries: [
							{
								source: 'cdsl',
								dictionary: 'mw',
								source_ref: 'cdsl:mw:99903.0',
								source_order_key: 'darma:00000000000099903000',
								order: {
									policy: 'source-native',
									label: 'Sanskrit source order',
									collation: 'source',
									key: 'darma:00000000000099903000',
									display_key: 'धर्म',
									explanation: 'Preserves the indexed source sequence.'
								}
							}
						]
					}
				}
			]
		}
	}),
	'Sanskrit source order'
);

assert.equal(wordIndexDisplayOrderLabel(baseResponse), 'Nearby lexeme order');

const browseResponse = {
	...baseResponse,
	request: { ...baseResponse.request, mode: 'browse' },
	order: {
		policy: 'grouped-source-native',
		label: 'Sanskrit grouped source-native browse',
		collation: 'source',
		key: 'd',
		display_key: 'd',
		explanation: 'Groups preserve source-native order.'
	},
	browse: {
		groups: [
			{
				source: 'cdsl',
				dictionary: 'mw',
				order: {
					policy: 'source-native',
					label: 'Sanskrit cdsl:mw browse order',
					collation: 'source',
					key: 'd',
					display_key: 'd',
					explanation: 'Rows preserve CDSL source order.'
				},
				item_count: 1,
				items: [
					{
						lexeme_id: 'lexeme:san:da',
						wheel_id: 'wheel:san:da',
						wheel_order_key: '001:san:da',
						index_entry_id: 'word-index:san:cdsl:mw:da',
						source_order_id: 'word-order:san:cdsl:mw:da',
						language: 'san',
						source: 'cdsl',
						dictionary: 'mw',
						kind: 'headword',
						canonical_name: 'द',
						canonical_key: 'da',
						source_name: 'da',
						lookup: 'da',
						display: {
							primary: 'द',
							transliteration: 'da',
							source_key: 'da'
						},
						sort_key: 'da',
						source_order_key: 'da:00000000000089217000:00000000000000000001',
						source_ref: 'cdsl:mw:89217.0',
						order: {
							policy: 'source-native',
							label: 'Sanskrit source order',
							collation: 'source',
							key: 'da:00000000000089217000:00000000000000000001',
							display_key: 'द',
							explanation: 'Preserves source order.'
						},
						ids: {
							lexeme: 'lexeme:san:da',
							wheel: 'wheel:san:da',
							index_entry: 'word-index:san:cdsl:mw:da',
							source_order: 'word-order:san:cdsl:mw:da',
							source_ref: 'cdsl:mw:89217.0'
						},
						encounter: {
							language: 'san',
							q: 'da',
							dictionary: 'cdsl'
						},
						metadata: {},
						source_entries: []
					}
				]
			}
		]
	}
} satisfies WordIndexResponse;

assert.equal(wordIndexDisplayOrderLabel(browseResponse), 'Sanskrit grouped source-native browse');
assert.equal(
	wordIndexBrowseGroups(browseResponse)[0]?.order?.label,
	'Sanskrit cdsl:mw browse order'
);
assert.equal(wordIndexBrowseGroups(null).length, 0);
assert.equal(
	wordIndexBrowseItems({
		...browseResponse,
		items: [
			{
				...wordIndexBrowseGroups(browseResponse)[0]!.items[0]!,
				canonical_name: 'ह',
				canonical_key: 'ha',
				lookup: 'ha',
				display: {
					primary: 'ह',
					transliteration: 'ha',
					source_key: 'ha'
				},
				homograph_count: 22,
				source_entry_count: 22,
				source_counts: [
					{ source: 'cdsl', dictionary: 'mw', count: 20 },
					{ source: 'cdsl', dictionary: 'ap90', count: 1 },
					{ source: 'dico', dictionary: 'dico', count: 1 }
				]
			}
		]
	})[0]?.display.primary,
	'ह'
);
assert.equal(wordIndexBrowseItems(browseResponse)[0]?.display.primary, 'द');
assert.equal(
	wordIndexItemEntryCount({
		...wordIndexBrowseGroups(browseResponse)[0]!.items[0]!,
		homograph_count: 20,
		source_entry_count: 36,
		source_entries: []
	}),
	20
);
assert.equal(
	wordIndexItemEntryCount({
		...wordIndexBrowseGroups(browseResponse)[0]!.items[0]!,
		source_entry_count: 36,
		source_entries: []
	}),
	36
);
assert.equal(
	wordIndexItemEntryCount({
		...wordIndexBrowseGroups(browseResponse)[0]!.items[0]!,
		source_entries: [
			{
				source: 'cdsl',
				dictionary: 'mw',
				source_ref: 'cdsl:mw:1',
				source_order_key: 'ha:1'
			},
			{
				source: 'cdsl',
				dictionary: 'mw',
				source_ref: 'cdsl:mw:2',
				source_order_key: 'ha:2'
			}
		]
	}),
	2
);

const sections = {
	schema_version: 'langnet.word_index_sections.v1',
	request: {
		language: 'grc',
		source: 'all'
	},
	order: {
		policy: 'language-native',
		label: 'Greek alphabet sections',
		collation: 'grc-lexical',
		key: 'grc:alphabet',
		display_key: 'Α Β Γ Δ ...',
		explanation: 'Greek alphabet anchors.'
	},
	sections: [
		{
			id: 'grc:a',
			label: 'Α',
			transliteration: 'a',
			group_label: 'Greek',
			order_key: '001',
			anchor: {
				language: 'grc',
				source: 'diogenes',
				dictionary: 'lsj',
				query: 'a',
				canonical_key: 'a',
				source_order_key: '000',
				lexeme_id: 'lexeme:grc:a',
				index_entry_id: 'word-index:grc:diogenes:lsj:a',
				source_order_id: 'word-order:grc:diogenes:lsj:a'
			},
			available: true,
			entry_count: 1
		},
		{
			id: 'grc:q',
			label: 'Ϙ',
			transliteration: 'q',
			group_label: 'Greek',
			order_key: '999',
			anchor: null,
			available: false,
			entry_count: 0
		}
	],
	warnings: []
} satisfies WordIndexSectionsResponse;

assert.equal(wordIndexDisplayOrderLabel(sections), 'Greek alphabet sections');
assert.deepEqual(
	wordIndexAvailableSections(sections).map((section) => [section.label, section.anchor?.query]),
	[
		['Α', 'a'],
		['Ϙ', undefined]
	]
);
assert.deepEqual(wordIndexSectionLookupTarget(sections.sections[0]), {
	language: 'grc',
	query: 'a',
	dictionary: 'diogenes'
});
assert.equal(wordIndexSectionLookupTarget(sections.sections[1]), null);

assert.deepEqual(
	wordIndexSectionLookupTarget({
		id: 'lat:w',
		label: 'W',
		transliteration: 'w',
		group_label: 'Latin',
		order_key: '023',
		anchor: {
			language: 'lat',
			source: 'gaffiot',
			dictionary: 'gaffiot',
			query: 'w',
			canonical_key: 'walani',
			source_order_key: 'w:1',
			lexeme_id: 'lexeme:lat:walani',
			index_entry_id: 'word-index:lat:gaffiot:w',
			source_order_id: 'word-order:lat:gaffiot:w',
			display: {
				primary: 'walani',
				transliteration: 'walani',
				source_key: 'walani'
			}
		},
		available: true,
		entry_count: 1
	}),
	{
		language: 'lat',
		query: 'w',
		dictionary: 'gaffiot'
	}
);

assert.deepEqual(
	wordIndexSectionLookupTarget({
		id: 'san:velars:ka',
		label: 'क',
		transliteration: 'ka',
		group_label: 'Velars',
		order_key: '017',
		anchor: {
			language: 'san',
			source: 'cdsl',
			dictionary: 'ap90',
			query: 'k',
			canonical_key: 'ka',
			source_order_key: 'ka:1',
			lexeme_id: 'lexeme:san:ka',
			index_entry_id: 'word-index:san:cdsl:ap90:ka',
			source_order_id: 'word-order:san:cdsl:ap90:ka',
			display: {
				primary: 'क',
				transliteration: 'ka',
				source_key: 'ka'
			}
		},
		available: true,
		entry_count: 1
	}),
	{
		language: 'san',
		query: 'ka',
		dictionary: 'cdsl'
	}
);

assert.deepEqual(
	wordIndexSectionLookupTarget({
		id: 'san:vowels:aa',
		label: 'आ',
		transliteration: 'ā',
		group_label: 'Vowels',
		order_key: '002',
		anchor: {
			language: 'san',
			source: 'cdsl',
			dictionary: 'ap90',
			query: 'A',
			canonical_key: 'aa',
			source_order_key: 'a:1',
			lexeme_id: 'lexeme:san:aa',
			index_entry_id: 'word-index:san:cdsl:ap90:aa',
			source_order_id: 'word-order:san:cdsl:ap90:aa',
			display: {
				primary: 'आ',
				transliteration: 'ā',
				source_key: 'A'
			}
		},
		available: true,
		entry_count: 1
	}),
	{
		language: 'san',
		query: 'ā',
		dictionary: 'cdsl'
	}
);

const sectionFixture = {
	schema_version: 'langnet.word_index_sections.v1',
	request: {
		language: 'san',
		source: 'all'
	},
	sections: [
		{
			id: 'san:dentals:d',
			label: 'द',
			transliteration: 'd',
			group_label: 'Dentals',
			order_key: '034',
			anchor: null,
			available: true,
			entry_count: 1
		},
		{
			id: 'san:dentals:dh',
			label: 'ध',
			transliteration: 'dh',
			group_label: 'Dentals',
			order_key: '035',
			anchor: null,
			available: true,
			entry_count: 1
		}
	],
	warnings: []
} satisfies WordIndexSectionsResponse;

function wordIndexItem(overrides: Partial<WordIndexItem>): WordIndexItem {
	return {
		lexeme_id: 'lexeme:test',
		wheel_id: 'wheel:test',
		wheel_order_key: '',
		index_entry_id: 'index:test',
		source_order_id: 'order:test',
		language: 'san',
		source: 'cdsl',
		dictionary: 'mw',
		kind: 'headword',
		canonical_name: 'धात्रीपुत्र',
		canonical_key: 'dhaatriiputra',
		source_name: 'DAtrIputra',
		lookup: 'dhaatriiputra',
		display: {
			primary: 'धात्रीपुत्र',
			transliteration: 'dhātrīputra',
			source_key: 'DAtrIputra'
		},
		sort_key: 'dhaatriiputra',
		source_order_key: 'dhaatriiputra:1',
		source_ref: 'cdsl:mw:test',
		ids: {
			lexeme: 'lexeme:test',
			wheel: 'wheel:test',
			index_entry: 'index:test',
			source_order: 'order:test',
			source_ref: 'cdsl:mw:test'
		},
		encounter: {
			language: 'san',
			q: 'dhaatriiputra',
			dictionary: 'cdsl'
		},
		metadata: {},
		source_entries: [],
		...overrides
	};
}

assert.equal(wordIndexSectionForItem(wordIndexItem({}), sectionFixture)?.label, 'ध');
assert.equal(
	wordIndexActiveSection(
		{
			...baseResponse,
			request: { ...baseResponse.request, language: 'san' },
			neighborhood: {
				groups: [],
				anchor: wordIndexItem({}),
				items: []
			}
		},
		sectionFixture
	)?.id,
	'san:dentals:dh'
);

assert.equal(
	wordIndexSectionForItem(
		wordIndexItem({
			language: 'lat',
			canonical_name: 'ratio',
			canonical_key: 'ratio',
			lookup: 'ratio',
			display: { primary: 'ratio', transliteration: 'ratio', source_key: 'ratio' },
			encounter: { language: 'lat', q: 'ratio', dictionary: 'all' }
		}),
		{
			schema_version: 'langnet.word_index_sections.v1',
			request: { language: 'lat', source: 'all' },
			sections: [
				{
					id: 'lat:r',
					label: 'R',
					transliteration: 'r',
					group_label: 'Latin',
					order_key: '018',
					anchor: null,
					available: true,
					entry_count: 1
				}
			],
			warnings: []
		}
	)?.label,
	'R'
);

assert.equal(
	wordIndexSectionForItem(
		wordIndexItem({
			language: 'grc',
			canonical_name: 'θεός',
			canonical_key: 'theos',
			lookup: 'theos',
			display: { primary: 'θεός', transliteration: 'theos', source_key: 'theos' },
			encounter: { language: 'grc', q: 'theos', dictionary: 'all' }
		}),
		{
			schema_version: 'langnet.word_index_sections.v1',
			request: { language: 'grc', source: 'all' },
			sections: [
				{
					id: 'grc:t',
					label: 'Τ',
					transliteration: 't',
					group_label: 'Greek',
					order_key: '019',
					anchor: null,
					available: true,
					entry_count: 1
				},
				{
					id: 'grc:th',
					label: 'Θ',
					transliteration: 'th',
					group_label: 'Greek',
					order_key: '008',
					anchor: null,
					available: true,
					entry_count: 1
				}
			],
			warnings: []
		}
	)?.label,
	'Θ'
);
