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

export type LearningSourceEvidence = {
	evidence_level: string;
	source_anchor_id: string;
	work_id: string;
	canonical_text_id: string;
	cts_work_urn: string | null;
	citation_path: string | null;
	canonical_address: string | null;
	label: string;
};

export type LearningFosterBridge = {
	id: string;
	status: string;
	foster_terms: string[];
	concept_ids: string[];
	related_concept_ids: string[];
	plain_english: string;
	learner_action: string;
	product_use: string;
	morphology_predicates: string[];
	source_refs: string[];
	summary_refs: string[];
	caveats: string[];
};

export type LearningNativeGateway = {
	language: LanguageMode;
	label: string;
	term: string;
	role: string;
	foster_gateway: string;
	explanation: string;
};

export type LearningConcept = {
	id: string;
	kind: string;
	foster_gateway: string;
	plain_english: string;
	traditional: Record<string, string>;
	native_gateways: LearningNativeGateway[];
	source_evidence: LearningSourceEvidence[];
	foster_bridges: LearningFosterBridge[];
};

export type LearningEvidenceGap = {
	concept_id: string;
	missing: string[];
};

export type LearningOverlay = {
	schema_version: string;
	status: string;
	concept_ids: string[];
	concepts: LearningConcept[];
	missing_evidence: string[];
	evidence_gaps: LearningEvidenceGap[];
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
	observed_form: string | null;
	slot_features: Record<string, ParadigmFeatureValue>;
	foster_display: string;
	display_summary: string | null;
	ranking_reasons: string[];
	concept_ids: string[];
	native_analyses: ParadigmAnalysis[];
	functional_analyses: FunctionalParadigmAnalysis[];
	paradigm_request: ParadigmRequest | null;
	confidence: string;
	provenance: string[];
	unresolved_reason: string | null;
	learning_overlay: LearningOverlay | null;
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
		observed_form: stringValue(candidate.observed_form) || null,
		slot_features: featureRecord(candidate.slot_features),
		foster_display: stringValue(candidate.foster_display),
		display_summary: stringValue(candidate.display_summary) || null,
		ranking_reasons: arrayOfStrings(candidate.ranking_reasons),
		concept_ids: arrayOfStrings(candidate.concept_ids),
		native_analyses: arrayOfRecords(candidate.native_analyses).map(normalizeNativeAnalysis),
		functional_analyses: arrayOfRecords(candidate.functional_analyses).map(
			normalizeFunctionalAnalysis
		),
		paradigm_request: request,
		confidence: stringValue(candidate.confidence),
		provenance: arrayOfStrings(candidate.provenance),
		unresolved_reason: stringValue(candidate.unresolved_reason) || null,
		learning_overlay: normalizeLearningOverlay(candidate.learning_overlay)
	};
}

function normalizeLearningOverlay(value: unknown): LearningOverlay | null {
	if (!isRecord(value)) return null;
	return {
		schema_version: stringValue(value.schema_version) || 'langnet.learning_overlay.v1',
		status: stringValue(value.status),
		concept_ids: arrayOfStrings(value.concept_ids),
		concepts: arrayOfRecords(value.concepts).map(normalizeLearningConcept),
		missing_evidence: arrayOfStrings(value.missing_evidence),
		evidence_gaps: arrayOfRecords(value.evidence_gaps).map(normalizeLearningEvidenceGap)
	};
}

function normalizeLearningConcept(concept: JsonRecord): LearningConcept {
	return {
		id: stringValue(concept.id),
		kind: stringValue(concept.kind),
		foster_gateway: stringValue(concept.foster_gateway),
		plain_english: stringValue(concept.plain_english),
		traditional: stringRecord(concept.traditional),
		native_gateways: arrayOfRecords(concept.native_gateways).map(normalizeLearningNativeGateway),
		source_evidence: arrayOfRecords(concept.source_evidence).map(normalizeLearningSourceEvidence),
		foster_bridges: arrayOfRecords(concept.foster_bridges).map(normalizeLearningFosterBridge)
	};
}

function normalizeLearningNativeGateway(gateway: JsonRecord): LearningNativeGateway {
	return {
		language: normalizeLanguage(stringValue(gateway.language)),
		label: stringValue(gateway.label),
		term: stringValue(gateway.term),
		role: stringValue(gateway.role),
		foster_gateway: stringValue(gateway.foster_gateway),
		explanation: stringValue(gateway.explanation)
	};
}

function normalizeLearningSourceEvidence(evidence: JsonRecord): LearningSourceEvidence {
	return {
		evidence_level: stringValue(evidence.evidence_level),
		source_anchor_id: stringValue(evidence.source_anchor_id),
		work_id: stringValue(evidence.work_id),
		canonical_text_id: stringValue(evidence.canonical_text_id),
		cts_work_urn: stringValue(evidence.cts_work_urn) || null,
		citation_path: stringValue(evidence.citation_path) || null,
		canonical_address: stringValue(evidence.canonical_address) || null,
		label: stringValue(evidence.label)
	};
}

function normalizeLearningFosterBridge(bridge: JsonRecord): LearningFosterBridge {
	return {
		id: stringValue(bridge.id),
		status: stringValue(bridge.status),
		foster_terms: arrayOfStrings(bridge.foster_terms),
		concept_ids: arrayOfStrings(bridge.concept_ids),
		related_concept_ids: arrayOfStrings(bridge.related_concept_ids),
		plain_english: stringValue(bridge.plain_english),
		learner_action: stringValue(bridge.learner_action),
		product_use: stringValue(bridge.product_use),
		morphology_predicates: arrayOfStrings(bridge.morphology_predicates),
		source_refs: arrayOfStrings(bridge.source_refs),
		summary_refs: arrayOfStrings(bridge.summary_refs),
		caveats: arrayOfStrings(bridge.caveats)
	};
}

function normalizeLearningEvidenceGap(gap: JsonRecord): LearningEvidenceGap {
	return {
		concept_id: stringValue(gap.concept_id),
		missing: arrayOfStrings(gap.missing)
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

function stringRecord(value: unknown) {
	if (!isRecord(value)) return {};

	return Object.fromEntries(
		Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === 'string')
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
