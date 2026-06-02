import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import type { ReaderCatalog, ReaderStructureResponse, ReaderWorkDossierResponse } from './reader';
import {
	buildReaderTokenParts,
	cleanReaderToken,
	buildReaderRouteSearch,
	parseReaderRouteState,
	readerAddressRouteValue,
	readerDiscoverySortValues,
	readerFacetValuesForLanguage,
	readerShelfRouteState,
	readerAuthorRouteStateFromWork,
	readerAuthorMatchesId,
	readerIndexSummaryLabel,
	readerLanguageLabel,
	readerLoadingStatusLabel,
	readerPopularityLabel,
	readerSegmentDisplayText,
	readerSegmentTransliterationText,
	readerWorkDiscoveryTags,
	readerWorkDisplayAuthor,
	readerWorkContributorLabels,
	readerWorkListDiscriminator,
	readerWorkLabel,
	readerWorkListLabel,
	readerWorkRef,
	readerCatalogDefaults,
	readerHasIndexStats,
	readerIndexStatsKey,
	readerProductCatalogs,
	resolveReaderCatalogChoice
} from './reader';

const readerSource = readFileSync(new URL('./reader.ts', import.meta.url), 'utf8');

assert.ok(readerSource.includes('export type ReaderStructureNode'));
assert.ok(readerSource.includes('export type ReaderStructureResponse'));
assert.ok(readerSource.includes('export type ReaderWorkDossierResponse'));

assert.equal(cleanReaderToken('λόγος;'), 'λόγος');
assert.equal(cleanReaderToken('“nox”'), 'nox');
assert.equal(cleanReaderToken('येनाक्षरसमाम्नायमधिगम्य'), 'येनाक्षरसमाम्नायमधिगम्य');

assert.equal(readerLanguageLabel('san'), 'Sanskrit');
assert.equal(readerLanguageLabel('grc'), 'Greek');
assert.equal(readerLanguageLabel('lat'), 'Latin');
assert.equal(readerLoadingStatusLabel('Searching texts', 0), 'Searching texts');
assert.equal(readerLoadingStatusLabel('Searching texts', 4), 'Searching texts... 4s');
assert.equal(readerLoadingStatusLabel('Searching texts', 65), 'Searching texts... 1m 5s');

const structurePayload: ReaderStructureResponse = {
	schema_version: 'langnet.reader.v1',
	mode: 'structure',
	catalog_path: 'catalog.duckdb',
	request: { work_ref: 'urn:cts:sanskritLit:mbh.bhg' },
	summary: {
		node_count: 1,
		top_level_count: 1,
		kinds: ['chapter'],
		has_division_metadata: true
	},
	items: [
		{
			work_id: 'urn:cts:sanskritLit:mbh.bhg',
			node_id: 'bhg-09',
			parent_node_id: null,
			level: 1,
			kind: 'chapter',
			object_type: 'chapter',
			label: 'Rāja Vidyā Rāja Guhya Yoga',
			native_label: 'राजविद्याराजगुह्ययोग',
			ordinal: 9,
			start_citation: '231273',
			end_citation: '231341',
			provenance: 'curated',
			confidence: 'high',
			status: 'accepted',
			note: 'fixture',
			source_file: 'fixture',
			summary: 'A reviewed chapter note.',
			short_label: 'Royal knowledge',
			traditional_reference: 'BhG 9',
			provenance_chips: ['Curated', 'Reviewed'],
			word_count: 10,
			word_count_method: 'whitespace_tokens'
		}
	]
};

assert.equal(structurePayload.items[0].traditional_reference, 'BhG 9');

const dossierPayload: ReaderWorkDossierResponse = {
	schema_version: 'langnet.reader.v1',
	mode: 'work-dossier',
	catalog_path: 'catalog.duckdb',
	request: { work_ref: 'urn:cts:sanskritLit:mbh.bhg' },
	work: {
		work_id: 'urn:cts:sanskritLit:mbh.bhg',
		collection_id: 'sanskrit_dcs',
		language: 'san',
		title: 'Bhagavadgītā',
		author: 'Vyāsa',
		author_id: null,
		source_id: 'mbh.bhg',
		cts_work_urn: 'urn:cts:sanskritLit:mbh.bhg'
	},
	summary: {
		structure_count: 1,
		top_level_count: 1,
		top_level_kind: 'chapter',
		structure_label: '1 chapter',
		division_bio_count: 1,
		has_division_metadata: true
	},
	headings: structurePayload.items,
	division_bios: structurePayload.items,
	provenance_chips: ['Curated', 'Reviewed']
};

