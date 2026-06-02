import type { LanguageMode, ToolRequest } from './search-data';

export type EncounterBriefingMeaning = {
	summary: string;
	source_glosses: string[];
	source_gloss_language: string;
	translation_status: string;
	sources: string[];
	translation_sources: string[];
	confidence?: string;
	source_refs: string[];
};

export type EncounterBriefingGrammarFunction = {
	summary: string;
	form: string;
	lemma: string;
	analysis: string;
	foster_display: string;
	source: string;
};

export type EncounterBriefingWordDecomposition = {
	form: string;
	lemma: string;
	analysis: string;
	source: string;
	note: string;
};

export type EncounterBriefingReaderUsage = {
	label: string;
	snippet: string;
	note: string;
};

export type EncounterBriefingPhrasePair = {
	phrase: string;
	gloss: string;
	source: string;
	source_ref: string;
	note: string;
};

export type EncounterBriefingSummary = {
	schema_version: 'langnet.encounter_briefing.summary.v1' | string;
	short: string;
	forms: string[];
	meanings: EncounterBriefingMeaning[];
	grammar_functions: EncounterBriefingGrammarFunction[];
	word_decomposition: EncounterBriefingWordDecomposition[];
	reader_usages: EncounterBriefingReaderUsage[];
	phrase_pairs: EncounterBriefingPhrasePair[];
	dictionary_sources: string[];
	caveats: string[];
};

export type EncounterBriefingFlow = {
	schema_version: string;
	digest?: {
		query?: string;
		language?: LanguageMode | string;
		forms?: string[];
	};
	generation: {
		status: string;
		cached_status?: string;
		model?: string;
		prompt_version?: string;
		validation_issue_count?: number;
		validation_issues?: { code: string; path: string; message: string }[];
	};
	draft_output?: EncounterBriefingSummary;
	final_output?: EncounterBriefingSummary;
	model_output?: EncounterBriefingSummary | null;
	error?: string;
};

export type EncounterBriefingRequest = {
	language: LanguageMode;
	query: string;
	dictionaries: ToolRequest[];
	translationMode: string;
	maxBuckets: number;
	maxGlossChars: number;
	maxMeanings: number;
	maxReaderUsages: number;
	maxSourceRefs: number;
	model: string;
	generate: boolean;
	cachePolicy: 'read-write' | 'read-only' | 'off';
	timeoutMs: number;
};

export function encounterBriefingOutput(
	flow: EncounterBriefingFlow | null | undefined
): EncounterBriefingSummary | null {
	return flow?.final_output ?? flow?.draft_output ?? null;
}

export function encounterBriefingIsGenerated(flow: EncounterBriefingFlow | null | undefined) {
	const status = flow?.generation?.status ?? '';
	const cachedStatus = flow?.generation?.cached_status ?? '';
	return status === 'accepted' || cachedStatus === 'accepted';
}

export function encounterBriefingCanGenerate(flow: EncounterBriefingFlow | null | undefined) {
	if (encounterBriefingIsGenerated(flow)) return false;
	const output = encounterBriefingOutput(flow);
	return Boolean(output?.meanings?.length);
}

export function encounterBriefingStatusLabel(flow: EncounterBriefingFlow | null | undefined) {
	const status = flow?.generation?.status ?? '';
	const cachedStatus = flow?.generation?.cached_status ?? '';
	if (status === 'cache_hit' && cachedStatus === 'accepted') return 'Generated';
	if (status === 'cache_hit') return 'Draft';
	if (status === 'accepted') return 'Generated';
	if (status === 'rejected' || status === 'invalid_json') return 'Draft';
	if (status === 'cache_miss' || status === 'not_requested') return 'Draft';
	return status ? status.replace(/_/g, ' ') : 'Draft';
}

export function encounterBriefingModelLabel(flow: EncounterBriefingFlow | null | undefined) {
	if (!encounterBriefingIsGenerated(flow)) return '';
	const model = flow?.generation?.model?.trim();
	if (!model) return '';
	return model.replace(/^openai:/u, '');
}

export function encounterBriefingProvenanceLabel(flow: EncounterBriefingFlow | null | undefined) {
	const statusLabel = encounterBriefingStatusLabel(flow);
	const modelLabel = encounterBriefingModelLabel(flow);
	if (!modelLabel) return statusLabel;
	return `${statusLabel} by ${modelLabel}`;
}

export function encounterBriefingCompactText(value: string, maxChars = 180) {
	const text = value.replace(/\s+/g, ' ').trim();
	if (text.length <= maxChars) return text;
	return `${text.slice(0, Math.max(0, maxChars - 3)).replace(/[ ,;:]+$/u, '')}...`;
}
