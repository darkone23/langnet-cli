import type { WordIndexOrder, WordIndexSection, WordIndexSectionsResponse } from './word-index';
import type { LanguageMode } from './search-data';

type SectionSpec = {
	id: string;
	label: string;
	transliteration: string;
	prefix: string;
	sourcePrefix?: string;
	groupLabel: string;
	orderKey: string;
};

export function wordIndexSectionsResponse(
	language: LanguageMode,
	source = 'all'
): WordIndexSectionsResponse {
	return {
		schema_version: 'langnet.word_index.sections.v1',
		request: { language, source },
		order: sectionOrder(language, source),
		sections: sectionSpecs(language).map((spec) => sectionFromSpec(spec, language, source)),
		warnings: sectionWarnings(language, source)
	};
}

function sectionFromSpec(
	spec: SectionSpec,
	language: LanguageMode,
	source: string
): WordIndexSection {
	const query = spec.sourcePrefix ?? spec.prefix;
	const order = sectionOrder(language, source);

	return {
		id: spec.id,
		label: spec.label,
		transliteration: spec.transliteration,
		group_label: spec.groupLabel,
		order_key: spec.orderKey,
		available: true,
		entry_count: 0,
		anchor: {
			language,
			source,
			dictionary: source === 'all' ? '' : source,
			query,
			canonical_key: spec.prefix,
			source_order_key: spec.orderKey,
			lexeme_id: '',
			index_entry_id: '',
			source_order_id: '',
			display: {
				primary: spec.label,
				transliteration: spec.transliteration,
				source_key: query
			},
			order
		}
	};
}

function sectionOrder(language: LanguageMode, source: string): WordIndexOrder {
	if (language === 'san') {
		return {
			policy: 'language-native',
			label: 'Sanskrit varnamala sections',
			collation: 'san-varnamala',
			key: 'san:varnamala',
			display_key: 'अ आ इ ई ... क ख ग घ ...',
			explanation: `Section anchors for source=${source} follow Sanskrit varnamala order.`
		};
	}

	if (language === 'grc') {
		return {
			policy: 'language-native',
			label: 'Greek alphabet sections',
			collation: 'grc-lexical',
			key: 'grc:alphabet',
			display_key: 'Α Β Γ Δ ...',
			explanation: `Section anchors for source=${source} follow Greek alphabet sections.`
		};
	}

	return {
		policy: 'language-native',
		label: 'Latin alphabet sections',
		collation: 'lat-lexical',
		key: 'lat:alphabet',
		display_key: 'A B C D ...',
		explanation: `Section anchors for source=${source} follow conventional Latin alphabet sections.`
	};
}

function sectionWarnings(language: LanguageMode, source: string) {
	if (language !== 'san') return [];
	return [
		{
			source,
			language,
			message:
				'Section anchors follow a Sanskrit varnamala rail. Open a section with word-index nearby to use source-local dictionary order.'
		}
	];
}

function sectionSpecs(language: LanguageMode): SectionSpec[] {
	if (language === 'san') return sanskritSectionSpecs();
	if (language === 'grc') return greekSectionSpecs();
	return latinSectionSpecs();
}

function latinSectionSpecs(): SectionSpec[] {
	return Array.from({ length: 26 }, (_, index) => {
		const label = String.fromCharCode('A'.charCodeAt(0) + index);
		const transliteration = label.toLowerCase();
		return {
			id: `lat:${transliteration}`,
			label,
			transliteration,
			prefix: transliteration,
			groupLabel: 'Latin',
			orderKey: `${index + 1}`.padStart(3, '0')
		};
	});
}

function greekSectionSpecs(): SectionSpec[] {
	const labels: [string, string, string?][] = [
		['Α', 'a'],
		['Β', 'b'],
		['Γ', 'g'],
		['Δ', 'd'],
		['Ε', 'e'],
		['Ζ', 'z'],
		['Η', 'h'],
		['Θ', 'th', 'q'],
		['Ι', 'i'],
		['Κ', 'k'],
		['Λ', 'l'],
		['Μ', 'm'],
		['Ν', 'n'],
		['Ξ', 'x', 'c'],
		['Ο', 'o'],
		['Π', 'p'],
		['Ρ', 'r'],
		['Σ', 's'],
		['Τ', 't'],
		['Υ', 'u'],
		['Φ', 'ph', 'f'],
		['Χ', 'ch', 'x'],
		['Ψ', 'ps', 'y'],
		['Ω', 'w', 'ō']
	];

	return labels.map(([label, transliteration, sourcePrefix], index) => ({
		id: `grc:${transliteration}`,
		label,
		transliteration,
		prefix: transliteration,
		sourcePrefix,
		groupLabel: 'Greek',
		orderKey: `${index + 1}`.padStart(3, '0')
	}));
}