assert.equal(dossierPayload.summary.structure_label, '1 chapter');
assert.equal(dossierPayload.division_bios[0].traditional_reference, 'BhG 9');

const readerCatalogFixture: ReaderCatalog[] = [
	{
		id: 'classics',
		label: 'Classics audit',
		path: '/catalogs/classics.duckdb',
		languages: ['grc', 'lat'],
		readiness: 'audit_artifact',
		available: true,
		work_count: 6625,
		segment_count: 9000000,
		description: 'Classics audit artifact.'
	},
	{
		id: 'development',
		label: 'Unified development',
		path: '/catalogs/development.duckdb',
		languages: ['san', 'grc', 'lat', 'eng'],
		readiness: 'verified',
		available: true,
		work_count: 10424,
		segment_count: 14469026,
		description: 'Verified unified local build.'
	},
	{
		id: 'default',
		label: 'Default packaged',
		path: '/catalogs/default.duckdb',
		languages: ['san', 'grc', 'lat'],
		readiness: 'packaged',
		available: true,
		work_count: 10424,
		segment_count: 14469026,
		description: 'Packaged catalog.'
	},
	{
		id: 'sanskrit',
		label: 'Sanskrit audit',
		path: '/catalogs/sanskrit.duckdb',
		languages: ['san'],
		readiness: 'audit_artifact',
		available: true,
		work_count: 977,
		segment_count: 1200000,
		description: 'Sanskrit audit artifact.'
	}
];

assert.deepEqual(
	readerProductCatalogs(readerCatalogFixture).map((catalog) => catalog.id),
	['development', 'default']
);
assert.deepEqual(readerCatalogDefaults(readerCatalogFixture), {
	san: 'development',
	grc: 'development',
	lat: 'development'
});
assert.equal(resolveReaderCatalogChoice(readerCatalogFixture, null, 'lat')?.id, 'development');
assert.equal(resolveReaderCatalogChoice(readerCatalogFixture, 'classics', 'lat')?.id, 'classics');

assert.equal(
	readerAddressRouteValue({
		addressInput: 'urn:cts:greekLit:tlg0020.tlg004 1.n',
		defaultAddress: 'Od. 3.74',
		hasWork: false,
		showAddressLookup: false
	}),
	undefined
);
assert.equal(
	readerAddressRouteValue({
		addressInput: 'urn:cts:greekLit:tlg0020.tlg004 1.n',
		defaultAddress: 'Od. 3.74',
		hasWork: false,
		showAddressLookup: true
	}),
	'urn:cts:greekLit:tlg0020.tlg004 1.n'
);

assert.equal(
	readerIndexSummaryLabel('san', 'sanskrit', {
		language: 'grc',
		catalogId: 'classics',
		workCount: 6625,
		authorCount: 900
	}),
	'Sanskrit index'
);
assert.equal(
	readerIndexSummaryLabel('san', 'sanskrit', {
		language: 'san',
		catalogId: 'sanskrit',
		workCount: 977,
		authorCount: 412
	}),
	'Sanskrit index · 977 works from 412 authors'
);
assert.equal(
	readerIndexSummaryLabel('lat', 'digiliblt', {
		language: 'lat',
		catalogId: 'digiliblt',
		workCount: 1,
		authorCount: 1
	}),
	'Latin index · 1 work from 1 author'
);
assert.equal(readerIndexStatsKey('san', 'development'), 'san:development');
assert.equal(
	readerHasIndexStats(
		[
			{
				language: 'san',
				catalogId: 'development',
				workCount: 977,
				authorCount: 412
			}
		],
		'san',
		'development'
	),
	true
);
assert.equal(
	readerHasIndexStats(
		[
			{
				language: 'san',
				catalogId: 'development',
				workCount: 977,
				authorCount: 412
			}
		],
		'grc',
		'development'
	),
	false
);

