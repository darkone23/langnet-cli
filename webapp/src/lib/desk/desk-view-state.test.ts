import assert from 'node:assert/strict';

import {
	nextBranchCollapseState,
	nextComponentMeaningExpansionState,
	nextComponentTextLayerState,
	nextGroupTextLayerState,
	nextSectionExpansionState
} from './desk-view-state';

const bucket = {
	bucket_id: 'bucket-1',
	source_refs: ['bailly:source-a'],
	source_tools: ['bailly'],
	witnesses: [],
	bucket_lemmas: [],
	learner_quality_order: 0
} as any;
const group = {
	buckets: [
		bucket,
		{
			bucket_id: 'bucket-2',
			source_refs: ['diogenes:source-b'],
			source_tools: ['diogenes'],
			witnesses: [],
			bucket_lemmas: [],
			learner_quality_order: 0
		}
	]
} as any;
const meaning = {
	bucket_id: 'component-bucket',
	source_refs: ['component-source'],
	source_tools: ['bailly']
} as any;
const component = {
	evidence: {
		meanings: [
			meaning,
			{ bucket_id: 'component-bucket-2', source_refs: ['source-2'], source_tools: ['diogenes'] }
		]
	}
} as any;

assert.deepEqual(nextSectionExpansionState({}, bucket), { 'bucket-1:bailly:source-a': true });
assert.deepEqual(nextSectionExpansionState({ 'bucket-1:bailly:source-a': true }, bucket), {
	'bucket-1:bailly:source-a': false
});
assert.deepEqual(nextBranchCollapseState({}, bucket), { 'bucket-1:bailly:source-a': true });
assert.deepEqual(nextComponentMeaningExpansionState({}, meaning), {
	'component:component-bucket:component-source': true
});
assert.deepEqual(nextComponentTextLayerState({}, component, 'source'), {
	'component:component-bucket:component-source': 'source',
	'component:component-bucket-2:source-2': 'source'
});
assert.deepEqual(nextGroupTextLayerState({}, group, 'reader'), {
	'bucket-1': 'reader',
	'bucket-2': 'reader'
});

console.log('desk view state checks complete');
