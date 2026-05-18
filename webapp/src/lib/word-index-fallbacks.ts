import { isSingleWord, type EncounterResult } from './search-data';

export function wordIndexCandidateQueries(
	result: EncounterResult | null | undefined,
	requestedQuery: string
) {
	const requested = requestedQuery.trim();
	return dedupeStrings([requested, ...wordIndexFallbackQueries(result, requested)]);
}

export function wordIndexFallbackQueries(
	result: EncounterResult | null | undefined,
	requestedQuery: string
) {
	const requested = requestedQuery.trim().toLowerCase();
	const candidates: string[] = [];

	if (!result) return [];

	for (const anchor of result.lexeme_anchors) candidates.push(cleanWordIndexFallback(anchor));
	for (const bucket of result.buckets) {
		for (const lemma of bucket.bucket_lemmas) candidates.push(cleanWordIndexFallback(lemma));
		for (const witness of bucket.witnesses) {
			candidates.push(cleanWordIndexFallback(witness.headword));
			candidates.push(cleanWordIndexFallback(witness.lexeme_anchor));
		}
	}

	const exactAnchors =
		result.word_index?.anchors.filter((anchor) => anchor.anchor_status === 'exact') ?? [];
	const otherAnchors =
		result.word_index?.anchors.filter((anchor) => anchor.anchor_status !== 'exact') ?? [];

	for (const anchor of [...exactAnchors, ...otherAnchors]) {
		candidates.push(anchor.canonical_key);
		candidates.push(anchor.canonical_name);
		candidates.push(anchor.source_name);
		candidates.push(anchor.query);
	}

	return dedupeStrings(candidates).filter(
		(candidate) => candidate && candidate.toLowerCase() !== requested && isSingleWord(candidate)
	);
}

function cleanWordIndexFallback(value: string | undefined) {
	return (value ?? '')
		.replace(/^lex:/, '')
		.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '')
		.trim();
}

function dedupeStrings(values: string[]) {
	return [...new Set(values)];
}