const work = {
	work_id: 'langnet:reader:tlg:tlg0012.002',
	collection_id: 'tlg',
	language: 'grc' as const,
	title: 'Odyssea',
	author: 'Homer',
	author_id: 'urn:cts:greekLit:tlg0012',
	source_author: 'Homer',
	source_id: 'tlg0012.002',
	cts_work_urn: 'urn:cts:greekLit:tlg0012.tlg002',
	canonical_text_id: 'urn:ctsv2:grc:odyssey-andra-moi-ennepe',
	canonical_address: 'urn:ctsv2:grc:odyssey-andra-moi-ennepe',
	classification_discovery_group_id: 'epic',
	classification_discovery_tags: 'epic|homeric|poetry',
	classification_global_popularity_score: 99,
	classification_global_popularity_tier: 'canonical',
	classification_group_popularity_score: 98,
	classification_group_popularity_tier: 'canonical',
	word_count: 121000
};

assert.equal(readerWorkRef(work), 'urn:ctsv2:grc:odyssey-andra-moi-ennepe');
assert.equal(readerWorkLabel(work), 'Homer, Odyssea');
assert.equal(readerWorkListLabel(work, [work]), 'Odyssea');
assert.equal(readerWorkDisplayAuthor(work), 'Homer');
assert.deepEqual(readerWorkDiscoveryTags(work), ['epic', 'homeric', 'poetry']);
assert.equal(readerPopularityLabel(work), 'Canonical · 99 global · 98 group');
assert.deepEqual(readerAuthorRouteStateFromWork(work), {
	readerView: 'authors',
	authorId: 'urn:cts:greekLit:tlg0012',
	authorName: 'Homer'
});

const sudaLexicon = {
	...work,
	work_id: 'langnet:reader:tlg:tlg9010.001',
	title: 'Lexicon',
	author: 'Unknown',
	author_id: 'tlg9010',
	source_author: 'Soudas',
	source_author_id: 'tlg9010',
	source_id: 'tlg9010.001',
	cts_work_urn: 'urn:cts:greekLit:tlg9010.tlg001',
	canonical_author_id: 'urn:cts:langnet:author.grc.unknown',
	canonical_author_name: 'Unknown',
	canonical_author_kind: 'anonymous_label'
};

assert.equal(readerWorkDisplayAuthor(sudaLexicon), 'Soudas');
assert.equal(readerWorkLabel(sudaLexicon), 'Soudas, Lexicon');
assert.deepEqual(readerAuthorRouteStateFromWork(sudaLexicon), {
	readerView: 'authors',
	authorId: 'tlg9010',
	authorName: 'Soudas'
});

assert.deepEqual(
	readerWorkContributorLabels({
		...work,
		title: 'Revelation (Apocalypse)',
		author: 'Saint Jerome',
		canonical_author_name: 'Saint Jerome',
		translator_names: ['Saint Jerome'],
		traditional_author_names: ['John of Patmos'],
		attributed_author_names: ['John of Patmos']
	}),
	['Saint Jerome, translator', 'John of Patmos, traditional author']
);

assert.equal(
	readerAuthorMatchesId(
		{
			author_id: 'tlg0020',
			source_author_id: 'urn:cts:greekLit:tlg0020',
			display_name: 'Hesiod',
			author: 'Hesiod',
			index_name: 'Hesiod',
			native_name: 'Hesiod',
			section_key: 'Η',
			language: 'grc',
			work_count: 8,
			alternate_names: [],
			sort_key: 'hesiod',
			canonical_author_id: 'urn:cts:greekLit:tlg0020'
		},
		'urn:cts:greekLit:tlg0020'
	),
	true
);

const hesiodFragmentA = {
	...work,
	work_id: 'langnet:reader:tlg:tlg0020.004',
	title: 'Fragmenta',
	author: 'Hesiod',
	source_id: 'tlg0020.004',
	cts_work_urn: 'urn:cts:greekLit:tlg0020.tlg004'
};
const hesiodFragmentB = {
	...work,
	work_id: 'langnet:reader:tlg:tlg0020.007',
	title: 'Fragmenta',
	author: 'Hesiod',
	source_id: 'tlg0020.007',
	cts_work_urn: 'urn:cts:greekLit:tlg0020.tlg007'
};
assert.equal(readerWorkListLabel(hesiodFragmentA, [hesiodFragmentA, hesiodFragmentB]), 'Fragmenta');
assert.equal(
	readerWorkListDiscriminator(hesiodFragmentA, [hesiodFragmentA, hesiodFragmentB]),
	'tlg0020.004'
);
assert.equal(readerWorkListLabel(hesiodFragmentB, [hesiodFragmentA, hesiodFragmentB]), 'Fragmenta');
assert.equal(
	readerWorkListDiscriminator(hesiodFragmentB, [hesiodFragmentA, hesiodFragmentB]),
	'tlg0020.007'
);

