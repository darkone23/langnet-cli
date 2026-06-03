import type {
	ReaderDiscoveryShelf,
	ReaderFacetValue,
	ReaderRouteState,
	ReaderSearchQueryCandidate,
	ReaderSegment,
	ReaderWork
} from './reader';
import type { LanguageMode } from './search-data';

type ReaderIndexView = 'choose' | NonNullable<ReaderRouteState['readerView']>;

export function readerVisibleTextSearchCandidates(candidates: ReaderSearchQueryCandidate[]) {
	return candidates
		.filter((candidate) => candidate.query && candidate.kind !== 'input')
		.slice(0, 8);
}

export function readerTextSearchCandidateLabel(candidate: ReaderSearchQueryCandidate) {
	if (candidate.kind === 'concept_alias' && candidate.concept_label) {
		return `${candidate.concept_label}: ${candidate.query}`;
	}
	return candidate.query;
}

export function readerWordCountLabel(count: number | undefined) {
	if (!count) return '';
	return `${count.toLocaleString()} words`;
}

export function readerWorkMetaLine(work: ReaderWork) {
	const parts = [
		work.classification_category || work.classification_scope || '',
		work.classification_period || '',
		readerWordCountLabel(work.word_count)
	].filter(Boolean);
	return parts.join(' · ');
}

export function readerShelfMetaLabel(shelf: ReaderDiscoveryShelf) {
	const workLabel = `${shelf.work_count.toLocaleString()} ${
		shelf.work_count === 1 ? 'work' : 'works'
	}`;
	const authorLabel = shelf.author_count
		? `${shelf.author_count.toLocaleString()} ${shelf.author_count === 1 ? 'author' : 'authors'}`
		: '';
	return [workLabel, authorLabel].filter(Boolean).join(' · ');
}

export function readerAuthorSectionRomanHint(nextLanguage: LanguageMode, key: string) {
	if (nextLanguage === 'grc') {
		const hints: Record<string, string> = {
			Α: 'A',
			Β: 'B',
			Γ: 'G',
			Δ: 'D',
			Ε: 'E',
			Ζ: 'Z',
			Η: 'E',
			Θ: 'Th',
			Ι: 'I',
			Κ: 'K',
			Λ: 'L',
			Μ: 'M',
			Ν: 'N',
			Ξ: 'X',
			Ο: 'O',
			Π: 'P',
			Ρ: 'R',
			Σ: 'S',
			Τ: 'T',
			Υ: 'Y',
			Φ: 'Ph'
		};
		return hints[key] ?? '';
	}
	if (nextLanguage === 'san') {
		const hints: Record<string, string> = {
			अ: 'a',
			आ: 'aa',
			ई: 'ii',
			उ: 'u',
			ऐ: 'ai',
			क: 'ka',
			ग: 'ga',
			घ: 'gha',
			च: 'ca',
			छ: 'cha',
			ज: 'ja',
			त: 'ta',
			द: 'da',
			ध: 'dha',
			न: 'na',
			प: 'pa',
			ब: 'ba',
			भ: 'bha',
			म: 'ma',
			य: 'ya',
			र: 'ra',
			ल: 'la',
			व: 'va',
			श: 'sha',
			ष: 'ssa',
			स: 'sa',
			ह: 'ha'
		};
		return hints[key] ?? '';
	}
	return '';
}

export function readerCitationRangeLabel(items: ReaderSegment[], fallback: ReaderSegment | null) {
	const first = items[0]?.citation_path;
	const last = items[items.length - 1]?.citation_path;
	if (first && last && first !== last) return `${first} - ${last}`;
	return first || fallback?.citation_path || '';
}

export function deriveReaderPagePagination(items: ReaderSegment[], pageLimit: number) {
	const firstSortKey = items[0]?.sort_key;
	const lastSortKey = items[items.length - 1]?.sort_key;
	return {
		previous:
			typeof firstSortKey === 'number' && firstSortKey > pageLimit
				? String(Math.max(0, firstSortKey - 1 - pageLimit))
				: null,
		next: typeof lastSortKey === 'number' ? String(lastSortKey) : null
	};
}

export function readerDiscoverySummaryLabel({
	discoveryGroup,
	discoveryTag,
	workQuery,
	discoveryAuthorLabel,
	discoveryGroups,
	discoveryTags,
	languageLabel
}: {
	discoveryGroup: string;
	discoveryTag: string;
	workQuery: string;
	discoveryAuthorLabel: string;
	discoveryGroups: ReaderFacetValue[];
	discoveryTags: ReaderFacetValue[];
	languageLabel: string;
}) {
	const parts = [];
	if (discoveryGroup) parts.push(facetValueLabel(discoveryGroups, discoveryGroup));
	if (discoveryTag) parts.push(facetValueLabel(discoveryTags, discoveryTag));
	if (!parts.length && workQuery.trim()) parts.push(`Search: ${workQuery.trim()}`);
	if (discoveryAuthorLabel) parts.push(discoveryAuthorLabel);
	if (!parts.length) parts.push(`${languageLabel} works`);
	return parts.join(' · ');
}

export function readerDiscoveryTitleLabel({
	readerView,
	activeDiscoverySummary,
	textQuery,
	activeAuthorSection,
	workQuery,
	languageLabel
}: {
	readerView: ReaderIndexView;
	activeDiscoverySummary: string;
	textQuery: string;
	activeAuthorSection: string;
	workQuery: string;
	languageLabel: string;
}) {
	if (readerView === 'choose') return 'Choose a library view';
	if (readerView === 'shelves') return activeDiscoverySummary;
	if (readerView === 'search') {
		return textQuery.trim()
			? `Text matches for "${textQuery.trim()}"`
			: `${languageLabel} text search`;
	}
	if (activeAuthorSection) return `${languageLabel} author section ${activeAuthorSection}`;
	if (workQuery.trim()) return `Authors matching "${workQuery.trim()}"`;
	return `${languageLabel} authors`;
}

function facetValueLabel(values: ReaderFacetValue[], id: string) {
	return values.find((value) => value.id === id)?.label || labelFromId(id);
}

function labelFromId(id: string) {
	return id
		.replace(/[_-]+/g, ' ')
		.replace(/\b\w/g, (letter) => letter.toUpperCase())
		.trim();
}
