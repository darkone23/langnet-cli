import {
	Bird,
	BookmarkCheck,
	BookOpen,
	Bug,
	Cat,
	Dog,
	Fish,
	Shell,
	Snail,
	Squirrel,
	ScrollText,
	Turtle
} from 'lucide-svelte';
import { buildComponentHeadwordDisplay, buildHeadwordDisplay } from '../headword-display';
import {
	isCompactOutlinedDictionaryText,
	isOutlinedDictionaryHeading,
	isOutlinedDictionaryTool,
	sourceOutlineDepth
} from '../source-outline';
import { languageModes, tools } from '../search-data';
import type {
	EncounterBucket,
	EncounterComponent,
	EncounterComponentMeaning,
	EncounterWordIndexAnchor,
	LanguageMode,
	ToolId,
	ToolMeta
} from '../search-data';
import { uiCopy } from '../ui-copy';
import { isTranslatedSourceTool } from './desk-session';

export type TextLayerState = Record<string, 'reader' | 'source'>;
export type ExpandedState = Record<string, boolean>;
export type ToolStyle = Record<ToolId, { accent: string; badge: string }>;

export type BucketGroup = {
	id: string;
	toolId: ToolId;
	dictionary: string;
	lexeme: string;
	buckets: EncounterBucket[];
	witnessCount: number;
	sourceRefCount: number;
	reasons: string[];
};

export type Mnemonic = {
	Icon: typeof Bird;
	name: string;
};

export const toolStyle: ToolStyle = {
	cdsl: { accent: 'border-l-secondary', badge: 'badge-secondary' },
	heritage: { accent: 'border-l-accent', badge: 'badge-accent' },
	dico: { accent: 'border-l-success', badge: 'badge-success' },
	diogenes: { accent: 'border-l-info', badge: 'badge-info' },
	bailly: { accent: 'border-l-success', badge: 'badge-success' },
	strongs_greek: { accent: 'border-l-warning', badge: 'badge-warning' },
	cts_index: { accent: 'border-l-accent', badge: 'badge-accent' },
	spacy: { accent: 'border-l-neutral', badge: 'badge-neutral' },
	cltk: { accent: 'border-l-success', badge: 'badge-success' },
	whitakers: { accent: 'border-l-secondary', badge: 'badge-secondary' },
	gaffiot: { accent: 'border-l-accent', badge: 'badge-accent' },
	lewis_1890: { accent: 'border-l-info', badge: 'badge-info' }
};

export function primaryTool(bucket: EncounterBucket): ToolId {
	return (
		bucket.translation?.source_tool ??
		bucket.witnesses[0]?.tool ??
		bucket.source_tools[0] ??
		'diogenes'
	);
}

export function primaryLexeme(bucket: EncounterBucket, fallbackQuery = '') {
	return bucket.witnesses[0]?.headword ?? bucket.bucket_lemmas[0] ?? fallbackQuery;
}

export function primaryDictionary(bucket: EncounterBucket) {
	return bucket.witnesses[0]?.dictionary ?? primaryTool(bucket);
}

export function groupHeadwordDisplay(
	group: BucketGroup,
	language: LanguageMode,
	anchors: EncounterWordIndexAnchor[] = []
) {
	return buildHeadwordDisplay({
		language,
		lexeme: group.lexeme,
		source: group.toolId,
		dictionary: group.dictionary,
		groupValues: groupHeadwordValues(group),
		anchors
	});
}

export function groupHeadwordValues(group: BucketGroup) {
	return [
		group.lexeme,
		...group.buckets.flatMap((bucket) => [
			...bucket.bucket_lemmas,
			...bucket.witnesses.flatMap((witness) => [witness.headword, witness.lexeme_anchor])
		])
	].filter((value): value is string => Boolean(value));
}

export function groupBuckets(buckets: EncounterBucket[], fallbackQuery = ''): BucketGroup[] {
	const groups = new Map<string, BucketGroup>();

	for (const bucket of buckets) {
		const toolId = primaryTool(bucket);
		const dictionary = primaryDictionary(bucket);
		const lexeme = primaryLexeme(bucket, fallbackQuery);
		const id = `${toolId}:${dictionary}:${lexeme}`;
		const existing = groups.get(id);

		if (existing) {
			existing.buckets.push(bucket);
			existing.witnessCount += bucket.witness_count;
			existing.sourceRefCount += bucket.source_refs.length;
			existing.reasons = dedupeStrings([...existing.reasons, ...bucket.reasons]);
		} else {
			groups.set(id, {
				id,
				toolId,
				dictionary,
				lexeme,
				buckets: [bucket],
				witnessCount: bucket.witness_count,
				sourceRefCount: bucket.source_refs.length,
				reasons: dedupeStrings(bucket.reasons)
			});
		}
	}

	return [...groups.values()]
		.map((group) => ({
			...group,
			buckets: [...group.buckets].sort(compareBucketsBySourceOrder)
		}))
		.sort(compareGroupsBySourceOrder);
}

