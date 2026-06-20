import type { LanguageMode } from '../search-data';
import { tagIsRelevantForLanguage } from './reader-discovery-tags';
import { readerWorkPublicKey } from './reader-public-keys';

export * from './text';
export {
	readerIsDeprecatedWorkRef,
	readerSourceIndexPublicKey,
	readerWorkPublicKey
} from './reader-public-keys';
export {
	readerWordContextEvidenceItemLabel,
	readerWordContextItemSourceLabel,
	readerWordContextMorphologyItemLabel,
	readerWordContextStatusLabel
} from './reader-word-context';

export type ReaderCatalogLanguage = LanguageMode | 'eng' | 'und';

export type ReaderCatalog = {
	id: string;
	label: string;
	path: string;
	languages: ReaderCatalogLanguage[];
	readiness: string;
	available: boolean;
	work_count?: number;
	segment_count?: number;
	description: string;
};

export type ReaderCatalogsResponse = {
	schema_version: 'langnet.reader.web.v1';
	mode: 'catalogs';
	items: ReaderCatalog[];
	defaults: Partial<Record<LanguageMode, string>>;
	warnings: string[];
};

export type ReaderWork = {
	work_id: string;
	collection_id: string;
	language: LanguageMode;
	title: string;
	author: string;
	author_id: string | null;
	source_author?: string | null;
	source_author_id?: string | null;
	source_id: string;
	cts_work_urn: string | null;
	canonical_text_id?: string | null;
	canonical_address?: string | null;
	work_kind?: string;
	parent_work_id?: string | null;
	start_citation?: string | null;
	end_citation?: string | null;
	word_count?: number;
	word_count_method?: string;
	classification_category?: string | null;
	classification_period?: string | null;
	classification_date_range?: string | null;
	classification_authorship_status?: string | null;
	classification_popularity_tier?: string | null;
	classification_scope?: string | null;
	classification_discovery_group_id?: string | null;
	classification_discovery_tags?: string | null;
	classification_global_popularity_score?: number | null;
	classification_global_popularity_tier?: string | null;
	classification_group_popularity_score?: number | null;
	classification_group_popularity_tier?: string | null;
	classification_confidence?: string | null;
	classification_notes?: string | null;
	canonical_author_id?: string | null;
	canonical_author_name?: string | null;
	canonical_author_kind?: string | null;
	translator_names?: string[];
	traditional_author_names?: string[];
	attributed_author_names?: string[];
	metadata_attributions?: {
		relation_type: string;
		agent: string;
		status: string;
		confidence: string;
		note?: string;
		evidence_citation?: string;
		evidence_label?: string;
	}[];
};

export type ReaderAuthorSection = {
	key: string;
	label: string;
	native_label: string;
	sort_key: string;
	author_count: number;
	work_count: number;
};

export type ReaderIndexStats = {
	language: LanguageMode;
	catalogId: string;
	workCount: number;
	authorCount: number;
};

export type ReaderAuthor = {
	author_id: string;
	source_author_id: string;
	display_name: string;
	author: string;
	index_name: string;
	native_name: string;
	section_key: string;
	language: LanguageMode;
	work_count: number;
	alternate_names: string[];
	sort_key: string;
	canonical_author_id?: string | null;
	canonical_author_name?: string | null;
	canonical_author_kind?: string | null;
};

export type ReaderStructureNode = {
	work_id: string;
	node_id: string;
	parent_node_id?: string | null;
	level: number;
	kind: string;
	object_type: string;
	label: string;
	native_label?: string | null;
	ordinal: number;
	start_citation: string;
	end_citation: string;
	provenance: string;
	confidence: string;
	status: string;
	note?: string;
	source_file?: string;
	canonical_text_id?: string | null;
	canonical_address?: string | null;
	summary?: string | null;
	short_label?: string | null;
	traditional_reference?: string | null;
	division_metadata_status?: string | null;
	division_review_status?: string | null;
	division_confidence?: string | null;
	division_evidence_count?: number | null;
	provenance_chips?: string[];
	word_count?: number;
	word_count_method?: string;
};

export type ReaderStructureResponse = {
	schema_version: string;
	mode: 'structure';
	catalog_path: string;
	request: {
		work_ref: string;
	};
	summary: {
		node_count: number;
		top_level_count: number;
		kinds: string[];
		has_division_metadata: boolean;
	};
	items: ReaderStructureNode[];
};

