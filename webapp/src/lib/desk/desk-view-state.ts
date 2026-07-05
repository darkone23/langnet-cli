import type {
	EncounterBucket,
	EncounterComponent,
	EncounterComponentMeaning
} from '../search-data';
import type { BucketGroup } from './desk-entry';
import { componentMeaningKey, sectionExpansionKey } from './desk-entry';

type ExpansionState = Record<string, boolean>;
type TextLayerState = Record<string, 'reader' | 'source'>;

export function nextSectionExpansionState(state: ExpansionState, bucket: EncounterBucket) {
	const key = sectionExpansionKey(bucket);
	return {
		...state,
		[key]: !state[key]
	};
}

export function nextBranchCollapseState(state: ExpansionState, bucket: EncounterBucket) {
	const key = sectionExpansionKey(bucket);
	return {
		...state,
		[key]: !state[key]
	};
}

export function nextComponentMeaningExpansionState(
	state: ExpansionState,
	meaning: EncounterComponentMeaning
) {
	const key = componentMeaningKey(meaning);
	return {
		...state,
		[key]: !state[key]
	};
}

export function nextComponentTextLayerState(
	state: TextLayerState,
	component: EncounterComponent,
	layer: 'reader' | 'source'
) {
	return {
		...state,
		...Object.fromEntries(
			component.evidence.meanings.map((meaning) => [componentMeaningKey(meaning), layer])
		)
	};
}

export function nextGroupTextLayerState(
	state: TextLayerState,
	group: BucketGroup,
	layer: 'reader' | 'source'
) {
	return {
		...state,
		...Object.fromEntries(group.buckets.map((bucket) => [bucket.bucket_id, layer]))
	};
}