export function compareGroupsBySourceOrder(a: BucketGroup, b: BucketGroup) {
	return (
		compareBucketsBySourceOrder(a.buckets[0], b.buckets[0]) || a.lexeme.localeCompare(b.lexeme)
	);
}

export function compareBucketsBySourceOrder(a: EncounterBucket, b: EncounterBucket) {
	return (
		compareSourceRefs(primarySourceRef(a), primarySourceRef(b)) ||
		a.learner_quality_order - b.learner_quality_order ||
		a.bucket_id.localeCompare(b.bucket_id)
	);
}

export function primarySourceRef(bucket: EncounterBucket) {
	const tool = primaryTool(bucket);
	return (
		bucket.source_refs.find((sourceRef) => sourceRef.startsWith(`${tool}:`)) ??
		bucket.source_refs[0] ??
		bucket.witnesses[0]?.source_ref ??
		''
	);
}

export function compareSourceRefs(a: string, b: string) {
	const aParts = sourceRefParts(a);
	const bParts = sourceRefParts(b);
	const length = Math.max(aParts.length, bParts.length);

	for (let index = 0; index < length; index += 1) {
		const aPart = aParts[index];
		const bPart = bParts[index];

		if (aPart === undefined) return -1;
		if (bPart === undefined) return 1;
		if (typeof aPart === 'number' && typeof bPart === 'number' && aPart !== bPart) {
			return aPart - bPart;
		}
		if (aPart !== bPart) {
			return String(aPart).localeCompare(String(bPart), undefined, { numeric: true });
		}
	}

	return 0;
}

export function sourceRefParts(sourceRef: string) {
	const [, rest = sourceRef] = sourceRef.split(/:(.*)/s);
	return rest
		.split(/[:_]/)
		.filter(Boolean)
		.map((part) => (/^\d+$/.test(part) ? Number(part) : part));
}

export function dedupeStrings(values: string[]) {
	return [...new Set(values.filter(Boolean))];
}

export function languageLabel(mode: LanguageMode) {
	return languageModes.find((candidate) => candidate.id === mode)?.label ?? mode;
}

export function countLabel(count: number, singular: string, plural = `${singular}s`) {
	return `${count} ${count === 1 ? singular : plural}`;
}

export function glossSegments(gloss: string) {
	const segments = gloss
		.split('|')
		.map((segment) => segment.trim())
		.filter(Boolean);
	return segments.length ? segments : [uiCopy.errors.noGloss];
}

export function activeGloss(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	const text =
		bucket.translation &&
		(!bucket.translation.available || layerState[bucket.bucket_id] === 'source')
			? bucket.translation.source_text
			: (bucket.translation?.target_text ?? bucket.display_gloss);

	return postProcessDisplayText(bucket, text);
}

export function postProcessDisplayText(bucket: EncounterBucket, value: string) {
	if (primaryTool(bucket) !== 'dico') return value;
	return value.replace(/_\d+\b/g, '');
}

export function activeGlossSegments(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	return glossSegments(activeGloss(bucket, layerState));
}

export function sectionText(
	bucket: EncounterBucket,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	if (expansionState[sectionExpansionKey(bucket)] && sectionHasSourceDetail(bucket, layerState)) {
		return sourceDetailText(bucket);
	}

	if (
		shouldCollapseReaderSection(bucket, layerState) &&
		!expansionState[sectionExpansionKey(bucket)]
	) {
		return truncateText(activeGloss(bucket, layerState), sectionPreviewLength(bucket));
	}

	return activeGloss(bucket, layerState);
}

export function sectionSegments(
	bucket: EncounterBucket,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	return glossSegments(sectionText(bucket, layerState, expansionState));
}

export function sectionHasSourceDetail(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	if (bucket.translation?.available && isTranslatedSourceTool(bucket.translation.source_tool)) {
		return false;
	}

	const detail = sourceDetailText(bucket);
	if (!detail) return false;
	if (detail.length <= activeGloss(bucket, layerState).length + 24) return false;
	return isSectionTruncated(bucket, layerState);
}