export type ReaderWorkDossierResponse = {
	schema_version: string;
	mode: 'work-dossier';
	catalog_path: string;
	request: {
		work_ref: string;
	};
	work: ReaderWork | null;
	summary: {
		structure_count: number;
		top_level_count: number;
		top_level_kind: string;
		structure_label: string;
		division_bio_count: number;
		has_division_metadata: boolean;
	};
	headings: ReaderStructureNode[];
	division_bios: ReaderStructureNode[];
	provenance_chips?: string[];
};

export type ReaderSegment = {
	segment_id: string;
	work_id: string;
	edition_id: string;
	segment_kind: string;
	citation_path: string;
	text: string;
	source_text?: string | null;
	normalized_text?: string;
	sort_key?: number;
	address?: string;
	address_kind?: string;
	stored_address?: string;
	canonical_text_id?: string | null;
	canonical_address?: string | null;
	language?: LanguageMode;
	script?: string;
	transliteration?: string;
	native_script?: string;
	available_layers?: string[];
	current_divisions?: ReaderStructureNode[];
	display?: {
		primary?: string;
		transliteration?: string;
		script?: string;
		transliteration_script?: string;
		available_layers?: string[];
		native_script?: string;
	};
	artifact?: {
		artifact_id?: string;
		work_id?: string;
		edition_id?: string;
		artifact_path?: string;
		source_path?: string;
		adapter?: string;
		source_hash?: string;
		segment_count?: number;
		token_count?: number;
	};
};

export type ReaderContentsResponse = {
	schema_version: string;
	mode: 'contents';
	catalog_path: string;
	request: {
		work_id: string;
		limit: number;
	};
	items: ReaderSegment[];
	pagination?: {
		next_cursor: string | null;
		prev_cursor: string | null;
		limit: number;
	};
	window?: {
		anchor: string;
		before_count: number;
		after_count: number;
	};
};

export type ReaderShowResponse = {
	schema_version: string;
	mode: 'show' | 'resolve-address';
	catalog_path: string;
	address: string;
	work_ref?: string;
	citation_path?: string;
	resolved_address?: string;
	resolution_status?: 'resolved' | 'not_found';
	resolution_kind?: 'segment' | 'citation_reference' | 'structure' | 'not_found';
	segment: ReaderSegment | null;
	segments?: ReaderSegment[];
	structure_node?: ReaderStructureNode | null;
	current_divisions?: ReaderStructureNode[];
	navigation?: {
		previous: ReaderNavigationTarget | null;
		next: ReaderNavigationTarget | null;
	};
};

export type ReaderWorksResponse = {
	schema_version: string;
	mode: 'works';
	catalog_path: string;
	request: Record<string, unknown>;
	items: ReaderWork[];
	pagination?: {
		limit: number;
		next_cursor: string | null;
		prev_cursor: string | null;
		total_filtered?: number;
	};
};

export type ReaderSourceIndexItem = {
	collection_id: string;
	language: ReaderCatalogLanguage;
	work_id: string;
	title: string;
	author: string;
	author_id: string | null;
	source_id: string;
	cts_work_urn: string | null;
	canonical_text_id: string | null;
	edition_id: string | null;
	edition_label: string;
	source_path: string;
	cts_edition_urn: string | null;
	file_role: string;
	file_status: string;
	source_hash: string;
	size_bytes?: number;
	artifact_count: number;
	segment_count: number;
	token_count: number;
	adapters: string;
	artifact_paths: string;
	source_witness_count: number;
	source_witness_collections: string;
};

export type ReaderSourceIndexResponse = {
	schema_version: string;
	mode: 'source-index';
	catalog_path: string;
	request: Record<string, unknown>;
	items: ReaderSourceIndexItem[];
	pagination?: {
		limit: number;
		next_cursor: string | null;
		prev_cursor: string | null;
	};
	catalog?: ReaderCatalog;
};

export type ReaderSearchQueryCandidate = {
	query: string;
	kind: string;
	field: string;
	rank: number;
	concept_id?: string;
	concept_label?: string;
	explanation?: string;
	source_file?: string;
};

