import type { LanguageMode } from './search-data';

export type ParadigmFeatureValue = string | number | boolean | null;

export type ParadigmAnalysis = {
	language: LanguageMode;
	features: Record<string, ParadigmFeatureValue>;
	source: string;
};

export type FunctionalParadigmAnalysis = {
	relation: string;
	native_feature: Record<string, ParadigmFeatureValue>;
	confidence: string;
};

export type ParadigmRequest = {
	source: string;
	language: LanguageMode;
	lemma: string;
	kind: 'declension' | 'conjugation' | string;
	options: Record<string, ParadigmFeatureValue>;
};

export type ParadigmResolutionCandidate = {
	lemma: string;
	entry_type: string;
	part_of_speech: string;
	paradigm_kind: string;
	native_analyses: ParadigmAnalysis[];
	functional_analyses: FunctionalParadigmAnalysis[];
	paradigm_request: ParadigmRequest | null;
	confidence: string;
	provenance: string[];
	unresolved_reason: string | null;
};

export type ParadigmResolutionPayload = {
	searched_form: string;
	normalized_form: string;
	language: LanguageMode;
	candidates: ParadigmResolutionCandidate[];
	warnings: string[];
	schema_version: string;
};

type JsonRecord = Record<string, unknown>;

export function normalizeParadigmResolution(value: unknown): ParadigmResolutionPayload | undefined {
	if (!isRecord(value)) return undefined;

	return {
		searched_form: stringValue(value.searched_form),
		normalized_form: stringValue(value.normalized_form),
		language: normalizeLanguage(stringValue(value.language)),
		candidates: arrayOfRecords(value.candidates).map(normalizeCandidate),
		warnings: arrayOfStrings(value.warnings),
		schema_version: stringValue(value.schema_version) || 'langnet.paradigm_resolution.v1'
	};
}

function normalizeCandidate(candidate: JsonRecord): ParadigmResolutionCandidate {
	const request = isRecord(candidate.paradigm_request)
		? normalizeParadigmRequest(candidate.paradigm_request)
		: null;

	return {
		lemma: stringValue(candidate.lemma),
		entry_type: stringValue(candidate.entry_type),
		part_of_speech: stringValue(candidate.part_of_speech),
		paradigm_kind: stringValue(candidate.paradigm_kind),
		native_analyses: arrayOfRecords(candidate.native_analyses).map(normalizeNativeAnalysis),
		functional_analyses: arrayOfRecords(candidate.functional_analyses).map(
			normalizeFunctionalAnalysis
		),
		paradigm_request: request,
		confidence: stringValue(candidate.confidence),
		provenance: arrayOfStrings(candidate.provenance),
		unresolved_reason: stringValue(candidate.unresolved_reason) || null
	};
}

function normalizeNativeAnalysis(analysis: JsonRecord): ParadigmAnalysis {
	return {
		language: normalizeLanguage(stringValue(analysis.language)),
		features: featureRecord(analysis.features),
		source: stringValue(analysis.source)
	};
}

function normalizeFunctionalAnalysis(analysis: JsonRecord): FunctionalParadigmAnalysis {
	return {
		relation: stringValue(analysis.relation),
		native_feature: featureRecord(analysis.native_feature),
		confidence: stringValue(analysis.confidence)
	};
}

function normalizeParadigmRequest(request: JsonRecord): ParadigmRequest {
	return {
		source: stringValue(request.source),
		language: normalizeLanguage(stringValue(request.language)),
		lemma: stringValue(request.lemma),
		kind: stringValue(request.kind),
		options: featureRecord(request.options)
	};
}

function featureRecord(value: unknown) {
	if (!isRecord(value)) return {};

	return Object.fromEntries(
		Object.entries(value).filter((entry): entry is [string, ParadigmFeatureValue] =>
			isFeatureValue(entry[1])
		)
	);
}

function isFeatureValue(value: unknown): value is ParadigmFeatureValue {
	return (
		value === null ||
		typeof value === 'string' ||
		typeof value === 'number' ||
		typeof value === 'boolean'
	);
}

function arrayOfRecords(value: unknown): JsonRecord[] {
	return Array.isArray(value) ? value.filter(isRecord) : [];
}

function arrayOfStrings(value: unknown): string[] {
	return Array.isArray(value)
		? value.filter((item): item is string => typeof item === 'string')
		: [];
}

function isRecord(value: unknown): value is JsonRecord {
	return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function stringValue(value: unknown) {
	return typeof value === 'string' ? value : '';
}

function normalizeLanguage(value: string): LanguageMode {
	if (value === 'lat' || value === 'grc' || value === 'san') return value;
	return 'san';
}
