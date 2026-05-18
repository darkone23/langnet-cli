import type { LanguageMode } from './search-data';
import type { ParadigmFeatureValue, ParadigmRequest } from './paradigm-resolution';

export type ParadigmForm = {
	text: string;
	normalized: string;
	source_key: string;
};

export type ParadigmSlot = {
	features: Record<string, ParadigmFeatureValue>;
	forms: ParadigmForm[];
	source_label: string;
	is_ambiguous: boolean;
};

export type ParadigmBlock = {
	label: string;
	dimensions: string[];
	slots: ParadigmSlot[];
};

export type ParadigmPayload = {
	schema_version: string;
	language: LanguageMode;
	lemma: string;
	kind: string;
	source: string;
	source_request: Record<string, unknown>;
	paradigms: ParadigmBlock[];
	warnings: string[];
	error?: string;
};

type JsonRecord = Record<string, unknown>;

export function normalizeParadigmPayload(value: unknown): ParadigmPayload | undefined {
	if (!isRecord(value)) return undefined;

	return {
		schema_version: stringValue(value.schema_version) || 'langnet.paradigm.v1',
		language: normalizeLanguage(stringValue(value.language)),
		lemma: stringValue(value.lemma),
		kind: stringValue(value.kind),
		source: stringValue(value.source),
		source_request: isRecord(value.source_request) ? value.source_request : {},
		paradigms: arrayOfRecords(value.paradigms).map(normalizeParadigmBlock),
		warnings: arrayOfStrings(value.warnings),
		error: stringValue(value.error) || undefined
	};
}

export function paradigmRequestKey(request: ParadigmRequest) {
	return [
		request.language,
		request.kind,
		request.source,
		request.lemma,
		JSON.stringify(request.options ?? {})
	].join(':');
}

function normalizeParadigmBlock(block: JsonRecord): ParadigmBlock {
	return {
		label: stringValue(block.label),
		dimensions: arrayOfStrings(block.dimensions),
		slots: arrayOfRecords(block.slots).map(normalizeParadigmSlot)
	};
}

function normalizeParadigmSlot(slot: JsonRecord): ParadigmSlot {
	return {
		features: featureRecord(slot.features),
		forms: arrayOfRecords(slot.forms).map(normalizeParadigmForm),
		source_label: stringValue(slot.source_label),
		is_ambiguous: Boolean(slot.is_ambiguous)
	};
}

function normalizeParadigmForm(form: JsonRecord): ParadigmForm {
	return {
		text: stringValue(form.text),
		normalized: stringValue(form.normalized),
		source_key: stringValue(form.source_key)
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
