import type { LanguageMode } from './search-data';

export type HeadwordDisplayAnchor = {
	source: string;
	dictionary: string;
	query: string;
	canonical_key: string;
	canonical_name: string;
	source_name: string;
};

export type HeadwordDisplay = {
	primary: string;
	primaryLang?: string;
	title?: {
		script: 'devanagari' | 'plain';
		initial: string;
		rest: string;
	};
	forms: { label: string; value: string; kind?: 'code' }[];
};

export function buildHeadwordDisplay({
	language,
	lexeme,
	source,
	dictionary,
	groupValues,
	anchors
}: {
	language: LanguageMode;
	lexeme: string;
	source: string;
	dictionary: string;
	groupValues: string[];
	anchors: HeadwordDisplayAnchor[];
}): HeadwordDisplay {
	if (language === 'lat') {
		const primary = lexeme.normalize('NFC');
		const title = splitPlainTitle(primary);
		return { primary, ...(title ? { title } : {}), forms: [] };
	}

	if (language !== 'san' && language !== 'grc') return { primary: lexeme, forms: [] };

	const anchor = findMatchingAnchor({
		source,
		dictionary,
		groupValues: [lexeme, ...groupValues],
		anchors
	});
	if (!anchor || !hasNativeScript(anchor.canonical_name)) {
		const fallback =
			language === 'san' ? romanSanskritHeadwordFallback([lexeme, ...groupValues]) : null;
		if (fallback) return fallback;
		return { primary: lexeme, forms: [] };
	}

	const primary = anchor.canonical_name.normalize('NFC');
	const forms = dedupeForms(primary, headwordFormsForLanguage(language, anchor, lexeme));
	const title = language === 'san' ? splitDevanagariTitle(primary) : splitPlainTitle(primary);

	return {
		primary,
		primaryLang: language === 'san' ? 'sa-Deva' : 'grc',
		...(title ? { title } : {}),
		forms
	};
}

export function buildComponentHeadwordDisplay({
	language,
	label
}: {
	language: LanguageMode;
	label: string;
}): HeadwordDisplay {
	if (language !== 'san') return { primary: label, forms: [] };

	const normalizedLabel = label.normalize('NFC').trim();
	if (!normalizedLabel) return { primary: label, forms: [] };

	if (!hasDevanagari(normalizedLabel) && !canTransliterateRomanSanskrit(normalizedLabel)) {
		return { primary: normalizedLabel, forms: [] };
	}

	const primary = hasDevanagari(normalizedLabel)
		? normalizedLabel
		: romanSanskritToDevanagari(normalizedLabel);
	const title = splitDevanagariTitle(primary);
	const forms = dedupeForms(primary, [{ label: 'roman', value: normalizedLabel }]);

	return {
		primary,
		primaryLang: 'sa-Deva',
		...(title ? { title } : {}),
		forms
	};
}

function romanSanskritHeadwordFallback(values: string[]): HeadwordDisplay | null {
	const roman = values
		.map((value) => value.normalize('NFC').trim())
		.find(canTransliterateRomanSanskrit);
	if (!roman) return null;

	const primary = romanSanskritToDevanagari(roman);
	const title = splitDevanagariTitle(primary);

	return {
		primary,
		primaryLang: 'sa-Deva',
		...(title ? { title } : {}),
		forms: dedupeForms(primary, [{ label: 'roman', value: roman }])
	};
}

function headwordFormsForLanguage(
	language: LanguageMode,
	anchor: HeadwordDisplayAnchor,
	lexeme: string
) {
	if (language === 'grc') {
		return [
			{ label: 'key', value: anchor.canonical_key, kind: 'code' as const },
			{ label: 'entry', value: lexeme, kind: 'code' as const }
		];
	}

	return [
		{ label: 'roman', value: anchor.query },
		{ label: 'key', value: anchor.canonical_key, kind: 'code' as const },
		{ label: 'entry', value: lexeme, kind: 'code' as const }
	];
}

function findMatchingAnchor({
	source,
	dictionary,
	groupValues,
	anchors
}: {
	source: string;
	dictionary: string;
	groupValues: string[];
	anchors: HeadwordDisplayAnchor[];
}) {
	const groupKeys = new Set<string>();
	for (const value of groupValues) addMatchKey(groupKeys, value);

	const matchingAnchors = anchors.filter((anchor) => {
		const anchorKeys = new Set<string>();
		addMatchKey(anchorKeys, anchor.canonical_key);
		addMatchKey(anchorKeys, anchor.canonical_name);
		addMatchKey(anchorKeys, anchor.source_name);
		addMatchKey(anchorKeys, anchor.query);
		return [...anchorKeys].some((key) => groupKeys.has(key));
	});

	return (
		matchingAnchors.find((candidate) => anchorMatchesSource(candidate, source, dictionary)) ??
		matchingAnchors[0]
	);
}

