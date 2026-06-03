import type {
	LanguageMode,
	SearchBackend,
	ToolRequest,
	TranslationMode,
	WordRecommendationItem,
	WordRecommendationResult
} from '../search-data';

type LooseWordRecommendationItem = Partial<WordRecommendationItem> & {
	canonical_name?: string;
	canonical?: {
		name?: string;
		display?: string;
		transliteration?: string;
		roman?: string;
		iast?: string;
		script?: string;
	};
	display_forms?: Partial<WordRecommendationItem['display_forms']> & {
		devanagari?: string;
		greek?: string;
		iast?: string;
		transliteration?: string;
	};
	forms?: Partial<WordRecommendationItem['display_forms']> & {
		devanagari?: string;
		greek?: string;
		iast?: string;
		transliteration?: string;
	};
};

export function normalizeMotdResult(result: WordRecommendationResult): WordRecommendationResult {
	return {
		schema_version: result.schema_version || 'langnet.word_of_day.v1',
		generated_at: result.generated_at || new Date().toISOString(),
		suggested_ttl_seconds: result.suggested_ttl_seconds || 3600,
		items: Array.isArray(result.items)
			? result.items.map((item) => normalizeMotdItem(item)).filter(isPresentableMotdItem)
			: [],
		exhaustion: result.exhaustion,
		warnings: Array.isArray(result.warnings) ? result.warnings : [],
		error: result.error
	};
}

export function normalizeMotdItem(input: WordRecommendationItem): WordRecommendationItem {
	const item = input as LooseWordRecommendationItem;
	const language = item.language ?? 'san';
	const query = item.query || item.primary_lexeme || item.display || 'word';
	const canonical = item.canonical;
	const forms = item.display_forms ?? item.forms ?? {};
	const native =
		forms.native ||
		forms.devanagari ||
		forms.greek ||
		canonical?.name ||
		canonical?.display ||
		item.canonical_name ||
		item.display ||
		query;
	const roman =
		forms.roman ||
		forms.iast ||
		forms.transliteration ||
		canonical?.transliteration ||
		canonical?.roman ||
		canonical?.iast ||
		item.display ||
		query;
	const canonicalDisplay =
		forms.canonical || canonical?.display || canonical?.name || item.canonical_name || native;

	return {
		language,
		query,
		key: item.key || `${language}:${query}`,
		display: item.display || query,
		primary_lexeme: item.primary_lexeme || query,
		lexeme_anchors: item.lexeme_anchors ?? [],
		summary: item.summary ?? '',
		learner_note: item.learner_note ?? '',
		mnemonic: item.mnemonic ?? '',
		difficulty: item.difficulty ?? 'beginner',
		confidence: item.confidence ?? 'unknown',
		ambiguity: {
			has_multiple_lexemes: Boolean(item.ambiguity?.has_multiple_lexemes),
			lexeme_count: item.ambiguity?.lexeme_count ?? 0,
			note: item.ambiguity?.note ?? ''
		},
		recommended_request: {
			language: item.recommended_request?.language ?? language,
			q: item.recommended_request?.q ?? query,
			dictionary: item.recommended_request?.dictionary ?? ('all' as ToolRequest),
			translation: item.recommended_request?.translation ?? ('auto' as TranslationMode),
			backend: item.recommended_request?.backend ?? ('cli' as SearchBackend)
		},
		source_basis: item.source_basis ?? [],
		display_forms: {
			native,
			roman,
			canonical: canonicalDisplay,
			script: forms.script || canonical?.script || ''
		},
		ui: {
			href_query: item.ui?.href_query ?? '',
			badge: item.ui?.badge ?? '',
			short_gloss: item.ui?.short_gloss ?? ''
		},
		novelty: item.novelty
	};
}

export function isPresentableMotdItem(item: WordRecommendationItem) {
	return Boolean(
		(
			item.display ||
			item.query ||
			item.primary_lexeme ||
			item.ui?.short_gloss ||
			item.summary ||
			item.learner_note ||
			item.mnemonic
		).trim()
	);
}

export function motdDisplayWord(item: WordRecommendationItem) {
	const display = item.display || item.query || item.primary_lexeme || 'word';
	const preferred = item.display_forms.native || item.display_forms.canonical || display;
	const cleaned =
		item.language === 'lat'
			? stripLatinMotdTags(preferred)
			: item.language === 'grc'
				? stripGreekMotdEncoding(preferred)
				: item.language === 'san'
					? stripSanskritMotdEncoding(preferred)
					: preferred;
	return cleaned.normalize('NFC');
}

export function motdWordClass(item: WordRecommendationItem) {
	if (item.language === 'grc') return 'orion-motd-word orion-motd-word-grc';
	if (item.language === 'san') return 'orion-motd-word orion-motd-word-san';
	return 'orion-motd-word';
}