export function sourceDetailText(bucket: EncounterBucket) {
	return postProcessDisplayText(
		bucket,
		bucket.evidence_note
			.replace(/^examples:\s*/i, '')
			.replace(/^cross refs:\s*/i, 'Cross refs: ')
			.trim()
	);
}

export function isSectionTruncated(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	return /(?:…|\.\.\.)\s*$/u.test(activeGloss(bucket, layerState).trim());
}

export function sectionIsClippedWithoutDetail(
	bucket: EncounterBucket,
	layerState: TextLayerState = {}
) {
	return isSectionTruncated(bucket, layerState) && !sectionHasSourceDetail(bucket, layerState);
}

export function sectionShowsReturnedEndingNote(
	bucket: EncounterBucket,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	return (
		sectionIsClippedWithoutDetail(bucket, layerState) &&
		(!sectionCanToggle(bucket, layerState) || expansionState[sectionExpansionKey(bucket)])
	);
}

export function sectionCanToggle(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	return (
		sectionHasSourceDetail(bucket, layerState) || shouldCollapseReaderSection(bucket, layerState)
	);
}

export function shouldCollapseReaderSection(
	bucket: EncounterBucket,
	layerState: TextLayerState = {}
) {
	const tool = primaryTool(bucket);
	const text = activeGloss(bucket, layerState);
	const segments = activeGlossSegments(bucket, layerState);

	if (isOutlinedDictionaryTool(tool)) {
		if (isCompactOutlineHeading(bucket, layerState)) return false;
		return text.length > sectionPreviewLength(bucket) || segments.length > 1;
	}

	if (isTranslatedSourceTool(tool)) {
		return text.length > sectionPreviewLength(bucket) || segments.length > 3;
	}

	return false;
}

export function sectionPreviewLength(bucket: EncounterBucket) {
	const tool = primaryTool(bucket);
	if (isTranslatedSourceTool(tool)) return 420;
	return 260;
}

export function sectionToggleLabel(
	bucket: EncounterBucket,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	if (expansionState[sectionExpansionKey(bucket)]) return uiCopy.readerText.closePassage;
	return sectionHasSourceDetail(bucket, layerState)
		? uiCopy.passage.openSource
		: uiCopy.passage.openFull;
}

export function branchToggleLabel(bucket: EncounterBucket, collapsedBranches: ExpandedState = {}) {
	return collapsedBranches[sectionExpansionKey(bucket)]
		? uiCopy.passage.openNested
		: uiCopy.passage.closeNested;
}

export function sectionExpansionKey(bucket: EncounterBucket) {
	return `${bucket.bucket_id}:${primarySourceRef(bucket)}`;
}

export function groupToolIds(group: BucketGroup): ToolId[] {
	return [...new Set(group.buckets.flatMap((bucket) => bucket.source_tools))];
}

export function componentToolIds(component: EncounterComponent): ToolId[] {
	const meaningTools = component.evidence.meanings.flatMap((meaning) => meaning.source_tools);
	return meaningTools.length ? [...new Set(meaningTools)] : [component.source_tool];
}

export function componentPrimaryTool(component: EncounterComponent): ToolId {
	return componentToolIds(component)[0] ?? component.source_tool;
}

export function componentLabel(component: EncounterComponent) {
	return component.display || component.surface || component.lemma || 'compound member';
}

export function componentHeadwordDisplay(component: EncounterComponent, language: LanguageMode) {
	return buildComponentHeadwordDisplay({
		language,
		label: componentLabel(component)
	});
}

export function componentLookupLine(component: EncounterComponent) {
	const terms = component.lookup_terms.length ? component.lookup_terms.join(', ') : component.lemma;
	const role = component.role ? `${component.role} member` : 'compound member';
	return `${role}${terms ? `; lookup terms: ${terms}` : ''}`;
}

export function componentMeaningSegments(
	meaning: EncounterComponentMeaning,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	return glossSegments(componentMeaningText(meaning, layerState, expansionState));
}

export function componentMeaningActiveGloss(
	meaning: EncounterComponentMeaning,
	layerState: TextLayerState = {}
) {
	const key = componentMeaningKey(meaning);
	const text =
		meaning.translation && (!meaning.translation.available || layerState[key] === 'source')
			? meaning.translation.source_text
			: (meaning.translation?.target_text ?? meaning.display_gloss);
	return postProcessComponentText(meaning, text);
}

