import type { ToolId } from './search-data';

export type SourceOutlineSegment = {
	sourceRef: string;
	text: string;
	translatedText?: string;
	marker: string;
	level: number;
	path: string;
	parentPath: string;
};

export function isOutlinedDictionaryTool(tool: ToolId | undefined) {
	return tool === 'diogenes' || tool === 'bailly';
}

export function sourceOutlineDepth(sourceRef: string) {
	const stem = sourceRef.includes(':') ? sourceRef.split(/:(.*)/s)[1] : sourceRef;
	return stem ? Math.max(0, stem.split(':').length - 1) : 0;
}

export function isOutlinedDictionaryHeading(tool: ToolId | undefined, text: string) {
	if (!isOutlinedDictionaryTool(tool)) return false;
	const value = text.replace(/\s+/g, ' ').trim();
	if (!isCompactOutlinedDictionaryText(value)) return false;
	return (
		/^(?:[IVXLCDM]+|[A-Z]|[α-ωΑ-Ω])\.?\s+/u.test(value) || /^(?:Lit|Trop|Transf)\.?$/u.test(value)
	);
}

export function isCompactOutlinedDictionaryText(text: string) {
	const value = text.replace(/\s+/g, ' ').trim();
	if (value.length > 88) return false;
	if (/[;:]/u.test(value)) return false;
	return true;
}

export function extractSourceOutlineSegments({
	tool,
	rawWitnesses,
	entries
}: {
	tool: ToolId | undefined;
	rawWitnesses: unknown[];
	entries: unknown[];
}) {
	if (!isOutlinedDictionaryTool(tool)) return [];

	const translatedBlocks = rawWitnesses.flatMap((witness) =>
		arrayOfRecords(recordField(recordField(witness, 'evidence'), 'translated_blocks'))
	);
	const evidenceSegments = rawWitnesses.flatMap((witness) =>
		arrayOfRecords(recordField(recordField(witness, 'evidence'), 'source_segments'))
	);
	const entryBlocks = entries.flatMap((entry) =>
		arrayOfRecords(recordField(recordField(entry, 'source_entry'), 'blocks'))
	);
	const segments = translatedBlocks.length
		? translatedBlocks
		: evidenceSegments.length
			? evidenceSegments
			: entryBlocks;
	const seen = new Set<string>();

	return segments
		.map((segment) => normalizeSourceOutlineSegment(segment))
		.filter((segment): segment is SourceOutlineSegment => {
			if (!segment) return false;
			const key = `${segment.sourceRef}:${segment.text}`;
			if (seen.has(key)) return false;
			seen.add(key);
			return true;
		});
}

function normalizeSourceOutlineSegment(
	segment: Record<string, unknown>
): SourceOutlineSegment | undefined {
	const sourceRef = stringField(segment, 'source_ref');
	const text = (
		stringField(segment, 'source_text') ||
		stringField(segment, 'display_text') ||
		stringField(segment, 'text') ||
		stringField(segment, 'raw_text')
	)
		.replace(/\s+/g, ' ')
		.trim();

	if (!sourceRef || !text) return undefined;

	return {
		sourceRef,
		text,
		...(stringField(segment, 'source_text') && stringField(segment, 'text')
			? { translatedText: stringField(segment, 'text').replace(/\s+/g, ' ').trim() }
			: {}),
		marker: stringField(segment, 'source_marker') || stringField(segment, 'marker'),
		level:
			numberField(segment, 'source_level') ??
			numberField(segment, 'level') ??
			sourceOutlineDepth(sourceRef),
		path: stringField(segment, 'source_path') || stringField(segment, 'path'),
		parentPath: stringField(segment, 'parent_path')
	};
}

function recordField(record: unknown, key: string) {
	if (!isRecord(record)) return undefined;
	return record[key];
}

function arrayOfRecords(value: unknown): Record<string, unknown>[] {
	return Array.isArray(value) ? value.filter(isRecord) : [];
}

function stringField(record: Record<string, unknown>, key: string) {
	const value = record[key];
	return typeof value === 'string' ? value : '';
}

function numberField(record: Record<string, unknown>, key: string) {
	const value = record[key];
	return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}