assert.equal(
	readerSegmentDisplayText({
		segment_id: 's1',
		work_id: 'w1',
		edition_id: 'e1',
		segment_kind: 'sentence',
		citation_path: '1',
		text: 'kascit',
		display: {
			primary: 'कश्चित्'
		}
	}),
	'कश्चित्'
);

assert.deepEqual(
	parseReaderRouteState(
		new URLSearchParams(
			'language=lat&catalog=digiliblt&q=vergil&author_section=V&author=vergilius&authors_cursor=authors-4&works_cursor=works-2&contents_cursor=contents-3&page_cursor=page-9&collection=poetry&work=urn%3Acts%3AlatinLit%3Aphi0690.phi003&segment=4.1&word=arma&theme=vespers'
		)
	),
	{
		language: 'lat',
		catalogId: 'digiliblt',
		query: 'vergil',
		authorSection: 'V',
		authorId: 'vergilius',
		authorsCursor: 'authors-4',
		worksCursor: 'works-2',
		contentsCursor: 'contents-3',
		pageCursor: 'page-9',
		collection: 'poetry',
		work: 'urn:cts:latinLit:phi0690.phi003',
		segment: '4.1',
		selectedWord: 'arma',
		theme: 'vespers'
	}
);

assert.deepEqual(
	parseReaderRouteState(
		new URLSearchParams(
			'lang=san&view=shelves&group=medicine&tag=ayurveda&sort=group-popularity&agent_kind=person&historicity=historical&works_cursor=5'
		)
	),
	{
		language: 'san',
		readerView: 'shelves',
		discoveryGroup: 'medicine',
		discoveryTag: 'ayurveda',
		discoverySort: 'group-popularity',
		authorAgentKind: 'person',
		authorHistoricity: 'historical',
		worksCursor: '5'
	}
);

assert.deepEqual(parseReaderRouteState(new URLSearchParams('lang=san&view=discover')), {
	language: 'san',
	readerView: 'shelves'
});

assert.deepEqual(
	parseReaderRouteState(
		new URLSearchParams('lang=grc&view=search&text_q=logos&search_mode=fuzzy&search_cursor=20')
	),
	{
		language: 'grc',
		readerView: 'search',
		textQuery: 'logos',
		textSearchMode: 'fuzzy',
		textSearchCursor: '20'
	}
);

assert.deepEqual(
	parseReaderRouteState(
		new URLSearchParams(
			'lang=grc&view=shelves&work_author=urn%3Acts%3AgreekLit%3Atlg0012&work_author_label=Homer'
		)
	),
	{
		language: 'grc',
		readerView: 'shelves',
		discoveryAuthorId: 'urn:cts:greekLit:tlg0012',
		discoveryAuthorLabel: 'Homer'
	}
);

assert.equal(
	parseReaderRouteState(new URLSearchParams('lang=grc&translit=1')).transliteration,
	true
);

assert.deepEqual(parseReaderRouteState(new URLSearchParams('lang=grc&theme=bad')), {
	language: 'grc'
});

const search = buildReaderRouteSearch({
	language: 'grc',
	catalogId: 'classics',
	query: '',
	authorSection: '',
	authorId: 'urn:cts:greekLit:tlg0012',
	authorsCursor: '50',
	work: 'urn:cts:greekLit:tlg0012.tlg002',
	segment: '3.74',
	selectedWord: 'λόγος',
	readerView: 'shelves',
	discoveryGroup: 'medicine',
	discoveryTag: 'hippocratic_galenic_medicine',
	discoveryAuthorId: 'urn:cts:greekLit:tlg0012',
	discoveryAuthorLabel: 'Homer',
	discoverySort: 'group-popularity',
	authorAgentKind: 'person',
	authorHistoricity: 'historical',
	transliteration: true,
	theme: 'vespers'
});
assert.equal(
	search,
	'?lang=grc&catalog=classics&view=shelves&group=medicine&tag=hippocratic_galenic_medicine&work_author=urn%3Acts%3AgreekLit%3Atlg0012&work_author_label=Homer&sort=group-popularity&agent_kind=person&historicity=historical&author=urn%3Acts%3AgreekLit%3Atlg0012&authors_cursor=50&work=urn%3Acts%3AgreekLit%3Atlg0012.tlg002&segment=3.74&word=%CE%BB%CF%8C%CE%B3%CE%BF%CF%82&theme=vespers&translit=1'
);