export function postProcessComponentText(meaning: EncounterComponentMeaning, value: string) {
	const tool = meaning.translation?.source_tool ?? meaning.source_tools[0];
	if (tool !== 'dico') return value;
	return value.replace(/_\d+\b/g, '');
}

export function componentMeaningText(
	meaning: EncounterComponentMeaning,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	const text = componentMeaningActiveGloss(meaning, layerState);
	if (expansionState[componentMeaningKey(meaning)]) return text;
	if (componentMeaningCanToggle(meaning, layerState)) return truncateText(text, 420);
	return text;
}

export function componentMeaningCanToggle(
	meaning: EncounterComponentMeaning,
	layerState: TextLayerState = {}
) {
	const text = componentMeaningActiveGloss(meaning, layerState);
	return text.length > 420 || glossSegments(text).length > 3;
}

export function componentMeaningKey(meaning: EncounterComponentMeaning) {
	return `component:${meaning.bucket_id}:${meaning.source_refs[0] ?? ''}`;
}

export function componentMeaningToggleLabel(
	meaning: EncounterComponentMeaning,
	expansionState: ExpandedState = {}
) {
	return expansionState[componentMeaningKey(meaning)]
		? uiCopy.passage.closeComponent
		: uiCopy.passage.openComponent;
}

export function componentHasTranslationToggle(component: EncounterComponent) {
	return component.evidence.meanings.some((meaning) =>
		isTranslatedSourceTool(meaning.translation?.source_tool)
	);
}

export function componentHasReaderTranslation(component: EncounterComponent) {
	return component.evidence.meanings.some((meaning) => meaning.translation?.available === true);
}

export function componentAwaitsReaderTranslation(
	component: EncounterComponent,
	enrichingTranslations = false
) {
	return (
		enrichingTranslations &&
		component.evidence.meanings.some((meaning) => meaningAwaitsReaderTranslation(meaning))
	);
}

export function meaningAwaitsReaderTranslation(meaning: EncounterComponentMeaning) {
	const translation = meaning.translation;
	if (!translation || translation.available) return false;
	if (translation.source_lang !== 'fr') return false;
	return isTranslatedSourceTool(translation.source_tool);
}

export function componentCanSwitchTextLayer(component: EncounterComponent) {
	return componentHasTranslationToggle(component) && componentHasReaderTranslation(component);
}

export function componentLayerIsSource(
	component: EncounterComponent,
	layerState: TextLayerState = {}
) {
	return component.evidence.meanings.some(
		(meaning) => layerState[componentMeaningKey(meaning)] === 'source'
	);
}

export function componentSourceLayerLabel(component: EncounterComponent) {
	const meaning =
		component.evidence.meanings.find((candidate) => candidate.translation) ??
		component.evidence.meanings[0];
	return meaning?.translation?.source_label ?? 'Source';
}

export function componentTranslationModel(component: EncounterComponent) {
	return component.evidence.meanings.find((meaning) => meaning.translation?.model)?.translation
		?.model;
}

export function componentMeaningSourceLabel(meaning: EncounterComponentMeaning) {
	const toolLabels = meaning.source_tools.length
		? meaning.source_tools.map((tool) => toolMeta(tool).shortLabel).join(', ')
		: 'source';
	const refs = meaning.source_refs.slice(0, 2).join(', ');
	return refs ? `${toolLabels}; ${refs}` : toolLabels;
}

export function groupWitnesses(group: BucketGroup) {
	const seen = new Set<string>();
	return group.buckets
		.flatMap((bucket) => bucket.witnesses)
		.filter((witness) => {
			const key = `${witness.tool}:${witness.source_ref ?? ''}:${witness.headword ?? ''}:${witness.label}`;
			if (seen.has(key)) return false;
			seen.add(key);
			return true;
		});
}

export function visibleGroupBuckets(group: BucketGroup, collapsedBranches: ExpandedState = {}) {
	if (!isOutlinedDictionaryTool(group.toolId)) return group.buckets;

	const buckets: EncounterBucket[] = [];
	let hiddenDepth: number | null = null;

	for (const bucket of group.buckets) {
		const depth = sourceRefDepth(bucket);

		if (hiddenDepth !== null) {
			if (depth > hiddenDepth) continue;
			hiddenDepth = null;
		}

		buckets.push(bucket);

		if (sectionHasTreeChildren(group, bucket) && collapsedBranches[sectionExpansionKey(bucket)]) {
			hiddenDepth = depth;
		}
	}

	return buckets;
}

