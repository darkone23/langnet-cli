import {
	branchToggleLabel as branchToggleLabelForState,
	componentAwaitsReaderTranslation as componentAwaitsReaderTranslationForState,
	componentCanSwitchTextLayer,
	componentHasTranslationToggle,
	componentHeadwordDisplay as componentHeadwordDisplayForLanguage,
	componentLayerIsSource,
	componentLookupLine,
	componentMeaningCanToggle,
	componentMeaningKey,
	componentMeaningSegments,
	componentMeaningSourceLabel,
	componentMeaningToggleLabel,
	componentPrimaryTool,
	componentSourceLayerLabel,
	componentToolIds,
	componentTranslationModel,
	countLabel,
	groupAwaitsReaderTranslation as groupAwaitsReaderTranslationForState,
	groupCanSwitchTextLayer,
	groupHasReaderTranslation,
	groupHasTranslationToggle,
	groupHeadwordDisplay as groupHeadwordDisplayForLanguage,
	groupLayerIsSource,
	groupLead,
	groupSourceLayerLabel,
	groupToolIds,
	groupTranslationModel,
	groupTranslationRetrying as groupTranslationRetryingForState,
	groupWitnesses,
	readerEntryLabel,
	readerSectionClass,
	readerSectionStyle,
	retryableGroupTranslation,
	sectionCanToggle,
	sectionExpansionKey,
	sectionHasTreeChildren,
	sectionId,
	sectionSegments,
	sectionShowsReturnedEndingNote,
	sectionToggleLabel,
	toolMeta,
	toolMnemonic,
	translationModelLabel,
	visibleGroupBuckets as visibleGroupBucketsForState,
	type BucketGroup
} from '$lib/desk/desk-entry';
import type {
	EncounterComponent,
	EncounterComponentMeaning,
	EncounterBucket,
	EncounterWordIndexAnchor,
	LanguageMode
} from '$lib/search-data';

type EntryHelpersState = {
	language: LanguageMode;
	encounter: { language?: LanguageMode; word_index?: { anchors?: EncounterWordIndexAnchor[] } } | null;
	enrichingTranslations: boolean;
	translationRetrying: Record<string, boolean>;
	collapsedBranches: Record<string, boolean>;
};

type EntryHelpersActions = {
	setComponentTextLayer: (
		component: EncounterComponent,
		layer: 'reader' | 'source'
	) => void;
	toggleComponentMeaning: (meaning: EncounterComponentMeaning) => void;
	setGroupTextLayer: (group: BucketGroup, layer: 'reader' | 'source') => void;
	retryGroupTranslation: (group: BucketGroup) => Promise<void>;
	toggleSectionExpansion: (bucket: EncounterBucket) => void;
	toggleBranchCollapse: (bucket: EncounterBucket) => void;
};

export function createDeskEntryHelpers(
	state: EntryHelpersState,
	actions: EntryHelpersActions
) {
	const { language, encounter, enrichingTranslations, translationRetrying, collapsedBranches } =
		state;

	const componentLedgerHelpers = {
		countLabel,
		componentPrimaryTool,
		componentToolIds,
		componentHeadwordDisplay: (component: EncounterComponent) =>
			componentHeadwordDisplayForLanguage(component, encounter?.language ?? language),
		componentLookupLine,
		componentCanSwitchTextLayer,
		componentLayerIsSource,
		setComponentTextLayer: actions.setComponentTextLayer,
		componentSourceLayerLabel,
		componentHasTranslationToggle,
		componentAwaitsReaderTranslation: (component: EncounterComponent) =>
			componentAwaitsReaderTranslationForState(component, enrichingTranslations),
		componentTranslationModel,
		componentMeaningSegments,
		componentMeaningCanToggle,
		componentMeaningToggleLabel,
		componentMeaningKey,
		componentMeaningSourceLabel,
		toggleComponentMeaning: actions.toggleComponentMeaning,
		toolMeta,
		toolMnemonic,
		translationModelLabel
	};

	const dictionaryGroupHelpers = {
		countLabel,
		groupHeadwordDisplay: (group: BucketGroup) =>
			groupHeadwordDisplayForLanguage(
				group,
				encounter?.language ?? language,
				encounter?.word_index?.anchors ?? []
			),
		groupLead,
		groupToolIds,
		groupWitnesses,
		readerEntryLabel,
		groupCanSwitchTextLayer,
		groupLayerIsSource,
		groupHasReaderTranslation,
		setGroupTextLayer: actions.setGroupTextLayer,
		groupSourceLayerLabel,
		groupTranslationModel,
		groupHasTranslationToggle,
		groupAwaitsReaderTranslation: (group: BucketGroup) =>
			groupAwaitsReaderTranslationForState(group, enrichingTranslations),
		retryableGroupTranslation,
		groupTranslationRetrying: (group: BucketGroup) =>
			groupTranslationRetryingForState(group, translationRetrying),
		retryGroupTranslation: actions.retryGroupTranslation,
		visibleGroupBuckets: (group: BucketGroup) =>
			visibleGroupBucketsForState(group, collapsedBranches),
		sectionSegments,
		sectionHasTreeChildren,
		sectionId,
		readerSectionClass,
		readerSectionStyle,
		branchToggleLabel: (bucket: EncounterBucket) =>
			branchToggleLabelForState(bucket, collapsedBranches),
		toggleBranchCollapse: actions.toggleBranchCollapse,
		sectionExpansionKey,
		sectionCanToggle,
		sectionToggleLabel,
		toggleSectionExpansion: actions.toggleSectionExpansion,
		sectionShowsReturnedEndingNote,
		toolMeta,
		toolMnemonic,
		translationModelLabel
	};

	return { componentLedgerHelpers, dictionaryGroupHelpers };
}
