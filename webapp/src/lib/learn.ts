import type { LanguageMode } from './search-data';

export type LearnGateway = {
	language: LanguageMode;
	label: string;
	term: string;
	role: string;
};

export type LearnPracticeWord = {
	language: LanguageMode;
	word: string;
	gloss: string;
	note: string;
};

export type LearnSourceReference = {
	language: LanguageMode;
	label: string;
	workId: string;
	canonicalId: string;
	segment?: string;
	note: string;
};

export type LearnConcept = {
	id: string;
	kind: string;
	foster: string;
	traditional: string;
	plainEnglish: string;
	readerQuestion: string;
	tableCue: string;
	gateways: Record<LanguageMode, LearnGateway[]>;
	practice: LearnPracticeWord[];
	sources: Record<LanguageMode, LearnSourceReference[]>;
};

export type LearnStep = {
	title: string;
	body: string;
};

export type LearnStartCard = {
	id: string;
	title: string;
	body: string;
	prompt: string;
};

export type LearnScriptRow = {
	symbol: string;
	roman: string;
	name: string;
	note: string;
};

export type LearnScriptGuide = {
	language: LanguageMode;
	label: string;
	script: string;
	intro: string;
	rows: LearnScriptRow[];
};

export const learnStartCards: LearnStartCard[] = [
	{
		id: 'form',
		title: 'What is a form?',
		body: 'A form is the word shape on the page. In these languages, a small ending can carry the job that English often shows with word order or helper words.',
		prompt: 'Start by asking what changed in the word shape.'
	},
	{
		id: 'case',
		title: 'What is a case?',
		body: 'A case is a noun-form job: acting, receiving, possessing, calling, source, place, means, and related functions.',
		prompt: 'Ask what relationship this noun form marks.'
	},
	{
		id: 'language-packaging',
		title: 'Why do the languages differ?',
		body: 'Sanskrit, Greek, and Latin share many inherited functions, but each language packages them differently in its own grammar tradition.',
		prompt: 'Look for the function first, then learn the local name.'
	},
	{
		id: 'foster-gateway',
		title: 'Why start with Foster?',
		body: 'Foster labels are gateway questions. They help a beginner read before memorizing every traditional label.',
		prompt: 'Use the gateway, then map it to Sanskrit, Greek, or Latin.'
	}
];

export const learnScriptGuides: Record<LanguageMode, LearnScriptGuide> = {
	san: {
		language: 'san',
		label: 'Sanskrit',
		script: 'Devanagari and transliteration',
		intro:
			'Sanskrit often appears in Devanagari or roman transliteration. Learn the vowel marks slowly; one sign can change the form and the meaning.',
		rows: [
			{ symbol: 'अ', roman: 'a', name: 'short a', note: 'default vowel' },
			{ symbol: 'आ', roman: 'ā', name: 'long a', note: 'length matters' },
			{ symbol: 'इ / ई', roman: 'i / ī', name: 'i vowels', note: 'short and long' },
			{ symbol: 'उ / ऊ', roman: 'u / ū', name: 'u vowels', note: 'short and long' },
			{ symbol: 'ऋ', roman: 'ṛ', name: 'vocalic r', note: 'common in roots' },
			{ symbol: 'क ख ग घ', roman: 'ka kha ga gha', name: 'velars', note: 'throat sounds' },
			{ symbol: 'त थ द ध', roman: 'ta tha da dha', name: 'dentals', note: 'tongue at teeth' },
			{ symbol: 'प फ ब भ', roman: 'pa pha ba bha', name: 'labials', note: 'lip sounds' },
			{
				symbol: 'ṃ / ḥ',
				roman: 'anusvāra / visarga',
				name: 'final signs',
				note: 'often affect sandhi'
			}
		]
	},
	grc: {
		language: 'grc',
		label: 'Greek',
		script: 'Greek alphabet',
		intro:
			'Greek uses its own alphabet. Accents and breathings can matter, but a first pass should focus on recognizing the letters and common endings.',
		rows: [
			{ symbol: 'α β γ δ', roman: 'a b g d', name: 'alpha to delta', note: 'opening letters' },
			{ symbol: 'ε ζ η θ', roman: 'e z ē th', name: 'epsilon to theta', note: 'eta is long ē' },
			{ symbol: 'ι κ λ μ', roman: 'i k l m', name: 'iota to mu', note: 'common stems/endings' },
			{ symbol: 'ν ξ ο π', roman: 'n x o p', name: 'nu to pi', note: 'watch final nu' },
			{ symbol: 'ρ σ/ς τ', roman: 'r s t', name: 'rho sigma tau', note: 'ς is final sigma' },
			{
				symbol: 'υ φ χ ψ ω',
				roman: 'u/ph ch ps ō',
				name: 'upsilon to omega',
				note: 'omega is long ō'
			},
			{ symbol: '᾿ / ῾', roman: 'smooth / rough', name: 'breathings', note: 'rough adds h' },
			{ symbol: 'λόγος', roman: 'logos', name: 'sample word', note: 'case endings attach here' }
		]
	},
	lat: {
		language: 'lat',
		label: 'Latin',
		script: 'Latin alphabet',
		intro:
			'Latin is visually familiar to English readers, but the endings carry much more grammatical work. Long vowels are often marked in learning materials.',
		rows: [
			{ symbol: 'a e i o u y', roman: 'a e i o u y', name: 'vowels', note: 'length can matter' },
			{
				symbol: 'ā ē ī ō ū',
				roman: 'long vowels',
				name: 'macrons',
				note: 'help distinguish forms'
			},
			{ symbol: 'c g', roman: 'c g', name: 'hard consonants', note: 'classical c is k-like' },
			{ symbol: 'i / j', roman: 'i / j', name: 'vowel or consonant', note: 'editions vary' },
			{ symbol: 'u / v', roman: 'u / v', name: 'vowel or consonant', note: 'editions vary' },
			{
				symbol: '-us -um -ī',
				roman: 'case endings',
				name: 'noun endings',
				note: 'small endings do large work'
			},
			{ symbol: '-ō -s -t', roman: 'verb endings', name: 'person endings', note: 'who is acting' },
			{
				symbol: 'lupus',
				roman: 'wolf',
				name: 'sample word',
				note: 'change the ending, change the job'
			}
		]
	}
};