export function motdWordLang(item: WordRecommendationItem) {
	if (item.language === 'grc') return 'grc';
	if (item.language === 'san') {
		const script = item.display_forms.script.toLowerCase();
		if (script.includes('deva') || /[\u0900-\u097F]/u.test(motdDisplayWord(item))) {
			return 'sa-Deva';
		}
		return 'sa-Latn';
	}
	return 'la';
}

export function motdDisplayLookup(item: WordRecommendationItem) {
	if (item.language !== 'grc' && item.language !== 'san') return '';
	const display = motdDisplayWord(item).toLowerCase();
	const lookup =
		item.language === 'grc'
			? greekMotdRomanLookup(item)
			: stripSanskritMotdEncoding(
					item.display_forms.roman || item.query || item.primary_lexeme || item.display
				);
	if (!lookup || lookup.toLowerCase() === display) return '';
	return lookup;
}

export function motdDisplayGloss(item: WordRecommendationItem) {
	return (
		item.ui?.short_gloss || item.summary || item.learner_note || item.mnemonic || 'Learner word.'
	);
}

export function motdDisplayNote(item: WordRecommendationItem) {
	const note = item.mnemonic || item.ui?.short_gloss || item.summary || item.learner_note || '';
	return note
		.replace(/^Query\s+`[^`]+`\s+is backed by source evidence for\s+[^.]+\.?\s*/i, '')
		.replace(/^Query\s+`[^`]+`\s+opens\s+[^,]+,\s*/i, '')
		.trim();
}

export function motdVisibleWarnings(result: WordRecommendationResult | null) {
	const hasItems = Boolean(result?.items.some(isPresentableMotdItem));
	return (
		result?.warnings.filter((warning) => shouldShowMotdWarning(warning.message, hasItems)) ?? []
	);
}

export function shouldShowMotdWarning(message: string, hasItems: boolean) {
	if (!hasItems) return true;
	return !isRecoverableMotdWarning(message);
}

export function isRecoverableMotdWarning(message: string) {
	return (
		/encounter returned no usable source-backed buckets/i.test(message) ||
		/LLM card finalization unavailable/i.test(message) ||
		/Precomputed learner pool fell back to curated words/i.test(message) ||
		/Precomputed learner pool returned no cards/i.test(message) ||
		/MOTD pool database does not exist/i.test(message) ||
		/live LLM recommendations warm in the background/i.test(message)
	);
}

export function stripLatinMotdTags(value: string) {
	return value.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '').trim() || value;
}

export function stripGreekMotdEncoding(value: string) {
	const cleaned = value
		.normalize('NFC')
		.replace(/_\d+\b/g, '')
		.replace(/[_]+/g, '')
		.replace(/(?:^|[\s([{])[-]+/g, (match) => match.replace(/-/g, ''))
		.replace(/[-]+(?=$|[\s)\]}])/g, '')
		.replace(/-/g, '')
		.replace(/\s+/g, ' ')
		.trim();

	return cleaned || value;
}

export function stripSanskritMotdEncoding(value: string) {
	return value
		.normalize('NFC')
		.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '')
		.replace(/_\d+\b/g, '')
		.replace(/[_-]+/g, '')
		.replace(/\s+/g, ' ')
		.trim();
}

function greekMotdRomanLookup(item: WordRecommendationItem) {
	const provided = stripGreekMotdLookup(
		item.display_forms.roman || item.primary_lexeme || item.query || item.display
	);
	if (provided && !/[\u0370-\u03ff]/u.test(provided)) return provided;
	return transliterateGreekMotd(motdDisplayWord(item));
}

function stripGreekMotdLookup(value: string) {
	return stripGreekMotdEncoding(value).replace(/-/g, '').trim();
}

function transliterateGreekMotd(value: string) {
	const table: Record<string, string> = {
		α: 'a',
		β: 'b',
		γ: 'g',
		δ: 'd',
		ε: 'e',
		ζ: 'z',
		η: 'e',
		θ: 'th',
		ι: 'i',
		κ: 'k',
		λ: 'l',
		μ: 'm',
		ν: 'n',
		ξ: 'x',
		ο: 'o',
		π: 'p',
		ρ: 'r',
		σ: 's',
		ς: 's',
		τ: 't',
		υ: 'u',
		φ: 'ph',
		χ: 'ch',
		ψ: 'ps',
		ω: 'o'
	};
	const normalized = stripGreekMotdEncoding(value)
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase();
	return normalized
		.split('')
		.map((char) => table[char] ?? char)
		.join('')
		.replace(/\s+/g, ' ')
		.trim();
}
