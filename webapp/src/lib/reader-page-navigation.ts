import {
	readerWorkRef,
	type ReaderDiscoveryShelf,
	type ReaderSearchResult,
	type ReaderSegment,
	type ReaderWork
} from './reader';

export function readerShelfIsActive(
	shelf: ReaderDiscoveryShelf,
	{
		discoveryGroup,
		discoveryTag
	}: {
		discoveryGroup: string;
		discoveryTag: string;
	}
) {
	return (
		(Boolean(shelf.query.group) && discoveryGroup === shelf.query.group && !discoveryTag) ||
		(Boolean(shelf.query.tag) && discoveryTag === shelf.query.tag && !discoveryGroup)
	);
}

export function readerSegmentIsActive(
	selectedSegment: ReaderSegment | null,
	segment: ReaderSegment
) {
	return selectedSegment?.citation_path === segment.citation_path;
}

export function readerCurrentReadingWorkRef(
	selectedWork: ReaderWork | null,
	selectedSegment: ReaderSegment | null
) {
	return selectedWork ? readerWorkRef(selectedWork) : selectedSegment?.work_id || '';
}

export function readerSearchResultWorkRef(result: ReaderSearchResult) {
	return result.target?.work_ref || result.cts_work_urn || result.work_id;
}
