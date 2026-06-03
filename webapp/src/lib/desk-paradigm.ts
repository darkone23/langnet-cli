import { paradigmRequestKey, type ParadigmBlock } from './paradigm';
import type {
	LearningConcept,
	LearningFosterBridge,
	LearningNativeGateway,
	ParadigmResolutionCandidate
} from './paradigm-resolution';
import type { LanguageMode } from './search-data';
import { learnerDisplayForm } from './paradigm-ui';

export function paradigmCandidateKey(candidate: ParadigmResolutionCandidate) {
	if (candidate.paradigm_request) return paradigmRequestKey(candidate.paradigm_request);
	return [
		candidate.lemma,
		candidate.entry_type,
		candidate.part_of_speech,
		candidate.paradigm_kind,
		candidate.unresolved_reason ?? 'unresolved'
	].join(':');
}

export function paradigmCandidateTitle(candidate: ParadigmResolutionCandidate, fallback = 'form') {
	const kind =
		candidate.paradigm_kind && candidate.paradigm_kind !== 'unknown'
			? candidate.paradigm_kind
			: 'form';
	const label = learnerDisplayForm(candidate.lemma || fallback);
	return `${label || 'form'} ${kind}`;
}

export function paradigmCandidateSubtitle(candidate: ParadigmResolutionCandidate) {
	return [
		candidate.observed_form ? `form ${learnerDisplayForm(candidate.observed_form)}` : '',
		candidate.part_of_speech && candidate.part_of_speech !== 'unknown'
			? candidate.part_of_speech
			: '',
		candidate.entry_type && candidate.entry_type !== 'unknown' ? candidate.entry_type : '',
		candidate.foster_display,
		candidate.ranking_reasons.includes('ambiguous-analysis') ? 'ambiguous analysis' : '',
		candidate.confidence ? `${candidate.confidence} confidence` : ''
	]
		.filter(Boolean)
		.join(' · ');
}

export function paradigmFeatureEntries(candidate: ParadigmResolutionCandidate) {
	const seen = new Set<string>();
	const entries: { key: string; value: string }[] = [];

	for (const analysis of candidate.native_analyses) {
		for (const [key, value] of Object.entries(analysis.features)) {
			const label = paradigmFeatureLabel(key);
			const display = paradigmFeatureValue(value);
			const entryKey = `${label}:${display}`;
			if (!display || display === 'unknown' || seen.has(entryKey)) continue;
			seen.add(entryKey);
			entries.push({ key: label, value: display });
		}
	}

	return entries;
}

export function paradigmFunctionalLabels(candidate: ParadigmResolutionCandidate) {
	return [
		...new Set(
			candidate.functional_analyses
				.map((analysis) => paradigmRelationLabel(analysis.relation))
				.filter((label) => label && label !== 'unknown')
		)
	];
}

export function learningConcepts(candidate: ParadigmResolutionCandidate) {
	return candidate.learning_overlay?.concepts ?? [];
}

export function learningPrimarySummary(candidate: ParadigmResolutionCandidate) {
	const overlay = candidate.learning_overlay;
	const caseConcept =
		overlay?.concepts.find((concept) => concept.kind === 'case') ?? overlay?.concepts[0];
	if (candidate.display_summary) return learnerDisplayForm(candidate.display_summary);
	if (caseConcept?.plain_english) return caseConcept.plain_english;
	return candidate.foster_display || '';
}

export function learningGatewayTitle(concepts: LearningConcept[]) {
	return learningPrimaryConcept(concepts)?.foster_gateway || '';
}

export function learningPrimaryConcept(concepts: LearningConcept[]) {
	const priority = ['case', 'person', 'tense', 'mood', 'voice', 'number', 'gender', 'process'];
	return (
		[...concepts].sort(
			(left, right) => conceptPriority(left.kind, priority) - conceptPriority(right.kind, priority)
		)[0] ?? null
	);
}

export function learningNativeGateways(concepts: LearningConcept[], targetLanguage: LanguageMode) {
	const seen = new Set<string>();
	const gateways: LearningNativeGateway[] = [];
	const primaryConcept = learningPrimaryConcept(concepts);
	for (const concept of primaryConcept ? [primaryConcept] : concepts) {
		const nativeGateways = concept.native_gateways.length
			? concept.native_gateways
			: derivedNativeGateways(concept, targetLanguage);
		for (const gateway of nativeGateways) {
			if (gateway.language !== targetLanguage) continue;
			if (!gateway.term) continue;
			const key = `${gateway.language}:${gateway.term}:${gateway.role}`;
			if (seen.has(key)) continue;
			seen.add(key);
			gateways.push(gateway);
		}
	}
	return gateways.slice(0, 1);
}

