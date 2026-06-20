import type { ReaderCatalogLanguage } from './index';

export type ReaderAcquisitionStatus =
	| 'planned'
	| 'staged'
	| 'imported'
	| 'missing_local_source'
	| 'needs_source_review'
	| 'needs_ocr'
	| 'needs_segmentation'
	| 'needs_rights_review';

export type ReaderWatchlistTarget = {
	id: string;
	displayName: string;
	aliases: string[];
	languages: ReaderCatalogLanguage[];
	period: string;
	tradition: string;
	status: ReaderAcquisitionStatus;
	sourcePlan: string;
	note: string;
	evidence?: {
		source_type?: string;
		citation?: string;
		label?: string;
		retrieved_at?: string;
	}[];
	localArtifacts?: string[];
};

export type ReaderWatchlistResponse = {
	schema_version: string;
	mode: 'library-watchlist';
	items: ReaderWatchlistTarget[];
	summary?: {
		target_count?: number;
	};
	error?: string;
};

const normalize = (value: string) => value.toLowerCase().normalize('NFKD');
const fallbackStatusLabel = (value: string) =>
	value
		.trim()
		.split(/[_\-\s]+/)
		.filter(Boolean)
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
		.join(' ');

const acquisitionStatusLabels: Record<string, string> = {
	planned: 'Planned',
	staged: 'Staged',
	imported: 'Imported',
	missing_local_source: 'Missing local source',
	needs_source_review: 'Needs source review',
	needs_ocr: 'Needs OCR',
	needs_segmentation: 'Needs segmentation',
	needs_rights_review: 'Needs rights review'
};

const sourceFileStatusLabels: Record<string, string> = {
	accepted: 'Accepted',
	imported: 'Imported',
	imported_from_staging: 'Imported from staging',
	missing_local_source: 'Missing local source',
	needs_ocr: 'Needs OCR',
	needs_rights_review: 'Needs rights review',
	needs_segmentation: 'Needs segmentation',
	needs_source_review: 'Needs source review',
	planned: 'Planned',
	source_candidate: 'Source candidate',
	staged: 'Staged'
};

export function readerAcquisitionStatusLabel(status: ReaderAcquisitionStatus | string) {
	return acquisitionStatusLabels[status] ?? fallbackStatusLabel(status);
}

export function readerSourceFileStatusLabel(status: string | null | undefined) {
	const normalized = status?.trim();
	if (!normalized) return 'Source status unknown';
	return sourceFileStatusLabels[normalized] ?? fallbackStatusLabel(normalized);
}

export function readerWorkAvailabilityLabel(work: {
	word_count?: number | null;
	segment_count?: number | null;
}) {
	return Number(work.word_count ?? 0) > 0 || Number(work.segment_count ?? 0) > 0
		? 'Readable text'
		: 'Catalog shell';
}

export function findReaderWatchlistMatches(targets: ReaderWatchlistTarget[], query: string) {
	const normalized = normalize(query.trim());
	if (!normalized) return [];
	return targets.filter((target) => {
		const haystack = normalize(
			[target.displayName, ...target.aliases, target.period, target.tradition, target.sourcePlan].join(' ')
		);
		return haystack.includes(normalized) || normalized.split(/\s+/).every((part) => haystack.includes(part));
	});
}