export type ReaderSearchContextLine = {
	citation_path: string;
	text: string;
	sort_key?: number;
};

export type ReaderSearchResult = {
	score: number;
	work_id: string;
	collection_id: string;
	language: LanguageMode;
	title: string;
	author: string;
	canonical_author_id?: string | null;
	canonical_author_name?: string | null;
	cts_work_urn?: string | null;
	canonical_text_id?: string | null;
	canonical_address?: string | null;
	citation_path: string;
	segment_id: string;
	sort_key?: number;
	text: string;
	snippet: string;
	context_before?: ReaderSearchContextLine[];
	context_after?: ReaderSearchContextLine[];
	target?: {
		reader_command?: string;
		work_ref?: string;
		segment?: string;
	};
	matched_query?: string;
	input_query?: string;
	match_type?: string;
	candidate_rank?: number;
	matched_field?: string;
};

export type ReaderSearchMode = 'keyword' | 'phrase' | 'exact' | 'fuzzy';

export type ReaderSearchResponse = {
	schema_version: string;
	mode: 'search';
	catalog_path: string;
	index_path: string;
	request: {
		query: string;
		language?: LanguageMode | null;
		collection_id?: string | null;
		search_mode?: ReaderSearchMode;
		field?: string;
		query_candidates?: ReaderSearchQueryCandidate[];
	};
	items: ReaderSearchResult[];
	pagination?: {
		limit: number;
		next_cursor: string | null;
		prev_cursor: string | null;
	};
};

export type ReaderWordContextEvidenceItem = {
	lemma?: string;
	source_tool?: string;
	source_label?: string;
	gloss?: string;
	evidence_gloss?: string;
	source_ref?: string;
	bucket_id?: string;
	witness_id?: string;
	confidence_label?: string;
};

export type ReaderWordContextMorphologyItem = {
	source_tool?: string;
	form?: string;
	lemma?: string;
	analysis?: string;
	solution_number?: string;
};

export type ReaderWordContextResponse = {
	schema_version: string;
	mode: 'word-context';
	catalog_path: string;
	request: {
		language: LanguageMode;
		query: string;
		work_ref?: string | null;
		segment_ref?: string | null;
		search_limit?: number;
		search_context?: number;
		index_path?: string;
	};
	normalization: {
		surface: string;
		normalized?: string;
		candidates: string[];
	};
	lexical_evidence: {
		status: string;
		items: ReaderWordContextEvidenceItem[];
		note?: string;
	};
	morphology: {
		status: string;
		items: ReaderWordContextMorphologyItem[];
		note?: string;
	};
	reader_hits: {
		status: string;
		index_status: Record<string, unknown>;
		items: ReaderSearchResult[];
	};
	passage_context: {
		status: string;
		work?: ReaderWork | null;
		segment?: ReaderSegment | null;
		source_index?: ReaderSourceIndexItem[];
	};
	provenance: Record<string, unknown>;
	caveats: string[];
	timing: {
		total_ms: number;
		steps: { name: string; duration_ms: number; [key: string]: unknown }[];
	};
};

export type ReaderFacetValue = {
	id: string;
	label: string;
	description: string;
	work_count?: number;
	classified_work_count?: number;
	author_count?: number;
	max_group_popularity_score?: number;
};

export type ReaderShelfSampleWork = {
	work_id: string;
	title: string;
	author: string;
	language: LanguageMode;
	source_id: string;
	classification_group_popularity_score?: number | null;
};

export type ReaderDiscoveryShelf = {
	id: string;
	label: string;
	description: string;
	query: {
		group?: string;
		tag?: string;
		sort?: ReaderRouteState['discoverySort'];
	};
	work_count: number;
	classified_work_count: number;
	author_count: number;
	max_group_popularity_score?: number;
	sample_works: ReaderShelfSampleWork[];
};

export type ReaderFacet = {
	id: string;
	label: string;
	description: string;
	command?: string;
	filter?: string;
	values?: ReaderFacetValue[];
	examples?: {
		question: string;
		command: string;
	}[];
};

export type ReaderFacetsResponse = {
	schema_version: string;
	mode: 'facets' | 'groups' | 'tags' | 'author-facets';
	catalog_path: string;
	request: Record<string, unknown>;
	items: ReaderFacet[];
};

