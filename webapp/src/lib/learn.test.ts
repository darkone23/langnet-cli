import assert from 'node:assert/strict';
import {
	learnConceptById,
	learnConcepts,
	learnConceptsForLanguage,
	learnScriptGuides,
	learnStartCards,
	practiceHref,
	sourceReferenceHref
} from './learn';
import type { LanguageMode } from './search-data';

const languages: LanguageMode[] = ['san', 'grc', 'lat'];

assert.ok(learnConcepts.length >= 7);
assert.ok(learnStartCards.length >= 4);
assert.equal(learnStartCards[0]?.title, 'What is a form?');

for (const concept of learnConcepts) {
	assert.ok(concept.foster, `${concept.id} needs a Foster gateway`);
	assert.ok(concept.readerQuestion, `${concept.id} needs a learner question`);
	assert.ok(concept.tableCue, `${concept.id} needs a table cue`);

	for (const language of languages) {
		assert.ok(concept.gateways[language]?.length, `${concept.id} needs ${language} gateways`);
		assert.ok(concept.sources[language]?.length, `${concept.id} needs ${language} source refs`);
	}
}

for (const language of languages) {
	const guide = learnScriptGuides[language];
	assert.equal(guide.language, language);
	assert.ok(guide.rows.length >= 8, `${language} needs an alphabet/script primer`);
	assert.ok(guide.rows.every((row) => row.symbol && row.roman && row.note));
}

for (const language of languages) {
	assert.equal(
		learnConceptsForLanguage(language).length,
		learnConcepts.length,
		`${language} should be able to use the full learning path`
	);
}

const receiving = learnConceptById('case.accusative');
assert.equal(receiving.foster, 'Receiving Function');
assert.equal(receiving.gateways.san[0]?.term, 'dvitīyā vibhakti');
assert.equal(receiving.sources.san[0]?.segment, '551190');
assert.equal(receiving.sources.grc[0]?.segment, '1.1.32.1');

const acting = learnConceptById('case.nominative');
assert.equal(acting.sources.grc[0]?.segment, '1.1.31.6');

const participle = learnConceptById('process.participle');
assert.equal(participle.foster, 'Action As Noun Form');
assert.equal(participle.gateways.lat[0]?.term, 'participium');
assert.equal(participle.gateways.grc[0]?.term, 'metochē');
assert.equal(participle.gateways.san[0]?.term, 'kṛdanta / kṛt');
assert.equal(participle.sources.san[0]?.segment, '551927');
assert.equal(participle.sources.grc[0]?.segment, '1.1.23.1');
assert.equal(participle.sources.lat[0]?.segment, '73');

assert.equal(learnConceptById('missing').id, learnConcepts[0]?.id);

const href = practiceHref({ language: 'san', word: 'gam', gloss: 'go', note: 'probe' });
assert.equal(href, '/?lang=san&q=gam&backend=cli&translation=auto&dictionary=all&load=yes');
assert.equal(
	practiceHref({ language: 'grc', word: 'logon', gloss: 'word', note: 'probe' }),
	'/?lang=grc&q=logon&backend=cli&translation=auto&dictionary=all&load=yes'
);
assert.equal(
	practiceHref({ language: 'lat', word: 'lupum', gloss: 'wolf', note: 'probe' }),
	'/?lang=lat&q=lupum&backend=cli&translation=auto&dictionary=all&load=yes'
);

assert.equal(
	sourceReferenceHref(receiving.sources.san[0]!),
	'/reader?lang=san&work=langnet%3Areader%3Asanskrit_dcs%3Adcs_413&segment=551190'
);

console.log('learn workflow data ok');