export const learnConcepts: LearnConcept[] = [
	{
		id: 'case.nominative',
		kind: 'case',
		foster: 'Acting Function',
		traditional: 'nominative case',
		plainEnglish: 'The form points to the named thing as the actor, topic, or subject.',
		readerQuestion: 'Who or what is being named as the actor or subject?',
		tableCue: 'Look for the nominative row in a noun table.',
		gateways: {
			san: [{ language: 'san', label: 'Sanskrit', term: 'prathamā vibhakti', role: 'kartṛ' }],
			grc: [{ language: 'grc', label: 'Greek', term: 'onomastikē ptōsis', role: 'subject' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'nominativus', role: 'subjectum' }]
		},
		practice: [
			{ language: 'san', word: 'devaḥ', gloss: 'god', note: 'named actor' },
			{ language: 'grc', word: 'logos', gloss: 'word', note: 'named subject' },
			{ language: 'lat', word: 'lupus', gloss: 'wolf', note: 'named subject' }
		],
		sources: {
			san: [panini('551234', 'prātipadikārthaliṅgaparimāṇavacanamātre prathamā')],
			grc: [dionysius('1.1.31.6', 'ὀρθὴ ὀνομαστικὴ καὶ εὐθεῖα')],
			lat: [donatusMinor('76', 'case list includes nominatiuus')]
		}
	},
	{
		id: 'case.accusative',
		kind: 'case',
		foster: 'Receiving Function',
		traditional: 'accusative case',
		plainEnglish: 'The form points to what receives an action, aim, motion, or reach.',
		readerQuestion: 'What receives the action or functions as the object or goal?',
		tableCue: 'Look for the accusative row in a noun table.',
		gateways: {
			san: [{ language: 'san', label: 'Sanskrit', term: 'dvitīyā vibhakti', role: 'karman' }],
			grc: [{ language: 'grc', label: 'Greek', term: 'aitiatikē ptōsis', role: 'object' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'accusativus', role: 'obiectum' }]
		},
		practice: [
			{ language: 'san', word: 'gam', gloss: 'going / reaching', note: 'object-like form probe' },
			{ language: 'grc', word: 'logon', gloss: 'word', note: 'receiving form' },
			{ language: 'lat', word: 'lupum', gloss: 'wolf', note: 'receiving form' }
		],
		sources: {
			san: [panini('551190', 'karmaṇi dvitīyā')],
			grc: [dionysius('1.1.32.1', 'αἰτιατικὴ / κατ’ αἰτιατικήν')],
			lat: [donatusMinor('76', 'case list includes accusatiuus')]
		}
	},
	{
		id: 'case.genitive',
		kind: 'case',
		foster: 'Possessing Function',
		traditional: 'genitive case',
		plainEnglish:
			'The form points to belonging, relation, source family, or part-whole connection.',
		readerQuestion: 'Whose? Of what? What relation is being marked?',
		tableCue: 'Look for the genitive row in a noun table.',
		gateways: {
			san: [{ language: 'san', label: 'Sanskrit', term: 'ṣaṣṭhī vibhakti', role: 'sambandha' }],
			grc: [{ language: 'grc', label: 'Greek', term: 'genikē ptōsis', role: 'relation' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'genetivus', role: 'relation' }]
		},
		practice: [
			{ language: 'san', word: 'devasya', gloss: 'of the god', note: 'relation form' },
			{ language: 'grc', word: 'logou', gloss: 'of a word', note: 'relation form' },
			{ language: 'lat', word: 'lupī', gloss: 'of the wolf', note: 'relation form' }
		],
		sources: {
			san: [panini('551238', 'ṣaṣṭhī śeṣe')],
			grc: [dionysius('1.1.31.7', 'γενικὴ κτητική')],
			lat: [donatusMinor('76', 'case list includes genetiuus')]
		}
	},
	{
		id: 'case.vocative',
		kind: 'case',
		foster: 'Calling Function',
		traditional: 'vocative case',
		plainEnglish: 'The form points to direct address: the person or thing being called.',
		readerQuestion: 'Who is being addressed?',
		tableCue: 'Look for the vocative row in a noun table.',
		gateways: {
			san: [
				{ language: 'san', label: 'Sanskrit', term: 'sambodhana / sambuddhi', role: 'address' }
			],
			grc: [{ language: 'grc', label: 'Greek', term: 'klētikē ptōsis', role: 'address' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'vocativus', role: 'address' }]
		},
		practice: [
			{ language: 'san', word: 'deva', gloss: 'O god', note: 'calling form' },
			{ language: 'grc', word: 'loge', gloss: 'O word', note: 'calling form' },
			{ language: 'lat', word: 'lupe', gloss: 'O wolf', note: 'calling form' }
		],
		sources: {
			san: [panini('551237', 'ekavacanaṃ sambuddhiḥ')],
			grc: [dionysius('1.1.32.1', 'κλητικὴ')],
			lat: [donatusMinor('76', 'case list includes uocatiuus'), donatusMajor('68', 'uocatiuus')]
		}
	},
	{
		id: 'verb.person-number',
		kind: 'verb',
		foster: 'Actor Count',
		traditional: 'person and number',
		plainEnglish:
			'The ending tells who is involved in the action and whether one or many are meant.',
		readerQuestion: 'Who is acting, and how many?',
		tableCue: 'Look across the person and number cells in a verb table.',
		gateways: {
			san: [{ language: 'san', label: 'Sanskrit', term: 'puruṣa / vacana', role: 'tiṅanta' }],
			grc: [{ language: 'grc', label: 'Greek', term: 'prosōpon / arithmos', role: 'verb ending' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'persona / numerus', role: 'verb ending' }]
		},
		practice: [
			{ language: 'san', word: 'gacchati', gloss: 'goes', note: 'single actor' },
			{ language: 'grc', word: 'lyei', gloss: 'loosens', note: 'single actor' },
			{ language: 'lat', word: 'amat', gloss: 'loves', note: 'single actor' }
		],
		sources: {
			san: [
				panini('550989', 'bahuṣu bahuvacanam'),
				panini('550990', 'dvyekayor dvivacanaikavacane')
			],
			grc: [
				dionysius('1.1.51.4', 'person terminology'),
				dionysius('1.1.30.5', 'number terminology')
			],
			lat: [donatusMajor('112', 'person terminology'), donatusMinor('7', 'number terminology')]
		}
	},
	{
		id: 'process.declension',
		kind: 'process',
		foster: 'Form Changes For Noun Jobs',
		traditional: 'declension',
		plainEnglish: 'Noun forms shift so a reader can see job, count, and agreement.',
		readerQuestion: 'What job is this noun-form doing in the sentence?',
		tableCue: 'Use the table to compare case, number, and gender shapes.',
		gateways: {
			san: [{ language: 'san', label: 'Sanskrit', term: 'śabdarūpa / vibhakti', role: 'subanta' }],
			grc: [{ language: 'grc', label: 'Greek', term: 'klisis', role: 'noun forms' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'declinatio', role: 'noun forms' }]
		},
		practice: [
			{ language: 'san', word: 'deva', gloss: 'god', note: 'noun table' },
			{ language: 'grc', word: 'logos', gloss: 'word', note: 'noun table' },
			{ language: 'lat', word: 'lupus', gloss: 'wolf', note: 'noun table' }
		],
		sources: {
			san: [panini(undefined, 'morphology and vibhakti source tradition')],
			grc: [
				{
					language: 'grc',
					label: 'Theodosius, Canones isagogici de flexione nominum',
					workId: 'langnet:reader:tlg:tlg2020.001',
					canonicalId:
						'urn:ctsv2:grc:canones-isagogici-de-flexione-nominum-theodosiou-grammatikou-alexandreos',
					note: 'introductory noun inflection source tradition'
				}
			],
			lat: [donatusMinor(undefined, 'Latin noun-form source tradition')]
		}
	},
	{
		id: 'process.participle',
		kind: 'process',
		foster: 'Action As Noun Form',
		traditional: 'participle',
		plainEnglish:
			'The form carries an action like a verb, but it can take noun-style shape such as case, gender, and number.',
		readerQuestion: 'What action is this form carrying, and what noun job is it doing?',
		tableCue: 'Check both sides: verb time or voice, then noun case, number, and gender.',
		gateways: {
			san: [
				{ language: 'san', label: 'Sanskrit', term: 'kṛdanta / kṛt', role: 'verbal noun-form' }
			],
			grc: [{ language: 'grc', label: 'Greek', term: 'metochē', role: 'participle' }],
			lat: [{ language: 'lat', label: 'Latin', term: 'participium', role: 'participle' }]
		},
		practice: [
			{ language: 'san', word: 'gacchan', gloss: 'going', note: 'action carried as form' },
			{ language: 'grc', word: 'lyōn', gloss: 'loosening', note: 'participle probe' },
			{ language: 'lat', word: 'legens', gloss: 'reading', note: 'present participle' }
		],
		sources: {
			san: [panini('551927', 'kartari kṛt')],
			grc: [dionysius('1.1.23.1', 'μετοχή among the parts of speech')],
			lat: [
				donatusMinor('73', 'participium takes part of noun and verb'),
				donatusMinor('74', 'six participle attributes')
			]
		}
	}
];