export type ReaderShelvesResponse = {
	schema_version: string;
	mode: 'shelves';
	catalog_path: string;
	request: Record<string, unknown>;
	items: ReaderDiscoveryShelf[];
};

export type ReaderAuthorSectionsResponse = {
	schema_version: string;
	mode: 'author-sections';
	catalog_path: string;
	request: Record<string, unknown>;
	items: ReaderAuthorSection[];
};

export type ReaderAuthorsResponse = {
	schema_version: string;
	mode: 'authors';
	catalog_path: string;
	request: Record<string, unknown>;
	items: ReaderAuthor[];
	pagination?: {
		limit: number;
		next_cursor: string | null;
		prev_cursor: string | null;
	};
};

export type ReaderAuthorResponse = {
	schema_version: string;
	mode: 'author';
	catalog_path: string;
	request: Record<string, unknown>;
	item: ReaderAuthor | null;
	representative_works?: ReaderWork[];
	works?: ReaderWork[];
	summary?: Record<string, unknown>;
};

export type ReaderWorkResponse = {
	schema_version: string;
	mode: 'work';
	catalog_path: string;
	item: ReaderWork | null;
};

export type ReaderNavigationTarget = {
	citation_path: string;
	address: string;
};

export type ReaderRouteState = {
	language: LanguageMode;
	catalogId?: string;
	readerView?: 'shelves' | 'authors' | 'search';
	address?: string;
	query?: string;
	textQuery?: string;
	textSearchMode?: ReaderSearchMode;
	textSearchCursor?: string;
	discoveryGroup?: string;
	discoveryTag?: string;
	discoveryAuthorId?: string;
	discoveryAuthorLabel?: string;
	discoverySort?: 'catalog' | 'popularity' | 'global-popularity' | 'group-popularity';
	authorAgentKind?: string;
	authorHistoricity?: string;
	authorSection?: string;
	authorId?: string;
	authorName?: string;
	authorsCursor?: string;
	worksCursor?: string;
	contentsCursor?: string;
	pageCursor?: string;
	collection?: string;
	work?: string;
	segment?: string;
	selectedWord?: string;
	theme?: 'manuscript' | 'vespers';
	transliteration?: boolean;
};

export function parseReaderRouteState(params: URLSearchParams): Partial<ReaderRouteState> {
	const language = readReaderLanguage(params);
	const theme = readReaderTheme(params.get('theme'));

	return withoutEmptyValues({
		...(language ? { language } : {}),
		catalogId: params.get('catalog') ?? undefined,
		readerView: readReaderView(params.get('view')),
		address: params.get('address') ?? undefined,
		query: params.get('q') ?? params.get('query') ?? undefined,
		textQuery: params.get('text_q') ?? params.get('textQuery') ?? undefined,
		textSearchMode: readReaderSearchMode(params.get('search_mode') ?? params.get('searchMode')),
		textSearchCursor: params.get('search_cursor') ?? params.get('searchCursor') ?? undefined,
		discoveryGroup: params.get('group') ?? undefined,
		discoveryTag: params.get('tag') ?? undefined,
		discoveryAuthorId: params.get('work_author') ?? undefined,
		discoveryAuthorLabel: params.get('work_author_label') ?? undefined,
		discoverySort: readReaderDiscoverySort(params.get('sort')),
		authorAgentKind: params.get('agent_kind') ?? params.get('agentKind') ?? undefined,
		authorHistoricity: params.get('historicity') ?? undefined,
		authorSection: params.get('author_section') ?? undefined,
		authorId: params.get('author') ?? undefined,
		authorName: params.get('author_name') ?? undefined,
		authorsCursor: params.get('authors_cursor') ?? undefined,
		worksCursor: params.get('works_cursor') ?? undefined,
		contentsCursor: params.get('contents_cursor') ?? undefined,
		pageCursor: params.get('page_cursor') ?? undefined,
		collection: params.get('collection') ?? undefined,
		work: params.get('work') ?? undefined,
		segment: params.get('segment') ?? undefined,
		selectedWord: params.get('word') ?? undefined,
		...(theme ? { theme } : {}),
		...(readReaderBoolean(params.get('translit')) ? { transliteration: true } : {})
	});
}

