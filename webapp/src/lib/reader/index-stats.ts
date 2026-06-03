import {
	readerIndexStatsKey,
	type ReaderAuthorSection,
	type ReaderCatalog,
	type ReaderIndexStats
} from './index';
import type { LanguageMode } from '../search-data';

type LanguageModeLike = {
	id: LanguageMode;
};

export function readerIndexStatsFromSections(
	targetLanguage: LanguageMode,
	targetCatalogId: string,
	sections: ReaderAuthorSection[]
): ReaderIndexStats {
	return {
		language: targetLanguage,
		catalogId: targetCatalogId,
		workCount: sections.reduce((count, section) => count + section.work_count, 0),
		authorCount: sections.reduce((count, section) => count + section.author_count, 0)
	};
}

export function findReaderIndexStatsInList(
	stats: ReaderIndexStats[],
	targetLanguage: LanguageMode,
	targetCatalogId: string
) {
	const key = readerIndexStatsKey(targetLanguage, targetCatalogId);
	return stats.find((item) => readerIndexStatsKey(item.language, item.catalogId) === key);
}

export function upsertReaderIndexStatsList(stats: ReaderIndexStats[], next: ReaderIndexStats) {
	const key = readerIndexStatsKey(next.language, next.catalogId);
	return [
		...stats.filter((item) => readerIndexStatsKey(item.language, item.catalogId) !== key),
		next
	];
}

export function defaultReaderCatalogForLanguage(
	catalogs: ReaderCatalog[],
	catalogDefaults: Partial<Record<LanguageMode, string>>,
	targetLanguage: LanguageMode
) {
	return (
		catalogDefaults[targetLanguage] ??
		catalogs.find((catalog) => catalog.available && catalog.languages.includes(targetLanguage))
			?.id ??
		''
	);
}

export function buildReaderIndexStatsTargets({
	catalogs,
	catalogDefaults,
	languageModes,
	activeLanguage,
	activeCatalogId
}: {
	catalogs: ReaderCatalog[];
	catalogDefaults: Partial<Record<LanguageMode, string>>;
	languageModes: LanguageModeLike[];
	activeLanguage: LanguageMode;
	activeCatalogId: string;
}) {
	const targets = new Map<string, { language: LanguageMode; catalogId: string }>();
	for (const mode of languageModes) {
		const catalogId = defaultReaderCatalogForLanguage(catalogs, catalogDefaults, mode.id);
		if (catalogId)
			targets.set(readerIndexStatsKey(mode.id, catalogId), { language: mode.id, catalogId });
	}
	if (activeCatalogId) {
		targets.set(readerIndexStatsKey(activeLanguage, activeCatalogId), {
			language: activeLanguage,
			catalogId: activeCatalogId
		});
	}
	return Array.from(targets.values());
}