export const learnSteps: LearnStep[] = [
	{
		title: 'Notice the form',
		body: 'Start with the letters on the page, not with a memorized table name.'
	},
	{
		title: 'Ask the function question',
		body: 'Use the Foster gateway to ask what job the form is doing in this sentence.'
	},
	{
		title: 'Name the native grammar',
		body: 'Map the function into Sanskrit, Greek, or Latin terms once the reading job is clear.'
	},
	{
		title: 'Check the source',
		body: 'Open the dictionary or table when the form is ambiguous or the source disagrees.'
	}
];

export function learnConceptById(id: string): LearnConcept {
	return learnConcepts.find((concept) => concept.id === id) ?? learnConcepts[0]!;
}

export function learnConceptsForLanguage(language: LanguageMode) {
	return learnConcepts.filter((concept) => concept.gateways[language]?.length);
}

export function practiceHref(item: LearnPracticeWord) {
	const params = new URLSearchParams({
		lang: item.language,
		q: item.word,
		backend: 'cli',
		translation: 'auto',
		dictionary: 'all',
		load: 'yes'
	});
	return `/q?${params.toString()}`;
}

export function sourceReferenceHref(reference: LearnSourceReference) {
	const params = new URLSearchParams({
		lang: reference.language,
		work: reference.workId
	});
	if (reference.segment) params.set('segment', reference.segment);
	return `/reader?${params.toString()}`;
}