export function sectionHasTreeChildren(group: BucketGroup, bucket: EncounterBucket) {
	if (!isOutlinedDictionaryTool(primaryTool(bucket))) return false;
	const index = group.buckets.indexOf(bucket);
	if (index === -1) return false;
	const nextBucket = group.buckets[index + 1];
	if (!nextBucket) return false;
	return sourceRefDepth(nextBucket) > sourceRefDepth(bucket);
}

export function sourceRefDepth(bucket: EncounterBucket) {
	return sourceOutlineDepth(primarySourceRef(bucket));
}

export function readerSectionClass(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	const tool = primaryTool(bucket);
	const classes = ['orion-reader-section', `orion-reader-section-${tool}`];

	if (isOutlinedDictionaryTool(tool)) {
		classes.push('orion-reader-section-outline');

		if (sourceRefDepth(bucket) === 0) classes.push('orion-reader-section-root');
		if (sourceRefDepth(bucket) === 0 && isCompactOutlineHeading(bucket, layerState)) {
			classes.push('orion-reader-section-root-compact');
		}
		if (isOutlineHeading(bucket, layerState)) classes.push('orion-reader-section-heading');
	}

	return classes.join(' ');
}

export function readerSectionStyle(bucket: EncounterBucket) {
	const depth = sourceRefDepth(bucket);
	const isOutlined = isOutlinedDictionaryTool(primaryTool(bucket));
	const indent = isOutlined ? Math.min(depth * 1.25, 5) : 0;
	const ruleWidth = isOutlined ? Math.min(depth, 4) : 0;
	const fontSize = Math.max(0.98, 1.08 - depth * 0.025);

	return `--orion-indent: ${indent}rem; --orion-rule-width: ${ruleWidth}rem; --orion-section-font: ${fontSize}rem;`;
}

export function isOutlineHeading(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	return isOutlinedDictionaryHeading(primaryTool(bucket), activeGloss(bucket, layerState));
}

export function isCompactOutlineHeading(bucket: EncounterBucket, layerState: TextLayerState = {}) {
	if (!isOutlinedDictionaryTool(primaryTool(bucket))) return false;
	return isCompactOutlinedDictionaryText(activeGloss(bucket, layerState));
}

export function groupLead(
	group: BucketGroup,
	layerState: TextLayerState = {},
	expansionState: ExpandedState = {}
) {
	const root = group.buckets.find((bucket) => sourceRefDepth(bucket) === 0) ?? group.buckets[0];
	if (!root) return '';
	const firstSegment = activeGlossSegments(root, layerState)[0] ?? activeGloss(root, layerState);
	const lead = truncateText(firstSegment, 220);
	const firstRenderedSegment =
		sectionSegments(root, layerState, expansionState)[0] ??
		sectionText(root, layerState, expansionState);

	if (
		firstSegment.replace(/\s+/g, ' ').trim().length <= 220 &&
		lead === firstRenderedSegment.replace(/\s+/g, ' ').trim()
	) {
		return '';
	}

	return lead;
}

export function sectionId(group: BucketGroup, bucket: EncounterBucket) {
	return `entry-${safeDomId(group.id)}-${safeDomId(primarySourceRef(bucket) || bucket.bucket_id)}`;
}

export function truncateText(value: string, maxLength: number) {
	const normalized = value.replace(/\s+/g, ' ').trim();
	if (normalized.length <= maxLength) return normalized;
	return `${normalized.slice(0, maxLength - 1).trim()}...`;
}

export function safeDomId(value: string) {
	return value.replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'section';
}

export function groupHasTranslationToggle(group: BucketGroup) {
	return group.buckets.some(showTranslationToggle);
}

export function groupHasReaderTranslation(group: BucketGroup) {
	return group.buckets.some(hasReaderTranslation);
}

export function groupAwaitsReaderTranslation(group: BucketGroup, enrichingTranslations = false) {
	return enrichingTranslations && group.buckets.some(bucketAwaitsReaderTranslation);
}

export function bucketAwaitsReaderTranslation(bucket: EncounterBucket) {
	const translation = bucket.translation;
	if (!translation || translation.available) return false;
	if (translation.source_lang !== 'fr') return false;
	return isTranslatedSourceTool(translation.source_tool);
}

export function groupCanSwitchTextLayer(group: BucketGroup) {
	return groupHasTranslationToggle(group) && groupHasReaderTranslation(group);
}

export function groupSourceLayerLabel(group: BucketGroup) {
	const bucket = group.buckets.find((candidate) => candidate.translation) ?? group.buckets[0];
	return sourceLayerLabel(bucket);
}

