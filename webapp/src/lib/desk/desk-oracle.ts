import type { EncounterResult, ToolId } from '../search-data';

const MAX_ORACLE_WARNING_PREVIEW = 3;

export type OracleTrace = {
	requestWord: string;
	normalizedCandidates: string[];
	sourceTools: ToolId[];
	bucketCount: number;
	bucketSources: string[];
	translationMode: string;
	backend: string;
	cachePolicy: string;
	normalizationWrites: boolean;
	translationWrites: boolean;
	indexAnchorCount: number;
	indexAnchorPreview: string[];
	warnings: string[];
	warningsOverflow: number;
	provenanceChips: string[];
};

function normalizeCandidateWord(word: string) {
	return word.trim().toLowerCase();
}

export function buildDeskOracleTrace(
	encounter: EncounterResult | null,
	fallbackQuery = ''
): OracleTrace {
	if (!encounter) {
		const trace: OracleTrace = {
			requestWord: fallbackQuery.trim(),
			normalizedCandidates: [],
			sourceTools: [],
			bucketCount: 0,
			bucketSources: [],
			translationMode: 'off',
			backend: 'cli',
			cachePolicy: 'not available',
			normalizationWrites: false,
			translationWrites: false,
			indexAnchorCount: 0,
			indexAnchorPreview: [],
			warnings: [],
			warningsOverflow: 0,
			provenanceChips: []
		};
		return trace;
	}

	const requestWord = encounter.query.trim();
	const normalizedCandidates = Array.from(
		new Set(
			(encounter.word_index?.request.query_candidates ?? [])
				.map(normalizeCandidateWord)
				.filter(Boolean)
		)
	);
	const bucketSources = Array.from(
		new Set(encounter.buckets.map((bucket) => bucket.bucket_id))
	).slice(0, MAX_ORACLE_WARNING_PREVIEW);
	const indexAnchors = encounter.word_index?.anchors ?? [];
	const warnings = Array.from(
		new Set([
			...encounter.warnings,
			...(encounter.word_index?.warnings ?? []).map((entry) => entry.message)
		])
	);
	const normalizedWarnings = warnings.map((value) => value.trim()).filter(Boolean);
	const cachePolicy = encounter.request.cache_policy ?? 'default';
	const provenanceChips = [
		`backend=${encounter.backend}`,
		`mode=${encounter.request.translation_mode}`,
		`cache=${cachePolicy}`
	];

	const trace: OracleTrace = {
		requestWord,
		normalizedCandidates,
		sourceTools: encounter.source_tools,
		bucketCount: encounter.buckets.length,
		bucketSources,
		translationMode: encounter.request.translation_mode,
		backend: encounter.backend,
		cachePolicy,
		normalizationWrites: Boolean(encounter.request.normalization_cache_writes),
		translationWrites: Boolean(encounter.request.translation_cache_writes),
		indexAnchorCount: indexAnchors.length,
		indexAnchorPreview: indexAnchors
			.slice(0, MAX_ORACLE_WARNING_PREVIEW)
			.map((anchor) => `${anchor.language} ${anchor.query}`),
		warnings: normalizedWarnings.slice(0, MAX_ORACLE_WARNING_PREVIEW),
		warningsOverflow: Math.max(0, normalizedWarnings.length - MAX_ORACLE_WARNING_PREVIEW),
		provenanceChips
	};
	return trace;
}
