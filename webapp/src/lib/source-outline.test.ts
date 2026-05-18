import assert from 'node:assert/strict';
import {
	extractSourceOutlineSegments,
	isOutlinedDictionaryHeading,
	isOutlinedDictionaryTool,
	sourceOutlineDepth
} from './source-outline';

assert.equal(isOutlinedDictionaryTool('diogenes'), true);
assert.equal(isOutlinedDictionaryTool('bailly'), true);
assert.equal(isOutlinedDictionaryTool('gaffiot'), false);

assert.equal(sourceOutlineDepth('diogenes:00'), 0);
assert.equal(sourceOutlineDepth('diogenes:00:02:01'), 2);
assert.equal(sourceOutlineDepth('bailly:00:02:01'), 2);
assert.equal(sourceOutlineDepth('bailly:bailly-p1450-c1-0024'), 0);
assert.equal(sourceOutlineDepth('bailly:bailly-p1450-c1-0024:01:02'), 2);

assert.equal(isOutlinedDictionaryHeading('bailly', 'VI entretien'), true);
assert.equal(isOutlinedDictionaryHeading('bailly', 'Trop.'), true);
assert.equal(isOutlinedDictionaryHeading('bailly', 'parole : la parole, en general'), false);
assert.equal(isOutlinedDictionaryHeading('gaffiot', 'VI entretien'), false);

assert.deepEqual(
	extractSourceOutlineSegments({
		tool: 'bailly',
		rawWitnesses: [
			{
				evidence: {
					source_segments: [
						{
							display_text: 'parole :',
							source_ref: 'bailly:bailly-p1450-c1-0024:01',
							source_level: 1,
							source_marker: 'A',
							source_path: '01'
						},
						{
							display_text: 'discours, entretien',
							source_ref: 'bailly:bailly-p1450-c1-0024:01:00',
							source_level: 2,
							source_marker: '1'
						}
					]
				}
			}
		],
		entries: []
	}),
	[
		{
			sourceRef: 'bailly:bailly-p1450-c1-0024:01',
			text: 'parole :',
			marker: 'A',
			level: 1,
			path: '01',
			parentPath: ''
		},
		{
			sourceRef: 'bailly:bailly-p1450-c1-0024:01:00',
			text: 'discours, entretien',
			marker: '1',
			level: 2,
			path: '',
			parentPath: ''
		}
	]
);

assert.deepEqual(
	extractSourceOutlineSegments({
		tool: 'gaffiot',
		rawWitnesses: [{ evidence: { source_segments: [{ display_text: 'A', source_ref: 'x:00' }] } }],
		entries: []
	}),
	[]
);

assert.deepEqual(
	extractSourceOutlineSegments({
		tool: 'bailly',
		rawWitnesses: [
			{
				evidence: {
					translated_blocks: [
						{
							path: '01',
							level: 1,
							marker: 'A',
							source_ref: 'bailly:bailly-p1450-c1-0024:01',
							source_text: 'parole :',
							text: 'speech:'
						},
						{
							path: '01:00',
							level: 2,
							marker: '1',
							source_ref: 'bailly:bailly-p1450-c1-0024:01:00',
							source_text: 'discours, entretien',
							text: 'discourse, conversation'
						}
					]
				}
			}
		],
		entries: []
	}),
	[
		{
			sourceRef: 'bailly:bailly-p1450-c1-0024:01',
			text: 'parole :',
			translatedText: 'speech:',
			marker: 'A',
			level: 1,
			path: '01',
			parentPath: ''
		},
		{
			sourceRef: 'bailly:bailly-p1450-c1-0024:01:00',
			text: 'discours, entretien',
			translatedText: 'discourse, conversation',
			marker: '1',
			level: 2,
			path: '01:00',
			parentPath: ''
		}
	]
);