assert.equal(
	buildReaderRouteSearch({
		language: 'grc',
		readerView: 'search',
		textQuery: 'logos',
		textSearchMode: 'fuzzy',
		textSearchCursor: '20'
	}),
	'?lang=grc&view=search&text_q=logos&search_mode=fuzzy&search_cursor=20'
);

const sampleTags = [
	{ id: 'ayurveda', label: 'Ayurveda', description: '' },
	{ id: 'vyakarana', label: 'Vyakarana', description: '' },
	{ id: 'tragedy', label: 'Tragedy', description: '' },
	{ id: 'roman_law', label: 'Roman Law', description: '' },
	{
		id: 'hippocratic_galenic_medicine',
		label: 'Hippocratic/Galenic Medicine',
		description: ''
	},
	{ id: 'grammar', label: 'Grammar', description: '' }
];

assert.deepEqual(
	readerFacetValuesForLanguage(sampleTags, 'grc').map((tag) => tag.id),
	['tragedy', 'hippocratic_galenic_medicine', 'grammar']
);
assert.deepEqual(
	readerFacetValuesForLanguage(sampleTags, 'lat').map((tag) => tag.id),
	['tragedy', 'roman_law', 'hippocratic_galenic_medicine', 'grammar']
);
assert.deepEqual(
	readerFacetValuesForLanguage(sampleTags, 'san').map((tag) => tag.id),
	['ayurveda', 'vyakarana', 'grammar']
);

assert.deepEqual(
	readerDiscoverySortValues([
		{ id: 'catalog', label: 'Catalog order', description: '' },
		{ id: 'global-popularity', label: 'Global popularity', description: '' },
		{ id: 'group-popularity', label: 'Group popularity', description: '' },
		{ id: 'popularity', label: 'Legacy popularity', description: '' }
	]).map((sort) => sort.id),
	['catalog', 'global-popularity', 'group-popularity']
);

assert.deepEqual(
	readerShelfRouteState({
		id: 'rhetoric',
		label: 'Rhetoric',
		description: '',
		query: { group: 'rhetoric', sort: 'group-popularity' },
		work_count: 145,
		classified_work_count: 145,
		author_count: 85,
		sample_works: []
	}),
	{
		discoveryGroup: 'rhetoric',
		discoveryTag: '',
		discoverySort: 'group-popularity'
	}
);
assert.deepEqual(
	readerShelfRouteState({
		id: 'ayurveda',
		label: 'Ayurveda',
		description: '',
		query: { tag: 'ayurveda', sort: 'group-popularity' },
		work_count: 50,
		classified_work_count: 50,
		author_count: 8,
		sample_works: []
	}),
	{
		discoveryGroup: '',
		discoveryTag: 'ayurveda',
		discoverySort: 'group-popularity'
	}
);

const greekSegment = {
	segment_id: 's2',
	work_id: 'w1',
	edition_id: 'e1',
	segment_kind: 'line',
	citation_path: '1.1',
	text: 'ἄνδρα μοι ἔννεπε',
	transliteration: 'andra moi ennepe'
};

assert.equal(readerSegmentTransliterationText(greekSegment), 'andra moi ennepe');
assert.deepEqual(
	buildReaderTokenParts(greekSegment, 'grc', true)
		.filter((part) => part.isWord)
		.map((part) => [part.word, part.transliteration]),
	[
		['ἄνδρα', 'andra'],
		['μοι', 'moi'],
		['ἔννεπε', 'ennepe']
	]
);

assert.deepEqual(
	buildReaderTokenParts(
		{
			...greekSegment,
			transliteration: ''
		},
		'grc',
		true
	)
		.filter((part) => part.isWord)
		.map((part) => [part.word, part.transliteration]),
	[
		['ἄνδρα', 'andra'],
		['μοι', 'moi'],
		['ἔννεπε', 'ennepe']
	]
);

assert.equal(
	buildReaderTokenParts(greekSegment, 'grc', false).some((part) => part.transliteration),
	false
);

console.log('reader helpers ok');