export function buildReaderRouteSearch(state: Partial<ReaderRouteState>) {
	const params = new URLSearchParams();
	setReaderParam(params, 'lang', state.language);
	setReaderParam(params, 'catalog', state.catalogId);
	setReaderParam(params, 'view', state.readerView);
	setReaderParam(params, 'address', state.address);
	setReaderParam(params, 'q', state.query);
	setReaderParam(params, 'text_q', state.textQuery);
	setReaderParam(params, 'search_mode', state.textSearchMode);
	setReaderParam(params, 'search_cursor', state.textSearchCursor);
	setReaderParam(params, 'group', state.discoveryGroup);
	setReaderParam(params, 'tag', state.discoveryTag);
	setReaderParam(params, 'work_author', state.discoveryAuthorId);
	setReaderParam(params, 'work_author_label', state.discoveryAuthorLabel);
	setReaderParam(params, 'sort', state.discoverySort);
	setReaderParam(params, 'agent_kind', state.authorAgentKind);
	setReaderParam(params, 'historicity', state.authorHistoricity);
	setReaderParam(params, 'author_section', state.authorSection);
	setReaderParam(params, 'author', state.authorId);
	setReaderParam(params, 'author_name', state.authorName);
	setReaderParam(params, 'authors_cursor', state.authorsCursor);
	setReaderParam(params, 'works_cursor', state.worksCursor);
	setReaderParam(params, 'contents_cursor', state.contentsCursor);
	setReaderParam(params, 'page_cursor', state.pageCursor);
	setReaderParam(params, 'collection', state.collection === 'all' ? undefined : state.collection);
	setReaderParam(params, 'work', state.work);
	setReaderParam(params, 'segment', state.segment);
	setReaderParam(params, 'word', state.selectedWord);
	setReaderParam(params, 'theme', state.theme);
	if (state.transliteration) params.set('translit', '1');

	const search = params.toString();
	return search ? `?${search}` : '';
}

export function readerWorkRef(work: ReaderWork) {
	return work.canonical_text_id || work.canonical_address || work.work_id;
}

function meaningfulAuthorName(value: string | null | undefined) {
	const name = value?.trim() ?? '';
	if (!name) return '';
	const normalized = name.toLocaleLowerCase();
	return normalized === 'unknown' || normalized === 'anonymous' ? '' : name;
}

function meaningfulAuthorId(value: string | null | undefined) {
	const id = value?.trim() ?? '';
	if (!id) return '';
	return id.includes('.unknown') ? '' : id;
}

export function readerWorkDisplayAuthor(work: ReaderWork) {
	return (
		meaningfulAuthorName(work.author) ||
		meaningfulAuthorName(work.source_author) ||
		meaningfulAuthorName(work.canonical_author_name) ||
		'Unknown'
	);
}

export function readerWorkLabel(work: ReaderWork) {
	const author = readerWorkDisplayAuthor(work);
	const title = work.title?.trim() || 'Untitled work';
	return `${author}, ${title}`;
}

export function readerWorkListLabel(work: ReaderWork, peers: ReaderWork[] = []) {
	const title = work.title?.trim() || 'Untitled work';
	return title;
}

export function readerWorkListDiscriminator(work: ReaderWork, peers: ReaderWork[] = []) {
	const title = readerWorkListLabel(work);
	const duplicateTitle = peers.some(
		(peer) =>
			peer.work_id !== work.work_id &&
			(peer.title?.trim() || 'Untitled work') === title &&
			readerWorkDisplayAuthor(peer) === readerWorkDisplayAuthor(work)
	);
	return duplicateTitle ? readerWorkPublicKey(work) : '';
}

export function readerAuthorRouteStateFromWork(work: ReaderWork): Partial<ReaderRouteState> | null {
	const canonicalAuthorId = meaningfulAuthorId(work.canonical_author_id);
	const sourceAuthorId = meaningfulAuthorId(work.source_author_id);
	const authorId = canonicalAuthorId || sourceAuthorId || meaningfulAuthorId(work.author_id);
	const authorName = readerWorkDisplayAuthor(work);
	if (!authorId && (!authorName || authorName === 'Unknown')) return null;
	return {
		readerView: 'authors',
		authorId: authorId || authorName,
		authorName: authorName || undefined
	};
}