function panini(segment: string | undefined, note: string): LearnSourceReference {
	return {
		language: 'san',
		label: 'Pāṇini, Aṣṭādhyāyī',
		workId: 'langnet:reader:sanskrit_dcs:dcs_413',
		canonicalId: 'urn:ctsv2:san:astadhyayi-vrddhir-adaic',
		segment,
		note
	};
}

function dionysius(segment: string | undefined, note: string): LearnSourceReference {
	return {
		language: 'grc',
		label: 'Dionysius Thrax, Ars grammatica',
		workId: 'langnet:reader:tlg:tlg0063.001',
		canonicalId: 'urn:ctsv2:grc:ars-grammatica-peri-grammatike-s',
		segment,
		note
	};
}

function donatusMinor(segment: string | undefined, note: string): LearnSourceReference {
	return {
		language: 'lat',
		label: 'Donatus, Ars minor',
		workId: 'langnet:reader:digiliblt:dlt000157',
		canonicalId: 'urn:ctsv2:lat:ars-minor-de-partibus-orationis',
		segment,
		note
	};
}

function donatusMajor(segment: string | undefined, note: string): LearnSourceReference {
	return {
		language: 'lat',
		label: 'Donatus, Ars maior',
		workId: 'langnet:reader:digiliblt:dlt000156',
		canonicalId: 'urn:ctsv2:lat:ars-maior-de-uoce',
		segment,
		note
	};
}
