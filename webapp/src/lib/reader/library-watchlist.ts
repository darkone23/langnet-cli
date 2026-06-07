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