export function groupTranslationModel(group: BucketGroup) {
	return group.buckets.find((bucket) => bucket.translation?.model)?.translation?.model;
}

export function retryableGroupTranslation(group: BucketGroup) {
	return group.buckets.find((bucket) => {
		const translation = bucket.translation;
		if (!translation) return false;
		if (!isTranslatedSourceTool(translation.source_tool)) return false;
		return Boolean(
			translation.translation_id ||
			(translation.source_lexicon &&
				translation.entry_id &&
				translation.occurrence !== undefined &&
				translation.source_text_hash)
		);
	})?.translation;
}

export function groupTranslationRetryKey(group: BucketGroup) {
	const translation = retryableGroupTranslation(group);
	return (
		translation?.translation_id ||
		[
			translation?.source_lexicon ?? translation?.source_tool ?? group.toolId,
			translation?.entry_id ?? group.lexeme,
			translation?.occurrence ?? 0,
			translation?.source_text_hash ?? group.id
		].join(':')
	);
}

export function groupTranslationRetrying(
	group: BucketGroup,
	translationRetrying: Record<string, boolean> = {}
) {
	return Boolean(translationRetrying[groupTranslationRetryKey(group)]);
}

export function groupLayerIsSource(group: BucketGroup, layerState: TextLayerState = {}) {
	return group.buckets.some((bucket) => layerState[bucket.bucket_id] === 'source');
}

export function readerEntryLabel(group: BucketGroup, layerState: TextLayerState = {}) {
	if (!group.buckets.length) return uiCopy.readerText.label;
	if (groupHasTranslationToggle(group)) {
		const bucket = group.buckets.find((candidate) => candidate.translation) ?? group.buckets[0];
		return groupLayerIsSource(group, layerState) || !groupHasReaderTranslation(group)
			? sourceLayerLabel(bucket)
			: readerLayerLabel(bucket);
	}
	return uiCopy.readerText.label;
}

export function toolMeta(toolId: ToolId, mode?: LanguageMode): ToolMeta {
	return (
		tools.find((tool) => tool.id === toolId && tool.language === mode) ??
		tools.find((tool) => tool.id === toolId) ?? {
			id: toolId,
			language: mode ?? 'san',
			label: toolId,
			shortLabel: toolId,
			kind: 'tool',
			description: 'Source entry evidence.'
		}
	);
}

export function toolMnemonic(toolId: ToolId): Mnemonic {
	const mnemonics: Record<ToolId, Mnemonic> = {
		cdsl: { Icon: Turtle, name: 'Long-form Sanskrit dictionaries' },
		heritage: { Icon: Shell, name: 'Inherited-form analysis' },
		dico: { Icon: Fish, name: 'Sanskrit source with reader English' },
		diogenes: { Icon: Bird, name: 'Greek and Latin dictionary entries' },
		bailly: { Icon: BookOpen, name: 'Bailly source entries' },
		strongs_greek: { Icon: BookmarkCheck, name: "Strong's Greek source entries" },
		cts_index: { Icon: Squirrel, name: 'Citation index' },
		spacy: { Icon: Bug, name: 'Grammar probe' },
		cltk: { Icon: Cat, name: 'Supplemental lexicon' },
		whitakers: { Icon: Dog, name: 'Latin morphology' },
		gaffiot: { Icon: Snail, name: 'Gaffiot source entries' },
		lewis_1890: { Icon: ScrollText, name: 'Lewis 1890 source entries' }
	};

	return mnemonics[toolId];
}

export function readerLayerLabel(bucket: EncounterBucket) {
	return bucket.translation?.available
		? `Reader ${bucket.reader_lang.toUpperCase()}`
		: uiCopy.readerText.pending;
}

export function sourceLayerLabel(bucket: EncounterBucket) {
	return bucket.translation?.source_label ?? 'Source';
}

export function showTranslationToggle(bucket: EncounterBucket) {
	return isTranslatedSourceTool(bucket.translation?.source_tool);
}

export function hasReaderTranslation(bucket: EncounterBucket) {
	return bucket.translation?.available === true;
}

export function translationModelLabel(model: string | undefined) {
	if (!model) return '';
	const withoutProvider = model.replace(/^openai:/, '');
	const labels: Record<string, string> = {
		'google/gemini-2.5-flash': 'Gemini 2.5 Flash',
		'deepseek/deepseek-v4-flash': 'DeepSeek V4 Flash'
	};
	return labels[withoutProvider] ?? withoutProvider;
}
