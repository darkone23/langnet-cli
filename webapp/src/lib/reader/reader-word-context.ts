import type { ReaderWordContextEvidenceItem, ReaderWordContextMorphologyItem } from './index';

export function readerWordContextStatusLabel(label: string, status: string, count: number) {
	if (status === 'available') return `${label}: ${count} ${count === 1 ? 'row' : 'rows'}`;
	if (status === 'no_hits') return `${label}: no rows`;
	if (status === 'index_unavailable' || status === 'unavailable') return `${label}: unavailable`;
	if (status === 'error') return `${label}: error`;
	return `${label}: ${status || 'pending'}`;
}

export function readerWordContextEvidenceItemLabel(item: ReaderWordContextEvidenceItem) {
	const lemma = item.lemma?.trim() ?? '';
	const gloss = item.gloss?.trim() ?? '';
	if (lemma && gloss) return `${lemma} — ${gloss}`;
	return lemma || gloss || 'Unlabelled evidence row';
}

export function readerWordContextMorphologyItemLabel(item: ReaderWordContextMorphologyItem) {
	const form = item.form?.trim() ?? '';
	const lemma = item.lemma?.trim() ?? '';
	const analysis = item.analysis?.trim() ?? '';
	const head = form && lemma && form !== lemma ? `${form} → ${lemma}` : form || lemma;
	if (head && analysis) return `${head} · ${analysis}`;
	return head || analysis || 'Unlabelled morphology row';
}

export function readerWordContextItemSourceLabel(
	item: ReaderWordContextEvidenceItem | ReaderWordContextMorphologyItem
) {
	const sourceLabel = 'source_label' in item ? item.source_label?.trim() : '';
	return sourceLabel || item.source_tool?.trim() || '';
}
