import {
	readerAuthorMatchesId,
	readerWorkContributorLabels,
	readerWorkDisplayAuthor,
	readerWorkListDiscriminator,
	readerWorkListLabel,
	type ReaderAuthor,
	type ReaderFacet,
	type ReaderFacetValue,
	type ReaderWork
} from './reader';
import type { LanguageMode } from './search-data';

export function readerAuthorIdentityValues(author: ReaderAuthor) {
	return [author.author_id, author.source_author_id, author.canonical_author_id].filter(
		(value): value is string => Boolean(value)
	);
}

export function readerAuthorsMatch(left: ReaderAuthor, right: ReaderAuthor) {
	return readerAuthorIdentityValues(right).some((id) => readerAuthorMatchesId(left, id));
}

export function upsertReaderAuthor(authors: ReaderAuthor[], author: ReaderAuthor) {
	if (authors.some((item) => readerAuthorsMatch(item, author))) {
		return authors.map((item) => (readerAuthorsMatch(item, author) ? author : item));
	}
	return [author, ...authors];
}

export function readerSyntheticAuthorFromWork(work: ReaderWork, authorId: string): ReaderAuthor {
	const displayName = readerWorkDisplayAuthor(work);
	return {
		author_id: authorId,
		source_author_id: work.source_author_id || '',
		display_name: displayName,
		author: displayName,
		index_name: displayName,
		native_name: displayName,
		section_key: '',
		language: work.language,
		work_count: 0,
		alternate_names: [work.source_author, work.canonical_author_name, work.author].filter(
			(value): value is string => Boolean(value && value !== displayName)
		),
		sort_key: displayName
	};
}

export function readerSyntheticAuthorFromRoute(
	authorId: string,
	authorName: string,
	language: LanguageMode
): ReaderAuthor {
	return {
		author_id: authorId,
		source_author_id: '',
		display_name: authorName,
		author: authorName,
		index_name: authorName,
		native_name: authorName,
		section_key: '',
		language,
		work_count: 0,
		alternate_names: [],
		sort_key: authorName
	};
}

export function readerFacetValues(items: ReaderFacet[], id: string): ReaderFacetValue[] {
	return items.find((item) => item.id === id)?.values ?? [];
}

export function readerFacetValueLabel(values: ReaderFacetValue[], id: string) {
	return values.find((value) => value.id === id)?.label || readerLabelFromId(id);
}

export function readerLabelFromId(id: string) {
	return id
		.replace(/[_-]+/g, ' ')
		.replace(/\b\w/g, (letter) => letter.toUpperCase())
		.trim();
}

export function readerSelectedWorkTitleLabel(work: ReaderWork | null, works: ReaderWork[]) {
	return work ? readerWorkListLabel(work, works) : '';
}

export function readerSelectedWorkDiscriminator(work: ReaderWork | null, works: ReaderWork[]) {
	return work ? readerWorkListDiscriminator(work, works) : '';
}

export function readerSelectedWorkContributorLine(work: ReaderWork | null) {
	return work ? readerWorkContributorLabels(work).join(' · ') : '';
}

export function readerSelectedWorkAuthorLabel(work: ReaderWork | null) {
	return work ? readerWorkDisplayAuthor(work) : '';
}