export function candidateLearningLanguage(
	candidate: ParadigmResolutionCandidate,
	fallbackLanguage: LanguageMode
): LanguageMode {
	return (
		candidate.paradigm_request?.language ??
		candidate.native_analyses.find((analysis) => analysis.language)?.language ??
		fallbackLanguage
	);
}

export function learningFosterBridges(concepts: LearningConcept[]) {
	const primaryConcept = learningPrimaryConcept(concepts);
	const byId = new Map<string, LearningFosterBridge>();
	for (const concept of primaryConcept ? [primaryConcept] : concepts) {
		for (const bridge of concept.foster_bridges) {
			if (bridge.id) byId.set(bridge.id, bridge);
		}
	}
	return [...byId.values()]
		.sort(
			(left, right) =>
				Number(right.status !== 'aggregate_candidate') -
				Number(left.status !== 'aggregate_candidate')
		)
		.slice(0, 1);
}

export function paradigmFeatureLabel(value: string) {
	return value.replace(/_/g, ' ');
}

export function paradigmFeatureValue(value: unknown) {
	if (value === null || value === undefined || value === '') return '';
	return String(value).replace(/_/g, ' ');
}

export function paradigmRelationLabel(value: string) {
	return value.replace(/_/g, ' ');
}

export function paradigmRequestUrl(candidate: ParadigmResolutionCandidate) {
	const request = candidate.paradigm_request;
	if (!request) return '';
	const params = new URLSearchParams({
		language: request.language,
		lemma: request.lemma,
		kind: request.kind,
		timeout_ms: '120000'
	});
	const gender = request.options.gender;
	const presentClass = request.options.class;
	if (typeof gender === 'string' && gender) params.set('gender', gender);
	if (typeof presentClass === 'string' && presentClass) params.set('class', presentClass);
	return `/api/paradigm?${params.toString()}`;
}

export function paradigmSlotFeatureSummary(features: Record<string, unknown>) {
	return Object.entries(features)
		.map(([key, value]) => `${paradigmFeatureLabel(key)} ${paradigmFeatureValue(value)}`.trim())
		.filter(Boolean)
		.join(' · ');
}

export function paradigmTableLearningTitle(candidate: ParadigmResolutionCandidate) {
	if (candidate.paradigm_kind === 'declension') return 'Reading a declension table';
	if (candidate.paradigm_kind === 'conjugation') return 'Reading a conjugation table';
	return 'Reading a form table';
}

export function paradigmTableLearningSummary(
	candidate: ParadigmResolutionCandidate,
	block: ParadigmBlock
) {
	const dimensionText = block.dimensions.map(paradigmFeatureLabel).join(', ');
	if (candidate.paradigm_kind === 'declension') {
		return `This table maps noun-form jobs. ${dimensionText || 'The listed features'} tell what role, count, and agreement shape a form can carry.`;
	}
	if (candidate.paradigm_kind === 'conjugation') {
		return `This table maps verb-form jobs. ${dimensionText || 'The listed features'} tell who acts, when or how the action is framed, and how the action relates to its subject.`;
	}
	return `This table maps possible forms by ${dimensionText || 'their grammatical features'}.`;
}

export function paradigmTableAxisNotes(block: ParadigmBlock) {
	return block.dimensions.map((dimension) => ({
		label: paradigmFeatureLabel(dimension),
		note: paradigmDimensionNote(dimension)
	}));
}

function conceptPriority(kind: string, priority: string[]) {
	const index = priority.indexOf(kind);
	return index === -1 ? priority.length : index;
}

function derivedNativeGateways(
	concept: LearningConcept,
	targetLanguage: LanguageMode
): LearningNativeGateway[] {
	const labels = {
		grc: 'Greek',
		lat: 'Latin',
		san: 'Sanskrit'
	} as const;
	return [targetLanguage]
		.map((language) => {
			const term = concept.traditional[language] ?? '';
			const role =
				language === 'san'
					? (concept.traditional.san_role ?? concept.traditional.san_process ?? '')
					: '';
			return {
				language,
				label: labels[language],
				term,
				role,
				foster_gateway: concept.foster_gateway,
				explanation: `${labels[language]} gateway: ${term}; LangNet uses ${concept.foster_gateway} as the learner gateway.`
			};
		})
		.filter((gateway) => gateway.term);
}

function paradigmDimensionNote(dimension: string) {
	const notes: Record<string, string> = {
		case: 'job in the expression',
		number: 'one, two, or many',
		gender: 'agreement class',
		person: 'speaker, addressee, or other',
		tense: 'time or verbal frame',
		mood: 'mode of statement',
		voice: 'action relation',
		degree: 'comparison level'
	};
	return notes[dimension] ?? 'form feature';
}