function sanskritSectionSpecs(): SectionSpec[] {
	const groups: [string, [string, string, string, string][]][] = [
		[
			'Vowels',
			[
				['अ', 'a', 'a', 'a'],
				['आ', 'ā', 'aa', 'A'],
				['इ', 'i', 'i', 'i'],
				['ई', 'ī', 'ii', 'I'],
				['उ', 'u', 'u', 'u'],
				['ऊ', 'ū', 'uu', 'U'],
				['ऋ', 'ṛ', 'r', 'f'],
				['ॠ', 'ṝ', 'rr', 'F'],
				['ऌ', 'ḷ', 'l', 'x'],
				['ॡ', 'ḹ', 'll', 'X'],
				['ए', 'e', 'e', 'e'],
				['ऐ', 'ai', 'ai', 'E'],
				['ओ', 'o', 'o', 'o'],
				['औ', 'au', 'au', 'O'],
				['अं', 'ṃ', 'anusvara', 'aM'],
				['अः', 'ḥ', 'visarga', 'aH']
			]
		],
		[
			'Velars',
			[
				['क', 'ka', 'ka', 'k'],
				['ख', 'kha', 'kha', 'K'],
				['ग', 'ga', 'ga', 'g'],
				['घ', 'gha', 'gha', 'G'],
				['ङ', 'ṅa', 'nga', 'N']
			]
		],
		[
			'Palatals',
			[
				['च', 'ca', 'ca', 'c'],
				['छ', 'cha', 'cha', 'C'],
				['ज', 'ja', 'ja', 'j'],
				['झ', 'jha', 'jha', 'J'],
				['ञ', 'ña', 'nya', 'Y']
			]
		],
		[
			'Retroflexes',
			[
				['ट', 'ṭa', 'tta', 'w'],
				['ठ', 'ṭha', 'ttha', 'W'],
				['ड', 'ḍa', 'dda', 'q'],
				['ढ', 'ḍha', 'ddha', 'Q'],
				['ण', 'ṇa', 'nna', 'R']
			]
		],
		[
			'Dentals',
			[
				['त', 'ta', 'ta', 't'],
				['थ', 'tha', 'tha', 'T'],
				['द', 'da', 'da', 'd'],
				['ध', 'dha', 'dha', 'D'],
				['न', 'na', 'na', 'n']
			]
		],
		[
			'Labials',
			[
				['प', 'pa', 'pa', 'p'],
				['फ', 'pha', 'pha', 'P'],
				['ब', 'ba', 'ba', 'b'],
				['भ', 'bha', 'bha', 'B'],
				['म', 'ma', 'ma', 'm']
			]
		],
		[
			'Semivowels',
			[
				['य', 'ya', 'ya', 'y'],
				['र', 'ra', 'ra', 'r'],
				['ल', 'la', 'la', 'l'],
				['व', 'va', 'va', 'v']
			]
		],
		[
			'Sibilants',
			[
				['श', 'śa', 'sha', 'S'],
				['ष', 'ṣa', 'ssa', 'z'],
				['स', 'sa', 'sa', 's']
			]
		],
		['Aspirate', [['ह', 'ha', 'ha', 'h']]],
		[
			'Conjuncts',
			[
				['क्ष', 'kṣa', 'ksha', 'kz'],
				['त्र', 'tra', 'tra', 'tr'],
				['ज्ञ', 'jña', 'jnya', 'jY']
			]
		]
	];

	let index = 1;
	const specs: SectionSpec[] = [];
	for (const [groupLabel, labels] of groups) {
		for (const [label, transliteration, idKey, sourcePrefix] of labels) {
			specs.push({
				id: `san:${idComponent(groupLabel)}:${idComponent(idKey)}`,
				label,
				transliteration,
				prefix: idKey,
				sourcePrefix,
				groupLabel,
				orderKey: `${index}`.padStart(3, '0')
			});
			index += 1;
		}
	}
	return specs;
}

function idComponent(value: string) {
	return value
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}