export function readerAuthorMatchesId(author: ReaderAuthor, authorId: string) {
	return [author.author_id, author.source_author_id, author.canonical_author_id].some(
		(value) => value === authorId
	);
}

export function readerWorkDiscoveryTags(work: ReaderWork) {
	return (work.classification_discovery_tags ?? '')
		.split('|')
		.map((tag) => tag.trim())
		.filter(Boolean);
}

export function readerWorkContributorLabels(work: ReaderWork): string[] {
	const labels: string[] = [];
	const seen = new Set<string>();
	const add = (name: string | null | undefined, role: string) => {
		const trimmed = name?.trim();
		if (!trimmed) return;
		const key = `${trimmed.toLocaleLowerCase()}|${role}`;
		if (seen.has(key)) return;
		seen.add(key);
		labels.push(`${trimmed}, ${role}`);
	};

	for (const name of work.translator_names ?? []) add(name, 'translator');
	for (const name of work.traditional_author_names ?? []) add(name, 'traditional author');
	for (const name of work.attributed_author_names ?? []) {
		if (!(work.traditional_author_names ?? []).includes(name)) add(name, 'attributed author');
	}

	return labels;
}

export function readerFacetValuesForLanguage(
	values: ReaderFacetValue[],
	language: LanguageMode
): ReaderFacetValue[] {
	return values.filter((value) => tagIsRelevantForLanguage(value.id, language));
}

export function readerDiscoverySortValue(
	value: string | null | undefined
): ReaderRouteState['discoverySort'] | undefined {
	return readReaderDiscoverySort(value ?? null);
}

export function readerShelfRouteState(shelf: ReaderDiscoveryShelf) {
	const sort = readerDiscoverySortValue(shelf.query.sort) ?? 'group-popularity';
	return {
		discoveryGroup: shelf.query.group ?? '',
		discoveryTag: shelf.query.tag ?? '',
		discoverySort: sort
	};
}

export function readerDiscoverySortValues(values: ReaderFacetValue[]): ReaderFacetValue[] {
	return values.filter((value) => value.id !== 'popularity');
}

export function readerPopularityLabel(work: ReaderWork) {
	const tier =
		work.classification_global_popularity_tier ||
		work.classification_group_popularity_tier ||
		work.classification_popularity_tier ||
		'';
	const globalScore = numberLabel(work.classification_global_popularity_score);
	const groupScore = numberLabel(work.classification_group_popularity_score);
	const parts = [];
	if (tier) parts.push(titleCase(tier));
	if (globalScore) parts.push(`${globalScore} global`);
	if (groupScore) parts.push(`${groupScore} group`);
	return parts.join(' · ');
}

export function readerLanguageLabel(language: LanguageMode) {
	if (language === 'san') return 'Sanskrit';
	if (language === 'grc') return 'Greek';
	return 'Latin';
}

export function readerLoadingStatusLabel(label: string, elapsedSeconds: number) {
	const seconds = Math.max(0, Math.floor(elapsedSeconds));
	if (seconds < 1) return label;
	const minutes = Math.floor(seconds / 60);
	const remainingSeconds = seconds % 60;
	const elapsed =
		minutes > 0
			? `${minutes}m${remainingSeconds ? ` ${remainingSeconds}s` : ''}`
			: `${remainingSeconds}s`;
	return `${label}... ${elapsed}`;
}

export function readerCatalogIsAuditArtifact(catalog: ReaderCatalog) {
	return catalog.readiness === 'audit_artifact';
}

export function readerProductCatalogs(catalogs: readonly ReaderCatalog[]) {
	return catalogs.filter((catalog) => !readerCatalogIsAuditArtifact(catalog));
}

export function readerCatalogDefaults(catalogs: readonly ReaderCatalog[]) {
	const defaults: Partial<Record<LanguageMode, string>> = {};
	for (const language of ['san', 'grc', 'lat'] as const) {
		const catalogId = resolveReaderCatalogChoice(catalogs, null, language)?.id;
		if (catalogId) defaults[language] = catalogId;
	}
	return defaults;
}

