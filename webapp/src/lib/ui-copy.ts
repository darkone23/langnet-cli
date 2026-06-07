import i18next from 'i18next';
import type { LanguageMode, TranslationMode } from './search-data';

const resources = {
	en: {
		translation: {
			app: {
				title: 'Project Orion Lexicon',
				description: 'A source-aware reading desk for Sanskrit, Greek, and Latin.',
				name: 'Project Orion',
				motto: 'Every day is a good day for learning.'
			},
			publicSite: {
				nav: {
					learn: 'Learn',
					evidence: 'Evidence',
					latin: 'Latin',
					greek: 'Greek',
					sanskrit: 'Sanskrit',
					openLookup: 'Open lookup'
				},
				home: {
					metaDescription:
						'A source-aware reading desk for Latin, Greek, and Sanskrit: word forms, meanings, morphology, and the evidence behind them.',
					eyebrow: 'Project Orion',
					title: 'Move from a classical word to accountable evidence.',
					intro:
						'Project Orion is the public reading desk for LangNet: a local evidence engine that connects Latin, Greek, and Sanskrit forms to dictionary witnesses, morphology, source claims, and learner-facing explanations.',
					primaryCta: 'Study a word',
					secondaryCta: 'Learn form and function',
					aboutCta: 'About Orion',
					principles: [
						{
							title: 'Evidence before fluency',
							body:
								'Every useful claim should point back to a dictionary, analyzer, citation, or explicit derivation.',
							tone: 'primary'
						},
						{
							title: 'Clarity before completeness',
							body:
								'Beginners get a reading path first; teachers, researchers, and builders can inspect provenance below it.',
							tone: 'secondary'
						}
					],
					languages: [
						{
							href: '/languages/latin',
							label: 'Latin',
							body:
								'Connect inflected forms to headwords, morphology, and source-backed glosses.',
							tone: 'warning',
							icon: 'latin'
						},
						{
							href: '/languages/greek',
							label: 'Greek',
							body: 'Keep script, form, lexeme, and dictionary witness visible together.',
							tone: 'info',
							icon: 'greek'
						},
						{
							href: '/languages/sanskrit',
							label: 'Sanskrit',
							body:
								'Study forms, compounds, and grammar gateways without hiding source caveats.',
							tone: 'success',
							icon: 'sanskrit'
						}
					]
				},
				about: {
					metaDescription:
						"Project Orion is LangNet's source-aware reading desk for Latin, Greek, and Sanskrit: useful first, auditable second.",
					eyebrow: 'About the project',
					title: 'Useful first. Auditable second. Never an oracle.',
					intro:
						'Project Orion is the web reading desk for LangNet. It helps a reader move from an inflected word in a classical text to an accountable explanation of what the word can mean, what form it may be, and which sources support that answer.',
					productPromiseTitle: 'The product promise',
					productPromise:
						'For a Latin, Greek, or Sanskrit word, Orion should help answer five questions: what headword it may belong to, what grammatical form it may be, what meanings are source-supported, where each claim came from, and where the sources agree, disagree, or remain incomplete.',
					principles: [
						{
							title: 'Evidence first',
							body:
								'Displayed lexical, morphological, and semantic facts should trace back to a tool response, dictionary entry, citation, cache row, or explicit derivation.'
						},
						{
							title: 'Tradition with function',
							body:
								'Orion keeps terms such as genitive, dative, or instrumental visible while adding functional reading questions such as possession, to/for, or by/with.'
						},
						{
							title: 'Determinism before inference',
							body:
								'Stable rules, repeatable IDs, fixture-backed tests, and exact reductions come before embeddings, broad inference, or fluent-looking generated interpretation.'
						}
					],
					audiencesTitle: 'Who it serves',
					audiences: [
						'Students reading classical texts who need help connecting forms to meanings.',
						'Teachers preparing concise lexical and grammatical explanations.',
						'Researchers checking source evidence across tools quickly.',
						'Developers building structured classical-language datasets.'
					],
					startTitle: 'Start with a word',
					startBody:
						'The reliable surface is word-level evidence: form, meaning, source support, and caveats. Passage interpretation and generated prose should not outrun that evidence.',
					provenanceTitle: 'What we take as input',
					provenanceIntro:
						'LangNet is a databuild system over many source traditions. We normalize them into local reader, lexicon, morphology, and pedagogy artifacts while keeping provenance visible instead of pretending everything came from one canonical format.',
					sourceGroups: [
						{
							title: 'Reader corpora',
							body:
								'Texts used to build the reader catalog and per-book segment artifacts.',
							items: [
								'PHI Latin legacy dumps with IDT metadata when available',
								'TLG Greek legacy dumps with author and canon metadata',
								'Perseus TEI XML',
								'First1KGreek TEI XML',
								'digilibLT TEI XML',
								'Sanskrit JSON, plain-text, grouped text, and DCS CONLLU sources',
								'OpenGreekAndLatin Latin, CSEL, Patrologia Latina, and Church Fathers corpora'
							]
						},
						{
							title: 'Lexica and morphology',
							body:
								'Dictionaries, analyzers, and lexical indices used as witnesses for lookup.',
							items: [
								'Whitaker’s Words',
								'Gaffiot Latin',
								'Lewis 1890 Latin',
								'Georges 1913 German-Latin',
								'Bailly Greek',
								'Diogenes Greek and Latin indices',
								'CDSL Sanskrit dictionaries',
								'DICO French-Sanskrit',
								'Strong’s Greek and related MorphGNT data'
							]
						},
						{
							title: 'External engines and references',
							body:
								'Programs, services, and extracted reference works that LangNet leans on during lookup, parsing, or pedagogy builds.',
							items: [
								'Diogenes for Greek and Latin lexical/index access',
								'Sanskrit Heritage tooling and data for Sanskrit analysis paths',
								'Whitaker’s Words as both source lexicon and analyzer dependency',
								'CLTK and local normalization/transliteration utilities where appropriate',
								'Foster/Ossa grammar reference material extracted from parsed local documents',
								'Firecrawl research artifacts used to support reviewed reader metadata enrichment'
							]
						},
						{
							title: 'Curated LangNet layers',
							body:
								'Small reviewed files that correct, enrich, or organize imported source data.',
							items: [
								'Reader aliases and display metadata overlays',
								'Attribution claims and contained-work boundaries',
								'Reader work maps, division metadata, and citation maps',
								'Reader search concepts and source-backed enrichment batches',
								'Reviewed word-of-day pools and learner-facing grammar bridges'
							]
						},
						{
							title: 'Generated and derived artifacts',
							body:
								'Useful rebuildable products, not source authority by themselves.',
							items: [
								'Generated reader classifications and author classifications',
								'Reader search Lance index',
								'Translation cache rows',
								'Word indexes, MOTD pool databases, and local runtime caches',
								'Future LangNet canonical catalog exports and EPUB/static presentation bundles'
							]
						}
					],
					provenanceNoteTitle: 'Canonical for LangNet does not mean source-original',
					provenanceNote:
						'CTS and TEI remain important source/provenance formats, but LangNet’s internal contract is source-aware and normalized. Reader-facing addresses prefer CTSv2; raw CTS URNs, file paths, hashes, and import statuses remain provenance.'
				},
				evidence: {
					metaDescription:
						"How Project Orion treats source evidence, dictionary witnesses, generated prose, and learner-facing explanations.",
					eyebrow: 'Evidence model',
					title: 'Orion explains what it can support, and where support stops.',
					intro:
						'The reading desk is designed around accountable word-level evidence. A fluent answer is useful only when a reader can inspect the dictionary witness, analyzer output, citation, cache row, or explicit derivation behind it.',
					sections: [
						{
							title: 'Dictionary witnesses',
							body:
								'Dictionaries and lexical tools are treated as witnesses. They may agree, differ, omit details, or preserve different traditions. Orion should keep that disagreement visible instead of flattening it into one answer.'
						},
						{
							title: 'Morphology and form',
							body:
								'Form analysis starts with the word on the page. The system should show possible headwords, grammatical labels, and learner-facing functional questions before asking the reader to choose a passage interpretation.'
						},
						{
							title: 'Generated prose',
							body:
								'Generated explanations may help summarize or translate source material, but generated text is not itself source evidence. It should remain marked as a derived reading aid.'
						},
						{
							title: 'Caveats',
							body:
								'Classical-language evidence is often incomplete. A useful interface should say when evidence is missing, ambiguous, cached, translated, or dependent on a particular source tradition.'
						}
					],
					ctaTitle: 'Use evidence in the lookup desk',
					ctaBody:
						'Start with one word, then inspect source groups, morphology, provenance chips, and cache notes before trusting a gloss.'
				},
				learn: {
					metaDescription:
						'A function-first learning path for Sanskrit, Greek, and Latin morphology.',
					headerMotto: 'Learn morphology by function.',
					aboutLabel: 'About',
					lookupLabel: 'Lookup',
					readerLabel: 'Reader',
					learnLabel: 'Learn',
					sidebarEyebrow: 'Foster gateway',
					sidebarTitle: 'Learn Forms',
					sidebarIntro:
						'Start with the shape of a word, ask what job it is doing, then learn the grammar name for the language in front of you.',
					conceptsAria: 'Learning concepts',
					foundationEyebrow: 'Start here',
					foundationTitle: 'How Ancient Forms Work',
					foundationIntro:
						'The first skill is not memorizing a table. It is noticing that the word ending is carrying a sentence job.',
					readerQuestion: 'Reader question',
					nativeGrammar: 'Native Grammar',
					tableCue: 'Table Cue',
					sourceTradition: 'Source Tradition',
					sourceTraditionIntro: 'Native grammar references for the terms shown above.',
					trySourceWord: 'Try A Source Word',
					trySourceWordIntro:
						'Open a live lookup, read the first form card, then come back to the question.'
				},
				languages: {
					lat: {
						label: 'Latin',
						metaDescription:
							'Latin in Project Orion: source-backed forms, dictionary witnesses, morphology, and learner-facing grammar.',
						lookupLabel: 'Open Latin lookup',
						eyebrow: 'Latin',
						title: 'Latin reading starts with the form on the page.',
						intro:
							'Orion connects Latin forms to possible headwords, morphology, compact learner glosses, and dictionary witnesses. The goal is not to replace judgement, but to make the evidence easier to inspect.',
						wordOfDayTitle: 'Latin word of the day',
						wordOfDayIntro:
							'One date-selected Latin lookup, chosen to invite source comparison rather than passive memorization.',
						features: [
							{
								icon: 'search',
								title: 'From form to lexeme',
								body:
									'Ask what headword this form may belong to before flattening the answer.'
							},
							{
								icon: 'book',
								title: 'Witnesses, not oracles',
								body:
									'Dictionary rows are displayed as source witnesses that can agree, differ, or remain incomplete.'
							},
							{
								icon: 'learn',
								title: 'Function beside terminology',
								body:
									'Keep Latin labels visible while asking what the form is doing in the expression.'
							}
						]
					},
					grc: {
						label: 'Greek',
						metaDescription:
							'Greek in Project Orion: source-backed forms, dictionary evidence, morphology, and learner-facing grammar.',
						lookupLabel: 'Open Greek lookup',
						eyebrow: 'Greek',
						title: 'Greek lookup should keep script, form, and evidence together.',
						intro:
							'Orion helps Greek readers move from surface form to possible lexeme and meaning without hiding morphology, source differences, or the transliteration details needed by backend tools.',
						wordOfDayTitle: 'Greek word of the day',
						wordOfDayIntro:
							'One date-selected Greek lookup that keeps script, transliteration, gloss, and evidence boundaries visible.',
						features: [
							{
								icon: 'search',
								title: 'Form before fluency',
								body:
									'A useful answer begins with what form may be in front of the reader.'
							},
							{
								icon: 'book',
								title: 'Citable evidence',
								body:
									'Lexical and grammatical claims should remain tied to inspectable source support.'
							},
							{
								icon: 'learn',
								title: 'Traditional terms, readable jobs',
								body:
									"Greek labels remain visible while learner copy explains the form's likely function."
							}
						]
					},
					san: {
						label: 'Sanskrit',
						metaDescription:
							'Sanskrit in Project Orion: source-backed dictionary evidence, forms, compounds, scripts, and learner-facing grammar.',
						lookupLabel: 'Open Sanskrit lookup',
						eyebrow: 'Sanskrit',
						title: 'Sanskrit evidence needs forms, compounds, scripts, and caveats.',
						intro:
							'Orion supports Sanskrit lookup with attention to dictionary witnesses, morphology, compound components, Devanagari and transliteration, and learner-friendly grammar gateways.',
						wordOfDayTitle: 'Sanskrit word of the day',
						wordOfDayIntro:
							'One date-selected Sanskrit lookup that treats script, transliteration, range, and caveat as part of the same reading object.',
						features: [
							{
								icon: 'search',
								title: 'Source-backed lookup',
								body:
									'Inspect Sanskrit words through dictionary and analyzer evidence, not unsupported summary.'
							},
							{
								icon: 'book',
								title: 'Compounds and components',
								body:
									'Compound members are kept as secondary evidence when the backend can support them.'
							},
							{
								icon: 'learn',
								title: 'Native labels, learner functions',
								body:
									'Sanskrit terms stay visible while gateway copy explains what the form is doing.'
							}
						]
					}
				}
			},
			boot: {
				aria: 'Loading the reading desk',
				title: 'Loading the reading desk',
				detail: 'Preparing type, saved state, source controls, and the reader layer.'
			},
			nav: {
				homeAria: 'Clear the desk and return home',
				languageStat: 'Language',
				statusStat: 'Status'
			},
			theme: {
				readerAria: 'Use reader theme',
				nightAria: 'Use night theme',
				reader: 'Reader',
				night: 'Night'
			},
			hero: {
				badge: "Reader's lectern",
				titleSan: 'Search Sanskrit sources',
				titleGrc: 'Search Greek sources',
				titleLat: 'Search Latin sources',
				intro:
					'Look up one word. Orion keeps each source answerable by dictionary, lexeme, and reader text.'
			},
			search: {
				loadingSteps: ['Find form', 'Test sources', 'Order entries'],
				loadingTitle: 'Consulting the sources',
				coldSources: 'Cold sources and fresh English may take time.',
				clear: 'Clear',
				buttonLoading: 'Looking up',
				buttonReady: 'Look up',
				inputAria: 'Look up one word',
				placeholder: 'Enter one {{language}} word',
				opening: 'Looking up {{query}} in {{language}} with dictionary={{dictionary}}.'
			},
			status: {
				searching: 'Looking up',
				awaitingReader: 'Awaiting English',
				attention: 'Attention',
				reading: 'Reading',
				ready: 'Ready',
				askingSources_one: 'Asking {{count}} selected source.',
				askingSources_other: 'Asking {{count}} selected sources.',
				awaitingReaderDetail:
					'Cached entries are open; untranslated source entries are awaiting English.',
				showingSections:
					'Showing {{visible}} {{sectionLabel}} of {{total}} {{totalLabel}} for {{query}}.',
				readyForWord: 'The reading desk is ready.',
				chooseWord: 'Choose a language and enter one word.',
				cacheUnavailable: 'cache unavailable',
				cacheWarm: 'cache warm',
				newTranslations: '{{count}} new translations',
				missingTranslations: '{{count}} missing'
			},
			readerLayer: {
				label: 'Reader English',
				modeAria: 'Reader translation mode',
				loadingAria: 'Preparing reader English',
				unsearched: 'Reader English appears after lookup.',
				awaiting: 'Selected {{mode}}; cached text is open while other entries await English.',
				cacheSupplied: 'Selected {{mode}}; cached English is available.',
				served: 'Served with translation={{mode}}.'
			},
			readerText: {
				label: 'Reader text',
				pending: 'English pending',
				closePassage: 'Close this passage'
			},
			encounterBriefing: {
				title: 'Encounter',
				subtitle: 'Word study',
				statusDraft: 'Draft',
				statusGenerated: 'Generated',
				provenanceGenerated: 'Generated by {{model}}',
				loading: 'Building briefing...',
				generateTitle: 'Generate model briefing',
				generateReady: 'Generate',
				generateLoading: 'Generating',
				generatingNotice: 'Generating model briefing...',
				studyWord: 'Study word',
				empty: 'Click a word in the passage to prepare a lookup.'
			},
			orionObjects: {
				word: 'Word',
				work: 'Work',
				author: 'Author',
				chapter: 'Chapter',
				passage: 'Passage',
				dossier: 'Dossier',
				leaf: 'Leaf',
				marginalium: 'Marginalia',
				canonTable: 'Canon Table',
				oracle: 'Oracle',
				wheel: 'Wheel'
			},
			provenance: {
				curated: 'Curated',
				source: 'Source',
				generated: 'LLM draft',
				reviewed: 'Reviewed',
				needsEvidence: 'Needs evidence',
				needsReview: 'Needs review'
			},
			async: {
				loading: 'Loading',
				refreshing: 'Refreshing',
				researching: 'Researching',
				seconds: '{{seconds}}s'
			},
			readerStructure: {
				title: 'Structure',
				empty: 'No accepted structure map yet.',
				loading: 'Loading structure',
				open: 'Open',
				study: 'Study division',
				evidence: 'Evidence',
				current: 'Current division'
			},
			workDossier: {
				title: 'About this work',
				loading: 'Loading work dossier',
				empty: 'No work dossier is available yet.',
				structureSummary: 'Structure summary',
				metadataReady: 'Metadata ready',
				metadataPending: 'Metadata pending',
				currentDivision: 'Current division',
				headings: 'Headings',
				divisionBios: 'Division notes',
				opening: 'Opening structure'
			},
			apparatus: {
				structure: 'Structure',
				word: 'Word',
				oracle: 'Oracle',
				evidence: 'Evidence',
				close: 'Close apparatus'
			},
			translator: {
				alert: 'Cached entries are open. Some source entries are still awaiting English.',
				title: 'This source entry is awaiting English.',
				badge: 'Awaiting English',
				failed: 'Cached entries remain shown. English could not be prepared: {{message}}'
			},
			components: {
				title: 'Component entries',
				intro:
					'Compound members returned by the CLI, shown as dictionary entries when evidence is available.',
				empty: 'No source-backed component entry was returned.'
			},
			results: {
				title: 'Source entries',
				intro: 'Grouped by source and lexeme, so entries can be read, compared, and challenged.',
				all: 'All entries',
				noFilterMatch: 'No loaded entry is visible under the active filters.',
				returnedEnding: 'Returned text ends here.'
			},
			margin: {
				title: 'Learner folio',
				intro: 'Three starter words for an empty desk. Refresh asks the live CLI.',
				linkModeLoad: 'Links look up immediately.',
				linkModePrefill: 'Links only set the word.',
				prepareAria: 'Preparing the learner folio',
				noWord: 'The folio has no learner word this time.',
				noFreshWord: 'The folio could not find a fresh word this time.',
				refreshingPrevious: 'Showing the previous word while a fresh one is prepared.',
				loadTitle: 'Choose whether folio links immediately look up the word.',
				refreshTitle: 'Ask the live CLI for fresh learner words.',
				linkToggleRead: 'read',
				linkToggleInk: 'ink',
				refresh: 'fresh word',
				cardActionSanLoad: 'Look up this Sanskrit word',
				cardActionSanPrefill: 'Use this Sanskrit word',
				cardActionGrcLoad: 'Look up this Greek word',
				cardActionGrcPrefill: 'Use this Greek word',
				cardActionLatLoad: 'Look up this Latin word',
				cardActionLatPrefill: 'Use this Latin word',
				active: 'open now',
				repeat: 'recently shown',
				multipleAnchors: 'multiple anchors'
			},
			wordIndex: {
				title: 'Dictionary index',
				intro:
					'Native sections and nearby headwords. Select a word to look it up; mark one to keep it nearby.',
				loading: 'Loading nearby headwords.',
				empty: 'No indexed neighbors were found for this word.',
				earmarks: 'Earmarks',
				earmarkTitle: 'Keep this term in the index panel.',
				removeEarmarkTitle: 'Remove this term from the earmarks.',
				clearEarmarks: 'Clear',
				clearEarmarksTitle: 'Clear all saved earmarks.',
				sectionsTitle: 'Native index',
				sectionsLoading: 'Loading native index sections.',
				browseSection: 'Browse section',
				orderTitle: 'Nearby lexeme order',
				active: 'resolved term',
				before: 'before',
				after: 'after',
				anchor: 'index anchor',
				nearby: 'nearby',
				browse: 'browse'
			},
			sidebar: {
				sourceTitle: 'Source shelf',
				sourceIntro: 'Choose which dictionaries and tools may answer. No source speaks alone.',
				returnedTitle: 'Visible entries',
				generatorAllTitle: 'Use the generator with dictionary=all.',
				showLoaded: 'Show every loaded entry.',
				all: 'All'
			},
			colophon: {
				title: 'Colophon',
				translationAccount: 'Translation account',
				requestSeal: 'Request record'
			},
			pageMarks: {
				title: 'Route marks',
				clearTitle: 'Clear URL parameters, storage, and the current desk.',
				pageLink: 'Page link',
				endpoint: 'Lookup endpoint',
				contractPrefix: 'This route preserves the CLI contract: one language, one word, and',
				contractSuffix: 'or a concrete source tool.'
			},
			oracleTrace: {
				title: 'Encounter trace',
				provenance: 'Provenance chain',
				requested: 'Requested form',
				prefill: 'No form',
				none: 'None',
				cache: 'Cache policy',
				backend: 'Backend / translation',
				sources: 'Source tools',
				candidates: 'Normalized candidates',
				dictionaryBuckets: 'Dictionary buckets',
				bucketOne: 'bucket',
				bucketMany: 'buckets',
				wordIndexAnchors: 'Word-index anchors',
				anchor: 'anchor',
				anchors: 'anchors',
				cacheWrites: 'Cache writes',
				normalizationEnabled: 'normalization',
				normalizationDisabled: 'no normalization',
				translationWrites: 'translation cache write',
				warnings: 'Warnings',
				moreWarnings: '{{count}} more warning(s)',
				bucketSamples: 'Bucket samples'
			},
			errors: {
				enterOneWord: 'Enter one word to look up.',
				oneWordOnly: 'Lookup accepts one word at a time.',
				searchFailed: 'Lookup failed.',
				indexFailed: 'Dictionary index lookup failed.',
				recommendationsFailed: 'Word recommendations failed.',
				translationFailed: 'Translation enrichment failed.',
				liveFallback: 'Live CLI fallback: {{message}}',
				noGloss: 'No display gloss returned.',
				noComponentGloss: 'No component gloss returned.'
			},
			passage: {
				openSource: 'Open source passage',
				openFull: 'Open full passage',
				openNested: 'Open nested passages',
				closeNested: 'Close nested passages',
				openComponent: 'Open the full component entry',
				closeComponent: 'Close this component entry'
			}
		}
	}
} as const;

