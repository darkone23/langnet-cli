import { romanizeSearchTerm } from '../search-romanization';
import type { LanguageMode } from '../search-data';
import type { ReaderSegment } from './index';

export type ReaderTokenPart = {
	key: string;
	text: string;
	word: string;
	isWord: boolean;
	transliteration?: string;
};

export function cleanReaderToken(value: string) {
	return value
		.normalize('NFC')
		.replace(/^[^\p{L}\p{M}]+|[^\p{L}\p{M}]+$/gu, '')
		.trim();
}

export function readerSegmentDisplayText(segment: ReaderSegment) {
	return (
		segment.display?.primary ||
		segment.native_script ||
		segment.display?.native_script ||
		segment.text ||
		''
	);
}

export function readerSegmentTransliterationText(segment: ReaderSegment) {
	return segment.display?.transliteration || segment.transliteration || '';
}

export function buildReaderTokenParts(
	segment: ReaderSegment,
	language: LanguageMode,
	showTransliteration: boolean
): ReaderTokenPart[] {
	const parts = tokenizeReaderText(readerSegmentDisplayText(segment));
	if (!showTransliteration) return parts;

	const alignedTransliteration = alignedTransliterationWords(
		parts,
		readerSegmentTransliterationText(segment)
	);
	let wordIndex = 0;

	return parts.map((part) => {
		if (!part.isWord) return part;

		const transliteration =
			alignedTransliteration[wordIndex] || romanizeSearchTerm(language, part.word)?.value || '';
		wordIndex += 1;

		return transliteration ? { ...part, transliteration } : part;
	});
}

export function tokenizeReaderText(text: string): ReaderTokenPart[] {
	const parts =
		text.match(
			/[\p{L}\p{M}\u0300-\u036f]+(?:[’'][\p{L}\p{M}\u0300-\u036f]+)?|[^\p{L}\p{M}\u0300-\u036f]+/gu
		) ?? [];
	return parts.map((part, index) => {
		const word = cleanReaderToken(part);
		return {
			key: `${index}:${part}`,
			text: part,
			word,
			isWord: Boolean(word && /[\p{L}]/u.test(word))
		};
	});
}

function alignedTransliterationWords(parts: ReaderTokenPart[], transliteration: string) {
	const sourceWordCount = parts.filter((part) => part.isWord).length;
	const transliterationWords = tokenizeReaderText(transliteration)
		.filter((part) => part.isWord)
		.map((part) => part.word);

	return transliterationWords.length === sourceWordCount ? transliterationWords : [];
}