function anchorMatchesSource(anchor: HeadwordDisplayAnchor, source: string, dictionary: string) {
	const anchorSource = anchor.source.toLowerCase();
	const anchorDictionary = anchor.dictionary.toLowerCase();
	const groupDictionary = dictionary.toLowerCase();

	return (
		anchorSource === source.toLowerCase() &&
		(anchorDictionary === groupDictionary || groupDictionary.includes(anchorDictionary))
	);
}

function dedupeForms(
	primary: string,
	forms: { label: string; value: string; kind?: 'code' }[]
): HeadwordDisplay['forms'] {
	const seen = new Set<string>();
	addDisplayKey(seen, primary);

	return forms.filter((form) => {
		const value = form.value.normalize('NFC').trim();
		if (!value) return false;

		const key = displayKey(value);
		if (!key || seen.has(key)) return false;
		seen.add(key);
		form.value = value;
		return true;
	});
}

function hasNativeScript(value: string) {
	return /[\u0370-\u03ff\u1f00-\u1fff\u0900-\u097f]/u.test(value);
}

function hasDevanagari(value: string) {
	return /[\u0900-\u097f]/u.test(value);
}

function splitDevanagariTitle(value: string): HeadwordDisplay['title'] {
	if (!hasDevanagari(value)) return undefined;

	const segments = graphemeSegments(value);
	if (!segments.length) return undefined;

	return {
		script: 'devanagari',
		initial: segments[0],
		rest: segments.slice(1).join('')
	};
}

function splitPlainTitle(value: string): HeadwordDisplay['title'] {
	const segments = graphemeSegments(value.trim().normalize('NFC'));
	if (!segments.length) return undefined;

	return {
		script: 'plain',
		initial: segments[0],
		rest: segments.slice(1).join('')
	};
}

function graphemeSegments(value: string) {
	const Segmenter = (
		Intl as typeof Intl & {
			Segmenter?: new (
				locale: string,
				options: { granularity: 'grapheme' }
			) => { segment(input: string): Iterable<{ segment: string }> };
		}
	).Segmenter;

	if (Segmenter) {
		return [...new Segmenter('hi', { granularity: 'grapheme' }).segment(value)].map(
			(segment) => segment.segment
		);
	}

	return Array.from(value);
}

function romanSanskritToDevanagari(value: string) {
	const tokens = tokenizeRomanSanskrit(normalizeRomanSanskrit(value));
	let output = '';

	for (let index = 0; index < tokens.length; index += 1) {
		const token = tokens[index];
		const consonant = devanagariConsonants[token];
		const vowel = devanagariVowels[token];

		if (consonant) {
			output += consonant;
			const next = tokens[index + 1];

			if (next && next in devanagariVowels) {
				output += devanagariMatras[next] ?? '';
				index += 1;
			} else {
				output += '्';
			}
		} else if (vowel) {
			output += vowel;
		} else if (token === 'ṃ') {
			output += 'ं';
		} else if (token === 'ḥ') {
			output += 'ः';
		} else {
			output += token;
		}
	}

	return output;
}

