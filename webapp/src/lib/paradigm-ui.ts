import {
	paradigmRequestKey,
	type ParadigmBlock,
	type ParadigmPayload,
	type ParadigmSlot
} from './paradigm';
import type { ParadigmResolutionCandidate } from './paradigm-resolution';

export type CuratedParadigmCandidates = {
	visible: ParadigmResolutionCandidate[];
	hiddenCount: number;
};

export type ParadigmSlotGroup = {
	id: string;
	label: string;
	slots: ParadigmBlock['slots'];
};

const maxResolvedCandidates = 3;

export function curateParadigmCandidates(
	candidates: ParadigmResolutionCandidate[],
	query = ''
): CuratedParadigmCandidates {
	const deduped = dedupeCandidates(candidates).sort((left, right) =>
		compareCandidates(left, right, query)
	);
	const resolved = deduped.filter((candidate) => isResolvedCandidate(candidate));

	if (resolved.length) {
		const visible = resolved.slice(0, maxResolvedCandidates);
		return {
			visible,
			hiddenCount: deduped.length - visible.length
		};
	}

	const [best] = deduped;
	return {
		visible: best ? [best] : [],
		hiddenCount: Math.max(0, deduped.length - (best ? 1 : 0))
	};
}

export function paradigmPayloadHasForms(payload: ParadigmPayload | undefined) {
	return Boolean(
		payload?.paradigms.some((block) => block.slots.some((slot) => slot.forms.length > 0))
	);
}

export function paradigmUnavailableMessage(payload: ParadigmPayload | undefined) {
	const warning = payload?.warnings.find(Boolean);
	if (warning) return `Table unavailable: ${warning.replace(/_/g, ' ')}.`;
	return 'Table unavailable: the source returned no forms.';
}

export function paradigmSlotMatchesCandidate(
	slot: ParadigmSlot,
	candidate: ParadigmResolutionCandidate,
	query: string
) {
	const slotFeatures = slot.features ?? {};
	const targetFeatures = candidate.slot_features ?? {};
	const featureKeys = Object.keys(targetFeatures);

	if (
		featureKeys.length > 0 &&
		featureKeys.every(
			(key) => String(slotFeatures[key] ?? '') === String(targetFeatures[key] ?? '')
		)
	) {
		return true;
	}

	const targets = new Set(
		[candidate.observed_form, query].filter((value): value is string => Boolean(value))
	);
	return slot.forms.some(
		(form) => targets.has(form.text) || targets.has(form.normalized) || targets.has(form.source_key)
	);
}

export function paradigmSlotGroups(block: ParadigmBlock): ParadigmSlotGroup[] {
	const groups: ParadigmSlotGroup[] = [];
	const byId = new Map<string, ParadigmSlotGroup>();

	for (const slot of block.slots) {
		const label = paradigmSlotGroupLabel(block, slot.features);
		const id = label.toLowerCase();
		let group = byId.get(id);

		if (!group) {
			group = { id, label, slots: [] };
			byId.set(id, group);
			groups.push(group);
		}

		group.slots.push(slot);
	}

	return groups;
}

export function sanskritParadigmLemmaFallbacks(lemma: string) {
	return unique([lemma, asciiSanskritLemma(lemma)]).filter(Boolean);
}

export function learnerDisplayForm(value: string | null | undefined) {
	return (value ?? '').replace(/_\d+\b/gu, '');
}

function dedupeCandidates(candidates: ParadigmResolutionCandidate[]) {
	const seen = new Set<string>();
	const deduped: ParadigmResolutionCandidate[] = [];

	for (const candidate of candidates) {
		const key = candidate.paradigm_request
			? paradigmRequestKey(candidate.paradigm_request)
			: [
					candidate.lemma,
					candidate.part_of_speech,
					candidate.paradigm_kind,
					candidate.unresolved_reason ?? ''
				].join(':');

		if (seen.has(key)) continue;
		seen.add(key);
		deduped.push(candidate);
	}

	return deduped;
}

function compareCandidates(
	left: ParadigmResolutionCandidate,
	right: ParadigmResolutionCandidate,
	query: string
) {
	return (
		Number(isResolvedCandidate(right)) - Number(isResolvedCandidate(left)) ||
		determinedRank(right) - determinedRank(left) ||
		confidenceRank(right.confidence) - confidenceRank(left.confidence) ||
		Number(!isAmbiguousCandidate(right)) - Number(!isAmbiguousCandidate(left)) ||
		exactObservedRank(right, query) - exactObservedRank(left, query) ||
		Number(Boolean(right.observed_form)) - Number(Boolean(left.observed_form)) ||
		right.native_analyses.length - left.native_analyses.length ||
		left.lemma.localeCompare(right.lemma)
	);
}

function isResolvedCandidate(candidate: ParadigmResolutionCandidate) {
	return Boolean(candidate.paradigm_request && !candidate.unresolved_reason);
}

function confidenceRank(value: string) {
	if (value === 'high') return 3;
	if (value === 'medium') return 2;
	if (value === 'low') return 1;
	return 0;
}

function exactObservedRank(candidate: ParadigmResolutionCandidate, query: string) {
	return query && candidate.observed_form === query ? 1 : 0;
}

function determinedRank(candidate: ParadigmResolutionCandidate) {
	const reasons = new Set(candidate.ranking_reasons);
	if (reasons.has('case-number-gender') || reasons.has('person-number-tense-voice-mood')) {
		return 2;
	}
	if (Object.keys(candidate.slot_features ?? {}).length > 0) return 1;
	return 0;
}

function isAmbiguousCandidate(candidate: ParadigmResolutionCandidate) {
	return candidate.ranking_reasons.includes('ambiguous-analysis');
}

function paradigmSlotGroupLabel(block: ParadigmBlock, features: Record<string, unknown>) {
	if (block.dimensions.some((dimension) => ['mood', 'tense', 'voice'].includes(dimension))) {
		return labelParts([features.mood, features.tense, features.voice], 'Forms');
	}

	if (block.dimensions.includes('number')) {
		return labelParts([features.number], 'Forms');
	}

	return 'Forms';
}

function labelParts(values: unknown[], fallback: string) {
	const parts = values
		.map((value) => (value === null || value === undefined ? '' : String(value)))
		.filter((value) => value && value !== 'unknown')
		.map((value) => value.replace(/_/g, ' '));

	return parts.length ? capitalize(parts.join(' · ')) : fallback;
}

function capitalize(value: string) {
	return value ? `${value[0].toUpperCase()}${value.slice(1)}` : value;
}

function asciiSanskritLemma(value: string) {
	return value
		.replace(/_\d+$/u, '')
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/gu, '')
		.normalize('NFC');
}

function unique(values: string[]) {
	return [...new Set(values)];
}
