import {
	toolsForLanguage,
	type EncounterResult,
	type LanguageMode,
	type ToolId
} from '../search-data';

export function encounterNeedsFreshReaderLayer(result: EncounterResult) {
	const after = result.translation_cache?.after;
	if ((after?.missing ?? 0) > 0 || (after?.errors ?? 0) > 0 || (after?.empty ?? 0) > 0) {
		return true;
	}

	return hasMissingSourceReaderTranslations(result) || hasStaleTranslatedSourceLayer(result);
}

export function hasStaleTranslatedSourceLayer(result: EncounterResult) {
	return result.buckets.some((bucket) => {
		const translation = bucket.translation;
		if (!translation?.available) return false;
		if (translation.source_lang !== 'fr') return false;
		if (!isTranslatedSourceTool(translation.source_tool)) return false;
		return sourceLayerLooksLikeReaderEnglish(translation.source_text, translation.target_text);
	});
}

export function sourceLayerLooksLikeReaderEnglish(sourceText: string, targetText: string) {
	const source = sourceText.replace(/\s+/g, ' ').trim().toLowerCase();
	const target = targetText.replace(/\s+/g, ' ').trim().toLowerCase();
	if (!source || !target) return true;
	if (source === target) return true;
	return source.length > 80 && target.length > 80 && source.slice(0, 80) === target.slice(0, 80);
}

export function hasMissingSourceReaderTranslations(result: EncounterResult) {
	const missingBucketTranslation = result.buckets.some((bucket) => {
		const translation = bucket.translation;
		if (!translation || translation.available) return false;
		if (translation.source_lang !== 'fr') return false;
		return isTranslatedSourceTool(translation.source_tool);
	});

	const missingComponentTranslation = result.components.some((component) =>
		component.evidence.meanings.some((meaning) => {
			const translation = meaning.translation;
			if (!translation || translation.available) return false;
			if (translation.source_lang !== 'fr') return false;
			return isTranslatedSourceTool(translation.source_tool);
		})
	);

	return missingBucketTranslation || missingComponentTranslation;
}

export function encounterMatchesStoredRoute(
	storedEncounter: EncounterResult | null | undefined,
	language: LanguageMode,
	query: string
) {
	return Boolean(
		storedEncounter &&
		storedEncounter.language === language &&
		storedEncounter.query.trim().toLowerCase() === query.trim().toLowerCase()
	);
}

export function validStoredTools(values: ToolId[] | undefined, mode: LanguageMode) {
	if (!values?.length) return null;
	const validToolSet = new Set(toolsForLanguage(mode).map(({ id }) => id));
	const parsed = values.filter((tool): tool is ToolId => validToolSet.has(tool));
	return parsed.length ? [...new Set(parsed)] : null;
}

export function returnedToolsForEncounter(result: EncounterResult) {
	return [
		...new Set([...result.source_tools, ...result.buckets.flatMap((bucket) => bucket.source_tools)])
	];
}

export function isTranslatedSourceTool(tool: ToolId | undefined) {
	return tool === 'dico' || tool === 'gaffiot' || tool === 'bailly';
}
