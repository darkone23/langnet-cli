import assert from 'node:assert/strict';
import { componentGlossFromCli } from './component-gloss';

assert.equal(
	componentGlossFromCli(
		'aṅga n. limb, part of the body',
		'aṅga n. limb; part of the body; the entire body; the person; part, portion, subdivision.'
	),
	'aṅga n. limb; part of the body; the entire body; the person; part, portion, subdivision.'
);

assert.equal(componentGlossFromCli('aṣṭan m. eight', ''), 'aṣṭan m. eight');
assert.equal(componentGlossFromCli('', 'full upstream evidence'), 'full upstream evidence');
