import assert from 'node:assert/strict';
import type { EncounterBucket, EncounterComponentMeaning } from '../search-data';
import {
	activeGloss,
	componentMeaningKey,
	componentMeaningSegments,
	countLabel,
	groupBuckets,
	groupLayerIsSource,
	sectionExpansionKey,
	sectionSegments,
	toolMeta,
	translationModelLabel
} from './desk-entry';

function bucket(partial: Partial<EncounterBucket>): EncounterBucket {
	return {
		bucket_id: partial.bucket_id ?? 'bucket:1',
		display_gloss: partial.display_gloss ?? 'plain gloss',
		normalized_gloss: partial.normalized_gloss ?? 'plain gloss',
		bucket_lemmas: partial.bucket_lemmas ?? [],
		source_tools: partial.source_tools ?? ['dico'],
		source_refs: partial.source_refs ?? ['dico:2'],
		reasons: partial.reasons ?? [],
		witnesses: partial.witnesses ?? [],
		witness_count: partial.witness_count ?? 1,
		preferred_lemma_rank: partial.preferred_lemma_rank ?? 0,
		effective_preferred_lemma_rank: partial.effective_preferred_lemma_rank ?? 0,
		learner_quality_order: partial.learner_quality_order ?? 0,
		has_english_translation: partial.has_english_translation ?? false,
		has_source_translation: partial.has_source_translation ?? false,
		source_langs: partial.source_langs ?? ['fr'],
		reader_lang: 'en',
		evidence_note: partial.evidence_note ?? 'source detail',
		translation_note: partial.translation_note ?? '',
		translation: partial.translation
	};
}

const grouped = groupBuckets(
	[
		bucket({
			bucket_id: 'later',
			bucket_lemmas: ['jyotis'],
			source_refs: ['dico:10'],
			witnesses: [
				{ tool: 'dico', label: 'DICO', detail: '', dictionary: 'dico', headword: 'jyotis' }
			]
		}),
		bucket({
			bucket_id: 'earlier',
			bucket_lemmas: ['jyotis'],
			source_refs: ['dico:2'],
			witnesses: [
				{ tool: 'dico', label: 'DICO', detail: '', dictionary: 'dico', headword: 'jyotis' }
			]
		})
	],
	'jyotin'
);

assert.equal(grouped.length, 1);
assert.equal(grouped[0].lexeme, 'jyotis');
assert.deepEqual(
	grouped[0].buckets.map((item) => item.bucket_id),
	['earlier', 'later'],
	'entry buckets should preserve source-reference reading order inside a grouped lexeme'
);

const translatedBucket = bucket({
	bucket_id: 'dico-reader',
	display_gloss: 'reader gloss_2...',
	evidence_note: 'examples: full source gloss_9 with additional material beyond the reader layer',
	source_tools: ['dico'],
	source_refs: ['dico:1'],
	translation: {
		available: true,
		source_tool: 'dico',
		source_lang: 'fr',
		source_label: 'DICO FR',
		source_text: 'source gloss_9',
		target_lang: 'en',
		target_text: 'reader gloss_2...'
	}
});

assert.equal(activeGloss(translatedBucket), 'reader gloss...');
assert.equal(
	activeGloss(translatedBucket, { [translatedBucket.bucket_id]: 'source' }),
	'source gloss'
);

const truncatedSourceBucket = bucket({
	bucket_id: 'dico-source',
	display_gloss: 'short gloss...',
	evidence_note: 'examples: full source gloss_9 with additional material beyond the reader layer',
	source_tools: ['dico'],
	source_refs: ['dico:3']
});

assert.equal(
	sectionSegments(
		truncatedSourceBucket,
		{},
		{ [sectionExpansionKey(truncatedSourceBucket)]: true }
	)[0],
	'full source gloss with additional material beyond the reader layer'
);

assert.equal(groupLayerIsSource(grouped[0], { earlier: 'source' }), true);
assert.equal(countLabel(2, 'section'), '2 sections');
assert.equal(toolMeta('dico', 'san').shortLabel, 'DICO');
assert.equal(translationModelLabel('openai:google/gemini-2.5-flash'), 'Gemini 2.5 Flash');

const meaning: EncounterComponentMeaning = {
	bucket_id: 'member',
	display_gloss: 'a long member gloss with source suffix_4',
	source_tools: ['dico'],
	source_refs: ['dico:member:1'],
	source_langs: ['fr'],
	translation: {
		available: true,
		source_tool: 'dico',
		source_lang: 'fr',
		source_label: 'DICO FR',
		source_text: 'source member gloss_4',
		target_lang: 'en',
		target_text: 'reader member gloss_4',
		model: 'openai:google/gemini-2.5-flash'
	}
};

assert.equal(componentMeaningKey(meaning), 'component:member:dico:member:1');
assert.deepEqual(componentMeaningSegments(meaning), ['reader member gloss']);
assert.deepEqual(componentMeaningSegments(meaning, { [componentMeaningKey(meaning)]: 'source' }), [
	'source member gloss'
]);
