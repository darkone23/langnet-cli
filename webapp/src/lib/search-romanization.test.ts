import assert from 'node:assert/strict';
import { romanizeSearchTerm } from './search-romanization';

assert.deepEqual(romanizeSearchTerm('san', 'येनाक्षरसमाम्नायमधिगम्य'), {
	label: 'IAST',
	value: 'yenākṣarasamāmnāyamadhigamya'
});

assert.deepEqual(romanizeSearchTerm('san', 'दत्त'), {
	label: 'IAST',
	value: 'datta'
});

assert.deepEqual(romanizeSearchTerm('san', 'कर्म'), {
	label: 'IAST',
	value: 'karma'
});

assert.deepEqual(romanizeSearchTerm('grc', 'λόγος'), {
	label: 'roman',
	value: 'logos'
});

assert.deepEqual(romanizeSearchTerm('grc', 'λόγου'), {
	label: 'roman',
	value: 'logou'
});

assert.deepEqual(romanizeSearchTerm('grc', 'ψυχή'), {
	label: 'roman',
	value: 'psychē'
});

assert.deepEqual(romanizeSearchTerm('grc', 'ὁ'), {
	label: 'roman',
	value: 'ho'
});

assert.equal(romanizeSearchTerm('lat', 'ratio'), null);
assert.equal(romanizeSearchTerm('san', 'datta'), null);