export function resolveReaderCatalogChoice(
	catalogs: readonly ReaderCatalog[],
	id?: string | null,
	language?: LanguageMode
) {
	const requested = id ? catalogs.find((catalog) => catalog.id === id) : undefined;
	if (requested) return requested;

	const productCatalogs = readerProductCatalogs(catalogs).filter((catalog) => catalog.available);
	const catalogHasLanguage = (catalog: ReaderCatalog) =>
		!language || catalog.languages.includes(language);
	const preferredIds = ['development', 'default'];

	for (const preferredId of preferredIds) {
		const catalog = productCatalogs.find(
			(candidate) => candidate.id === preferredId && catalogHasLanguage(candidate)
		);
		if (catalog) return catalog;
	}

	return (
		productCatalogs.find(catalogHasLanguage) ??
		catalogs.find((catalog) => catalog.available && catalogHasLanguage(catalog)) ??
		productCatalogs[0] ??
		catalogs.find((catalog) => catalog.available)
	);
}

export function readerIndexSummaryLabel(
	language: LanguageMode,
	catalogId: string,
	stats?: ReaderIndexStats | null
) {
	const label = readerLanguageLabel(language);
	if (!stats || stats.language !== language || stats.catalogId !== catalogId || !stats.workCount) {
		return `${label} index`;
	}

	return `${label} index · ${stats.workCount} ${
		stats.workCount === 1 ? 'work' : 'works'
	} from ${stats.authorCount} ${stats.authorCount === 1 ? 'author' : 'authors'}`;
}

export function readerIndexStatsKey(language: LanguageMode, catalogId: string) {
	return `${language}:${catalogId}`;
}

export function readerHasIndexStats(
	stats: ReaderIndexStats[],
	language: LanguageMode,
	catalogId: string
) {
	const key = readerIndexStatsKey(language, catalogId);
	return stats.some((item) => readerIndexStatsKey(item.language, item.catalogId) === key);
}

export function readerAddressRouteValue({
	addressInput,
	defaultAddress,
	hasWork,
	showAddressLookup
}: {
	addressInput: string;
	defaultAddress: string;
	hasWork: boolean;
	showAddressLookup: boolean;
}) {
	const address = addressInput.trim();
	if (hasWork || !showAddressLookup || !address || address === defaultAddress) return undefined;
	return address;
}

function readReaderLanguage(params: URLSearchParams): LanguageMode | undefined {
	const value = params.get('lang') ?? params.get('language');
	if (value === 'san' || value === 'grc' || value === 'lat') return value;
	return undefined;
}

function readReaderTheme(value: string | null): ReaderRouteState['theme'] | undefined {
	if (value === 'manuscript' || value === 'vespers') return value;
	return undefined;
}

function readReaderView(value: string | null): ReaderRouteState['readerView'] | undefined {
	if (value === 'shelves' || value === 'discover') return 'shelves';
	if (value === 'search') return value;
	if (value === 'authors') return value;
	return undefined;
}

function readReaderSearchMode(value: string | null): ReaderSearchMode | undefined {
	if (value === 'keyword' || value === 'phrase' || value === 'exact' || value === 'fuzzy') {
		return value;
	}
	return undefined;
}

function readReaderDiscoverySort(
	value: string | null
): ReaderRouteState['discoverySort'] | undefined {
	if (
		value === 'catalog' ||
		value === 'popularity' ||
		value === 'global-popularity' ||
		value === 'group-popularity'
	) {
		return value;
	}
	return undefined;
}

function numberLabel(value: number | null | undefined) {
	return typeof value === 'number' && Number.isFinite(value) ? String(value) : '';
}

function titleCase(value: string) {
	return value
		.replace(/[_-]+/g, ' ')
		.replace(/\b\w/g, (letter) => letter.toUpperCase())
		.trim();
}

function readReaderBoolean(value: string | null) {
	if (!value) return false;
	const normalized = value.toLowerCase();
	return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}

function setReaderParam(params: URLSearchParams, key: string, value: string | undefined) {
	const trimmed = value?.trim();
	if (trimmed) params.set(key, trimmed);
}

function withoutEmptyValues<T extends Record<string, unknown>>(value: T) {
	return Object.fromEntries(
		Object.entries(value).filter(([, entryValue]) => {
			if (typeof entryValue === 'string') return entryValue.trim() !== '';
			return entryValue !== undefined && entryValue !== null;
		})
	) as Partial<T>;
}
