import type { LanguageMode, ToolRequest, TranslationMode } from '$lib/search-data';

export type PublicWordOfDay = {
	language: LanguageMode;
	date: string;
	query: string;
	display: string;
	transliteration?: string;
	gloss: string;
	note: string;
	dictionary: ToolRequest;
	translation: TranslationMode;
	href: string;
	sourceNote: string;
};

const wordsByLanguage: Record<LanguageMode, Omit<PublicWordOfDay, 'date' | 'href'>[]> = {
	lat: [
		{
			language: 'lat',
			query: 'lumen',
			display: 'lumen',
			gloss: 'light; clarity; daylight',
			note: 'A compact Latin noun for practicing how dictionary senses move from physical light into metaphor.',
			dictionary: 'whitakers',
			translation: 'cache',
			sourceNote: 'Open the lookup desk to compare forms, headwords, and dictionary witnesses.'
		},
		{
			language: 'lat',
			query: 'fero',
			display: 'fero',
			gloss: 'carry; bear; bring',
			note: 'A high-frequency verb where form recognition matters before choosing a smooth English gloss.',
			dictionary: 'whitakers',
			translation: 'cache',
			sourceNote: 'Use the source shelf to inspect how tools handle irregular stems and common meanings.'
		},
		{
			language: 'lat',
			query: 'virtus',
			display: 'virtus',
			gloss: 'excellence; courage; worth',
			note: 'A good test case for keeping lexical range visible instead of collapsing to one modern abstraction.',
			dictionary: 'lewis_1890',
			translation: 'cache',
			sourceNote: 'Compare witnesses before deciding which sense fits a passage.'
		}
	],
	grc: [
		{
			language: 'grc',
			query: 'logos',
			display: 'λόγος',
			transliteration: 'logos',
			gloss: 'word; account; reason',
			note: 'A Greek word that demonstrates why readable glosses need visible source and context boundaries.',
			dictionary: 'diogenes',
			translation: 'cache',
			sourceNote: 'Open lookup to inspect lexeme, morphology, and dictionary evidence together.'
		},
		{
			language: 'grc',
			query: 'physis',
			display: 'φύσις',
			transliteration: 'physis',
			gloss: 'nature; growth; origin',
			note: 'A useful word for seeing how Greek lexical evidence preserves range and tradition.',
			dictionary: 'diogenes',
			translation: 'cache',
			sourceNote: 'Keep script, transliteration, and source witness in view while reading.'
		},
		{
			language: 'grc',
			query: 'dikaios',
			display: 'δίκαιος',
			transliteration: 'dikaios',
			gloss: 'just; right; lawful',
			note: 'A strong example of why the reading desk should show witnesses rather than a single oracle answer.',
			dictionary: 'diogenes',
			translation: 'cache',
			sourceNote: 'Use lookup to compare dictionary grouping and learner-facing glosses.'
		}
	],
	san: [
		{
			language: 'san',
			query: 'agni',
			display: 'अग्नि',
			transliteration: 'agni',
			gloss: 'fire; Agni',
			note: 'A beginner-friendly Sanskrit entry where script, transliteration, dictionary range, and name/function all matter.',
			dictionary: 'cdsl',
			translation: 'cache',
			sourceNote: 'Open lookup to inspect source-backed meanings and available morphology.'
		},
		{
			language: 'san',
			query: 'dharma',
			display: 'धर्म',
			transliteration: 'dharma',
			gloss: 'law; duty; order',
			note: 'A Sanskrit word where source range and caveats are more useful than a single fluent translation.',
			dictionary: 'cdsl',
			translation: 'cache',
			sourceNote: 'Use the desk to keep dictionary witnesses and learner notes separate.'
		},
		{
			language: 'san',
			query: 'ātman',
			display: 'आत्मन्',
			transliteration: 'ātman',
			gloss: 'self; breath; essence',
			note: 'A helpful example for preserving lexical range while making the first reading step approachable.',
			dictionary: 'cdsl',
			translation: 'cache',
			sourceNote: 'Lookup can expose source claims without pretending context has been solved.'
		}
	]
};

export function publicWordOfDay(language: LanguageMode, date = new Date()): PublicWordOfDay {
	const words = wordsByLanguage[language];
	const day = date.toISOString().slice(0, 10);
	const index = dayNumber(date) % words.length;
	const word = words[index];
	const params = new URLSearchParams({
		lang: word.language,
		q: word.query,
		translation: word.translation
	});
	return {
		...word,
		date: day,
		href: `/q?${params.toString()}`
	};
}

export function isPublicWordLanguage(value: string | null): value is LanguageMode {
	return value === 'lat' || value === 'grc' || value === 'san';
}

function dayNumber(date: Date) {
	return Math.floor(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) / 86_400_000);
}
