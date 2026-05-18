import type { LanguageMode } from './search-data';

export type SearchRomanization = {
	label: 'IAST' | 'roman';
	value: string;
};

export function romanizeSearchTerm(
	language: LanguageMode,
	value: string
): SearchRomanization | null {
	const input = value.trim().normalize('NFC');
	if (!input) return null;

	if (language === 'san' && /[\u0900-\u097f]/u.test(input)) {
		const roman = romanizeDevanagari(input);
		return roman ? { label: 'IAST', value: roman } : null;
	}

	if (language === 'grc' && /[\u0370-\u03ff\u1f00-\u1fff]/u.test(input)) {
		const roman = romanizeGreek(input);
		return roman ? { label: 'roman', value: roman } : null;
	}

	return null;
}

function romanizeDevanagari(value: string) {
	let output = '';

	for (let index = 0; index < value.length; index += 1) {
		const char = value[index];
		const next = value[index + 1];

		if (char in devanagariConsonants) {
			output += devanagariConsonants[char];

			if (next === virama) {
				index += 1;
				continue;
			}

			if (next && next in devanagariMatras) {
				output += devanagariMatras[next];
				index += 1;
				continue;
			}

			output += 'a';
			continue;
		}

		if (char in devanagariVowels) {
			output += devanagariVowels[char];
			continue;
		}

		if (char in devanagariMarks) {
			output += devanagariMarks[char];
			continue;
		}

		if (char in devanagariMatras || char === virama || char === '\u200d' || char === '\u200c') {
			continue;
		}

		output += char;
	}

	return output.normalize('NFC').trim();
}

function romanizeGreek(value: string) {
	let output = '';
	const chars = Array.from(value.normalize('NFC'));

	for (let index = 0; index < chars.length; index += 1) {
		const char = chars[index];
		if (isGreekCombiningMark(char)) continue;

		const decomposed = char.normalize('NFD');
		const base = decomposed[0];
		const marks = decomposed.slice(1);
		const next = chars[index + 1];
		const nextBase = next?.normalize('NFD')[0].toLowerCase();
		const diphthong = greekDiphthongs[`${base.toLowerCase()}${nextBase ?? ''}`];
		const roman = greekLetters[base.toLowerCase()];
		if (!roman) {
			output += char;
			continue;
		}

		const hasRoughBreathing = marks.includes('\u0314');
		if (hasRoughBreathing && isGreekVowel(base)) output += 'h';
		if (hasRoughBreathing && base.toLowerCase() === 'ρ') {
			output += 'rh';
			continue;
		}

		if (diphthong) {
			output += diphthong;
			index += 1;
			continue;
		}

		output += roman;
	}

	return output.normalize('NFC').trim();
}

function isGreekCombiningMark(value: string) {
	return /[\u0300-\u036f]/u.test(value);
}

function isGreekVowel(value: string) {
	return /[αεηιουω]/iu.test(value);
}

const virama = '्';

const devanagariVowels: Record<string, string> = {
	अ: 'a',
	आ: 'ā',
	इ: 'i',
	ई: 'ī',
	उ: 'u',
	ऊ: 'ū',
	ऋ: 'ṛ',
	ॠ: 'ṝ',
	ऌ: 'ḷ',
	ॡ: 'ḹ',
	ए: 'e',
	ऐ: 'ai',
	ओ: 'o',
	औ: 'au'
};

const devanagariMatras: Record<string, string> = {
	'ा': 'ā',
	'ि': 'i',
	'ी': 'ī',
	'ु': 'u',
	'ू': 'ū',
	'ृ': 'ṛ',
	'ॄ': 'ṝ',
	'ॢ': 'ḷ',
	'ॣ': 'ḹ',
	'े': 'e',
	'ै': 'ai',
	'ो': 'o',
	'ौ': 'au'
};

const devanagariMarks: Record<string, string> = {
	'ं': 'ṃ',
	'ँ': 'm̐',
	'ः': 'ḥ',
	ऽ: "'"
};

const devanagariConsonants: Record<string, string> = {
	क: 'k',
	ख: 'kh',
	ग: 'g',
	घ: 'gh',
	ङ: 'ṅ',
	च: 'c',
	छ: 'ch',
	ज: 'j',
	झ: 'jh',
	ञ: 'ñ',
	ट: 'ṭ',
	ठ: 'ṭh',
	ड: 'ḍ',
	ढ: 'ḍh',
	ण: 'ṇ',
	त: 't',
	थ: 'th',
	द: 'd',
	ध: 'dh',
	न: 'n',
	प: 'p',
	फ: 'ph',
	ब: 'b',
	भ: 'bh',
	म: 'm',
	य: 'y',
	र: 'r',
	ल: 'l',
	व: 'v',
	श: 'ś',
	ष: 'ṣ',
	स: 's',
	ह: 'h',
	ळ: 'ḷ'
};

const greekLetters: Record<string, string> = {
	α: 'a',
	β: 'b',
	γ: 'g',
	δ: 'd',
	ε: 'e',
	ζ: 'z',
	η: 'ē',
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
	υ: 'y',
	φ: 'ph',
	χ: 'ch',
	ψ: 'ps',
	ω: 'ō'
};

const greekDiphthongs: Record<string, string> = {
	αι: 'ai',
	ει: 'ei',
	οι: 'oi',
	υι: 'yi',
	αυ: 'au',
	ευ: 'eu',
	ηυ: 'ēu',
	ου: 'ou'
};