void i18next.init({
	lng: 'en',
	fallbackLng: 'en',
	resources,
	initAsync: false,
	interpolation: {
		escapeValue: false
	}
});

function text(key: string, options?: Record<string, unknown>) {
	return i18next.t(key, options);
}

function objectText<T>(key: string): T {
	return i18next.t(key, { returnObjects: true }) as T;
}

export const uiCopy = {
	app: {
		title: text('app.title'),
		description: text('app.description'),
		name: text('app.name'),
		motto: text('app.motto')
	},
	publicSite: {
		nav: objectText<{
			learn: string;
			evidence: string;
			latin: string;
			greek: string;
			sanskrit: string;
			openLookup: string;
		}>('publicSite.nav'),
		home: objectText<{
			metaDescription: string;
			eyebrow: string;
			title: string;
			intro: string;
			primaryCta: string;
			secondaryCta: string;
			aboutCta: string;
			principles: { title: string; body: string; tone: 'primary' | 'secondary' }[];
			languages: {
				href: string;
				label: string;
				body: string;
				tone: 'warning' | 'info' | 'success';
				icon: 'latin' | 'greek' | 'sanskrit';
			}[];
		}>('publicSite.home'),
		about: objectText<{
			metaDescription: string;
			eyebrow: string;
			title: string;
			intro: string;
			productPromiseTitle: string;
			productPromise: string;
			principles: { title: string; body: string }[];
			audiencesTitle: string;
			audiences: string[];
			provenanceTitle: string;
			provenanceIntro: string;
			sourceGroups: { title: string; body: string; items: string[] }[];
			provenanceNoteTitle: string;
			provenanceNote: string;
			startTitle: string;
			startBody: string;
		}>('publicSite.about'),
		evidence: objectText<{
			metaDescription: string;
			eyebrow: string;
			title: string;
			intro: string;
			sections: { title: string; body: string }[];
			ctaTitle: string;
			ctaBody: string;
		}>('publicSite.evidence'),
		learn: objectText<{
			metaDescription: string;
			headerMotto: string;
			aboutLabel: string;
			lookupLabel: string;
			readerLabel: string;
			learnLabel: string;
			sidebarEyebrow: string;
			sidebarTitle: string;
			sidebarIntro: string;
			conceptsAria: string;
			foundationEyebrow: string;
			foundationTitle: string;
			foundationIntro: string;
			readerQuestion: string;
			nativeGrammar: string;
			tableCue: string;
			sourceTradition: string;
			sourceTraditionIntro: string;
			trySourceWord: string;
			trySourceWordIntro: string;
		}>('publicSite.learn'),
		languages: objectText<{
			lat: {
				label: string;
				metaDescription: string;
				lookupLabel: string;
				eyebrow: string;
				title: string;
				intro: string;
				wordOfDayTitle: string;
				wordOfDayIntro: string;
				features: { icon: 'search' | 'book' | 'learn'; title: string; body: string }[];
			};
			grc: {
				label: string;
				metaDescription: string;
				lookupLabel: string;
				eyebrow: string;
				title: string;
				intro: string;
				wordOfDayTitle: string;
				wordOfDayIntro: string;
				features: { icon: 'search' | 'book' | 'learn'; title: string; body: string }[];
			};
			san: {
				label: string;
				metaDescription: string;
				lookupLabel: string;
				eyebrow: string;
				title: string;
				intro: string;
				wordOfDayTitle: string;
				wordOfDayIntro: string;
				features: { icon: 'search' | 'book' | 'learn'; title: string; body: string }[];
			};
		}>('publicSite.languages')
	},
	boot: {
		aria: text('boot.aria'),
		title: text('boot.title'),
		detail: text('boot.detail')
	},
	nav: {
		homeAria: text('nav.homeAria'),
		languageStat: text('nav.languageStat'),
		statusStat: text('nav.statusStat')
	},
	theme: {
		readerAria: text('theme.readerAria'),
		nightAria: text('theme.nightAria'),
		reader: text('theme.reader'),
		night: text('theme.night')
	},
	hero: {
		badge: text('hero.badge'),
		title: (language: 'san' | 'grc' | 'lat') =>
			text(
				language === 'san'
					? 'hero.titleSan'
					: language === 'grc'
						? 'hero.titleGrc'
						: 'hero.titleLat'
			),
		intro: text('hero.intro')
	},
	search: {
		loadingSteps: i18next.t('search.loadingSteps', { returnObjects: true }) as string[],
		loadingTitle: text('search.loadingTitle'),
		coldSources: text('search.coldSources'),
		clear: text('search.clear'),
		button: (loading: boolean) => text(loading ? 'search.buttonLoading' : 'search.buttonReady'),
		inputAria: text('search.inputAria'),
		placeholder: (language: string) => text('search.placeholder', { language }),
		opening: (query: string, language: string, dictionary: string) =>
			text('search.opening', { query, language, dictionary })
	},
	status: {
		searching: text('status.searching'),
		awaitingReader: text('status.awaitingReader'),
		attention: text('status.attention'),
		reading: text('status.reading'),
		ready: text('status.ready'),
		askingSources: (count: number) => text('status.askingSources', { count }),
		awaitingReaderDetail: text('status.awaitingReaderDetail'),
		showingSections: (visible: number, total: number, query: string) =>
			text('status.showingSections', {
				visible,
				total,
				query,
				sectionLabel: visible === 1 ? 'section' : 'sections',
				totalLabel: total === 1 ? 'section' : 'sections'
			}),
		readyForWord: text('status.readyForWord'),
		chooseWord: text('status.chooseWord'),
		cacheUnavailable: text('status.cacheUnavailable'),
		cacheWarm: text('status.cacheWarm'),
		newTranslations: (count: number) => text('status.newTranslations', { count }),
		missingTranslations: (count: number) => text('status.missingTranslations', { count })
	},
	readerLayer: {
		label: text('readerLayer.label'),
		modeAria: text('readerLayer.modeAria'),
		loadingAria: text('readerLayer.loadingAria'),
		unsearched: text('readerLayer.unsearched'),
		awaiting: (mode: TranslationMode) => text('readerLayer.awaiting', { mode }),
		cacheSupplied: (mode: TranslationMode) => text('readerLayer.cacheSupplied', { mode }),
		served: (mode: TranslationMode) => text('readerLayer.served', { mode })
	},
	readerText: {
		label: text('readerText.label'),
		pending: text('readerText.pending'),
		closePassage: text('readerText.closePassage')
	},
	encounterBriefing: {
		title: text('encounterBriefing.title'),
		subtitle: text('encounterBriefing.subtitle'),
		statusDraft: text('encounterBriefing.statusDraft'),
		statusGenerated: text('encounterBriefing.statusGenerated'),
		provenanceGenerated: (model: string) =>
			text('encounterBriefing.provenanceGenerated', { model }),
		loading: text('encounterBriefing.loading'),
		generateTitle: text('encounterBriefing.generateTitle'),
		generateReady: text('encounterBriefing.generateReady'),
		generateLoading: text('encounterBriefing.generateLoading'),
		generatingNotice: text('encounterBriefing.generatingNotice'),
		studyWord: text('encounterBriefing.studyWord'),
		empty: text('encounterBriefing.empty')
	},
	orionObjects: {
		word: text('orionObjects.word'),
		work: text('orionObjects.work'),
		author: text('orionObjects.author'),
		chapter: text('orionObjects.chapter'),
		passage: text('orionObjects.passage'),
		dossier: text('orionObjects.dossier'),
		leaf: text('orionObjects.leaf'),
		marginalium: text('orionObjects.marginalium'),
		canonTable: text('orionObjects.canonTable'),
		oracle: text('orionObjects.oracle'),
		wheel: text('orionObjects.wheel')
	},
	provenance: {
		curated: text('provenance.curated'),
		source: text('provenance.source'),
		generated: text('provenance.generated'),
		reviewed: text('provenance.reviewed'),
		needsEvidence: text('provenance.needsEvidence'),
		needsReview: text('provenance.needsReview')
	},
	async: {
		loading: text('async.loading'),
		refreshing: text('async.refreshing'),
		researching: text('async.researching'),
		seconds: (seconds: number) => text('async.seconds', { seconds })
	},
	readerStructure: {
		title: text('readerStructure.title'),
		empty: text('readerStructure.empty'),
		loading: text('readerStructure.loading'),
		open: text('readerStructure.open'),
		study: text('readerStructure.study'),
		evidence: text('readerStructure.evidence'),
		current: text('readerStructure.current')
	},
	workDossier: {
		title: text('workDossier.title'),
		loading: text('workDossier.loading'),
		empty: text('workDossier.empty'),
		structureSummary: text('workDossier.structureSummary'),
		metadataReady: text('workDossier.metadataReady'),
		metadataPending: text('workDossier.metadataPending'),
		currentDivision: text('workDossier.currentDivision'),
		headings: text('workDossier.headings'),
		divisionBios: text('workDossier.divisionBios'),
		opening: text('workDossier.opening')
	},
	apparatus: {
		structure: text('apparatus.structure'),
		word: text('apparatus.word'),
		oracle: text('apparatus.oracle'),
		evidence: text('apparatus.evidence'),
		close: text('apparatus.close')
	},
	translator: {
		alert: text('translator.alert'),
		title: text('translator.title'),
		badge: text('translator.badge'),
		failed: (message: string) => text('translator.failed', { message })
	},
	components: {
		title: text('components.title'),
		intro: text('components.intro'),
		empty: text('components.empty')
	},
	results: {
		title: text('results.title'),
		intro: text('results.intro'),
		all: text('results.all'),
		noFilterMatch: text('results.noFilterMatch'),
		returnedEnding: text('results.returnedEnding')
	},
	margin: {
		title: text('margin.title'),
		intro: text('margin.intro'),
		linkMode: (loads: boolean) => text(loads ? 'margin.linkModeLoad' : 'margin.linkModePrefill'),
		prepareAria: text('margin.prepareAria'),
		noWord: text('margin.noWord'),
		noFreshWord: text('margin.noFreshWord'),
		refreshingPrevious: text('margin.refreshingPrevious'),
		loadTitle: text('margin.loadTitle'),
		refreshTitle: text('margin.refreshTitle'),
		linkToggle: (loads: boolean) => text(loads ? 'margin.linkToggleRead' : 'margin.linkToggleInk'),
		refresh: text('margin.refresh'),
		cardAction: (language: LanguageMode, loads: boolean) =>
			text(
				language === 'san'
					? loads
						? 'margin.cardActionSanLoad'
						: 'margin.cardActionSanPrefill'
					: language === 'grc'
						? loads
							? 'margin.cardActionGrcLoad'
							: 'margin.cardActionGrcPrefill'
						: loads
							? 'margin.cardActionLatLoad'
							: 'margin.cardActionLatPrefill'
			),
		active: text('margin.active'),
		repeat: text('margin.repeat'),
		multipleAnchors: text('margin.multipleAnchors')
	},
	wordIndex: {
		title: text('wordIndex.title'),
		intro: text('wordIndex.intro'),
		loading: text('wordIndex.loading'),
		empty: text('wordIndex.empty'),
		earmarks: text('wordIndex.earmarks'),
		earmarkTitle: text('wordIndex.earmarkTitle'),
		removeEarmarkTitle: text('wordIndex.removeEarmarkTitle'),
		clearEarmarks: text('wordIndex.clearEarmarks'),
		clearEarmarksTitle: text('wordIndex.clearEarmarksTitle'),
		sectionsTitle: text('wordIndex.sectionsTitle'),
		sectionsLoading: text('wordIndex.sectionsLoading'),
		browseSection: text('wordIndex.browseSection'),
		orderTitle: text('wordIndex.orderTitle'),
		active: text('wordIndex.active'),
		browse: text('wordIndex.browse'),
		position: (position: 'before' | 'anchor' | 'after' | 'nearby' | 'browse') =>
			text(`wordIndex.${position}`)
	},
	sidebar: {
		sourceTitle: text('sidebar.sourceTitle'),
		sourceIntro: text('sidebar.sourceIntro'),
		returnedTitle: text('sidebar.returnedTitle'),
		generatorAllTitle: text('sidebar.generatorAllTitle'),
		showLoaded: text('sidebar.showLoaded'),
		all: text('sidebar.all')
	},
	colophon: {
		title: text('colophon.title'),
		translationAccount: text('colophon.translationAccount'),
		requestSeal: text('colophon.requestSeal')
	},
	pageMarks: {
		title: text('pageMarks.title'),
		clearTitle: text('pageMarks.clearTitle'),
		pageLink: text('pageMarks.pageLink'),
		endpoint: text('pageMarks.endpoint'),
		contractPrefix: text('pageMarks.contractPrefix'),
		contractSuffix: text('pageMarks.contractSuffix')
	},
	oracleTrace: {
		title: text('oracleTrace.title'),
		provenance: text('oracleTrace.provenance'),
		requested: text('oracleTrace.requested'),
		prefill: text('oracleTrace.prefill'),
		none: text('oracleTrace.none'),
		cache: text('oracleTrace.cache'),
		backend: text('oracleTrace.backend'),
		sources: text('oracleTrace.sources'),
		candidates: text('oracleTrace.candidates'),
		dictionaryBuckets: text('oracleTrace.dictionaryBuckets'),
		bucketOne: text('oracleTrace.bucketOne'),
		bucketMany: text('oracleTrace.bucketMany'),
		wordIndexAnchors: text('oracleTrace.wordIndexAnchors'),
		anchor: text('oracleTrace.anchor'),
		anchors: text('oracleTrace.anchors'),
		cacheWrites: text('oracleTrace.cacheWrites'),
		normalization: (enabled: boolean) =>
			text(enabled ? 'oracleTrace.normalizationEnabled' : 'oracleTrace.normalizationDisabled'),
		translationWrites: text('oracleTrace.translationWrites'),
		warnings: text('oracleTrace.warnings'),
		moreWarnings: (count: number) => text('oracleTrace.moreWarnings', { count }),
		bucketSamples: text('oracleTrace.bucketSamples')
	},
	errors: {
		enterOneWord: text('errors.enterOneWord'),
		oneWordOnly: text('errors.oneWordOnly'),
		searchFailed: text('errors.searchFailed'),
		indexFailed: text('errors.indexFailed'),
		recommendationsFailed: text('errors.recommendationsFailed'),
		translationFailed: text('errors.translationFailed'),
		liveFallback: (message: string) => text('errors.liveFallback', { message }),
		noGloss: text('errors.noGloss'),
		noComponentGloss: text('errors.noComponentGloss')
	},
	passage: {
		openSource: text('passage.openSource'),
		openFull: text('passage.openFull'),
		openNested: text('passage.openNested'),
		closeNested: text('passage.closeNested'),
		openComponent: text('passage.openComponent'),
		closeComponent: text('passage.closeComponent')
	}
} as const;