function normalizeRomanSanskrit(value: string) {
	return value
		.normalize('NFC')
		.toLowerCase()
		.replace(/aa/g, 'ā')
		.replace(/ii/g, 'ī')
		.replace(/uu/g, 'ū')
		.replace(/\.rr/g, 'ṝ')
		.replace(/\.r/g, 'ṛ')
		.replace(/\.l/g, 'ḷ')
		.replace(/~n/g, 'ñ')
		.replace(/"n/g, 'ṅ')
		.replace(/\.t/g, 'ṭ')
		.replace(/\.d/g, 'ḍ')
		.replace(/\.n/g, 'ṇ')
		.replace(/\.s/g, 'ṣ')
		.replace(/;s/g, 'ś')
		.replace(/z/g, 'ś');
}

function tokenizeRomanSanskrit(value: string) {
	const tokens: string[] = [];
	const tokenPattern =
		/kh|gh|ch|jh|ṭh|ḍh|th|dh|ph|bh|ai|au|[aāiīuūṛṝḷeoṃḥkgṅcjñṭḍṇtdnpbmyrlvśṣsh]/gy;
	let index = 0;

	while (index < value.length) {
		tokenPattern.lastIndex = index;
		const match = tokenPattern.exec(value);

		if (match) {
			tokens.push(match[0]);
			index = tokenPattern.lastIndex;
		} else {
			tokens.push(value[index]);
			index += 1;
		}
	}

	return tokens;
}

function canTransliterateRomanSanskrit(value: string) {
	const normalizedValue = normalizeRomanSanskrit(value);
	if (
		!normalizedValue ||
		genericComponentLabels.has(normalizedValue) ||
		/\s/u.test(normalizedValue)
	) {
		return false;
	}

	const tokens = tokenizeRomanSanskrit(normalizedValue);
	return (
		tokens.length > 0 &&
		tokens.every(isRomanSanskritToken) &&
		tokens.some((token) => token in devanagariVowels)
	);
}

function isRomanSanskritToken(token: string) {
	return (
		token in devanagariConsonants || token in devanagariVowels || token === 'ṃ' || token === 'ḥ'
	);
}

const genericComponentLabels = new Set(['compound', 'compound member', 'member']);

const devanagariVowels: Record<string, string> = {
	a: 'अ',
	ā: 'आ',
	i: 'इ',
	ī: 'ई',
	u: 'उ',
	ū: 'ऊ',
	ṛ: 'ऋ',
	ṝ: 'ॠ',
	ḷ: 'ऌ',
	e: 'ए',
	ai: 'ऐ',
	o: 'ओ',
	au: 'औ'
};

const devanagariMatras: Record<string, string> = {
	a: '',
	ā: 'ा',
	i: 'ि',
	ī: 'ी',
	u: 'ु',
	ū: 'ू',
	ṛ: 'ृ',
	ṝ: 'ॄ',
	ḷ: 'ॢ',
	e: 'े',
	ai: 'ै',
	o: 'ो',
	au: 'ौ'
};

const devanagariConsonants: Record<string, string> = {
	k: 'क',
	kh: 'ख',
	g: 'ग',
	gh: 'घ',
	ṅ: 'ङ',
	c: 'च',
	ch: 'छ',
	j: 'ज',
	jh: 'झ',
	ñ: 'ञ',
	ṭ: 'ट',
	ṭh: 'ठ',
	ḍ: 'ड',
	ḍh: 'ढ',
	ṇ: 'ण',
	t: 'त',
	th: 'थ',
	d: 'द',
	dh: 'ध',
	n: 'न',
	p: 'प',
	ph: 'फ',
	b: 'ब',
	bh: 'भ',
	m: 'म',
	y: 'य',
	r: 'र',
	l: 'ल',
	v: 'व',
	ś: 'श',
	ṣ: 'ष',
	s: 'स',
	h: 'ह'
};

function addMatchKey(keys: Set<string>, value: string | undefined) {
	const key = strictStudyKey(value);
	if (key) keys.add(key);
	const sanskritKey = sanskritSourceStudyKey(value);
	if (sanskritKey) keys.add(sanskritKey);
}

function addDisplayKey(keys: Set<string>, value: string | undefined) {
	const key = displayKey(value);
	if (key) keys.add(key);
}

function displayKey(value: string | undefined) {
	return strictStudyKey(value);
}

function strictStudyKey(value: string | undefined) {
	return (value ?? '')
		.replace(/^lex:/, '')
		.replace(/#(?:noun|verb|adj|adjective|adv|adverb)\b/gi, '')
		.normalize('NFC')
		.toLowerCase()
		.replace(/[^a-z0-9.\-āīūṛṝḷḹṃḥṅñṭḍṇśṣ\u0370-\u03ff\u1f00-\u1fff\u0900-\u097f]+/gu, '')
		.trim();
}

function sanskritSourceStudyKey(value: string | undefined) {
	return strictStudyKey(value)
		.replace(/\.n/g, 'ṇ')
		.replace(/\.s/g, 'ṣ')
		.replace(/aa/g, 'ā')
		.replace(/ii/g, 'ī')
		.replace(/uu/g, 'ū')
		.replace(/[^a-z0-9āīūṛṝḷḹṃḥṅñṭḍṇśṣ\u0900-\u097f]+/gu, '')
		.trim();
}
